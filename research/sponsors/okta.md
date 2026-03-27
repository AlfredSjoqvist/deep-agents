# Okta — Identity & Auth for AI Agents

## Role in Project
**Secure agent identity and authorization.** Ensure agents only access what they should.

## Why Identity Matters for Agents
- Agents act on behalf of users — calling APIs, reading docs, modifying data
- Without proper identity: prompt injection, unauthorized access, no audit trail
- Only 10% of orgs have a strategy for non-human identities, yet 91% already use AI agents
- Okta's position: **every agent needs an identity** as a first-class entity

## Two Product Lines (USE Auth0 FOR HACKATHON)

| | **Okta for AI Agents** (Enterprise) | **Auth0 for AI Agents** (Developer) |
|---|---|---|
| GA date | April 30, 2026 | October 2025 (ALREADY GA) |
| Target | IT admins governing fleets of agents | **Developers building agent apps** |
| Key features | Agent Gateway, Universal Directory, XAA protocol | Token Vault, Async Auth (CIBA), FGA for RAG |
| Free tier | 100 MAUs | **25,000 MAUs** (no credit card) |
| Sign up | developer.okta.com/signup | **auth0.com** |

## Auth0 for AI Agents — Core Capabilities

### 1. Token Vault
Securely connects agents to third-party tools (Gmail, Slack, GitHub) via OAuth 2.0. Handles token storage, automatic refresh, exchange — agent never touches raw credentials.

### 2. Async Authorization (Human-in-the-Loop)
Uses CIBA (Client-Initiated Backchannel Authentication). Agent pauses on high-risk actions, sends approval request to human, resumes after approval.

### 3. Fine-Grained Authorization (FGA) for RAG
Document-level access control. Before agent returns retrieved docs, FGA checks user has permission to see each document. Built on OpenFGA (relationship-based).

### 4. Framework Integrations
First-class SDKs for:
- **LangChain / LangGraph** (Python)
- **LlamaIndex** (Python)
- **Vercel AI SDK** (TypeScript)
- **Amazon Bedrock AgentCore**
- **Google GenKit**

Open-source repo: https://github.com/auth0/auth-for-genai

## Quick Start (Auth0 — recommended for hackathon)

### Step 1: Create Free Account
Go to https://auth0.com — 25,000 MAUs free, no credit card.

### Step 2: Install SDK
```bash
# Python
pip install auth0-ai

# Node.js / TypeScript
npm install @auth0/ai
```

### Step 3: Configure
- Create application in Auth0 Dashboard
- Note your Domain, Client ID, Client Secret
- Enable connections (Google, GitHub, email/password)

### Step 4: Integrate with Agent Framework
```python
# With LangChain/LangGraph
from auth0_ai import Auth0AIClient

# Token delegation — agent operates with user's scoped OAuth token
# Token Vault — automatic refresh and revocation
# CIBA — human-in-the-loop for high-risk actions
```

### FGA Check Example
```python
# Before agent returns RAG results:
allowed = fga_client.check(
    user="agent:research-bot",
    relation="can_read",
    object="document:financial-report-2025"
)
if allowed:
    # return document to user
```

## Key Auth Patterns for Agents
1. **OAuth Token Delegation**: Agent operates with user's scoped token
2. **Human-in-the-Loop Gating**: Agent pauses for approval on high-risk actions (CIBA)
3. **Least-Privilege Scoping**: Request only needed OAuth scopes
4. **Document-Level Auth for RAG**: FGA checks before returning retrieved docs
5. **Audit Everything**: All agent actions logged through Auth0

## Integration Ideas for Hackathon
1. **Secure agent tools**: Agent authenticates via Auth0 before accessing APIs
2. **User-scoped access**: Agent inherits permissions from the user it serves
3. **Human approval for risky actions**: CIBA flow for high-stakes operations
4. **RAG with access control**: FGA ensures agent only returns authorized docs
5. **Audit trail**: Every agent action logged (great for Abdul's observability focus!)

## Docs
- Auth0 for AI Agents: https://auth0.com/ai
- Auth0 AI Docs: https://auth0.com/ai/docs
- GitHub SDK: https://github.com/auth0/auth-for-genai
- Human-in-the-Loop guide: https://auth0.com/blog/async-ciba-python-langgraph-auth0/
- Okta for AI Agents: https://www.okta.com/solutions/secure-ai/
- FGA: https://www.okta.com/products/fine-grained-authorization/
- Securing Bedrock AgentCore with Auth0: https://auth0.com/blog/securing-amazon-bedrock-agentcore-agents-auth0-for-ai-agents/
- Dev signup: https://auth0.com (free) or https://developer.okta.com/signup/
