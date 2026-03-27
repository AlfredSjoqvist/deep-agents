"""Sentinel entry point — run the breach response pipeline."""

import asyncio
import sys
from pathlib import Path

import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
)

from sentinel.agent.orchestrator import run_sentinel
from sentinel.integrations import ghost_db


async def main():
    log = structlog.get_logger()

    # Check for breach CSV argument
    csv_path = None
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
        if not Path(csv_path).exists():
            log.error("main.csv_not_found", path=csv_path)
            sys.exit(1)

    log.info("sentinel.starting", csv_path=csv_path or "default")
    print("\n" + "=" * 60)
    print("  SENTINEL — Autonomous Breach Response Agent")
    print("=" * 60 + "\n")

    try:
        result = await run_sentinel(
            breach_csv_path=csv_path,
            breach_source="DarkForum X",
        )

        print("\n" + "=" * 60)
        print("  SENTINEL REPORT")
        print("=" * 60)
        print(f"  Status:          {result.status}")
        print(f"  Duration:        {result.duration_seconds:.1f}s")
        print(f"  Breach Records:  {result.total_breach_records}")
        print(f"  Matches Found:   {result.total_matches}")
        print(f"    CRITICAL:      {result.critical_count}")
        print(f"    WARNING:       {result.warning_count}")
        print(f"  Accounts Locked: {result.accounts_locked}")
        print(f"  Calls Initiated: {result.calls_initiated}")

        if result.incident_report:
            print(f"\n  CVE:             {result.incident_report.get('cve_id', 'N/A')}")
            print(f"  Attack Vector:   {result.incident_report.get('attack_vector', 'N/A')}")
            print(f"  Severity:        {result.incident_report.get('severity', 'N/A')}")
            patches = result.incident_report.get('recommended_patches', [])
            if patches:
                print(f"  Patches:")
                for p in patches:
                    print(f"    - {p}")

        print("=" * 60 + "\n")

    finally:
        await ghost_db.close()


if __name__ == "__main__":
    asyncio.run(main())
