"""Main agent orchestrator — runs the full Sentinel breach response pipeline."""

import asyncio
import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path

import structlog

from sentinel.agent import breach_analyzer, researcher, responder
from sentinel.integrations import auth0_client, bland_caller, ghost_db, overmind_tracer
from sentinel.models import PipelineEvent, SentinelResult

log = structlog.get_logger()


# ── Module-level state for run tracking ──────────────────────────────────────

_runs: dict[str, SentinelResult] = {}
_event_queues: dict[str, asyncio.Queue] = {}

# Backward-compatible global state (used by dashboard/main.py)
_current_result: SentinelResult | None = None
_events: list[dict] = []


# ── Public accessors ─────────────────────────────────────────────────────────

def get_current_result() -> SentinelResult | None:
    """Return the most recent SentinelResult (backward compat)."""
    return _current_result


def get_events() -> list[dict]:
    """Return all events from the current/most recent run (backward compat)."""
    return list(_events)


def get_event_queue(run_id: str) -> asyncio.Queue | None:
    """Return the asyncio.Queue for a given run, or None if not found."""
    return _event_queues.get(run_id)


def ensure_event_queue(run_id: str) -> asyncio.Queue:
    """Create and return the event Queue for *run_id* if it doesn't exist yet.

    This allows the server to pre-create the Queue before launching the
    pipeline background task, avoiding a race where the SSE endpoint
    connects before run_sentinel() has a chance to set it up.
    """
    if run_id not in _event_queues:
        _event_queues[run_id] = asyncio.Queue()
    return _event_queues[run_id]


def get_run(run_id: str) -> SentinelResult | None:
    """Return the SentinelResult for a given run_id, or None."""
    return _runs.get(run_id)


# ── Internal helpers ─────────────────────────────────────────────────────────

async def _emit(run_id: str, event_type: str, message: str, phase: str = "", data: dict | None = None):
    """Emit a PipelineEvent to the run's queue and the legacy event list."""
    evt = PipelineEvent(
        type=event_type,
        message=message,
        timestamp=time.time(),
        data=data or {},
        phase=phase,
    )

    # Push to asyncio.Queue for SSE streaming
    if run_id in _event_queues:
        await _event_queues[run_id].put(evt)

    # Also append to the legacy flat list for backward compat
    _events.append(evt.model_dump())

    log.info(f"sentinel.{event_type}", message=message, **(data or {}))


# ── Concurrent response helpers ──────────────────────────────────────────────


async def _lock_one(match) -> dict:
    """Lock a single compromised account via Auth0 + update Ghost DB.

    Returns a result dict with keys: locked, sessions_revoked, failed, skipped.
    """
    result = {"locked": 0, "sessions_revoked": 0, "failed": 0, "skipped": 0}

    if match.severity not in ("CRITICAL", "WARNING"):
        result["skipped"] = 1
        return result

    if not match.auth0_user_id:
        log.warning("orchestrator.no_auth0_id", email=match.email)
        result["skipped"] = 1
        return result

    try:
        await auth0_client.block_user(match.auth0_user_id)
        result["locked"] = 1

        revoked = await auth0_client.revoke_sessions(match.auth0_user_id)
        if revoked:
            result["sessions_revoked"] = 1

        await ghost_db.execute(
            "UPDATE users SET status = 'locked' WHERE id = $1",
            match.user_id,
        )
        await ghost_db.execute(
            """INSERT INTO response_log (breach_event_id, user_id, action, details)
               VALUES ($1, $2, $3, $4)""",
            match.breach_event_id,
            match.user_id,
            "account_locked",
            json.dumps({
                "auth0_user_id": match.auth0_user_id,
                "severity": match.severity,
                "sessions_revoked": revoked,
            }),
        )
    except Exception as e:
        log.error("orchestrator.lock_failed", email=match.email, error=str(e))
        result["failed"] = 1
        try:
            await ghost_db.execute(
                """INSERT INTO response_log (breach_event_id, user_id, action, details, status)
                   VALUES ($1, $2, $3, $4, $5)""",
                match.breach_event_id,
                match.user_id,
                "account_lock_failed",
                json.dumps({"error": str(e)}),
                "failed",
            )
        except Exception:
            log.exception("orchestrator.lock_log_failed", email=match.email)

    return result


async def _lock_accounts_concurrent(matches: list) -> dict:
    """Lock all compromised accounts concurrently via asyncio.gather."""
    individual_results = await asyncio.gather(
        *[_lock_one(m) for m in matches],
        return_exceptions=True,
    )

    totals = {"locked": 0, "sessions_revoked": 0, "failed": 0, "skipped": 0}
    for r in individual_results:
        if isinstance(r, Exception):
            log.error("orchestrator.lock_gather_exception", error=str(r))
            totals["failed"] += 1
        else:
            for key in totals:
                totals[key] += r.get(key, 0)

    log.info("orchestrator.accounts_locked", **totals)
    return totals


async def _call_one(match, report) -> dict:
    """Call a single critical user via Bland AI + log to Ghost DB.

    Returns a result dict with keys: calls_initiated, failed, skipped, call_id.
    """
    result = {"calls_initiated": 0, "failed": 0, "skipped": 0, "call_id": None}

    if not match.phone:
        log.warning("orchestrator.no_phone", email=match.email)
        result["skipped"] = 1
        return result

    try:
        call_result = await bland_caller.call_user(
            phone_number=match.phone,
            user_name=match.user_name,
            breach_details=f"a data breach from {report.breach_source} involving {report.cve_id}",
        )
        call_id = call_result.get("call_id", "unknown")
        result["calls_initiated"] = 1
        result["call_id"] = call_id

        await ghost_db.execute(
            """INSERT INTO response_log (breach_event_id, user_id, action, details)
               VALUES ($1, $2, $3, $4)""",
            match.breach_event_id,
            match.user_id,
            "phone_notification",
            json.dumps({"call_id": call_id, "phone": match.phone}),
        )
    except Exception as e:
        log.error("orchestrator.call_failed", email=match.email, error=str(e))
        result["failed"] = 1

    return result


async def _notify_users_concurrent(matches: list, report) -> dict:
    """Call all critical users concurrently via asyncio.gather."""
    critical_matches = [m for m in matches if m.severity == "CRITICAL"]

    if not critical_matches:
        return {"calls_initiated": 0, "failed": 0, "skipped": 0, "call_ids": []}

    individual_results = await asyncio.gather(
        *[_call_one(m, report) for m in critical_matches],
        return_exceptions=True,
    )

    totals = {"calls_initiated": 0, "failed": 0, "skipped": 0}
    call_ids = []
    for r in individual_results:
        if isinstance(r, Exception):
            log.error("orchestrator.call_gather_exception", error=str(r))
            totals["failed"] += 1
        else:
            totals["calls_initiated"] += r.get("calls_initiated", 0)
            totals["failed"] += r.get("failed", 0)
            totals["skipped"] += r.get("skipped", 0)
            if r.get("call_id"):
                call_ids.append(r["call_id"])

    totals["call_ids"] = call_ids
    log.info("orchestrator.notifications_sent", **totals)
    return totals


# ── Main pipeline ────────────────────────────────────────────────────────────

async def run_sentinel(
    breach_csv_path: str | None = None,
    breach_csv_content: str | None = None,
    breach_source: str = "DarkForum X",
    run_id: str | None = None,
) -> SentinelResult:
    """Run the complete Sentinel breach response pipeline.

    Args:
        breach_csv_path: Path to a breach CSV file on disk.
        breach_csv_content: Raw CSV content (takes precedence over path).
        breach_source: Human-readable name of the breach source.
        run_id: Optional run identifier. Generated if not provided.

    Returns:
        SentinelResult with full pipeline outcomes.
    """
    global _current_result, _events

    # Generate run_id if not provided
    if run_id is None:
        run_id = str(uuid.uuid4())

    # Reset legacy event list
    _events = []

    # Ensure Queue exists for this run (may already be pre-created by the server)
    ensure_event_queue(run_id)

    result = SentinelResult(run_id=run_id, status="running", start_time=time.time())
    _runs[run_id] = result
    _current_result = result

    # Initialize tracing
    overmind_tracer.init_tracing()

    try:
        # ── Phase 0: Setup ────────────────────────────────────────
        await _emit(run_id, "setup", "Initializing Ghost DB tables...", phase="setup")
        await ghost_db.init_tables()
        await _emit(run_id, "setup", "Database ready.", phase="setup")

        # ── Phase 1: Ingest & Match ────────────────────────────────
        await _emit(run_id, "ingest", "Ingesting breach data...", phase="ingest")

        if breach_csv_content is None:
            if breach_csv_path is None:
                breach_csv_path = str(Path(__file__).parent.parent / "data" / "breach_data.csv")
            breach_csv_content = Path(breach_csv_path).read_text()

        count = await breach_analyzer.ingest_breach_csv(breach_csv_content)
        result.total_breach_records = count
        await _emit(run_id, "ingest", f"Ingested {count} breach records into Ghost DB.", phase="ingest", data={"count": count})

        await _emit(run_id, "matching", "Cross-referencing breach emails against user database...", phase="ingest")
        matches = await breach_analyzer.match_breach_to_users()
        result.total_matches = len(matches)
        result.critical_count = sum(1 for m in matches if m.severity == "CRITICAL")
        result.warning_count = sum(1 for m in matches if m.severity == "WARNING")

        await _emit(run_id, "matching", f"Found {len(matches)} matches: {result.critical_count} CRITICAL, {result.warning_count} WARNING", phase="ingest", data={
            "total": len(matches),
            "critical": result.critical_count,
            "warning": result.warning_count,
        })

        if not matches:
            await _emit(run_id, "complete", "No matching users found. Pipeline complete.", phase="ingest")
            result.status = "complete_no_matches"
            result.end_time = time.time()
            result.duration_seconds = result.end_time - result.start_time
            _runs[run_id] = result
            # Signal end-of-stream
            await _event_queues[run_id].put(None)
            return result

        # ── Phase 2: Research ──────────────────────────────────────
        await _emit(run_id, "research", f"Researching attack vector for breach source: {breach_source}...", phase="research")

        report = await researcher.research_breach(
            breach_source=breach_source,
            total_leaked=count,
            critical_count=result.critical_count,
        )
        result.incident_report = asdict(report)
        result.incident_type = getattr(report, "incident_type", "unknown")

        await _emit(run_id, "research", f"Research complete. CVE: {report.cve_id}, Severity: {report.severity}", phase="research", data={
            "cve_id": report.cve_id,
            "attack_vector": report.attack_vector,
            "severity": report.severity,
            "incident_type": result.incident_type,
        })

        # ── Phase 2b: Compliance Analysis ─────────────────────────
        try:
            from sentinel.agent.compliance import analyze_compliance

            data_classes = getattr(report, "data_classes_exposed", None) or ["credentials", "PII"]
            incident_type_str = getattr(report, "incident_type", "unknown")
            compliance_result = analyze_compliance(
                data_classes=data_classes,
                incident_type=incident_type_str,
                record_count=count,
            )
            result.incident_report["compliance"] = compliance_result

            # Build a human-readable compliance summary for the event
            frameworks = [
                fw["framework"]
                for fw in compliance_result.get("applicable_frameworks", [])
            ]
            deadlines = [
                f"{fw['framework']} ({fw['notification_deadline']})"
                for fw in compliance_result.get("applicable_frameworks", [])
                if fw.get("notification_deadline")
            ]
            compliance_summary = {
                "frameworks_triggered": frameworks,
                "overall_risk": compliance_result.get("overall_risk", "UNKNOWN"),
                "most_urgent_deadline": compliance_result.get("most_urgent_deadline", "N/A"),
                "total_frameworks": compliance_result.get("total_frameworks_triggered", 0),
                "deadlines": deadlines,
            }

            deadline_parts = []
            if "GDPR" in frameworks:
                deadline_parts.append("GDPR (72h)")
            if "CCPA" in frameworks:
                deadline_parts.append("CCPA triggered")
            if "HIPAA" in frameworks:
                deadline_parts.append("HIPAA triggered")
            if "PCI_DSS" in frameworks:
                deadline_parts.append("PCI-DSS (24h)")
            compliance_msg = ", ".join(deadline_parts) if deadline_parts else "No frameworks triggered"

            await _emit(
                run_id,
                "compliance",
                f"Compliance analysis: {compliance_msg}",
                phase="research",
                data=compliance_summary,
            )
        except Exception as e:
            log.warning("orchestrator.compliance_failed", error=str(e))
            await _emit(
                run_id,
                "compliance",
                f"Compliance analysis failed: {e}",
                phase="research",
                data={"error": str(e)},
            )

        # ── Phase 3: Respond ──────────────────────────────────────
        await _emit(run_id, "lockdown", "Locking compromised accounts via Auth0...", phase="respond")
        lock_results = await _lock_accounts_concurrent(matches)
        result.accounts_locked = lock_results["locked"]
        result.sessions_revoked = lock_results["sessions_revoked"]
        result.lock_failures = lock_results["failed"]

        await _emit(run_id, "lockdown", f"Locked {lock_results['locked']} accounts, revoked {lock_results['sessions_revoked']} sessions.", phase="respond", data=lock_results)

        await _emit(run_id, "notify", "Calling critical users via Bland AI...", phase="respond")
        notify_results = await _notify_users_concurrent(matches, report)
        result.calls_initiated = notify_results["calls_initiated"]
        result.call_failures = notify_results["failed"]

        await _emit(run_id, "notify", f"Initiated {notify_results['calls_initiated']} phone calls.", phase="respond", data=notify_results)

        # ── Complete ──────────────────────────────────────────────
        result.status = "complete"
        result.end_time = time.time()
        result.duration_seconds = result.end_time - result.start_time

        await _emit(run_id, "complete", f"Sentinel complete in {result.duration_seconds:.1f}s. "
              f"{result.accounts_locked} locked, {result.calls_initiated} called.", phase="respond", data=result.model_dump())

    except Exception as e:
        result.status = "error"
        result.end_time = time.time()
        result.duration_seconds = result.end_time - result.start_time
        await _emit(run_id, "error", f"Pipeline error: {e}", phase="", data={"error": str(e)})
        log.exception("sentinel.pipeline_error")

    finally:
        _runs[run_id] = result
        _current_result = result
        # Signal end-of-stream to any SSE consumer
        if run_id in _event_queues:
            await _event_queues[run_id].put(None)

    return result
