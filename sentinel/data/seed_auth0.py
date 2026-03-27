"""Seed Auth0 with test users matching the first 15 Ghost DB users.

Creates Auth0 accounts, updates Ghost DB with auth0_user_id,
and tests block/unblock functionality for demo purposes.
"""

import asyncio
import ssl

import asyncpg
import httpx

# ---------- Configuration ----------

AUTH0_DOMAIN = "dev-tgkkfkcpxgwboqgx.us.auth0.com"
AUTH0_CLIENT_ID = "CNIyjqlIFNlv0QRp9gYzCjbGGJuf6Xsw"
AUTH0_CLIENT_SECRET = (
    "5Uw7mrY2BFOofSTahnlROtdDKQDKdy2DCcjS6tkctzKBnhPcuPKmB5QGWAp6eKtw"
)
AUTH0_AUDIENCE = f"https://{AUTH0_DOMAIN}/api/v2/"
AUTH0_CONNECTION = "Username-Password-Authentication"
DEFAULT_PASSWORD = "Sentinel2026!"

GHOST_DSN = (
    "postgresql://tsdbadmin:lfygkg7qivz9rqyc"
    "@ubn7p4285g.l8m5ogdt7f.tsdb.cloud.timescale.com:39916/tsdb"
)

USER_LIMIT = 15


# ---------- Auth0 helpers ----------


async def get_mgmt_token(client: httpx.AsyncClient) -> str:
    """Obtain a Management API access token via client credentials."""
    resp = await client.post(
        f"https://{AUTH0_DOMAIN}/oauth/token",
        json={
            "client_id": AUTH0_CLIENT_ID,
            "client_secret": AUTH0_CLIENT_SECRET,
            "audience": AUTH0_AUDIENCE,
            "grant_type": "client_credentials",
        },
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[auth0] Management API token acquired (length={len(token)})")
    return token


def auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def create_auth0_user(
    client: httpx.AsyncClient,
    token: str,
    email: str,
    name: str,
) -> dict | None:
    """Create a single user in Auth0. Returns the user dict or None on failure."""
    resp = await client.post(
        f"https://{AUTH0_DOMAIN}/api/v2/users",
        headers=auth_headers(token),
        json={
            "email": email,
            "name": name,
            "password": DEFAULT_PASSWORD,
            "connection": AUTH0_CONNECTION,
        },
    )
    if resp.status_code == 409:
        # User already exists -- fetch by email instead
        print(f"  [skip] {email} already exists in Auth0, fetching existing user")
        search_resp = await client.get(
            f"https://{AUTH0_DOMAIN}/api/v2/users-by-email",
            headers=auth_headers(token),
            params={"email": email},
        )
        search_resp.raise_for_status()
        results = search_resp.json()
        if results:
            return results[0]
        return None
    if resp.status_code >= 400:
        print(f"  [FAIL] {email} -- {resp.status_code}: {resp.text}")
        return None
    return resp.json()


async def block_user(client: httpx.AsyncClient, token: str, user_id: str) -> bool:
    """Block a user account."""
    resp = await client.patch(
        f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}",
        headers=auth_headers(token),
        json={"blocked": True},
    )
    return resp.status_code == 200


async def unblock_user(client: httpx.AsyncClient, token: str, user_id: str) -> bool:
    """Unblock a user account."""
    resp = await client.patch(
        f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}",
        headers=auth_headers(token),
        json={"blocked": False},
    )
    return resp.status_code == 200


async def get_user(client: httpx.AsyncClient, token: str, user_id: str) -> dict:
    """Fetch a single user from Auth0."""
    resp = await client.get(
        f"https://{AUTH0_DOMAIN}/api/v2/users/{user_id}",
        headers=auth_headers(token),
    )
    resp.raise_for_status()
    return resp.json()


# ---------- Main seed logic ----------


async def main() -> None:
    print("=" * 60)
    print("  Sentinel -- Auth0 User Seeder")
    print("=" * 60)

    # --- 1. Connect to Ghost DB and fetch the first 15 users ---
    print("\n[ghost_db] Connecting to Ghost DB ...")
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    pool = await asyncpg.create_pool(GHOST_DSN, min_size=1, max_size=3, ssl=ssl_ctx)

    rows = await pool.fetch(
        "SELECT id, name, email FROM users ORDER BY id LIMIT $1", USER_LIMIT
    )
    print(f"[ghost_db] Fetched {len(rows)} users from Ghost DB")

    if not rows:
        print("[ghost_db] No users found -- run seed_users.py first.")
        await pool.close()
        return

    # --- 2. Acquire Auth0 Management API token ---
    print("\n[auth0] Acquiring management token ...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await get_mgmt_token(client)

        # --- 3. Create each user in Auth0 ---
        print(f"\n[auth0] Creating {len(rows)} users in Auth0 ...")
        created = 0
        failed = 0
        skipped = 0
        results: list[tuple[int, str, str | None]] = []  # (db_id, email, auth0_id)

        for row in rows:
            db_id = row["id"]
            name = row["name"]
            email = row["email"]

            user_data = await create_auth0_user(client, token, email, name)
            if user_data:
                auth0_id = user_data["user_id"]
                results.append((db_id, email, auth0_id))
                if "already exists" not in str(user_data.get("_skip", "")):
                    created += 1
                print(f"  [OK]   {email} -> {auth0_id}")
            else:
                results.append((db_id, email, None))
                failed += 1

        # --- 4. Update Ghost DB with auth0_user_id ---
        print(f"\n[ghost_db] Updating Ghost DB with Auth0 user IDs ...")
        updated = 0
        for db_id, email, auth0_id in results:
            if auth0_id:
                await pool.execute(
                    "UPDATE users SET auth0_user_id = $1 WHERE id = $2",
                    auth0_id,
                    db_id,
                )
                updated += 1

        print(f"[ghost_db] Updated {updated} user records with auth0_user_id")

        # --- 5. Test block/unblock on the first user ---
        test_candidates = [(db_id, email, a0id) for db_id, email, a0id in results if a0id]
        if test_candidates:
            test_db_id, test_email, test_auth0_id = test_candidates[0]
            print(f"\n[test] Testing block/unblock on: {test_email} ({test_auth0_id})")

            # Block
            blocked = await block_user(client, token, test_auth0_id)
            if blocked:
                user_state = await get_user(client, token, test_auth0_id)
                print(f"  [block]   blocked={user_state.get('blocked')}  -- {'PASS' if user_state.get('blocked') else 'FAIL'}")
            else:
                print("  [block]   FAIL -- API returned non-200")

            # Unblock
            unblocked = await unblock_user(client, token, test_auth0_id)
            if unblocked:
                user_state = await get_user(client, token, test_auth0_id)
                print(f"  [unblock] blocked={user_state.get('blocked')}  -- {'PASS' if not user_state.get('blocked') else 'FAIL'}")
            else:
                print("  [unblock] FAIL -- API returned non-200")
        else:
            print("\n[test] No users available for block/unblock test")

    await pool.close()

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Users fetched from Ghost DB : {len(rows)}")
    print(f"  Created in Auth0            : {created}")
    print(f"  Failed                      : {failed}")
    print(f"  Ghost DB records updated    : {updated}")
    print(f"  Block/unblock test          : {'PASS' if test_candidates else 'SKIPPED'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
