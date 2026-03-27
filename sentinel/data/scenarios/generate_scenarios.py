"""Generate realistic breach scenario CSVs for Sentinel demo.

Reads existing users from Ghost DB, then creates two scenario files:
  1. credential_stuffing.csv  -- 500 rows, mixed domains
  2. phishing_campaign.csv    -- 300 rows, all @acme.com

Deterministic via Faker seed 42.  Run with:
    python3 -m sentinel.data.scenarios.generate_scenarios
"""

import asyncio
import csv
import hashlib
import random
from pathlib import Path

import asyncpg
from faker import Faker

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GHOST_CONNECTION_STRING = (
    "postgresql://tsdbadmin:lfygkg7qivz9rqyc@"
    "ubn7p4285g.l8m5ogdt7f.tsdb.cloud.timescale.com:39916/tsdb"
)

SCENARIO_DIR = Path(__file__).parent

CREDENTIAL_STUFFING_TOTAL = 500
CREDENTIAL_STUFFING_MATCHES = 45
CREDENTIAL_STUFFING_CRITICAL = 15

PHISHING_TOTAL = 300
PHISHING_MATCHES = 50
PHISHING_CRITICAL = 20

RANDOM_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "protonmail.com", "icloud.com", "aol.com", "zoho.com",
    "yandex.com", "mail.com", "gmx.com", "fastmail.com",
    "techcorp.io", "globex.com", "initech.com", "umbrella.net",
    "wayne-enterprises.com", "stark-industries.com", "oscorp.com",
    "lexcorp.com", "cyberdyne.com", "weyland-yutani.com",
]

PHISHING_URLS = [
    "https://acme-sso-login.com/auth",
    "https://acme-portal.net/signin",
    "https://login-acme-sso.com/oauth2",
    "https://acme-corp-login.net/sso",
    "https://acme-sso.org/authenticate",
    "https://portal-acme.com/login",
    "https://sso-acme-corp.net/auth/v2",
    "https://acme-login-portal.com/signin",
    "https://secure-acme-sso.com/oauth",
    "https://acme-identity.net/login",
]

CREDENTIAL_STUFFING_SOURCE = "HaveIBeenPwned_Compilation_2026"
PHISHING_SOURCE = "PhishTank_Campaign_APT29_2026"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

fake = Faker()
Faker.seed(42)
random.seed(42)


def _hash_password(password: str) -> str:
    """SHA-256 hash matching seed_users.py convention."""
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------------------------------------------------------------------
# DB access
# ---------------------------------------------------------------------------

async def _fetch_users() -> list[dict]:
    """Fetch all users from Ghost DB (email + password_hash)."""
    conn = await asyncpg.connect(GHOST_CONNECTION_STRING)
    try:
        rows = await conn.fetch("SELECT email, password_hash FROM users ORDER BY id")
        return [{"email": r["email"], "password_hash": r["password_hash"]} for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Credential Stuffing generator
# ---------------------------------------------------------------------------

def _generate_credential_stuffing(users: list[dict]) -> str:
    """Generate credential_stuffing.csv content.

    500 rows total:
      - 15 rows: acme.com email + MATCHING password hash  (CRITICAL)
      - 30 rows: acme.com email + different password hash  (WARNING)
      - 455 rows: random external emails                   (no match)
    """
    # Deterministic shuffle of user list for selection
    shuffled_users = list(users)
    random.shuffle(shuffled_users)

    if len(shuffled_users) < CREDENTIAL_STUFFING_MATCHES:
        raise RuntimeError(
            f"Need at least {CREDENTIAL_STUFFING_MATCHES} users in Ghost DB, "
            f"found {len(shuffled_users)}"
        )

    critical_users = shuffled_users[:CREDENTIAL_STUFFING_CRITICAL]
    warning_users = shuffled_users[CREDENTIAL_STUFFING_CRITICAL:CREDENTIAL_STUFFING_MATCHES]
    remaining_count = CREDENTIAL_STUFFING_TOTAL - CREDENTIAL_STUFFING_MATCHES

    rows: list[dict] = []

    # CRITICAL: matching email AND password hash
    for user in critical_users:
        rows.append({
            "leaked_email": user["email"],
            "leaked_password_hash": user["password_hash"],
            "source": CREDENTIAL_STUFFING_SOURCE,
        })

    # WARNING: matching email, different hash
    for user in warning_users:
        rows.append({
            "leaked_email": user["email"],
            "leaked_password_hash": _hash_password(fake.password(length=14)),
            "source": CREDENTIAL_STUFFING_SOURCE,
        })

    # Fill with random external emails from diverse domains
    for _ in range(remaining_count):
        domain = random.choice(RANDOM_DOMAINS)
        local_part = fake.user_name() + str(random.randint(1, 999))
        rows.append({
            "leaked_email": f"{local_part}@{domain}",
            "leaked_password_hash": _hash_password(fake.password(length=12)),
            "source": CREDENTIAL_STUFFING_SOURCE,
        })

    random.shuffle(rows)
    return _write_csv(rows, ["leaked_email", "leaked_password_hash", "source"])


# ---------------------------------------------------------------------------
# Phishing Campaign generator
# ---------------------------------------------------------------------------

def _generate_phishing_campaign(users: list[dict]) -> str:
    """Generate phishing_campaign.csv content.

    300 rows total (all @acme.com -- targeted attack):
      - 20 rows: email + MATCHING password hash  (CRITICAL -- real pw on fake page)
      - 30 rows: email + different hash           (WARNING -- entered wrong/old pw)
      - 250 rows: fake acme.com emails            (no match in user DB)
    """
    shuffled_users = list(users)
    random.shuffle(shuffled_users)

    if len(shuffled_users) < PHISHING_MATCHES:
        raise RuntimeError(
            f"Need at least {PHISHING_MATCHES} users in Ghost DB, "
            f"found {len(shuffled_users)}"
        )

    critical_users = shuffled_users[:PHISHING_CRITICAL]
    warning_users = shuffled_users[PHISHING_CRITICAL:PHISHING_MATCHES]
    remaining_count = PHISHING_TOTAL - PHISHING_MATCHES

    rows: list[dict] = []

    # CRITICAL: entered real password on fake SSO page
    for user in critical_users:
        rows.append({
            "leaked_email": user["email"],
            "leaked_password_hash": user["password_hash"],
            "source": PHISHING_SOURCE,
            "phishing_url": random.choice(PHISHING_URLS),
        })

    # WARNING: entered some password (not their real one) on fake page
    for user in warning_users:
        rows.append({
            "leaked_email": user["email"],
            "leaked_password_hash": _hash_password(fake.password(length=14)),
            "source": PHISHING_SOURCE,
            "phishing_url": random.choice(PHISHING_URLS),
        })

    # Remaining: fake acme.com employees (no match in user DB)
    for _ in range(remaining_count):
        first = fake.first_name().lower()
        last = fake.last_name().lower()
        email = f"{first}.{last}@acme.com"
        rows.append({
            "leaked_email": email,
            "leaked_password_hash": _hash_password(fake.password(length=12)),
            "source": PHISHING_SOURCE,
            "phishing_url": random.choice(PHISHING_URLS),
        })

    random.shuffle(rows)
    return _write_csv(
        rows, ["leaked_email", "leaked_password_hash", "source", "phishing_url"]
    )


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

def _write_csv(rows: list[dict], fieldnames: list[str]) -> str:
    """Serialize rows to CSV string."""
    import io

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("=== Sentinel Scenario Generator ===\n")

    # 1. Fetch existing users from Ghost DB
    print("Fetching users from Ghost DB...")
    users = await _fetch_users()
    print(f"  Found {len(users)} users\n")

    if len(users) == 0:
        print("ERROR: No users in Ghost DB. Run seed_users first:")
        print("  python3 -m sentinel.data.seed_users")
        return

    # 2. Generate credential stuffing CSV
    print(f"Generating credential_stuffing.csv ({CREDENTIAL_STUFFING_TOTAL} rows)...")
    cs_csv = _generate_credential_stuffing(users)
    cs_path = SCENARIO_DIR / "credential_stuffing.csv"
    cs_path.write_text(cs_csv)
    print(f"  Written to {cs_path}")
    print(
        f"  {CREDENTIAL_STUFFING_MATCHES} email matches, "
        f"{CREDENTIAL_STUFFING_CRITICAL} critical (hash match)\n"
    )

    # 3. Generate phishing campaign CSV
    print(f"Generating phishing_campaign.csv ({PHISHING_TOTAL} rows)...")
    ph_csv = _generate_phishing_campaign(users)
    ph_path = SCENARIO_DIR / "phishing_campaign.csv"
    ph_path.write_text(ph_csv)
    print(f"  Written to {ph_path}")
    print(
        f"  {PHISHING_MATCHES} email matches, "
        f"{PHISHING_CRITICAL} critical (hash match)\n"
    )

    print("--- Summary ---")
    print(f"Credential Stuffing: {CREDENTIAL_STUFFING_TOTAL} rows "
          f"({CREDENTIAL_STUFFING_MATCHES} match, {CREDENTIAL_STUFFING_CRITICAL} critical)")
    print(f"Phishing Campaign:   {PHISHING_TOTAL} rows "
          f"({PHISHING_MATCHES} match, {PHISHING_CRITICAL} critical)")
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
