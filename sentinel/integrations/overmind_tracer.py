"""Overmind — agent decision tracing. 2 lines to instrument everything."""

import structlog

from sentinel.config import config

log = structlog.get_logger()

_initialized = False


def init_tracing():
    """Initialize Overmind tracing. Call once at startup."""
    global _initialized
    if _initialized:
        return

    if not config.overmind_api_key:
        log.warning("overmind.no_api_key", msg="Overmind tracing disabled — no API key")
        _initialized = True
        return

    try:
        from overmind import init
        init(overmind_api_key=config.overmind_api_key, service_name="sentinel")
        log.info("overmind.initialized", service="sentinel")
    except ImportError:
        log.warning("overmind.not_installed", msg="pip install overmind to enable tracing")
    except Exception as e:
        log.warning("overmind.init_failed", error=str(e))

    _initialized = True
