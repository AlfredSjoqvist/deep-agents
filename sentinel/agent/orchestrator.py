"""Main agent orchestrator — runs the full Sentinel breach response pipeline."""

import asyncio
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import structlog

from sentinel.agent import breach_analyzer, researcher, responder
from sentinel.integrations import ghost_db, overmind_tracer

log = structlog.get_logger()


@dataclass
class SentinelResult:
    """Complete result of a Sentinel run."""
    status: str = "pending"
    start_time: float = 0.0
    end_time: float = 0.0
    duration_seconds: float = 0.0

    # Phase 1
    total_breach_records: int = 0
    total_matches: int = 0
    critical_count: int = 0
    warning_count: int = 0

    # Phase 2
    incident_report: dict = field(default_factory=dict)

    # Phase 3
    accounts_locked: int = 0
    sessions_revoked: int = 0
    calls_initiated: int = 0
    lock_failures: int = 0
    call_failures: int = 0

    # Events for dashboard
    events: list[dict] = field(default_factory=list)


# Global state for dashboard to read
_current_result: SentinelResult | None = None
_events: list[dict] = []


def get_current_result() -> SentinelResult | None:
    return _current_result


def get_events() -> list[dict]:
    return list(_events)


def _emit(event_type: str, message: str, data: dict | None = None):
    """Emit an event for the dashboard."""
    evt = {
        "type": event_type,
        "message": message,
        "timestamp": time.time(),
        "data": data or {},
    }
    _events.append(evt)
    log.info(f"sentinel.{event_type}", message=message, **(data or {}))


async def run_sentinel(
    breach_csv_path: str | None = None,
    breach_csv_content: str | None = None,
    breach_source: str = "DarkForum X",
) -> SentinelResult:
    """Run the complete Sentinel breach response pipeline."""
    global _current_result, _events
    _events = []

    result = SentinelResult(status="running", start_time=time.time())
    _current_result = result

    # Initialize tracing
    overmind_tracer.init_tracing()

    try:
        # ── Phase 0: Setup ────────────────────────────────────────
        _emit("setup", "Initializing Ghost DB tables...")
        await ghost_db.init_tables()
        _emit("setup", "Database ready.")

        # ── Phase 1: Ingest & Match ────────────────────────────────
        _emit("ingest", "Ingesting breach data...")

        if breach_csv_content is None:
            if breach_csv_path is None:
                breach_csv_path = str(Path(__file__).parent.parent / "data" / "breach_data.csv")
            breach_csv_content = Path(breach_csv_path).read_text()

        count = await breach_analyzer.ingest_breach_csv(breach_csv_content)
        result.total_breach_records = count
        _emit("ingest", f"Ingested {count} breach records into Ghost DB.", {"count": count})

        _emit("matching", "Cross-referencing breach emails against user database...")
        matches = await breach_analyzer.match_breach_to_users()
        result.total_matches = len(matches)
        result.critical_count = sum(1 for m in matches if m.severity == "CRITICAL")
        result.warning_count = sum(1 for m in matches if m.severity == "WARNING")

        _emit("matching", f"Found {len(matches)} matches: {result.critical_count} CRITICAL, {result.warning_count} WARNING", {
            "total": len(matches),
            "critical": result.critical_count,
            "warning": result.warning_count,
        })

        if not matches:
            _emit("complete", "No matching users found. Pipeline complete.")
            result.status = "complete_no_matches"
            result.end_time = time.time()
            result.duration_seconds = result.end_time - result.start_time
            return result

        # ── Phase 2: Research ──────────────────────────────────────
        _emit("research", f"Researching attack vector for breach source: {breach_source}...")

        report = await researcher.research_breach(
            breach_source=breach_source,
            total_leaked=count,
            critical_count=result.critical_count,
        )
        result.incident_report = asdict(report)

        _emit("research", f"Research complete. CVE: {report.cve_id}, Severity: {report.severity}", {
            "cve_id": report.cve_id,
            "attack_vector": report.attack_vector,
            "severity": report.severity,
        })

        # ── Phase 3: Respond ──────────────────────────────────────
        _emit("lockdown", "Locking compromised accounts via Auth0...")
        lock_results = await responder.lock_compromised_accounts(matches)
        result.accounts_locked = lock_results["locked"]
        result.sessions_revoked = lock_results["sessions_revoked"]
        result.lock_failures = lock_results["failed"]

        _emit("lockdown", f"Locked {lock_results['locked']} accounts, revoked {lock_results['sessions_revoked']} sessions.", lock_results)

        _emit("notify", "Calling critical users via Bland AI...")
        notify_results = await responder.notify_critical_users(matches, report)
        result.calls_initiated = notify_results["calls_initiated"]
        result.call_failures = notify_results["failed"]

        _emit("notify", f"Initiated {notify_results['calls_initiated']} phone calls.", notify_results)

        # ── Complete ──────────────────────────────────────────────
        result.status = "complete"
        result.end_time = time.time()
        result.duration_seconds = result.end_time - result.start_time

        _emit("complete", f"Sentinel complete in {result.duration_seconds:.1f}s. "
              f"{result.accounts_locked} locked, {result.calls_initiated} called.", asdict(result))

    except Exception as e:
        result.status = "error"
        result.end_time = time.time()
        result.duration_seconds = result.end_time - result.start_time
        _emit("error", f"Pipeline error: {e}", {"error": str(e)})
        log.exception("sentinel.pipeline_error")

    finally:
        _current_result = result

    return result
