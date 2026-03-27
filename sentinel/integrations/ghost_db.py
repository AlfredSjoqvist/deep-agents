"""Ghost DB (ghost.build) — PostgreSQL client for Sentinel."""

import asyncpg

from sentinel.config import config

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(config.ghost_connection_string, min_size=2, max_size=10)
    return _pool


async def execute(query: str, *args) -> str:
    """Execute a query (INSERT/UPDATE/DELETE)."""
    pool = await get_pool()
    return await pool.execute(query, *args)


async def fetch(query: str, *args) -> list[asyncpg.Record]:
    """Fetch multiple rows."""
    pool = await get_pool()
    return await pool.fetch(query, *args)


async def fetchrow(query: str, *args) -> asyncpg.Record | None:
    """Fetch a single row."""
    pool = await get_pool()
    return await pool.fetchrow(query, *args)


async def fetchval(query: str, *args):
    """Fetch a single value."""
    pool = await get_pool()
    return await pool.fetchval(query, *args)


async def init_tables():
    """Create Sentinel tables if they don't exist."""
    pool = await get_pool()
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            auth0_user_id TEXT,
            password_hash TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS breach_events (
            id SERIAL PRIMARY KEY,
            leaked_email TEXT NOT NULL,
            leaked_password_hash TEXT,
            source TEXT,
            match_status TEXT DEFAULT 'pending',
            matched_user_id INTEGER REFERENCES users(id),
            severity TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS response_log (
            id SERIAL PRIMARY KEY,
            breach_event_id INTEGER REFERENCES breach_events(id),
            user_id INTEGER REFERENCES users(id),
            action TEXT NOT NULL,
            details JSONB DEFAULT '{}',
            status TEXT DEFAULT 'success',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS research_cache (
            id SERIAL PRIMARY KEY,
            breach_source TEXT,
            cve_id TEXT,
            attack_vector TEXT,
            affected_software TEXT,
            severity TEXT,
            recommended_patches JSONB DEFAULT '[]',
            summary TEXT,
            raw_analysis JSONB DEFAULT '{}',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE INDEX IF NOT EXISTS idx_breach_email ON breach_events(leaked_email);
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
    """)


async def close():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
