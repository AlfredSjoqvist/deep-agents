# Idea 4: ScopeBot — Autonomous Code Review & Security Agent

## One-liner
An agent that watches your repo, reviews every PR for bugs and security issues, cross-references against your project docs, and calls the developer when it finds critical vulnerabilities.

## Why This Idea (Prize Optimization)
Designed to hit Macroscope AND Overmind hard (less competitive categories):
- **Macroscope** ($1,000): CORE — uses Macroscope's code review engine as the backbone
- **Overmind** ($651): Traces the agent's review decisions and security analysis
- **Auth0** ($1,750): Developer authentication + repo access control
- **Aerospike** ($650): Vulnerability pattern database + code embedding vectors
- **Bland** ($500): Calls developer for critical security vulnerabilities
- **Truefoundry** ($600): Deploy as a governed agent via AI Gateway

## How It Works
1. **Macroscope** reviews PRs for bugs and code quality issues
2. **Claude** performs deeper security analysis — OWASP Top 10, injection patterns
3. **Aerospike** stores vulnerability embeddings, matches against known CVE patterns
4. **Overmind** traces every review decision for audit trail
5. **Auth0** verifies developer identity before allowing merge approval
6. **Bland** calls the developer if a critical vulnerability is found
7. **Truefoundry** Gateway governs agent's access to repo and notification tools
8. Agent generates fix suggestions and can auto-create remediation PRs

## Sponsor Depth
| Sponsor | Integration | Prize | Depth |
|---------|------------|-------|-------|
| Macroscope | CORE — code review backbone | $1,000 | **DEEPEST** |
| Overmind | Review decision audit trail | $651 | DEEP |
| Auth0 | Developer auth + merge approval | $1,750 | MEDIUM |
| Aerospike | Vulnerability pattern vectors | $650 | MEDIUM |
| Bland | Critical vuln phone alerts | $500 | LIGHT |
| Truefoundry | Agent gateway | $600 | MEDIUM |

## Demo Script (3 min)
1. "Every merge could be a security incident. ScopeBot catches what humans miss." (10s)
2. New PR arrives — Macroscope reviews for code quality (20s)
3. Claude performs security analysis — finds SQL injection vulnerability (30s)
4. Aerospike matches against CVE database (15s)
5. Overmind trace: full decision chain visible (20s)
6. LIVE: Agent calls developer: "Critical SQLi found in PR #42, line 187..." (45s)
7. Agent generates fix, creates remediation PR (20s)
8. Auth0 approval flow for merge (10s)

## Feasibility (5.5 hrs)
Macroscope has easy GitHub integration. Overmind is 3 lines. Main work: security analysis prompts.
Risk: Low-Medium — depends on Macroscope API access working smoothly.

## EV Calculation
| Prize | P(1st) | P(2nd) | P(3rd) | EV |
|-------|--------|--------|--------|-----|
| Macroscope $1,000 | 20% | — | — | $200 |
| Overmind $651 | 18% | 10% | — | $117+? |
| Auth0 $1K/$500/$250 | 8% | 6% | 5% | $123 |
| Aerospike $500/$100/$50 | 8% | 6% | 5% | $49 |
| Truefoundry $600 | 10% | — | — | $60 |
| Bland $500 | 5% | — | — | $25 |
| Unlisted grand ~$4K | 4% | 3% | 2% | $280 |
| **TOTAL** | | | | **$854** |
