"""Sentinel configuration — loads .env and exposes typed settings."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path)


@dataclass(frozen=True)
class Config:
    # Anthropic
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))

    # Auth0
    auth0_domain: str = field(default_factory=lambda: os.environ.get("AUTH0_DOMAIN", ""))
    auth0_client_id: str = field(default_factory=lambda: os.environ.get("AUTH0_CLIENT_ID", ""))
    auth0_client_secret: str = field(default_factory=lambda: os.environ.get("AUTH0_CLIENT_SECRET", ""))
    auth0_mgmt_token: str = field(default_factory=lambda: os.environ.get("AUTH0_MANAGEMENT_API_TOKEN", ""))

    # Truefoundry
    truefoundry_token: str = field(default_factory=lambda: os.environ.get("TRUEFOUNDRY_ACCESS_TOKEN", ""))
    truefoundry_base_url: str = field(default_factory=lambda: os.environ.get("TRUEFOUNDRY_BASE_URL", "https://app.truefoundry.com/api/llm/api/inference/openai"))

    # Bland AI
    bland_api_key: str = field(default_factory=lambda: os.environ.get("BLAND_API_KEY", ""))

    # Ghost DB
    ghost_connection_string: str = field(default_factory=lambda: os.environ.get("GHOST_CONNECTION_STRING", ""))

    # Overmind
    overmind_api_key: str = field(default_factory=lambda: os.environ.get("OVERMIND_API_KEY", ""))

    # Aerospike
    aerospike_host: str = field(default_factory=lambda: os.environ.get("AEROSPIKE_HOST", "127.0.0.1"))
    aerospike_port: int = field(default_factory=lambda: int(os.environ.get("AEROSPIKE_PORT", "3000")))

    # Senso
    senso_api_key: str = field(default_factory=lambda: os.environ.get("SENSO_API_KEY", ""))

    # Airbyte
    airbyte_api_key: str = field(default_factory=lambda: os.environ.get("AIRBYTE_API_KEY", ""))


config = Config()
