"""Senso.ai — context store for security advisories and CVE data."""

import httpx
import structlog

from sentinel.config import config

log = structlog.get_logger()

SENSO_API_BASE = "https://sdk.senso.ai/api/v1"


async def upload_content(content: str, title: str | None = None) -> dict:
    """Upload content to Senso knowledge base."""
    if not config.senso_api_key:
        log.warning("senso.no_api_key")
        return {"status": "skipped", "reason": "no API key"}

    async with httpx.AsyncClient() as client:
        payload = {"content": content}
        if title:
            payload["title"] = title

        resp = await client.post(
            f"{SENSO_API_BASE}/content/raw",
            headers={"X-API-Key": config.senso_api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        log.info("senso.content_uploaded", title=title)
        return resp.json()


async def search(query: str) -> dict:
    """Search the Senso knowledge base for relevant context."""
    if not config.senso_api_key:
        log.warning("senso.no_api_key")
        return {"results": [], "status": "skipped"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SENSO_API_BASE}/search",
            headers={"X-API-Key": config.senso_api_key, "Content-Type": "application/json"},
            json={"query": query},
            timeout=30,
        )
        resp.raise_for_status()
        log.info("senso.search_completed", query=query[:50])
        return resp.json()
