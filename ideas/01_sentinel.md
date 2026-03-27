# Idea 1: Sentinel — Autonomous Data Breach Response Agent

## One-liner
An agent that monitors data sources for breach indicators, autonomously investigates the scope, locks down compromised accounts, and calls affected users to notify them.

## Why This Idea (Prize Optimization)
Designed to hit the TOP 5 cash prizes simultaneously:
- **Auth0** ($1,750): Agent uses Auth0 to lock compromised accounts, revoke tokens, verify user identity before sharing breach details
- **Airbyte** ($1,750): Ingests user data + breach indicators from multiple sources
- **Overmind** ($651): Auto-traces every agent decision (3 lines of code)
- **Aerospike** ($650): Stores user records + vector search for affected account matching
- **Bland** ($500): Calls affected users with personalized breach notification
- **Macroscope** ($1,000): Connect repo for code review prize (meta-tool)
- **Truefoundry** ($600): Deploy agent via AI Gateway
- **Ghost** ($1,998): TBD — ask at booth, potentially use Ghost for cross-app breach investigation

**Max eligible cash: $8,899** (every cash category)

## How It Works
1. **Airbyte** pulls user data from CRM/database + breach indicator feeds
2. **Claude** analyzes breach scope — which accounts, what data exposed, severity
3. **Aerospike** vector search matches compromised credentials against user DB
4. **Auth0** automatically locks affected accounts + revokes active sessions
5. **Bland AI** calls each affected user: "Your account was compromised, here's what we've done..."
6. **Overmind** traces every decision for full observability
7. **Truefoundry** Gateway governs agent's access to tools
8. Dashboard shows breach timeline, affected accounts, response status

## Sponsor Depth
| Sponsor | Integration | Prize | Depth |
|---------|------------|-------|-------|
| Auth0 | Lock accounts, revoke tokens, verify callers | $1,750 | DEEP |
| Airbyte | Ingest user data + breach feeds | $1,750 | DEEP |
| Overmind | Auto-trace all agent decisions | $651 | MEDIUM (3 lines) |
| Aerospike | User DB + vector matching | $650 | DEEP |
| Bland | Notify affected users by phone | $500 | MEDIUM |
| Truefoundry | Agent gateway/governance | $600 | MEDIUM |
| Macroscope | Code review on repo | $1,000 | META |
| Ghost | TBD | $1,998 | ASK AT BOOTH |

## Demo Script (3 min)
1. "A breach just hit. 847 accounts compromised. Watch what happens next." (10s)
2. Airbyte ingests breach data + user records (20s)
3. Claude analyzes scope, Aerospike matches affected users (30s)
4. Auth0 locks 847 accounts in real-time — show dashboard (20s)
5. Overmind trace: show every agent decision step (20s)
6. LIVE: Agent calls affected user with notification (45s)
7. Dashboard: "847 accounts locked, 612 users notified, 0 further exposure" (15s)

## Feasibility (5.5 hrs)
Simple pieces: Airbyte connector, Aerospike CRUD, Auth0 token revocation, Bland call, Overmind init.
Main risk: Auth0 account locking flow needs to work smoothly.

## EV Calculation
| Prize | P(1st) | P(2nd) | P(3rd) | EV |
|-------|--------|--------|--------|-----|
| Auth0 $1K/$500/$250 | 20% | 12% | 10% | $285 |
| Airbyte $1K/$500/$250 | 15% | 10% | 8% | $225 |
| Ghost $1,998 | 5% | — | — | $100 |
| Macroscope $1,000 | 10% | — | — | $100 |
| Overmind $651 | 18% | 10% | — | $117+? |
| Aerospike $500/$100/$50 | 15% | 10% | 8% | $89 |
| Truefoundry $600 | 12% | — | — | $72 |
| Bland $500 | 10% | — | — | $50 |
| Unlisted grand ~$4K | 6% | 4% | 3% | $405 |
| **TOTAL** | | | | **$1,443** |
