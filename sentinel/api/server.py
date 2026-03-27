"""FastAPI server wrapping the Sentinel breach response pipeline.

Endpoints:
    POST /api/trigger          - Start the pipeline
    GET  /api/events/{run_id}  - SSE event stream
    GET  /api/status/{run_id}  - Current pipeline status + result
    GET  /api/integrations     - Real integration health checks
    POST /api/call             - Trigger a Bland AI test call
    GET  /api/health           - Health check
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path

import structlog
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from sentinel.api.models import (
    CallRequest,
    CallResponse,
    HealthResponse,
    IntegrationStatus,
    IntegrationsResponse,
    RunStatusResponse,
    SSEEvent,
    TriggerRequest,
    TriggerResponse,
)
from sentinel.config import config

log = structlog.get_logger()

# ── App Setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Sentinel API",
    description="Autonomous breach response pipeline — REST + SSE interface",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-Memory Run Store ──────────────────────────────────────────────────────
# Each run is keyed by run_id and stores the result.
# The event Queue lives in the orchestrator module (keyed by run_id).

_runs: dict[str, dict] = {}
# _runs[run_id] = {
#     "result": SentinelResult | None,
#     "done": bool,
# }


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_run(run_id: str) -> dict:
    """Retrieve a run or raise 404."""
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


async def _run_pipeline(
    run_id: str,
    breach_source: str,
    breach_csv_content: str | None = None,
) -> None:
    """Execute the Sentinel pipeline in a background task.

    The orchestrator pushes events directly to its own asyncio.Queue (keyed
    by run_id) and sends a None sentinel when the pipeline finishes.  The
    SSE endpoint reads from that same Queue, so there is no polling delay.
    """
    from sentinel.agent.orchestrator import SentinelResult, run_sentinel

    run = _runs[run_id]

    try:
        result = await run_sentinel(
            breach_csv_content=breach_csv_content,
            breach_source=breach_source,
            run_id=run_id,
        )
        run["result"] = result
    except Exception as exc:
        log.exception("sentinel.pipeline_background_error", run_id=run_id)
        run["result"] = SentinelResult(status="error")

    run["done"] = True


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Simple health check."""
    return HealthResponse(status="ok", service="sentinel-api")


@app.post("/api/trigger", response_model=TriggerResponse)
async def trigger_pipeline(
    body: TriggerRequest | None = None,
    file: UploadFile | None = File(None),
    breach_source: str | None = Form(None),
):
    """Start the Sentinel pipeline.

    Accepts either:
      - JSON body with ``breach_source`` and ``use_sample``
      - Multipart form with a CSV file upload + optional ``breach_source`` field
    """
    run_id = str(uuid.uuid4())

    csv_content: str | None = None
    source = "DarkForum X"

    # Handle multipart CSV upload
    if file is not None:
        raw = await file.read()
        csv_content = raw.decode("utf-8")
        source = breach_source or source
    elif body is not None:
        source = body.breach_source
        if not body.use_sample:
            raise HTTPException(
                status_code=400,
                detail="Either set use_sample=true or upload a CSV file.",
            )
        # use_sample=True means the orchestrator will load the default CSV
        csv_content = None
    else:
        # No body and no file — use defaults (sample CSV)
        pass

    # Pre-create the orchestrator's event Queue so the SSE endpoint can
    # connect before the background task calls run_sentinel().
    from sentinel.agent.orchestrator import ensure_event_queue
    ensure_event_queue(run_id)

    # Set up the run record.
    _runs[run_id] = {
        "result": None,
        "done": False,
    }

    # Fire-and-forget background task
    asyncio.create_task(_run_pipeline(run_id, source, csv_content))

    log.info("api.trigger", run_id=run_id, source=source)
    return TriggerResponse(run_id=run_id, status="started")


@app.get("/api/events/{run_id}")
async def event_stream(run_id: str):
    """SSE stream of real-time pipeline events.

    Reads directly from the orchestrator's asyncio.Queue for this run_id,
    yielding each event immediately as it arrives (no polling, no batching).
    A None sentinel from the queue signals end-of-stream.
    """
    from sentinel.agent.orchestrator import get_event_queue

    # Validate run exists
    _get_run(run_id)

    queue = get_event_queue(run_id)
    if queue is None:
        raise HTTPException(status_code=404, detail=f"No event queue for run {run_id}")

    async def _generate():
        while True:
            try:
                evt = await asyncio.wait_for(queue.get(), timeout=60.0)
            except asyncio.TimeoutError:
                # Send a keep-alive comment so the connection stays open
                yield {"event": "ping", "data": "keep-alive"}
                continue

            if evt is None:
                # Pipeline finished — send a final close event and stop
                yield {
                    "event": "message",
                    "data": json.dumps({"type": "stream_end", "message": "Stream closed", "data": {}, "timestamp": time.time()}),
                }
                return

            # evt is a PipelineEvent (Pydantic model) — serialize via model_dump
            if hasattr(evt, "model_dump"):
                payload = evt.model_dump()
            else:
                payload = evt

            yield {
                "event": "message",
                "data": json.dumps(payload, default=str),
            }

    return EventSourceResponse(_generate())


@app.get("/api/status/{run_id}", response_model=RunStatusResponse)
async def run_status(run_id: str):
    """Get the current pipeline status and result for a run."""
    run = _get_run(run_id)
    result = run.get("result")

    if result is None:
        return RunStatusResponse(status="running")

    return RunStatusResponse(**asdict(result))


@app.get("/api/integrations", response_model=IntegrationsResponse)
async def check_integrations():
    """Check real connectivity for every Sentinel integration."""
    statuses: list[IntegrationStatus] = []

    # 1. Ghost DB ─────────────────────────────────────────────────────────────
    try:
        from sentinel.integrations import ghost_db
        pool = await ghost_db.get_pool()
        val = await pool.fetchval("SELECT 1")
        statuses.append(IntegrationStatus(
            name="Ghost DB",
            status="active" if val == 1 else "partial",
            role="Core database",
            detail="Connected and responsive",
        ))
    except Exception as exc:
        statuses.append(IntegrationStatus(
            name="Ghost DB",
            status="inactive",
            role="Core database",
            detail=str(exc),
        ))

    # 2. Auth0 ────────────────────────────────────────────────────────────────
    try:
        from sentinel.integrations import auth0_client

        if not config.auth0_domain or not config.auth0_client_id:
            statuses.append(IntegrationStatus(
                name="Auth0",
                status="inactive",
                role="Identity & access management",
                detail="Domain or client_id not configured",
            ))
        else:
            # Actually try to fetch a management token
            token = await auth0_client._get_mgmt_token()
            if token:
                statuses.append(IntegrationStatus(
                    name="Auth0",
                    status="active",
                    role="Identity & access management",
                    detail="Token fetch successful",
                ))
            else:
                statuses.append(IntegrationStatus(
                    name="Auth0",
                    status="partial",
                    role="Identity & access management",
                    detail="Configured but token fetch returned empty",
                ))
    except Exception as exc:
        statuses.append(IntegrationStatus(
            name="Auth0",
            status="partial" if config.auth0_domain else "inactive",
            role="Identity & access management",
            detail=str(exc),
        ))

    # 3. Bland AI ─────────────────────────────────────────────────────────────
    try:
        if not config.bland_api_key:
            statuses.append(IntegrationStatus(
                name="Bland AI",
                status="inactive",
                role="AI phone calls for breach notification",
                detail="No API key configured",
            ))
        else:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://api.bland.ai/v1/calls",
                    headers={"authorization": config.bland_api_key},
                    timeout=10,
                )
            if resp.status_code in (200, 201):
                statuses.append(IntegrationStatus(
                    name="Bland AI",
                    status="active",
                    role="AI phone calls for breach notification",
                    detail="API key valid",
                ))
            else:
                statuses.append(IntegrationStatus(
                    name="Bland AI",
                    status="partial",
                    role="AI phone calls for breach notification",
                    detail=f"API returned status {resp.status_code}",
                ))
    except Exception as exc:
        statuses.append(IntegrationStatus(
            name="Bland AI",
            status="partial" if config.bland_api_key else "inactive",
            role="AI phone calls for breach notification",
            detail=str(exc),
        ))

    # 4. Overmind ─────────────────────────────────────────────────────────────
    if config.overmind_api_key:
        statuses.append(IntegrationStatus(
            name="Overmind",
            status="active",
            role="Agent decision tracing",
            detail="API key configured",
        ))
    else:
        statuses.append(IntegrationStatus(
            name="Overmind",
            status="inactive",
            role="Agent decision tracing",
            detail="No API key set",
        ))

    # 5. Truefoundry ──────────────────────────────────────────────────────────
    if config.truefoundry_token:
        statuses.append(IntegrationStatus(
            name="Truefoundry",
            status="active",
            role="LLM gateway (AI inference)",
            detail="Token configured",
        ))
    else:
        statuses.append(IntegrationStatus(
            name="Truefoundry",
            status="inactive",
            role="LLM gateway (AI inference)",
            detail="No token set",
        ))

    # 6. Aerospike ────────────────────────────────────────────────────────────
    if config.aerospike_host and config.aerospike_host != "127.0.0.1":
        statuses.append(IntegrationStatus(
            name="Aerospike",
            status="active",
            role="High-performance cache / session store",
            detail=f"Configured at {config.aerospike_host}:{config.aerospike_port}",
        ))
    elif config.aerospike_host:
        statuses.append(IntegrationStatus(
            name="Aerospike",
            status="partial",
            role="High-performance cache / session store",
            detail="Using default localhost — may not be running",
        ))
    else:
        statuses.append(IntegrationStatus(
            name="Aerospike",
            status="inactive",
            role="High-performance cache / session store",
            detail="Not configured",
        ))

    # 7. Senso ────────────────────────────────────────────────────────────────
    if config.senso_api_key:
        statuses.append(IntegrationStatus(
            name="Senso",
            status="active",
            role="Context store for security advisories",
            detail="API key configured",
        ))
    else:
        statuses.append(IntegrationStatus(
            name="Senso",
            status="inactive",
            role="Context store for security advisories",
            detail="No API key set",
        ))

    return IntegrationsResponse(integrations=statuses)


@app.post("/api/call", response_model=CallResponse)
async def trigger_call(body: CallRequest):
    """Trigger a Bland AI test call directly."""
    if not config.bland_api_key:
        raise HTTPException(status_code=503, detail="Bland AI not configured — no API key")

    try:
        from sentinel.integrations.bland_caller import call_user

        result = await call_user(
            phone_number=body.phone_number,
            user_name=body.user_name,
            breach_details=body.breach_details,
        )
        return CallResponse(
            status="initiated",
            call_id=result.get("call_id", ""),
            detail=f"Call to {body.phone_number} initiated",
        )
    except Exception as exc:
        log.exception("api.call_failed", phone=body.phone_number)
        raise HTTPException(status_code=502, detail=f"Bland AI call failed: {exc}")


# ── Uvicorn runner (convenience) ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "sentinel.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
