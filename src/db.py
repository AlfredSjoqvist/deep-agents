"""Ghost Postgres DB operations — all state lives here."""

import json
import psycopg2
import psycopg2.extras
from datetime import datetime
from src.config import GHOST_DB_URL

_conn = None


def get_connection():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(GHOST_DB_URL)
        _conn.autocommit = True
    return _conn


def init_tables():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            auth0_user_id TEXT,
            password_hash TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS breach_events (
            id SERIAL PRIMARY KEY,
            breach_source TEXT,
            total_records INTEGER DEFAULT 0,
            matched_users INTEGER DEFAULT 0,
            critical_users INTEGER DEFAULT 0,
            warned_users INTEGER DEFAULT 0,
            locked_count INTEGER DEFAULT 0,
            called_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'idle',
            started_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS agent_log (
            id SERIAL PRIMARY KEY,
            breach_id INTEGER REFERENCES breach_events(id),
            timestamp TIMESTAMP DEFAULT NOW(),
            phase TEXT,
            message TEXT,
            detail TEXT,
            log_type TEXT DEFAULT 'info'
        );

        CREATE TABLE IF NOT EXISTS response_actions (
            id SERIAL PRIMARY KEY,
            breach_id INTEGER REFERENCES breach_events(id),
            user_id INTEGER REFERENCES users(id),
            user_email TEXT,
            user_name TEXT,
            action_type TEXT,
            severity TEXT,
            status TEXT DEFAULT 'pending',
            detail TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.close()


def reset_for_demo():
    """Reset all state for a fresh demo run."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM response_actions;")
    cur.execute("DELETE FROM agent_log;")
    cur.execute("DELETE FROM breach_events;")
    cur.execute("UPDATE users SET status = 'active';")
    cur.close()


# --- Users ---

def get_all_users():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


def get_user_by_email(email):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM users WHERE email = %s;", (email,))
    row = cur.fetchone()
    cur.close()
    return dict(row) if row else None


def update_user_status(user_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET status = %s WHERE id = %s;", (status, user_id))
    cur.close()


def get_user_counts():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'active') as active,
            COUNT(*) FILTER (WHERE status = 'locked') as locked,
            COUNT(*) FILTER (WHERE status = 'warned') as warned
        FROM users;
    """)
    row = cur.fetchone()
    cur.close()
    return dict(row)


# --- Breach Events ---

def create_breach_event(source, total_records):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO breach_events (breach_source, total_records, status) VALUES (%s, %s, 'analyzing') RETURNING id;",
        (source, total_records),
    )
    breach_id = cur.fetchone()[0]
    cur.close()
    return breach_id


def update_breach_event(breach_id, **fields):
    conn = get_connection()
    cur = conn.cursor()
    sets = ", ".join(f"{k} = %s" for k in fields.keys())
    cur.execute(f"UPDATE breach_events SET {sets} WHERE id = %s;", (*fields.values(), breach_id))
    cur.close()


def get_latest_breach():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM breach_events ORDER BY id DESC LIMIT 1;")
    row = cur.fetchone()
    cur.close()
    return dict(row) if row else None


# --- Agent Log ---

def log_agent(breach_id, phase, message, detail=None, log_type="info"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO agent_log (breach_id, phase, message, detail, log_type) VALUES (%s, %s, %s, %s, %s);",
        (breach_id, phase, message, json.dumps(detail) if detail else None, log_type),
    )
    cur.close()


def get_agent_logs(breach_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM agent_log WHERE breach_id = %s ORDER BY id ASC;", (breach_id,))
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


# --- Response Actions ---

def create_response_action(breach_id, user_id, user_email, user_name, action_type, severity):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO response_actions
           (breach_id, user_id, user_email, user_name, action_type, severity, status)
           VALUES (%s, %s, %s, %s, %s, %s, 'in_progress') RETURNING id;""",
        (breach_id, user_id, user_email, user_name, action_type, severity),
    )
    action_id = cur.fetchone()[0]
    cur.close()
    return action_id


def update_response_action(action_id, status, detail=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE response_actions SET status = %s, detail = %s WHERE id = %s;",
        (status, json.dumps(detail) if detail else None, action_id),
    )
    cur.close()


def get_response_actions(breach_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM response_actions WHERE breach_id = %s ORDER BY id ASC;", (breach_id,))
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]
