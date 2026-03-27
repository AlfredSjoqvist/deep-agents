# Deep Agents Hackathon — Project Context

## What This Is
The **Deep Agents Hackathon** — one-day in-person buildathon at AWS Builder Loft, San Francisco.
Organized by Creators Corner / tokens&. **Today, March 27, 2026.**

## Hard Constraints
- **47 participants** (~12-15 teams)
- **5.5 hours coding**: 11:00 AM - 4:30 PM PT
- **3-minute demo** presentations to judges
- **Max team size**: 4
- **Must use at least 3 sponsor tools**
- **Must submit**: 3-min demo recording, public GitHub repo, publish skill to shipables.dev
- **No previous projects** — fresh code only, GitHub will be checked

## Schedule
| Time | Event |
|------|-------|
| 9:30 AM | Doors open |
| 10:00 AM | Keynote & opening remarks |
| 11:00 AM | START CODING |
| 1:30 PM | Lunch |
| 4:30 PM | SUBMISSION DEADLINE |
| 5:00 PM | Finalist presentations |
| 7:00 PM | Awards ceremony |

## Judging Criteria (20% each, equal weight)
1. **Autonomy** — How well does the agent act on real-time data without manual intervention?
2. **Idea** — Does the solution solve a meaningful problem or demonstrate real-world value?
3. **Technical Implementation** — How well was the solution implemented?
4. **Tool Use** — Did the solution effectively use at least 3 sponsor tools?
5. **Presentation (Demo)** — Demonstration of the solution in 3 minutes

## Prize Structure (ACTUAL — from Devpost)

**Total: $17,850+ in prizes (cash + credits)**

### Cash Prizes (real money)
| Category | Cash | Winners | Details |
|----------|------|---------|---------|
| **Best Use of Ghost** | **$1,998** | 1 | $500 Visa GC per team member |
| **Best Use of Auth0** | **$1,750** | 3 | $1,000 / $500 / $250 Amazon GC |
| **Airbyte: Conquer with Context** | **$1,750** | 3 | $1,000 / $500 / $250 Visa GC |
| **Most Innovative Macroscope** | **$1,000** | 1 | $1,000 + $250pp credits + Divoom speaker |
| **Most Innovative Aerospike** | **$650** | 3 | $500 / $100 / $50 Visa |
| **Overmind Builders Prize** | **$651** | 2 | $651 + mystery prize |
| **Truefoundry: Best AI Gateway** | **$600** | 1 | $600 cash or hot air balloon tickets |
| **Most Ab-Norm-al Bland** | **$500** | 1 | $500 cash + $1,000 platform credits |
| **Total identifiable cash** | **$8,899** | | |

### Credit/Subscription Prizes (non-cash)
| Category | Value | Details |
|----------|-------|---------|
| Best Use of Kiro | ~$840 equiv | 1yr/6mo/3mo Kiro Pro+ subscriptions |
| Best use of Senso.ai | $6,000 credits | $3K/$2K/$1K in credits |

### Possibly unlisted: Grand Prize / Overall (~$4,000-9,000?)
The listed cash totals ~$8,899 but Devpost says "$17,850 in cash". There may be an unlisted grand prize or additional sponsor prizes announced at the event.

## Sponsors & Tools

### With Cash Prizes (prioritize these)
| Sponsor | What it does | Prize | How to integrate |
|---------|-------------|-------|-----------------|
| **Ghost** | AI assistant across 30+ apps, on-device privacy | $1,998 | tryghost.ai |
| **Auth0** (Okta) | Identity + auth for AI agents, Token Vault, FGA | $1,750 | `pip install auth0-ai` |
| **Airbyte** | 600+ data connectors, Agent Engine | $1,750 | `pip install airbyte` |
| **Macroscope** | AI code review, bug detection in PRs | $1,000 | macroscope.com (use during development) |
| **Aerospike** | Real-time DB, vector search, LangGraph memory | $650 | `pip install aerospike` |
| **Overmind** | Agent security/observability, behavior monitoring | $651 | overmindlab.ai |
| **Truefoundry** | AI Gateway for deploying/governing agents | $600 | truefoundry.com/ai-gateway |
| **Bland AI** | Voice AI phone calls (inbound + outbound) | $500 | `pip install bland` |

### With Credit-Only Prizes
| Sponsor | What | Prize |
|---------|------|-------|
| **Kiro** | AWS's spec-driven AI IDE (like Cursor) | Kiro Pro+ subscriptions |
| **Senso.ai** | AI platform (organizer-affiliated) | Credits |

### No Prize Category But Core Tech
| Sponsor | What | Role |
|---------|------|------|
| **Anthropic** | Claude API + Agent SDK | The LLM brain — use for all reasoning |
| **AWS** | Bedrock, Lambda, infrastructure | Hosting and compute |

## Meta-Tool Strategy (Free Prize Shots)
These tools are used DURING development, not in the product itself. Use them on ANY project for bonus prize eligibility:
- **Kiro**: Use Kiro IDE to build your project → eligible for Kiro prize. Write up how you used spec-driven development.
- **Macroscope**: Connect your GitHub repo to Macroscope for code review → eligible for Macroscope prize.

## Judges
Listed as "See Luma for judges" — likely same as announced:
- **Jon Turdiev** — Sr. Solutions Architect @ AWS (SA of the Year 2025)
- **Spencer Small** — Head of Engineering @ Bland AI
- **Lucca Psaila** — Customer Engineer @ Bland AI
- **Abdul Rahim Mirani** — Founder @ Baseline Labs (AgentBasis — agent observability)

## Key API Quick References
- **Bland AI**: `pip install bland` → `client.call(SendCall(phone_number, task))`
- **Auth0 for AI**: `pip install auth0-ai` — Token Vault, CIBA, FGA
- **Airbyte**: `pip install airbyte` → `ab.get_source(connector, config)`
- **Aerospike**: `pip install aerospike` + `pip install aerospike-vector-search`
- **Claude API**: `pip install anthropic` → `client.messages.create(model, tools, messages)`
- **Claude Agent SDK**: `pip install claude-agent-sdk` → `query(prompt, options)`
- **Ghost**: tryghost.ai — API TBD, check at sponsor booth
- **Truefoundry**: AI Gateway — truefoundry.com/agent-gateway
- **Overmind**: Agent observability — overmindlab.ai

## Development Guidelines
- **Language**: Python (all sponsor SDKs support it)
- **Framework**: Keep it thin — raw code / thin abstractions
- **Build with Kiro** IDE for the Kiro prize track
- **Connect Macroscope** to your repo for the Macroscope prize track
- **Publish to shipables.dev** — required for submission
- **Demo**: Record a 3-min backup video before 4:30 PM
