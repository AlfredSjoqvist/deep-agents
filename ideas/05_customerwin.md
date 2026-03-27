# Idea 5: CustomerWin — Autonomous Churn Prevention Agent

## One-liner
An agent that monitors customer health signals, detects churn risk, autonomously calls at-risk customers to resolve issues, and updates your CRM — turning churn into retention.

## Why This Idea (Prize Optimization)
Maximizes the two biggest cash prizes simultaneously:
- **Auth0** ($1,750): Customer identity verification before sharing account details on call
- **Airbyte** ($1,750): Pull customer data from CRM (HubSpot/Salesforce) + support tickets
- **Bland** ($500): Proactive retention calls to at-risk customers
- **Aerospike** ($650): Customer health score vectors + interaction history
- **Overmind** ($651): Trace churn prediction reasoning
- **Truefoundry** ($600): Deploy agent via gateway

Targets: "customer-support systems that actually resolve tickets" — hackathon's own example.

## How It Works
1. **Airbyte** pulls customer data + support tickets + usage metrics from CRM
2. **Claude** calculates churn risk score based on signals (declining usage, open tickets, sentiment)
3. **Aerospike** stores customer vectors, matches against historical churn patterns
4. **Auth0** verifies customer identity before sharing account-specific details
5. **Bland AI** calls at-risk customer: "Hi, we noticed [specific issue], how can we help?"
6. Agent resolves issue on the call OR escalates with full context
7. **Overmind** traces the entire prediction → action chain
8. CRM updated automatically via Airbyte

## Sponsor Depth
| Sponsor | Integration | Prize | Depth |
|---------|------------|-------|-------|
| Auth0 | Customer identity verification | $1,750 | DEEP |
| Airbyte | CRM + support ticket ingestion | $1,750 | DEEP |
| Bland | Proactive retention calls | $500 | DEEP |
| Aerospike | Customer health vectors | $650 | DEEP |
| Overmind | Prediction decision tracing | $651 | MEDIUM |
| Truefoundry | Agent gateway | $600 | LIGHT |
| Macroscope | Code review | $1,000 | META |

## Demo Script (3 min)
1. "You lose 30% of at-risk customers because nobody called them. CustomerWin does." (10s)
2. Airbyte pulls customer data — show churn risk dashboard (20s)
3. Claude flags customer: "Usage dropped 60%, 2 open tickets, negative sentiment" (20s)
4. Auth0 verifies customer identity in agent context (10s)
5. LIVE: Agent calls customer: "Hi Sarah, I noticed you had trouble with..." (60s)
6. Agent resolves issue during call, updates CRM (20s)
7. Overmind trace of full prediction → action chain (20s)
8. "CustomerWin saved 12 accounts worth $180K ARR this month." (10s)

## Feasibility (5.5 hrs)
Well-scoped. Airbyte HubSpot connector exists. Auth0 + Bland are straightforward.
Risk: Low — each piece is simple.

## EV Calculation
| Prize | P(1st) | P(2nd) | P(3rd) | EV |
|-------|--------|--------|--------|-----|
| Auth0 $1K/$500/$250 | 15% | 10% | 8% | $235 |
| Airbyte $1K/$500/$250 | 15% | 10% | 8% | $225 |
| Bland $500 | 12% | — | — | $60 |
| Aerospike $500/$100/$50 | 12% | 8% | 6% | $72 |
| Overmind $651 | 12% | 8% | — | $78+? |
| Truefoundry $600 | 5% | — | — | $30 |
| Macroscope $1,000 | 10% | — | — | $100 |
| Unlisted grand ~$4K | 5% | 4% | 3% | $380 |
| **TOTAL** | | | | **$1,180** |
