# Sentinel — Autonomous Breach Response & Research Agent

## Project Overview
**Hackathon:** Deep Agents Hackathon @ AWS Builder Loft, SF — March 27, 2026
**Team:** Arya Teja Rudraraju + Alfred Sjoqvist
**Deadline:** 4:30 PM PT today. No exceptions.

Sentinel is a hybrid autonomous agent that combines **breach response** with **research intelligence**. When a data breach is detected, it autonomously: ingests breach data, matches compromised accounts, researches the attack vector (CVEs, papers, advisories), locks accounts, calls affected users, and generates an incident report — all with full decision tracing.

## Architecture: Hybrid Sentinel + Research

```
Breach CSV → [Airbyte ingest] → [Ghost DB storage]
                                       ↓
                              [Aerospike fast match]
                                       ↓
                              [Claude research phase]
                              - CVE analysis
                              - Attack vector identification
                              - Patch recommendations
                              [Senso context retrieval]
                                       ↓
                              [Auth0 account lockdown]
                              [Bland AI phone calls]
                                       ↓
                              [Ghost DB response log]
                              [Overmind full trace]
```

## Sponsor Integration Map (8+ tools)

| Sponsor | Role | Priority |
|---------|------|----------|
| **Ghost DB** (ghost.build) | Core Postgres — users, breach_events, response_log, research_cache | CORE |
| **Auth0** | Lock compromised accounts, revoke sessions via Management API | CORE |
| **Bland AI** | Call CRITICAL users with breach notification | CORE |
| **Overmind** | Trace every agent decision (2 lines of code) | CORE |
| **Truefoundry** | Route LLM calls through AI Gateway | CORE |
| **Aerospike** | Fast email lookup, vector search for research results | MEDIUM |
| **Airbyte** | Ingest breach CSV into Ghost DB | MEDIUM |
| **Senso** | Context store — security advisories, CVE data, company policies | MEDIUM |
| **Kiro** | IDE used for development (meta-tool for prize) | META |
| **Macroscope** | Code review on repo (meta-tool for prize) | META |

## Tech Stack
- **Language:** Python 3.12+
- **Agent framework:** Raw Python + Claude API (tool use)
- **Database:** Ghost DB (Postgres) — ghost.build
- **Cache/Search:** Aerospike (fast KV + vector)
- **LLM:** Claude via Truefoundry AI Gateway
- **UI:** Streamlit dashboard
- **Tracing:** Overmind SDK

## Critical Constraints

### Time
- It is currently hackathon day. Every minute counts.
- Get MUST-HAVEs working first, then NICE-TO-HAVEs.
- If something takes >20 min to debug, hardcode it and move on.

### Code Quality
- Working > perfect. This is a hackathon.
- But NO security vulnerabilities — we're building a security product.
- `python -m py_compile` must pass on every file.
- Type hints on public functions only.

### Scope Management
**MUST HAVE (demo won't work without these):**
- Ghost DB with seeded users + breach data
- Breach CSV ingestion + email matching
- Auth0 account locking
- Bland AI phone call to affected user
- Overmind tracing
- Streamlit dashboard showing agent reasoning

**NICE TO HAVE (add after 2:00 PM if MUST HAVEs work):**
- Full CVE research via Claude (can hardcode findings for demo)
- Senso context integration
- Aerospike vector search (can fall back to Ghost DB queries)
- Truefoundry gateway routing (can fall back to direct Claude API)
- Airbyte formal pipeline (can fall back to direct CSV load into Ghost)

### Demo
- 3 minutes, no slides, live demo preferred
- Record a backup video by 4:00 PM
- Phone call is the wow moment — test Bland AI early

## File Structure
```
sentinel/
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py     # Main agent loop
│   ├── breach_analyzer.py  # Phase 1: ingest & match
│   ├── researcher.py       # Phase 2: CVE research
│   └── responder.py        # Phase 3: lock + call
├── integrations/
│   ├── ghost_db.py         # Ghost DB client
│   ├── auth0_client.py     # Auth0 Management API
│   ├── bland_caller.py     # Bland AI phone calls
│   ├── aerospike_store.py  # Aerospike fast lookup
│   ├── overmind_tracer.py  # Overmind init + helpers
│   ├── truefoundry_llm.py  # LLM via Truefoundry gateway
│   ├── senso_context.py    # Senso context retrieval
│   └── airbyte_ingest.py   # Airbyte CSV ingestion
├── dashboard/
│   └── app.py              # Streamlit dashboard
├── data/
│   ├── seed_users.py       # Generate 100 fake users
│   ├── breach_data.csv     # 500 leaked credentials
│   └── seed_breach.py      # Generate breach CSV
├── config.py               # Load .env, constants
├── main.py                 # Entry point
└── requirements.txt
```

## Environment Variables (.env — NEVER commit)
```
GHOST_CONNECTION_STRING=
AUTH0_DOMAIN=
AUTH0_CLIENT_ID=
AUTH0_CLIENT_SECRET=
AUTH0_MANAGEMENT_API_TOKEN=
BLAND_API_KEY=
OVERMIND_API_KEY=
TRUEFOUNDRY_API_KEY=
AEROSPIKE_HOST=127.0.0.1
AEROSPIKE_PORT=3000
SENSO_API_KEY=
ANTHROPIC_API_KEY=
AIRBYTE_API_KEY=
```

## Git Workflow
- Work on feature branches, merge to main via fast-forward
- Conventional commits: `feat(scope): description`
- Both team members push to shared branches
- Commit early, commit often

## Team Division
- **Arya:** Agent orchestration, memory/context architecture, Overmind, Truefoundry, research phase, Senso
- **Alfred:** Auth0 integration, Bland AI calls, Aerospike, Ghost DB setup, dashboard UI, Airbyte
