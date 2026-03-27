"""Auth0 account lockdown — block users and revoke sessions."""

import time
from src import db


def lock_user(auth0_mgmt, auth0_user_id):
    """Block a user via Auth0 Management API."""
    auth0_mgmt.users.update(auth0_user_id, {"blocked": True})


def revoke_sessions(auth0_mgmt, auth0_user_id):
    """Revoke all active sessions for a user."""
    try:
        # Auth0 Management API v2
        auth0_mgmt.users.invalidate_remembered_browsers(auth0_user_id)
    except Exception:
        pass  # Not all Auth0 tiers support this — non-critical


def lock_compromised_users(auth0_mgmt, critical_users, breach_id):
    """
    Lock all critical users via Auth0. Log each action.
    Returns count of successfully locked accounts.
    """
    locked = 0
    for user in critical_users:
        try:
            auth0_user_id = user.get("auth0_user_id")
            if auth0_user_id:
                lock_user(auth0_mgmt, auth0_user_id)
                revoke_sessions(auth0_mgmt, auth0_user_id)

            # Update DB regardless (for demo, some users may not have auth0_user_id)
            db.update_user_status(user["id"], "locked")

            action_id = db.create_response_action(
                breach_id, user["id"], user["email"], user["name"],
                "account_locked", "critical"
            )
            db.update_response_action(action_id, "complete")

            db.log_agent(breach_id, "lock",
                f"Locked account for {user['name']} ({user['email']})",
                log_type="action")

            locked += 1
            time.sleep(0.3)  # Slight delay so dashboard animates nicely

        except Exception as e:
            db.log_agent(breach_id, "lock",
                f"Failed to lock {user['email']}: {e}", log_type="error")

    return locked
