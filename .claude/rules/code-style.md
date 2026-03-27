# Code Style — Sentinel Agent

## Python
- Python 3.12+, use modern syntax (match/case, type unions with `|`)
- Type hints on public functions, skip on internal/hackathon-speed code
- Use `async/await` for all I/O operations (API calls, DB queries)
- Use `httpx` for HTTP calls (async-native), not `requests`
- Use `asyncpg` for Ghost DB (Postgres) connections
- Imports: stdlib → third-party → local, one blank line between groups
- f-strings for all string formatting
- No classes unless genuinely needed — prefer functions and dataclasses
- `@dataclass` for structured data, not dicts

## Error Handling
- Let exceptions propagate in agent code — the orchestrator catches them
- Log errors with `structlog` (structured JSON logging)
- Never silently swallow exceptions

## Files
- One concern per file, max ~200 lines
- All integrations go in `sentinel/integrations/`
- All agent logic goes in `sentinel/agent/`

## Speed Rules (Hackathon Mode)
- Working code > clean code
- Hardcode demo values if integration is taking >20 min
- Comment hardcoded values with `# HACKATHON: hardcoded for demo`
- No tests during hackathon — verify by running end-to-end
