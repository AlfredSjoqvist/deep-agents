"""Main agent orchestrator — runs the full Sentinel breach response pipeline."""

import asyncio
import time
import uuid
from dataclasses import asdict
from pathlib import Path

import structlog

from sentinel.agent import breach_analyzer, researcher, responder
from sentinel.integrations import ghost_db, overmind_tracer
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

    # Set up Queue for this run
    _event_queues[run_id] = asyncio.Queue()

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

        # ── Phase 3: Respond ──────────────────────────────────────
        await _emit(run_id, "lockdown", "Locking compromised accounts via Auth0...", phase="respond")
        lock_results = await responder.lock_compromised_accounts(matches)
        result.accounts_locked = lock_results["locked"]
        result.sessions_revoked = lock_results["sessions_revoked"]
        result.lock_failures = lock_results["failed"]

        await _emit(run_id, "lockdown", f"Locked {lock_results['locked']} accounts, revoked {lock_results['sessions_revoked']} sessions.", phase="respond", data=lock_results)

        await _emit(run_id, "notify", "Calling critical users via Bland AI...", phase="respond")
        notify_results = await responder.notify_critical_users(matches, report)
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
