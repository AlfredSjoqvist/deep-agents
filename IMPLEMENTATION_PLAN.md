# Sentinel — Implementation Plan

## Product Overview

Sentinel is an autonomous breach response agent. A breach file is uploaded. The agent takes over — matching compromised accounts, locking them down, calling affected users, and logging everything. A real-time dashboard shows every step as it happens.

---

## System Architecture

```
                        ┌─────────────────────┐
                        │   STREAMLIT DASHBOARD │
                        │                       │
                        │  ┌─────┐ ┌─────────┐ │
                        │  │Breach│ │  Agent   │ │
                        │  │Stats │ │ Reasoning│ │
                        │  └─────┘ │  Stream  │ │
                        │  ┌─────┐ │         │ │
                        │  │Users │ └─────────┘ │
                        │  │Table │ ┌─────────┐ │
                        │  └─────┘ │ Response │ │
                        │  ┌─────┐ │   Log    │ │
                        │  │Call  │ └─────────┘ │
                        │  │Status│              │
                        │  └─────┘              │
                        └────────┬──────────────┘
                                 │ reads state from
                                 │
                        ┌────────▼──────────────┐
                        │     GHOST POSTGRES DB   │
                        │                         │
                        │  users (100 seeded)     │
                        │  breach_events          │
                        │  agent_log (reasoning)  │
                        │  response_actions       │
                        └────────▲──────────────┘
                                 │ writes to
                                 │
               ┌─────────────────┴─────────────────┐
               │          SENTINEL AGENT            │
               │         (Python process)           │
               │                                    │
               │  1. Load breach CSV via Airbyte    │
               │  2. Match against users (Ghost DB) │
               │  3. Classify: CRITICAL / WARN      │
               │  4. Claude analyzes & decides       │
               │  5. Auth0: lock accounts            │
               │  6. Bland: call critical users      │
               │  7. Log everything to Ghost DB      │
               │                                    │
               │  [Overmind wraps all Claude calls]  │
               │  [Truefoundry routes LLM traffic]   │
               └────────────────────────────────────┘
```

---

## File Structure

```
deep-agents/
├── .env                          # API keys
├── .gitignore                    # .env excluded
├── CLAUDE.md                     # Project context
├── requirements.txt              # Python dependencies
├── README.md                     # Devpost description
│
├── data/
│   ├── seed_users.py             # Script to create 100 fake users in Ghost DB
│   ├── users.csv                 # 100 fake users (name, email, phone, password_hash)
│   └── breach_data.csv           # 500 leaked records (email, password_hash, source)
│
├── src/
│   ├── config.py                 # Load .env, initialize all clients
│   ├── db.py                     # Ghost DB connection + queries
│   ├── agent.py                  # Main agent loop (the brain)
│   ├── matcher.py                # Breach matching logic
│   ├── auth0_actions.py          # Lock accounts, revoke sessions
│   ├── bland_caller.py           # Make notification calls
│   ├── airbyte_ingest.py         # Ingest breach CSV
│   └── state.py                  # Shared state that dashboard reads
│
├── dashboard/
│   └── app.py                    # Streamlit dashboard
│
└── ideas/
    └── SENTINEL.md               # This plan
```

---

## Database Schema (Ghost Postgres)

### `users` — Pre-seeded with 100 fake users
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    auth0_user_id TEXT,          -- Auth0 user ID for blocking
    password_hash TEXT NOT NULL,  -- bcrypt hash
    status TEXT DEFAULT 'active', -- active | locked | warned
    created_at TIMESTAMP DEFAULT NOW()
);
```

### `breach_events` — Created when breach file is uploaded
```sql
CREATE TABLE breach_events (
    id SERIAL PRIMARY KEY,
    breach_source TEXT,           -- "darkweb_forum_x"
    total_records INTEGER,        -- 500
    matched_users INTEGER,        -- 40
    critical_users INTEGER,       -- 12
    warned_users INTEGER,         -- 28
    status TEXT DEFAULT 'analyzing', -- analyzing | responding | complete
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### `agent_log` — Every agent thought/action (powers the reasoning stream)
```sql
CREATE TABLE agent_log (
    id SERIAL PRIMARY KEY,
    breach_id INTEGER REFERENCES breach_events(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    phase TEXT,                   -- 'ingest' | 'match' | 'analyze' | 'lock' | 'notify'
    message TEXT,                 -- "Found 12 critical matches"
    detail TEXT,                  -- JSON with extra context
    log_type TEXT DEFAULT 'info'  -- 'info' | 'action' | 'decision' | 'error'
);
```

### `response_actions` — Every concrete action taken
```sql
CREATE TABLE response_actions (
    id SERIAL PRIMARY KEY,
    breach_id INTEGER REFERENCES breach_events(id),
    user_id INTEGER REFERENCES users(id),
    action_type TEXT,             -- 'account_locked' | 'session_revoked' | 'call_made' | 'call_completed'
    severity TEXT,                -- 'critical' | 'warning'
    status TEXT DEFAULT 'pending', -- 'pending' | 'in_progress' | 'complete' | 'failed'
    detail TEXT,                  -- JSON (call_id, auth0 response, etc.)
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Component Details

### 1. `config.py` — Initialize Everything

```python
# Loads .env
# Creates: anthropic client, auth0 management client, bland headers,
#          ghost db connection, overmind init, truefoundry config
# All other modules import from here
```

Key clients:
- `anthropic.Anthropic()` — Claude
- `Auth0` Management API client — for blocking users
- `requests` with Bland auth header — for calls
- `psycopg2` connection to Ghost DB
- `overmind_sdk.init()` — auto-traces Claude calls
- Truefoundry base URL + token for gateway

### 2. `db.py` — Ghost DB Operations

Functions needed:
- `get_connection()` → psycopg2 connection
- `get_all_users()` → list of user dicts
- `get_user_by_email(email)` → user dict or None
- `update_user_status(user_id, status)` → marks user as locked/warned
- `create_breach_event(source, total_records)` → returns breach_id
- `update_breach_event(breach_id, **fields)` → update counts/status
- `log_agent_action(breach_id, phase, message, detail, log_type)` → reasoning log
- `create_response_action(breach_id, user_id, action_type, severity)` → returns action_id
- `update_response_action(action_id, status, detail)` → update action
- `get_agent_log(breach_id)` → all log entries (for dashboard)
- `get_response_actions(breach_id)` → all actions (for dashboard)
- `get_breach_event(breach_id)` → current breach stats

### 3. `matcher.py` — Breach Matching

```python
def match_breach_data(breach_records, db_users):
    """
    For each leaked record:
    1. Check if email exists in our user DB
    2. If yes, check if password_hash matches
    3. Classify:
       - CRITICAL: email matches AND hash matches (reused password)
       - WARNING: email matches but hash differs (account exists, different password)
       - SAFE: no email match

    Returns: {
        "critical": [user_dicts...],
        "warning": [user_dicts...],
        "safe_count": int
    }
    """
```

This is a simple loop — no AI needed. Fast, deterministic matching.

### 4. `auth0_actions.py` — Lock Accounts

```python
def lock_user(auth0_client, auth0_user_id):
    """Block user via Auth0 Management API"""
    # PATCH /api/v2/users/{id} with {"blocked": true}

def revoke_sessions(auth0_client, auth0_user_id):
    """Revoke all active sessions"""
    # POST /api/v2/users/{id}/sessions/revoke

def lock_compromised_users(auth0_client, critical_users, breach_id, db):
    """Lock all critical users, log each action"""
    for user in critical_users:
        lock_user(auth0_client, user["auth0_user_id"])
        revoke_sessions(auth0_client, user["auth0_user_id"])
        db.update_user_status(user["id"], "locked")
        db.create_response_action(breach_id, user["id"], "account_locked", "critical")
        db.log_agent_action(breach_id, "lock",
            f"Locked account for {user['name']} ({user['email']})", ...)
```

### 5. `bland_caller.py` — Phone Notifications

```python
def call_user(user, breach_source):
    """Call a compromised user via Bland AI"""
    response = requests.post(
        "https://api.bland.ai/v1/calls",
        headers={"authorization": BLAND_API_KEY},
        json={
            "phone_number": user["phone"],
            "task": f"""You are a security notification agent for Acme Corp.
                You are calling {user['name']} to inform them about a security incident.

                Key facts to communicate:
                - Their account credentials were found in a data breach from {breach_source}
                - Their account has ALREADY been locked to protect them
                - They need to visit acme.com/reset to create a new password
                - They should change this password on any other sites where they used it
                - Their data is being monitored for further suspicious activity

                Be calm, professional, and reassuring. Answer any questions they have.
                If they ask technical questions you can't answer, tell them to email security@acme.com.""",
            "model": "enhanced",
            "first_sentence": f"Hi {user['name']}, this is the Acme Corp security team calling about your account.",
            "max_duration": 3,
            "record": True
        }
    )
    return response.json()  # contains call_id

def notify_critical_users(critical_users, breach_source, breach_id, db):
    """Call all critical users, log each call"""
    for user in critical_users:
        db.log_agent_action(breach_id, "notify",
            f"Calling {user['name']} at {user['phone']}...", ...)
        result = call_user(user, breach_source)
        db.create_response_action(breach_id, user["id"], "call_made", "critical",
            detail=json.dumps({"call_id": result.get("call_id")}))
```

### 6. `agent.py` — The Brain (Main Loop)

This is the core. It orchestrates everything.

```python
async def run_sentinel(breach_file_path: str):
    """
    Main agent loop. Called when breach file is uploaded.
    Every step logs to agent_log so the dashboard can show reasoning.
    """

    # PHASE 1: INGEST
    log("ingest", "Breach file detected. Ingesting data...")
    breach_records = load_breach_csv(breach_file_path)  # via Airbyte or direct
    breach_id = db.create_breach_event(source="darkweb_forum_x", total=len(breach_records))
    log("ingest", f"Loaded {len(breach_records)} leaked credential pairs")

    # PHASE 2: MATCH
    log("match", "Cross-referencing against user database...")
    users = db.get_all_users()
    results = match_breach_data(breach_records, users)

    db.update_breach_event(breach_id,
        matched=len(results["critical"]) + len(results["warning"]),
        critical=len(results["critical"]),
        warned=len(results["warning"]))

    log("match", f"CRITICAL: {len(results['critical'])} users (password hash match)")
    log("match", f"WARNING: {len(results['warning'])} users (email match, different password)")
    log("match", f"SAFE: {results['safe_count']} records (no match in our system)")

    # PHASE 3: ANALYZE (Claude decides response strategy)
    log("analyze", "Analyzing breach severity and planning response...")

    analysis = claude.messages.create(
        model="claude-sonnet-4-6-20250514",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""A data breach has been detected. Here's the situation:

            - Source: darkweb_forum_x
            - Total leaked records: {len(breach_records)}
            - Users in our system affected: {len(results['critical']) + len(results['warning'])}
            - CRITICAL (password match): {len(results['critical'])}
            - WARNING (email only): {len(results['warning'])}

            Critical users (password hash matches our records — they reused passwords):
            {json.dumps([{"name": u["name"], "email": u["email"]} for u in results["critical"]])}

            Provide a brief incident assessment:
            1. Severity rating (P1/P2/P3)
            2. Immediate actions to take
            3. What to tell affected users
            Keep it concise — 3-4 sentences total."""
        }]
    )

    log("analyze", f"Claude assessment: {analysis.content[0].text}", log_type="decision")

    # PHASE 4: LOCK ACCOUNTS
    log("lock", f"Locking {len(results['critical'])} critical accounts via Auth0...")
    lock_compromised_users(auth0_client, results["critical"], breach_id, db)
    log("lock", f"All {len(results['critical'])} critical accounts locked. Sessions revoked.")

    # Also warn the email-only matches
    for user in results["warning"]:
        db.update_user_status(user["id"], "warned")
        db.create_response_action(breach_id, user["id"], "warned", "warning")
    log("lock", f"Flagged {len(results['warning'])} warning-level accounts for monitoring.")

    # PHASE 5: NOTIFY BY PHONE
    log("notify", f"Calling {len(results['critical'])} critical users to notify them...")
    notify_critical_users(results["critical"], "darkweb_forum_x", breach_id, db)
    log("notify", "All critical users have been called.")

    # PHASE 6: COMPLETE
    db.update_breach_event(breach_id, status="complete", completed_at=datetime.now())
    log("complete", f"Breach response complete. Total time: {elapsed}s")
```

### 7. `dashboard/app.py` — Streamlit Dashboard

The dashboard is the DEMO. It's what judges see for 3 minutes.

**Layout: 3 columns + header**

```
┌─────────────────────────────────────────────────────────┐
│  🛡️ SENTINEL — Autonomous Breach Response               │
│  Status: ● RESPONDING          Elapsed: 2m 34s          │
├──────────────┬──────────────────────┬───────────────────┤
│              │                      │                   │
│  BREACH      │  AGENT REASONING     │  RESPONSE LOG     │
│  OVERVIEW    │                      │                   │
│              │  [11:42:03]          │  ● sarah@acme.com │
│  ┌────────┐  │  Breach file         │    LOCKED ✓       │
│  │  500   │  │  detected.           │    Called ✓        │
│  │ leaked │  │  Ingesting data...   │                   │
│  └────────┘  │                      │  ● john@acme.com  │
│              │  [11:42:05]          │    LOCKED ✓       │
│  ┌────────┐  │  Loaded 500 leaked   │    Calling...     │
│  │   12   │  │  credential pairs    │                   │
│  │CRITICAL│  │                      │  ● mike@acme.com  │
│  │  🔴    │  │  [11:42:08]          │    LOCKED ✓       │
│  └────────┘  │  Cross-referencing   │    Pending call   │
│              │  against user DB...  │                   │
│  ┌────────┐  │                      │  ● lisa@acme.com  │
│  │   28   │  │  [11:42:12]          │    WARNED ⚠️      │
│  │WARNING │  │  CRITICAL: 12 users  │                   │
│  │  🟡    │  │  (password match)    │                   │
│  └────────┘  │                      │                   │
│              │  [11:42:15]          │                   │
│  ┌────────┐  │  🤖 DECISION:        │                   │
│  │  460   │  │  "P1 severity.       │                   │
│  │ SAFE   │  │  Immediate account   │                   │
│  │  🟢    │  │  lockdown required." │                   │
│  └────────┘  │                      │                   │
│              │  [11:42:18]          │                   │
│  ┌────────┐  │  Locking 12 accounts │                   │
│  │  12/12 │  │  via Auth0...        │                   │
│  │ LOCKED │  │                      │                   │
│  └────────┘  │  [11:42:22]          │                   │
│              │  All accounts locked. │                   │
│  ┌────────┐  │  Calling users...    │                   │
│  │  3/12  │  │                      │                   │
│  │ CALLED │  │                      │                   │
│  └────────┘  │                      │                   │
│              │                      │                   │
├──────────────┴──────────────────────┴───────────────────┤
│  Powered by: Anthropic | Auth0 | Ghost | Bland AI |     │
│  Airbyte | Aerospike | Overmind | Truefoundry           │
└─────────────────────────────────────────────────────────┘
```

**How it works technically:**

The agent writes to Ghost DB tables. The dashboard polls Ghost DB every 1 second using `st.rerun()` or `st.empty()` with a loop. As the agent progresses, the dashboard updates in real-time.

```python
import streamlit as st
import time
from src.db import get_breach_event, get_agent_log, get_response_actions

st.set_page_config(page_title="Sentinel", layout="wide")

# Header
st.title("🛡️ SENTINEL — Autonomous Breach Response")
breach = get_breach_event(latest=True)

if breach:
    status_color = {"analyzing": "🟡", "responding": "🔴", "complete": "🟢"}
    st.subheader(f"Status: {status_color.get(breach['status'], '⚪')} {breach['status'].upper()}")

# Three columns
col1, col2, col3 = st.columns([1, 2, 1.5])

with col1:  # Breach stats
    st.metric("Leaked Records", breach["total_records"])
    st.metric("Critical", breach["critical_users"], delta=None)
    st.metric("Warned", breach["warned_users"])
    st.metric("Accounts Locked", count_locked())
    st.metric("Users Called", count_called())

with col2:  # Agent reasoning stream
    st.subheader("Agent Reasoning")
    logs = get_agent_log(breach["id"])
    for log in logs:
        icon = {"info": "ℹ️", "action": "⚡", "decision": "🤖", "error": "❌"}
        st.markdown(f"**{log['timestamp'].strftime('%H:%M:%S')}** "
                    f"{icon.get(log['log_type'], '•')} {log['message']}")

with col3:  # Response actions per user
    st.subheader("Response Log")
    actions = get_response_actions(breach["id"])
    for user_email, user_actions in group_by_user(actions):
        locked = any(a["action_type"] == "account_locked" for a in user_actions)
        called = any(a["action_type"] == "call_made" for a in user_actions)
        st.markdown(f"**{user_email}**  "
                    f"{'🔒 Locked' if locked else '⏳'}  "
                    f"{'📞 Called' if called else ''}")

# Sponsor footer
st.divider()
st.caption("Powered by: Anthropic | Auth0 | Ghost | Bland AI | Airbyte | Aerospike | Overmind | Truefoundry")

# Auto-refresh every 2 seconds while breach is active
if breach and breach["status"] != "complete":
    time.sleep(2)
    st.rerun()
```

**Upload trigger:**
Add a file uploader at the top of the dashboard. When a CSV is uploaded, it kicks off the agent in a background thread:

```python
uploaded = st.file_uploader("Upload breach data", type="csv")
if uploaded and not st.session_state.get("running"):
    st.session_state.running = True
    # Save CSV to disk, start agent in background thread
    threading.Thread(target=run_sentinel, args=(csv_path,)).start()
```

This means the demo is:
1. Open dashboard (empty/idle)
2. Upload CSV
3. Watch everything happen in real-time

---

## Sponsor Integration Checklist

| Sponsor | Integration Point | Code Location | Prize |
|---------|------------------|---------------|-------|
| **Anthropic** | Claude analyzes breach severity, decides response | `agent.py` | core |
| **Ghost** | Primary Postgres DB for all state | `db.py` | $1,998 |
| **Auth0** | Lock accounts + revoke sessions via Management API | `auth0_actions.py` | $1,750 |
| **Airbyte** | Ingest breach CSV (PyAirbyte or direct load) | `airbyte_ingest.py` | $1,750 |
| **Bland AI** | Call affected users with notification | `bland_caller.py` | $500 |
| **Overmind** | `init()` in config.py — auto-traces all Claude calls | `config.py` (3 lines) | $651 |
| **Truefoundry** | Route Claude calls through AI Gateway | `config.py` | $600 |
| **Macroscope** | Connect GitHub repo for code review | (external) | $1,000 |
| **Kiro** | Build in Kiro IDE, write usage doc | (external) | credits |

---

## Build Order (Priority-Driven)

### BEFORE 11:00 AM (Pre-hackathon prep)
- [ ] `ghost create sentinel-db` — create the database
- [ ] Run SQL to create all 4 tables
- [ ] Generate and seed 100 fake users (with phone numbers from team)
- [ ] Create breach_data.csv (500 rows, 12 critical matches)
- [ ] Create 10-15 Auth0 test users that map to seeded DB users
- [ ] Test: `auth0.users.update(id, {"blocked": True})` works
- [ ] Test: Bland API call works with team member's phone
- [ ] Connect Macroscope to GitHub repo
- [ ] Create empty Streamlit app that connects to Ghost DB

### 11:00-12:00 — Core Agent Loop
Build `agent.py` with the full pipeline:
1. Load breach CSV
2. Match against users
3. Claude analysis
4. Log everything to agent_log

Test: run agent, verify agent_log table fills up correctly.

### 12:00-1:00 — Auth0 + Bland Integration
1. `auth0_actions.py` — lock accounts programmatically
2. `bland_caller.py` — make notification calls
3. Wire both into agent.py
4. Test: run full pipeline, verify accounts lock and call goes through

### 1:00-2:00 — Dashboard (Lunch overlap)
1. Build the 3-column Streamlit layout
2. Connect to Ghost DB — poll for updates
3. Add file uploader that triggers agent
4. Test: upload CSV in dashboard, watch it update in real-time

### 2:00-3:00 — Polish
1. Add Overmind tracing (3 lines in config.py)
2. Add Truefoundry gateway routing
3. Add Airbyte formal ingestion (or leave as direct CSV load)
4. Make dashboard look good — colors, icons, spacing
5. Add sponsor logos in footer

### 3:00-4:00 — Demo Prep
1. Full end-to-end test run (reset DB, upload fresh CSV, watch everything)
2. Record 3-minute backup demo video
3. Fix any bugs found during test
4. Write Devpost submission text
5. Write Kiro usage doc

### 4:00-4:30 — Submit
1. Push to public GitHub
2. Publish to shipables.dev
3. Upload demo recording + all Devpost fields
4. Double-check all submission requirements met

---

## Demo Execution Plan

### Setup (before going on stage)
- Reset DB: clear breach_events, agent_log, response_actions. Reset all user statuses to 'active'
- Open Streamlit dashboard in browser (full screen)
- Have breach_data.csv ready to upload
- Have teammate's phone ready (ringer ON, volume UP)
- Have Overmind console open in another tab (optional — to show traces)

### The 3 Minutes

**[0:00-0:15] Hook — The Problem**
*Dashboard is showing idle state — no breaches.*
"Data breaches affect 4 billion records a year. The average response time is 277 days. Sentinel responds in under 5 minutes. Watch."

**[0:15-0:35] Upload — Trigger the Agent**
*Drag breach_data.csv into the file uploader.*
"A dump of 500 leaked credentials just appeared. Sentinel takes over."
*Left column starts updating: 500 leaked... analyzing...*
*Middle column shows reasoning scrolling: "Ingesting data... Cross-referencing..."*

**[0:35-1:00] Matching — Finding Compromised Users**
*Numbers animate: 40 matches... 12 CRITICAL...*
*Agent reasoning: "12 users reused their passwords. These accounts are fully compromised."*
"Sentinel found 12 of our users in the breach with matching passwords. They're fully compromised."

**[1:00-1:30] Claude Analysis + Account Lockdown**
*Agent reasoning shows Claude's assessment: "P1 severity. Immediate lockdown."*
*Right column: users start showing "🔒 Locked" one by one*
"Sentinel classified this as P1 and is now locking all 12 accounts through Auth0. Active sessions revoked. Nobody can access these accounts."
*Left column: "12/12 LOCKED"*

**[1:30-2:20] The Phone Call — LIVE**
"But locking accounts isn't enough. Users need to know."
*Agent reasoning: "Calling sarah@acme.com..."*
*Teammate's phone RINGS in the room.*
*Let it play for ~30 seconds — agent introduces itself, explains the breach, gives next steps.*
*Right column updates: "📞 Called ✓"*
"Every critical user gets a personal call explaining what happened and what to do."

**[2:20-2:45] Results**
*Dashboard shows final state: all green.*
"In under 5 minutes, Sentinel:
- Analyzed 500 leaked credentials
- Found 12 compromised accounts
- Locked all of them via Auth0
- Called every affected user
- Logged every decision for compliance
Fully autonomous. Zero human intervention."

**[2:45-3:00] Tech + Close**
*Point to sponsor footer on dashboard.*
"Built with 8 sponsor integrations: Claude for reasoning, Ghost for data, Auth0 for identity, Airbyte for ingestion, Bland for voice, Overmind for observability, Truefoundry for governance, and Macroscope for code quality."

---

## Scoring Against Judging Criteria

| Criterion (20% each) | How Sentinel Scores | Score Est. |
|----------------------|--------------------|----|
| **Autonomy** | Upload CSV → everything happens automatically. Zero human intervention from start to finish. | 9/10 |
| **Idea** | Data breaches are a $4.5M avg cost problem. Every company needs this. Real-world value is obvious. | 8/10 |
| **Technical Implementation** | Ghost DB + Auth0 Management API + Bland calls + Claude reasoning + Overmind tracing + Streamlit dashboard. Clean architecture, working end-to-end. | 8/10 |
| **Tool Use** | 8 sponsor integrations (need 3 minimum). Ghost, Auth0, Airbyte, Bland, Overmind, Truefoundry, Macroscope, Kiro. | 10/10 |
| **Presentation** | Live demo with real-time dashboard. Phone rings in room. Clear metrics. Emotional hook. | 9/10 |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Auth0 Management API doesn't work | Test BEFORE the event. Have fallback: just update `status` in Ghost DB |
| Bland call fails during demo | Pre-record a backup call. Play it if live call doesn't connect in 10 seconds |
| Ghost DB connection issues | Have a local SQLite fallback. Swap connection string in config.py |
| Streamlit doesn't refresh properly | Use `st.empty()` containers with manual refresh loop instead of `st.rerun()` |
| Scope creep | STOP adding features at 2:00 PM. Only polish after that. |
| WiFi fails | Mobile hotspot as backup. All API keys work from any network. |
