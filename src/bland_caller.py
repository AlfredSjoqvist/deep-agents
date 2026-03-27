"""Bland AI voice notifications — call affected users."""

import requests
import time
from src.config import BLAND_API_KEY
from src import db


def call_user(user, breach_source):
    """Call a single user via Bland AI to notify them of the breach."""
    response = requests.post(
        "https://api.bland.ai/v1/calls",
        headers={
            "authorization": BLAND_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "phone_number": user["phone"],
            "task": f"""You are a security notification agent for Acme Corp.
You are calling {user['name']} to inform them about a security incident.

Key facts to communicate:
- Their account credentials were found in a data breach from {breach_source}
- Their account has ALREADY been locked to protect them
- They need to visit acme.com/reset to create a new password
- They should also change this password on any other sites where they used the same one
- Their data is being monitored for further suspicious activity

Be calm, professional, and reassuring. Keep it brief — under 60 seconds.
If they have questions you can't answer, tell them to email security@acme.com.""",
            "model": "enhanced",
            "first_sentence": f"Hi {user['name']}, this is the Acme Corp security team calling about your account security.",
            "max_duration": 3,
            "record": True,
            "wait_for_greeting": True,
        },
    )
    return response.json()


def notify_critical_users(critical_users, breach_source, breach_id):
    """
    Call all critical users. Log each call.
    Returns count of calls made.
    """
    called = 0
    for user in critical_users:
        try:
            db.log_agent(breach_id, "notify",
                f"Calling {user['name']} at {user['phone']}...",
                log_type="action")

            result = call_user(user, breach_source)
            call_id = result.get("call_id", "unknown")
            status = result.get("status", "unknown")

            action_id = db.create_response_action(
                breach_id, user["id"], user["email"], user["name"],
                "call_made", "critical"
            )
            db.update_response_action(action_id, "complete",
                detail={"call_id": call_id, "bland_status": status})

            db.log_agent(breach_id, "notify",
                f"Call queued for {user['name']} (call_id: {call_id})",
                log_type="action")

            called += 1
            time.sleep(1)  # Pace calls so dashboard updates visibly

        except Exception as e:
            db.log_agent(breach_id, "notify",
                f"Failed to call {user['email']}: {e}", log_type="error")

    return called
