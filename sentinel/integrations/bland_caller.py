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
) -> dict:
    """Make an outbound call to notify a user of a breach."""
    task = (
        f"You are calling from Acme Corp's Sentinel Security system. "
        f"Tell {user_name} that their account was compromised in {breach_details}. "
        f"Their account has already been locked to protect them. "
        f"They need to visit {reset_url} to create a new password. "
        f"Be calm, professional, and reassuring. Answer any questions they have."
    )

    first_sentence = (
        f"Hi {user_name}, this is Sentinel Security from Acme Corp "
        f"calling about your account security."
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
                "max_duration": 120,
                "wait_for_greeting": True,
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
