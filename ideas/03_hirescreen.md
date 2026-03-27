# Idea 3: HireScreen — Autonomous Interview Scheduling & Screening Agent

## One-liner
An agent that pulls candidates from your ATS, screens resumes, calls candidates for a phone screen, scores them, and schedules qualified ones for interviews — zero recruiter effort.

## Why This Idea (Prize Optimization)
Maximizes Bland's "Most Ab-Norm-al" prize (creative voice use):
- **Bland** ($500): Agent conducts phone screens AND schedules interviews via voice
- **Auth0** ($1,750): Candidate data access control + recruiter authentication
- **Airbyte** ($1,750): Pull candidates from ATS (Greenhouse connector available)
- **Aerospike** ($650): Candidate profile vectors for semantic matching to job requirements
- **Overmind** ($651): Trace screening decisions for bias auditing
- **Macroscope** ($1,000): Meta-tool

## How It Works
1. **Airbyte** pulls new candidates from Greenhouse/Lever ATS
2. **Claude** analyzes resumes against job requirements, generates screening questions
3. **Aerospike** stores candidate embeddings, matches against ideal candidate vectors
4. **Bland AI** calls candidates for 5-minute phone screen — asks tailored questions
5. **Claude** scores responses, generates candidate report
6. **Auth0** controls who sees candidate data (hiring manager vs. recruiter vs. agent)
7. **Overmind** traces every screening decision — useful for bias auditing
8. If qualified → **Bland** calls back to schedule interview

## Sponsor Depth
| Sponsor | Integration | Prize | Depth |
|---------|------------|-------|-------|
| Bland | Phone screen calls + scheduling callbacks | $500 | **DEEP** (2 call types) |
| Auth0 | Candidate data access control | $1,750 | DEEP |
| Airbyte | ATS data ingestion (Greenhouse/Lever) | $1,750 | DEEP |
| Aerospike | Candidate vectors + semantic matching | $650 | DEEP |
| Overmind | Decision tracing for bias audit | $651 | MEDIUM |
| Macroscope | Code review | $1,000 | META |

## Demo Script (3 min)
1. "Recruiters spend 23 hours/week on screening. HireScreen does it in minutes." (10s)
2. Airbyte pulls 5 candidates from ATS (15s)
3. Claude screens resumes, generates tailored questions (20s)
4. LIVE: Agent calls candidate for phone screen — asks 3 questions (60s)
5. Show Overmind trace of screening decision logic (20s)
6. Candidate scores displayed — one qualified (15s)
7. Agent calls qualified candidate to schedule interview (30s)
8. Auth0: show recruiter vs. hiring manager data access levels (10s)

## Feasibility (5.5 hrs)
Very buildable. Resume analysis is straightforward. Two Bland call types (screen + schedule).
Risk: Low — well-scoped pieces, clear demo flow.

## EV Calculation
| Prize | P(1st) | P(2nd) | P(3rd) | EV |
|-------|--------|--------|--------|-----|
| Auth0 $1K/$500/$250 | 14% | 10% | 8% | $220 |
| Airbyte $1K/$500/$250 | 12% | 8% | 6% | $175 |
| Bland $500 | 15% | — | — | $75 |
| Overmind $651 | 12% | 8% | — | $78+? |
| Aerospike $500/$100/$50 | 12% | 8% | 6% | $72 |
| Macroscope $1,000 | 10% | — | — | $100 |
| Unlisted grand ~$4K | 5% | 4% | 3% | $380 |
| **TOTAL** | | | | **$1,100** |
