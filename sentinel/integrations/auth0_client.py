"""Auth0 Management API — lock/unlock accounts, revoke sessions."""

import httpx
import structlog

from sentinel.config import config

log = structlog.get_logger()

_mgmt_token: str | None = None


async def _get_mgmt_token() -> str:
    """Get or fetch the Auth0 Management API token."""
    global _mgmt_token
    if _mgmt_token or config.auth0_mgmt_token:
        return _mgmt_token or config.auth0_mgmt_token

    # Fetch a new token via client credentials
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{config.auth0_domain}/oauth/token",
            json={
                "client_id": config.auth0_client_id,
                "client_secret": config.auth0_client_secret,
                "audience": f"https://{config.auth0_domain}/api/v2/",
                "grant_type": "client_credentials",
            },
        )
        resp.raise_for_status()
        _mgmt_token = resp.json()["access_token"]
        return _mgmt_token


async def _headers() -> dict:
    token = await _get_mgmt_token()
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def block_user(user_id: str) -> dict:
    """Block a user account by Auth0 user_id."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"https://{config.auth0_domain}/api/v2/users/{user_id}",
            headers=await _headers(),
            json={"blocked": True},
        )
        resp.raise_for_status()
        log.info("auth0.user_blocked", user_id=user_id)
        return resp.json()


async def unblock_user(user_id: str) -> dict:
    """Unblock a user account."""
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"https://{config.auth0_domain}/api/v2/users/{user_id}",
            headers=await _headers(),
            json={"blocked": False},
        )
        resp.raise_for_status()
        log.info("auth0.user_unblocked", user_id=user_id)
        return resp.json()


async def revoke_sessions(user_id: str) -> bool:
    """Delete all sessions for a user."""
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"https://{config.auth0_domain}/api/v2/users/{user_id}/sessions",
            headers=await _headers(),
        )
        if resp.status_code in (204, 200):
            log.info("auth0.sessions_revoked", user_id=user_id)
            return True
        log.warning("auth0.session_revoke_failed", user_id=user_id, status=resp.status_code)
        return False


async def list_users(page: int = 0, per_page: int = 100) -> list[dict]:
    """List users from Auth0."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://{config.auth0_domain}/api/v2/users",
            headers=await _headers(),
            params={"page": page, "per_page": per_page},
        )
        resp.raise_for_status()
        return resp.json()


async def create_user(email: str, name: str, password: str) -> dict:
    """Create a user in Auth0 (for seeding)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{config.auth0_domain}/api/v2/users",
            headers=await _headers(),
            json={
                "email": email,
                "name": name,
                "password": password,
                "connection": "Username-Password-Authentication",
            },
        )
        resp.raise_for_status()
        return resp.json()
