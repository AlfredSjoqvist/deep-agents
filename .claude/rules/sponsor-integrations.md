# Sponsor Integration Reference

## Ghost DB (ghost.build) — Core Database
- PostgreSQL database-as-a-service with MCP support
- Auth: `ghost login` (GitHub OAuth)
- Create: `ghost create sentinel-db`
- Connect: `ghost connect sentinel-db` → returns connection string
- Schema: `ghost schema sentinel-db` → LLM-optimized schema
- SQL: `ghost sql sentinel-db "SELECT * FROM users LIMIT 5"`
- Fork: `ghost fork sentinel-db` → safe experimentation
- Free: 100 compute hours/month, 1TB storage
- Use asyncpg for Python connections

## Auth0 — Account Lockdown
- Management API to block/unblock users
- `pip install auth0-python`
- Get Management API token: POST to `https://{domain}/oauth/token`
- Block user: `PATCH /api/v2/users/{id}` with `{"blocked": true}`
- Delete sessions: `DELETE /api/v2/users/{id}/sessions`
- Free: 25,000 MAU

## Bland AI — Phone Calls
- One POST call to make a phone call
- `POST https://api.bland.ai/v1/calls`
- Headers: `{"authorization": "YOUR_API_KEY"}`
- Body: `{"phone_number": "+1...", "task": "...", "first_sentence": "..."}`
- Returns call_id immediately, call happens async
- Free: 100 calls/day, $0.14/min connected

## Overmind — Agent Tracing
- 2 lines of code, auto-instruments all LLM calls
- `pip install overmind`
- `from overmind import init; init(overmind_api_key="...", service_name="sentinel")`
- Works with OpenAI, Anthropic, any LLM client
- View traces at console.overmindlab.ai
- Free during alpha

## Truefoundry — AI Gateway
- Drop-in OpenAI-compatible endpoint
- `base_url = "https://llm.truefoundry.com/api/v1"`
- `model = "anthropic/claude-sonnet-4-20250514"` (or other models)
- Free: 50,000 requests/month

## Aerospike — Fast KV + Vector Search
- `pip install aerospike`
- Docker: `docker run aerospike/aerospike-server`
- Client: `aerospike.client({'hosts': [('127.0.0.1', 3000)]}).connect()`
- Fast email lookup: store user emails as keys
- Vector search: `pip install aerospike-vector-search`
- Free: Community Edition, self-hosted

## Senso.ai — Context Store
- RAG-as-a-service: upload docs, query with context
- Upload: `POST https://sdk.senso.ai/api/v1/content/raw` with `X-API-Key` header
- Query: `POST https://sdk.senso.ai/api/v1/search` with query string
- Returns cited answers from ingested content

## Airbyte — Data Ingestion
- `pip install airbyte`
- PyAirbyte for local CSV-to-DB ingestion
- 600+ connectors
- Free: 14-day trial, 400 credits

## Macroscope — Code Review (Meta)
- Install GitHub App on the repo
- No code integration needed

## Kiro — IDE (Meta)
- Use Kiro to develop, write up spec-driven development usage
