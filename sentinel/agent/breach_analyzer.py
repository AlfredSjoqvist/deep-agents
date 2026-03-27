"""Phase 1: Ingest breach data and match against user database."""

import csv
import io
from dataclasses import dataclass

import structlog

from sentinel.integrations import ghost_db

log = structlog.get_logger()


@dataclass
class BreachMatch:
    breach_event_id: int
    user_id: int
    email: str
    user_name: str
    phone: str | None
    auth0_user_id: str | None
    severity: str  # CRITICAL, WARNING, SAFE


async def ingest_breach_csv(csv_content: str) -> int:
    """Ingest breach CSV data into Ghost DB. Returns number of records inserted."""
    reader = csv.DictReader(io.StringIO(csv_content))
    count = 0

    for row in reader:
        await ghost_db.execute(
            """INSERT INTO breach_events (leaked_email, leaked_password_hash, source)
               VALUES ($1, $2, $3)
               ON CONFLICT DO NOTHING""",
            row["leaked_email"].strip().lower(),
            row.get("leaked_password_hash", ""),
            row.get("source", "unknown"),
        )
        count += 1

    log.info("breach.ingested", records=count)
    return count


async def match_breach_to_users() -> list[BreachMatch]:
    """Match breach emails against user database. Classify severity."""
    matches = []

    # Find all breach events that match a user email
    rows = await ghost_db.fetch("""
        SELECT
            b.id AS breach_event_id,
            b.leaked_email,
            b.leaked_password_hash,
            u.id AS user_id,
            u.name AS user_name,
            u.email,
            u.phone,
            u.auth0_user_id,
            u.password_hash AS user_password_hash
        FROM breach_events b
        JOIN users u ON LOWER(u.email) = LOWER(b.leaked_email)
        WHERE b.match_status = 'pending'
    """)

    for row in rows:
        # Determine severity
        if row["leaked_password_hash"] and row["user_password_hash"]:
            if row["leaked_password_hash"] == row["user_password_hash"]:
                severity = "CRITICAL"
            else:
                severity = "WARNING"
        else:
            severity = "WARNING"

        match = BreachMatch(
            breach_event_id=row["breach_event_id"],
            user_id=row["user_id"],
            email=row["email"],
            user_name=row["user_name"],
            phone=row["phone"],
            auth0_user_id=row["auth0_user_id"],
            severity=severity,
        )
        matches.append(match)

        # Update breach event with match result
        await ghost_db.execute(
            """UPDATE breach_events
               SET match_status = 'matched', matched_user_id = $1, severity = $2
               WHERE id = $3""",
            row["user_id"],
            severity,
            row["breach_event_id"],
        )

    # Mark unmatched as safe
    await ghost_db.execute(
        "UPDATE breach_events SET match_status = 'no_match', severity = 'SAFE' WHERE match_status = 'pending'"
    )

    log.info(
        "breach.matched",
        total=len(matches),
        critical=sum(1 for m in matches if m.severity == "CRITICAL"),
        warning=sum(1 for m in matches if m.severity == "WARNING"),
    )

    return matches
