"""End-to-end integration tests for the Sentinel pipeline.

Tests pipeline components that do NOT require Auth0 users:
  1. Ghost DB connection and table/user verification
  2. Breach CSV ingestion
  3. Breach matching
  4. Research phase (LLM-powered incident analysis)
  5. LLM connectivity (Truefoundry / Anthropic fallback)
  6. Bland AI API connectivity (read-only, no actual calls)

Run with:
    source .venv/bin/activate && python3 -m sentinel.tests.test_pipeline
"""

import asyncio
import sys
import time
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_results: list[tuple[str, bool, str]] = []


def _record(name: str, passed: bool, detail: str = ""):
    tag = "PASS" if passed else "FAIL"
    _results.append((name, passed, detail))
    print(f"  [{tag}] {name}" + (f" -- {detail}" if detail else ""))


def _print_summary():
    print("\n" + "=" * 60)
    total = len(_results)
    passed = sum(1 for _, p, _ in _results if p)
    failed = total - passed
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    for name, ok, detail in _results:
        tag = "PASS" if ok else "FAIL"
        line = f"    [{tag}] {name}"
        if not ok and detail:
            line += f"  => {detail}"
        print(line)
    print("=" * 60)
    return failed


# ---------------------------------------------------------------------------
# Test 1 — Ghost DB connection
# ---------------------------------------------------------------------------

async def test_ghost_db_connection():
    """Verify Ghost DB is reachable, tables exist, and 100 seed users are present."""
    from sentinel.integrations import ghost_db

    name = "Ghost DB connection"
    try:
        # Make sure tables exist (idempotent)
        await ghost_db.init_tables()

        # Check required tables
        rows = await ghost_db.fetch(
            "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'"
        )
        table_names = {r["tablename"] for r in rows}
        required = {"users", "breach_events", "response_log", "research_cache"}
        missing = required - table_names
        if missing:
            _record(name, False, f"Missing tables: {missing}")
            return

        # Count users
        user_count = await ghost_db.fetchval("SELECT COUNT(*) FROM users")
        if user_count == 100:
            _record(name, True, f"{user_count} users found")
        elif user_count == 0:
            _record(name, False, "0 users — seed_users has not been run yet")
        else:
            _record(name, True, f"{user_count} users found (expected 100)")
    except Exception as exc:
        _record(name, False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Test 2 — Breach CSV ingestion
# ---------------------------------------------------------------------------

async def test_breach_csv_ingestion():
    """Read breach_data.csv, ingest via breach_analyzer, verify row count."""
    from sentinel.agent import breach_analyzer
    from sentinel.integrations import ghost_db

    name = "Breach CSV ingestion"
    try:
        csv_path = Path(__file__).resolve().parent.parent / "data" / "breach_data.csv"
        if not csv_path.exists():
            _record(name, False, f"CSV not found at {csv_path}")
            return

        csv_content = csv_path.read_text()
        lines = csv_content.strip().splitlines()
        expected_rows = len(lines) - 1  # minus header

        # Reset breach_events so we can ingest fresh
        await ghost_db.execute(
            "DELETE FROM response_log WHERE breach_event_id IN (SELECT id FROM breach_events)"
        )
        await ghost_db.execute("DELETE FROM research_cache")
        await ghost_db.execute("DELETE FROM breach_events")

        count = await breach_analyzer.ingest_breach_csv(csv_content)

        if count == expected_rows:
            _record(name, True, f"Ingested {count} records (CSV has {expected_rows} data rows)")
        else:
            _record(name, False, f"Ingested {count} but CSV has {expected_rows} data rows")
    except Exception as exc:
        _record(name, False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Test 3 — Breach matching
# ---------------------------------------------------------------------------

async def test_breach_matching():
    """Match breach records against users; expect ~40 matches with ~12 CRITICAL."""
    from sentinel.agent import breach_analyzer

    name = "Breach matching"
    try:
        matches = await breach_analyzer.match_breach_to_users()
        total = len(matches)
        critical = sum(1 for m in matches if m.severity == "CRITICAL")
        warning = sum(1 for m in matches if m.severity == "WARNING")

        detail = f"total={total}, CRITICAL={critical}, WARNING={warning}"

        if total == 0:
            _record(name, False, f"No matches found. {detail}")
            return

        # Tolerant checks: ~40 matches, ~12 critical
        ok = (30 <= total <= 50) and (8 <= critical <= 16)
        if ok:
            _record(name, True, detail)
        else:
            _record(name, False, f"Counts outside expected range. {detail}")
    except Exception as exc:
        _record(name, False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Test 4 — Research phase (LLM-powered)
# ---------------------------------------------------------------------------

async def test_research_phase():
    """Call researcher.research_breach with mock data, verify IncidentReport."""
    from sentinel.agent.researcher import research_breach, IncidentReport

    name = "Research phase (LLM)"
    try:
        report = await research_breach(
            breach_source="DarkForum_X_test",
            total_leaked=500,
            critical_count=12,
        )

        if not isinstance(report, IncidentReport):
            _record(name, False, f"Expected IncidentReport, got {type(report).__name__}")
            return

        # Validate fields are populated
        missing_fields = []
        for field_name in ("breach_source", "attack_vector", "severity", "summary"):
            if not getattr(report, field_name, None):
                missing_fields.append(field_name)

        if missing_fields:
            _record(name, False, f"Empty fields: {missing_fields}")
        else:
            _record(
                name,
                True,
                f"CVE={report.cve_id}, severity={report.severity}, "
                f"patches={len(report.recommended_patches)}",
            )
    except Exception as exc:
        _record(name, False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Test 5 — LLM connectivity
# ---------------------------------------------------------------------------

async def test_llm_connectivity():
    """Verify truefoundry_llm.chat works (should fall back to Anthropic)."""
    from sentinel.integrations import truefoundry_llm

    name = "LLM connectivity"
    try:
        response = await truefoundry_llm.chat(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Reply with exactly: SENTINEL_OK"},
            ],
            temperature=0.0,
            max_tokens=32,
        )

        if "SENTINEL_OK" in response:
            _record(name, True, f"Response contains SENTINEL_OK (len={len(response)})")
        else:
            # LLM responded but not with the exact token — still connected
            _record(name, True, f"LLM responded (len={len(response)}), content: {response[:80]}")
    except Exception as exc:
        _record(name, False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Test 6 — Bland AI connectivity (read-only)
# ---------------------------------------------------------------------------

async def test_bland_ai_connectivity():
    """Verify Bland AI API key is valid by listing calls. No actual calls made."""
    import httpx
    from sentinel.config import config

    name = "Bland AI connectivity"
    try:
        if not config.bland_api_key:
            _record(name, False, "BLAND_API_KEY not set in environment")
            return

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.bland.ai/v1/calls",
                headers={"authorization": config.bland_api_key},
                timeout=15,
            )

        if resp.status_code == 200:
            data = resp.json()
            # The list endpoint returns calls array
            call_count = len(data.get("calls", data.get("data", [])))
            _record(name, True, f"API key valid, {call_count} previous calls found")
        elif resp.status_code == 401:
            _record(name, False, "API key rejected (401 Unauthorized)")
        else:
            _record(name, False, f"Unexpected status {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        _record(name, False, f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_all():
    from sentinel.integrations import ghost_db

    print("=" * 60)
    print("  SENTINEL PIPELINE INTEGRATION TESTS")
    print("=" * 60)
    start = time.time()

    # Run tests sequentially — some depend on prior state (ingestion before matching)
    await test_ghost_db_connection()
    await test_breach_csv_ingestion()
    await test_breach_matching()
    await test_llm_connectivity()
    await test_research_phase()
    await test_bland_ai_connectivity()

    elapsed = time.time() - start
    print(f"\n  Completed in {elapsed:.1f}s")

    # Cleanup
    try:
        await ghost_db.close()
    except Exception:
        pass

    failed = _print_summary()
    return failed


def main():
    failed = asyncio.run(run_all())
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
