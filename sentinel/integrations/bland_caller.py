"""Bland AI — outbound phone calls for breach notification."""

import httpx
import structlog

from sentinel.config import config

log = structlog.get_logger()

BLAND_API_BASE = "https://api.bland.ai/v1"


async def call_user(
    phone_number: str,
    user_name: str,
    breach_details: str = "a data breach",
    reset_url: str = "acme.com/reset",
    incident_context: str = "",
) -> dict:
    """Make an outbound call to notify a user of a breach.

    The Bland AI agent can answer questions about the incident using the
    context provided in the task prompt.
    """
    task = (
        f"You are a security analyst from Acme Corp's Sentinel Security team. "
        f"You are calling {user_name} because their account was compromised in {breach_details}. "
        f"Their account has already been automatically locked to protect them. "
        f"They need to visit {reset_url} to create a new password and enable MFA. "
        f"\n\n"
        f"IMPORTANT GUIDELINES:\n"
        f"- Be calm, professional, and reassuring\n"
        f"- Answer any questions they have about the breach\n"
        f"- If they ask what happened, explain the incident details below\n"
        f"- If they ask about compliance, mention GDPR 72-hour notification requirement\n"
        f"- If they ask about next steps, walk them through: 1) Reset password at {reset_url}, "
        f"2) Enable MFA, 3) Check for suspicious activity, 4) Monitor credit reports\n"
        f"\n"
        f"INCIDENT DETAILS YOU CAN SHARE:\n"
        f"{incident_context or breach_details}\n"
    )

    first_sentence = (
        f"Hi {user_name}, this is Sentinel Security from Acme Corp. "
        f"I'm calling about an important security matter regarding your account."
    )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BLAND_API_BASE}/calls",
            headers={"authorization": config.bland_api_key},
            json={
                "phone_number": phone_number,
                "task": task,
                "first_sentence": first_sentence,
                "model": "enhanced",
                "max_duration": 180,
                "record": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        log.info("bland.call_initiated", phone=phone_number, call_id=result.get("call_id"))
        return result


async def get_call_status(call_id: str) -> dict:
    """Check the status of a call."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BLAND_API_BASE}/calls/{call_id}",
            headers={"authorization": config.bland_api_key},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
