# Idea Rankings — Cash EV (Final)

## Prize Pool Reality
| Category | 1st Cash | Total Cash | Competition Est. |
|----------|---------|-----------|-----------------|
| Ghost | $1,998 (team) | $1,998 | Unknown — unknown API |
| Auth0 | $1,000 | $1,750 | ~4-6 teams |
| Airbyte | $1,000 | $1,750 | ~4-6 teams |
| Macroscope | $1,000 | $1,000 | ~5-8 teams (meta-tool) |
| Overmind | $651 | $651 | ~3-5 teams |
| Aerospike | $500 | $650 | ~4-6 teams |
| Truefoundry | $600 | $600 | ~2-4 teams |
| Bland | $500 | $500 | ~5-8 teams |
| Unlisted/Grand | ~$4,000? | ~$4,000? | All teams |

**~12-15 teams total, ~47 participants.**

## Rankings

| Rank | Idea | Cash EV | Key Prize Targets | Risk |
|------|------|---------|--------------------|------|
| **1** | **Sentinel** (Breach Response) | **$1,443** | Auth0 + Airbyte + all others | Medium |
| **2** | **PipelineAgent** (Self-Healing Pipelines) | **$1,305** | Airbyte (deepest) + Auth0 + Grand | Medium |
| **3** | **CustomerWin** (Churn Prevention) | **$1,180** | Auth0 + Airbyte + Bland | **Low** |
| **4** | **HireScreen** (Candidate Screening) | **$1,100** | Auth0 + Airbyte + Bland | **Low** |
| **5** | **ScopeBot** (Code Review Security) | **$854** | Macroscope + Overmind | Low-Med |

## Why Sentinel is #1

It's the only idea with a plausible path to ALL 8 cash categories simultaneously:
- Auth0 is CORE (account locking, token revocation)
- Airbyte is CORE (data ingestion)
- Overmind is natural (trace breach investigation decisions)
- Aerospike is natural (user DB + vector matching)
- Truefoundry is natural (govern agent's access)
- Bland is natural (call affected users)
- Macroscope is free (meta-tool on repo)
- Ghost is TBD (ask at booth)

Even with modest win rates (10-20% per category), hitting 8 categories with $500-$1,750 each adds up fast.

## Recommendation

**Highest EV**: Build **Sentinel** — broadest prize eligibility, compelling demo, security angle.

**Safest (lowest risk)**: Build **CustomerWin** — simplest components, clearest demo, proven category ("customer support that resolves tickets" is the hackathon's own example).

**Best Airbyte shot**: Build **PipelineAgent** — Airbyte IS the product, strongest single-category probability.

## Universal Add-Ons (Do These Regardless)
1. `pip install overmind-sdk anthropic` → `init(service_name="my-agent")` → $651 shot for FREE
2. Connect repo to Macroscope → $1,000 shot for FREE
3. Build with Kiro IDE → write up spec-driven dev process → Kiro credits shot
4. Ask Ghost booth day-of → if API exists, integrate for $1,998 shot
