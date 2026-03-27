# Hackathon Constraints — ALWAYS FOLLOW

## Time
- Deadline: 4:30 PM PT, March 27, 2026
- Every decision should optimize for shipping before deadline
- If blocked >15 min on any single issue, hardcode and move on

## Judging Criteria (equal 20% each)
1. **Autonomy** — Agent acts on real-time data without manual intervention
2. **Idea** — Solves a meaningful, real-world problem
3. **Technical Implementation** — Well implemented
4. **Tool Use** — Effectively uses 3+ sponsor tools
5. **Presentation** — 3-min demo is compelling

## Scope Control
- NEVER add features not in CLAUDE.md MUST HAVE list without team approval
- NEVER refactor working code during hackathon
- NEVER write tests — verify by running the agent end-to-end
- NEVER spend >20 min on any single integration — fallback to hardcoded

## Demo Priority
- The demo IS the product. Optimize for demo impact.
- Phone call (Bland AI) = wow moment. Must work.
- Dashboard showing agent reasoning = visual proof of autonomy
- Auth0 lockdown = proof of real action
- Overmind trace = proof of observability

## Security
- Never commit .env files
- Never log API keys
- Never hardcode credentials in source files
- Use environment variables for all secrets
