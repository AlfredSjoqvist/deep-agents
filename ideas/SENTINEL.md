# Sentinel — Autonomous Breach Response & Research Agent

## The Pitch
"When a breach happens, security teams spend days investigating — matching compromised accounts, researching the attack vector, locking things down, and notifying users. Sentinel does all of it autonomously in minutes. It ingests breach data, matches compromised accounts, researches the CVE and attack method, locks accounts, recommends patches, and calls affected users — all while every decision is traced."

## What It Does (Step by Step)

```
TRIGGER: Breach data file uploaded (leaked email + password hash pairs)
                    |
                    v
    ┌─── PHASE 1: INGEST & MATCH ───┐
    │                                │
    │  [Airbyte] Ingest breach CSV   │
    │  [Ghost DB] User database      │
    │  [Aerospike] Fast email lookup  │
    │  → Match leaked creds against  │
    │    our users                   │
    │  → Classify: CRITICAL (hash    │
    │    matches), WARN (email only),│
    │    SAFE (no match)             │
    └────────────┬───────────────────┘
                 │
                 v
    ┌─── PHASE 2: RESEARCH ──────────┐
    │                                │
    │  [Claude] Analyze the breach:  │
    │  - What attack vector?         │
    │  - Which CVE?                  │
    │  - What systems are affected?  │
    │                                │
    │  [Senso] Pull relevant context │
    │  - Security advisories         │
    │  - Patch recommendations       │
    │  - Company policy docs         │
    │                                │
    │  [Aerospike] Store research    │
    │  as vectors for future lookups │
    │  → Generate: Incident Report   │
    │    with CVE details, severity, │
    │    recommended patches         │
    └────────────┬───────────────────┘
                 │
                 v
    ┌─── PHASE 3: RESPOND ───────────┐
    │                                │
    │  [Auth0] Lock compromised      │
    │  accounts via Management API   │
    │  Revoke active sessions        │
    │                                │
    │  [Bland AI] Call critical      │
    │  users: "Your account was      │
    │  compromised. We've locked it. │
    │  Here's what to do next..."    │
    │                                │
    │  [Ghost DB] Log every action   │
    │  in response_log table         │
    └────────────┬───────────────────┘
                 │
                 v
    ┌─── ALWAYS RUNNING ─────────────┐
    │  [Overmind] Traces every       │
    │  decision automatically        │
    │  [Truefoundry] Routes LLM      │
    │  calls through AI Gateway      │
    │  [Dashboard] Real-time view    │
    └────────────────────────────────┘
```

## The Breach Scenario (Pre-seeded)

**Ghost DB `users` table** (100 fake users):
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    auth0_user_id TEXT,
    password_hash TEXT,
    status TEXT DEFAULT 'active'
);
```

**Breach file** (breach_data.csv — ~500 rows):
```csv
leaked_email,leaked_password_hash,source
sarah@acme.com,$2b$12$abc...,darkweb_forum_x
random@gmail.com,$2b$12$xyz...,darkweb_forum_x
john@acme.com,$2b$12$def...,darkweb_forum_x
```

**Matching results:**
- ~40 emails match our user DB
- ~12 have matching password hashes = CRITICAL (reused passwords)
- ~28 email-only match = WARNING (credentials different, still notify)
- ~460 no match = not our users

**Research context:**
- The breach came from "DarkForum X" exploiting CVE-2026-1234
- Attack vector: SQL injection in a third-party auth provider
- Affected software: AuthLib v3.2.1
- Recommended patch: upgrade to AuthLib v3.2.2

## Sponsor Integration Map

| Sponsor | What It Does in Sentinel | Integration Type | Prize |
|---------|-------------------------|-----------------|-------|
| **Ghost** | Primary database — users, breach_events, response_log tables. Agent reads/writes all state here. | CORE | $1,998 |
| **Auth0** | Locks compromised accounts via Management API. Revokes sessions. Verifies agent identity. | CORE | $1,750 |
| **Airbyte** | Ingests breach CSV into Ghost DB. Could also pull user data from external sources. | MEDIUM | $1,750 |
| **Aerospike** | Fast email lookup for matching. Stores research vectors for CVE/attack pattern similarity search. | MEDIUM | $650 |
| **Bland AI** | Calls CRITICAL users with personalized breach notification. | MEDIUM | $500 |
| **Overmind** | 3 lines of code — auto-traces every Claude decision. Shows full investigation chain. | FREE (3 lines) | $651 |
| **Truefoundry** | Routes all Claude API calls through AI Gateway for governance/monitoring. | MEDIUM | $600 |
| **Senso** | Provides context docs — security advisories, CVE databases, company policies for the research phase. | LIGHT | credits |
| **Macroscope** | Connect repo — free code review prize shot. | META | $1,000 |
| **Kiro** | Build in Kiro IDE — write up spec-driven dev. | META | credits |

**Total eligible cash: $7,149 + $1,000 (Macroscope) = $8,149**

## Build Plan (5.5 Hours)

### Pre-hackathon (NOW — before 11 AM)
- [ ] Get Bland API key in .env ✓
- [ ] Get Overmind API key → console.overmindlab.ai
- [ ] Run `ghost login` → `ghost create sentinel-db`
- [ ] Create Ghost DB tables (users, breach_events, response_log)
- [ ] Seed 100 fake users
- [ ] Create breach_data.csv (500 rows)
- [ ] Create 10-15 real Auth0 test users (so blocking works live)
- [ ] Test: can you call the Bland API? Can you block an Auth0 user?
- [ ] Connect Macroscope to your GitHub repo
- [ ] Install Kiro IDE if not already

### Hour 1 (11:00-12:00): Data layer + ingestion
- Ghost DB tables created and seeded
- Airbyte: PyAirbyte loads breach CSV into Ghost DB
- Aerospike: index user emails for fast matching
- Write the matching logic: leaked emails → user DB → classify CRITICAL/WARN/SAFE
- Overmind: `init(service_name="sentinel")` — done in 30 seconds

### Hour 2 (12:00-1:00): Research phase + Claude brain
- Claude analyzes the breach:
  - "What attack vector caused this breach?"
  - "What CVE is associated?"
  - "What systems/software are affected?"
  - "What patches are recommended?"
- Senso: feed security context docs (CVE data, advisories)
- Aerospike: store research results as vectors
- Generate incident report with findings

### Hour 3 (1:00-2:00): Response actions
- Auth0 Management API: block compromised users
  ```python
  auth0.users.update(user_id, {"blocked": True})
  ```
- Auth0: revoke active sessions
- Truefoundry: route Claude calls through gateway
- Update Ghost DB response_log with every action

### Hour 4 (2:00-3:00): Voice + dashboard
- Bland AI: call CRITICAL users
  ```python
  requests.post("https://api.bland.ai/v1/calls",
      headers={"authorization": BLAND_API},
      json={
          "phone_number": user["phone"],
          "task": f"You are calling from Acme Corp security team. Tell {user['name']} that their account was compromised in a data breach. Their account has already been locked to protect them. They need to visit acme.com/reset to create a new password. Be calm, professional, and reassuring.",
          "model": "enhanced",
          "first_sentence": f"Hi {user['name']}, this is Sentinel Security from Acme Corp calling about your account security."
      })
  ```
- Streamlit dashboard:
  - Left: Breach status (total leaked, matched, critical, warned)
  - Middle: Agent reasoning stream (live — every thought scrolls by)
  - Right: Response log (accounts locked, calls made, research findings)

### Hour 5 (3:00-4:00): Polish + demo
- Full end-to-end run: upload CSV → matching → research → lock → call
- Fix bugs, improve dashboard visuals
- Record 3-minute backup demo video
- Write Devpost description + Kiro usage writeup

### Last 30 min (4:00-4:30): Submit
- Push to public GitHub
- Publish skill to shipables.dev
- Upload to Devpost with demo recording

## Demo Script (3 minutes)

### [0:00-0:15] Hook
"A data breach just hit. 500 leaked credentials from a dark web forum. 277 days — that's the average time companies take to respond. Sentinel responds in 5 minutes."

### [0:15-0:40] Phase 1: Ingest & Match
*Upload breach CSV. Dashboard lights up.*
"Sentinel ingested 500 leaked records through Airbyte. Cross-referencing against our user database in Ghost..."
*Numbers tick up: 40 matches found... 12 CRITICAL — password hashes match...*
"12 users reused their passwords. They're fully compromised."

### [0:40-1:15] Phase 2: Research
*Agent reasoning stream shows Claude thinking:*
"Now Sentinel researches the attack. What happened? How?"
*Show reasoning:*
- "Analyzing breach source... DarkForum X dump"
- "Identifying CVE... CVE-2026-1234: SQL injection in AuthLib v3.2.1"
- "Pulling security advisories via Senso..."
- "Recommended action: patch to AuthLib v3.2.2, force password resets"
*Show incident report generated with CVE details and patch recommendations.*

### [1:15-1:45] Phase 3: Lock Accounts
*Show Auth0 dashboard or dashboard counter:*
"Sentinel is now locking all 12 critical accounts via Auth0."
*Accounts getting blocked in real-time: 1... 5... 12. All locked.*
"Active sessions revoked. No compromised account can access anything."

### [1:45-2:30] Phase 3b: Call Affected Users — LIVE
"But we also need to tell the humans."
*Agent calls teammate's phone. Phone rings in the room.*
"Hi Sarah, this is Sentinel Security from Acme Corp. We detected unauthorized access to your account in a data breach earlier today. To protect you, we've already locked your account. You'll need to visit acme.com/reset to set a new password. Do you have any questions?"
*Show Overmind trace during the call — every decision visible.*

### [2:30-2:50] Results
*Show dashboard final state:*
"In 4 minutes and 12 seconds, Sentinel:
- Analyzed 500 leaked credentials
- Identified 12 critical, 28 at-risk accounts
- Researched the CVE and recommended patches
- Locked all 12 accounts via Auth0
- Called every critical user
- Full trace in Overmind, all data in Ghost, governed by Truefoundry"

### [2:50-3:00] Close
"8 sponsor integrations. Zero human intervention. This is what autonomous breach response looks like."

## Scope Management (CRITICAL)

The research phase is the scope creep risk. Here's how to manage it:

**MUST HAVE (without these, the demo doesn't work):**
- Breach CSV ingestion + user matching
- Auth0 account locking
- Bland notification call
- Streamlit dashboard with live reasoning
- Overmind tracing

**NICE TO HAVE (add if time allows):**
- CVE research via Claude (can be partially hardcoded for the demo)
- Senso integration for context docs
- Aerospike vector search (can fall back to simple DB lookups)
- Truefoundry gateway routing
- Airbyte formal pipeline (can fall back to direct CSV load)

**Rule: Get the MUST HAVEs working by 2:00 PM. Then add NICE TO HAVEs.**

If the research phase takes too long, hardcode the CVE findings and focus on the response actions. The demo still works — "Sentinel identified CVE-2026-1234 and recommended patches" is impressive whether Claude found it live or you seeded it. Nobody can tell the difference in a 3-minute demo.
