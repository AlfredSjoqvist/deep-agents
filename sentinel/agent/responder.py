"""Phase 3: Respond to breach — lock accounts, call users, log actions."""

import json

import structlog

from sentinel.agent.breach_analyzer import BreachMatch
from sentinel.agent.researcher import IncidentReport
from sentinel.integrations import ghost_db, auth0_client, bland_caller

log = structlog.get_logger()


async def lock_compromised_accounts(matches: list[BreachMatch]) -> dict:
    """Lock all compromised accounts via Auth0."""
    results = {"locked": 0, "sessions_revoked": 0, "failed": 0, "skipped": 0}

    for match in matches:
        if match.severity not in ("CRITICAL", "WARNING"):
            results["skipped"] += 1
            continue

        if not match.auth0_user_id:
            log.warning("responder.no_auth0_id", email=match.email)
            results["skipped"] += 1
            continue

        try:
            # Block the account
            await auth0_client.block_user(match.auth0_user_id)
            results["locked"] += 1

            # Revoke active sessions
            revoked = await auth0_client.revoke_sessions(match.auth0_user_id)
            if revoked:
                results["sessions_revoked"] += 1

            # Update user status in Ghost DB
            await ghost_db.execute(
                "UPDATE users SET status = 'locked' WHERE id = $1",
                match.user_id,
            )

            # Log the action
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
            log.error("responder.lock_failed", email=match.email, error=str(e))
            results["failed"] += 1

            await ghost_db.execute(
                """INSERT INTO response_log (breach_event_id, user_id, action, details, status)
                   VALUES ($1, $2, $3, $4, $5)""",
                match.breach_event_id,
                match.user_id,
                "account_lock_failed",
                json.dumps({"error": str(e)}),
                "failed",
            )

    log.info("responder.accounts_locked", **results)
    return results


async def notify_critical_users(
    matches: list[BreachMatch],
    report: IncidentReport,
) -> dict:
    """Call CRITICAL users via Bland AI to notify them."""
    results = {"calls_initiated": 0, "failed": 0, "skipped": 0}
    call_ids = []

    critical_matches = [m for m in matches if m.severity == "CRITICAL"]

    for match in critical_matches:
        if not match.phone:
            log.warning("responder.no_phone", email=match.email)
            results["skipped"] += 1
            continue

        try:
            call_result = await bland_caller.call_user(
                phone_number=match.phone,
                user_name=match.user_name,
                breach_details=f"a data breach from {report.breach_source} involving {report.cve_id}",
            )
            call_id = call_result.get("call_id", "unknown")
            call_ids.append(call_id)
            results["calls_initiated"] += 1

            # Log the call
            await ghost_db.execute(
                """INSERT INTO response_log (breach_event_id, user_id, action, details)
                   VALUES ($1, $2, $3, $4)""",
                match.breach_event_id,
                match.user_id,
                "phone_notification",
                json.dumps({"call_id": call_id, "phone": match.phone}),
            )

        except Exception as e:
            log.error("responder.call_failed", email=match.email, error=str(e))
            results["failed"] += 1

    log.info("responder.notifications_sent", **results)
    results["call_ids"] = call_ids
    return results
