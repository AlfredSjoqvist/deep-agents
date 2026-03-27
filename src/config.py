import os
from dotenv import load_dotenv

load_dotenv()

# --- Anthropic ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# --- Ghost Postgres ---
GHOST_DB_URL = os.getenv("GHOST_DB_URL", "")

# --- Auth0 ---
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")

# --- Bland AI ---
BLAND_API_KEY = os.getenv("BLAND_API")

# --- Overmind ---
OVERMIND_API_KEY = os.getenv("OVERMIND_API_KEY", "")

# --- Truefoundry ---
TRUEFOUNDRY_TOKEN = os.getenv("TRUEFOUNDRY_ACCESS_TOKEN", "")
TRUEFOUNDRY_BASE_URL = os.getenv("TRUEFOUNDRY_BASE_URL", "")


def init_overmind():
    """Initialize Overmind tracing — call once at startup."""
    if OVERMIND_API_KEY:
        try:
            from overmind_sdk import init
            init(
                overmind_api_key=OVERMIND_API_KEY,
                service_name="sentinel",
                environment="hackathon",
                providers=["anthropic"],
            )
            print("[Overmind] Tracing initialized")
        except Exception as e:
            print(f"[Overmind] Init failed (non-critical): {e}")


def get_anthropic_client():
    import anthropic
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def get_auth0_client():
    from auth0.authentication import GetToken
    from auth0.management import Auth0 as Auth0Mgmt

    token_client = GetToken(AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET)
    token = token_client.client_credentials(f"https://{AUTH0_DOMAIN}/api/v2/")
    return Auth0Mgmt(AUTH0_DOMAIN, token["access_token"])
