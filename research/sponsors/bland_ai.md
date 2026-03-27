# Bland AI — Voice AI Phone Agents

## Role in Project
The **voice interface** for the agent. Bland enables making and receiving phone calls with AI.
**CRITICAL**: 2 of 4 judges are from Bland AI. Integrating this is almost mandatory.

## What Bland Does
- AI-powered phone calls (inbound + outbound) + SMS + web chat
- 250+ enterprise customers, 60M+ AI phone calls handled
- Default LLM: Claude Instant (Anthropic), Whisper for transcription, ElevenLabs for TTS
- Enterprise-grade: SOC2 Type II, GDPR, HIPAA, PCI DSS compliant
- Custom voice cloning, multi-lingual support
- **Norm** (NEW March 26, 2026): AI that builds production-ready voice agents from a single prompt

## Pricing

| Plan | Monthly Fee | Per-Minute | Notes |
|------|------------|------------|-------|
| **Start (Free)** | $0 | $0.14/min | Low daily caps, enough for demos/testing |
| Build | $299/mo | ~$0.12/min | Higher concurrency |
| Scale | $499/mo | ~$0.11/min | Full features, priority support |
| Enterprise | Custom | Custom | Self-hosted, SIP, dedicated infra |

Free tier is fine for hackathon demos.

## Quick Start

### 1. Get API Key
Sign up at https://app.bland.ai/ — free tier, no credit card needed.

### 2. Install Python SDK
```bash
pip install bland
```

### 3. Send Your First Call (Python SDK)
```python
from blandai import SendCall, PronunciationObject
from blandai.client import BlandAI

client = BlandAI(api_key="YOUR_API_KEY")  # or set BLAND_API_KEY env var

client.call(
    request=SendCall(
        phone_number="+12025551234",
        task="You are a friendly scheduling assistant. Help the caller book an appointment.",
        model="enhanced",
        transfer_list={"default": "+10005551234"},
        pronunciation_guide=[
            PronunciationObject(word="API", pronunciation="A P I"),
        ],
    ),
)
```

### 4. Send Call via REST API
```bash
curl --request POST \
  --url https://api.bland.ai/v1/calls \
  --header 'Content-Type: application/json' \
  --header 'authorization: YOUR_API_KEY' \
  --data '{
    "phone_number": "+12025551234",
    "task": "You are a helpful assistant calling to confirm an appointment.",
    "model": "enhanced",
    "webhook": "https://your-server.com/call-complete"
  }'
```

### 5. Async Python Client
```python
from blandai.client import AsyncBlandAI
client = AsyncBlandAI(api_key="YOUR_API_KEY")
# Use await client.call(...) in async context
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/calls` | POST | Send outbound call (task or pathway_id) |
| `/v1/tools` | POST | Create custom tool (external API mid-call) |
| `/v1/intelligence/emotion-analysis` | POST | Analyze emotions from completed call |
| `/v1/postcall-webhooks` | POST | Register webhook for transcript delivery |
| `/v1/calls/{call_id}` | GET | Get call details and transcript |

Base URL: `https://api.bland.ai`

## Key Parameters for POST /v1/calls

| Parameter | Type | Description |
|-----------|------|-------------|
| phone_number | string | E.164 format (+1...) |
| task | string | Instructions for agent (up to 2000 chars) |
| pathway_id | string | Alternative to task — pre-built conversation flow |
| voice | string | "Maya", "Josh", or custom voice ID |
| model | string | "base" or "enhanced" (enhanced = lower latency) |
| first_sentence | string | Agent's opening line |
| max_duration | int | Max call length in minutes (default 30) |
| transfer_phone_number | string | Number to transfer to |
| record | bool | Record the call |
| webhook | string | URL to receive transcript after call |

## Conversational Pathways (Complex Flows)
For agents with branching logic, tool calls, or transfers:
- **Nodes**: Conversation steps (greeting, data collection, resolution, farewell)
- **Conditions**: Rules for transitions (e.g., "if user says yes → booking node")
- **Webhook Nodes**: API calls at any point with speech during/after
- **Custom Tools**: External API calls based on conversation context
- **Variables**: Extract from speech (`user_name`, `date`) → use as `{{input.variable_name}}`

## Integration Patterns for Hackathon

### Pattern 1: LLM-Orchestrated Outbound Caller
Your agent (Claude) decides WHEN and WHO to call, dispatches via Bland API:
```python
import requests

def make_bland_call(phone, task_prompt):
    resp = requests.post(
        "https://api.bland.ai/v1/calls",
        headers={"authorization": "YOUR_API_KEY", "Content-Type": "application/json"},
        json={"phone_number": phone, "task": task_prompt, "model": "enhanced",
              "webhook": "https://your-server.com/call-complete"}
    )
    return resp.json()  # returns call_id
```

### Pattern 2: Mid-Call Tool Integration
Voice agent calls your APIs during conversation:
- CRM lookup: "Let me pull up your account" → calls your API
- Booking: Confirms availability via calendar API in real-time
- Database query: Retrieves order status, balance, etc.

### Pattern 3: Inbound + Post-Call Pipeline
1. Purchase inbound number via Bland
2. Attach conversational pathway
3. Post-call webhook delivers full transcript
4. Your LLM processes transcript → summarize, create ticket, trigger follow-up

### Pattern 4: Web Chat Widget
```html
<script>
  // Paste Bland widget code from dashboard
  // Voice + text chat on any website
</script>
```

### Pattern 5: Norm (Fastest Path)
Describe your agent in natural language → Norm builds pathway, tests with simulated calls, deploys. Available on free tier.

## Hackathon Tips
1. **Start with free tier** — $0.14/min is fine for demos
2. **Use `task` for simple agents** — no need for Pathways for basic demo
3. **Use Pathways for complex flows** — branching, tool calls, transfers
4. **Try Norm first** — describe agent, let it scaffold, then customize
5. **Post-call webhooks** — pipe transcripts to your backend for analysis
6. **Python SDK supports async** — useful for web servers dispatching calls
7. **`enhanced` model** — optimized for low latency, use as default

## Docs
- Platform: https://app.bland.ai/
- Docs: https://docs.bland.ai/welcome-to-bland
- Send Call API: https://docs.bland.ai/api-v1/post/calls
- First Call Tutorial: https://docs.bland.ai/tutorials/send-first-call
- Pathways Tutorial: https://docs.bland.ai/tutorials/pathways
- Custom Tools: https://docs.bland.ai/tutorials/tools
- Chat Widget: https://docs.bland.ai/tutorials/chat-widget
- Python SDK: https://pypi.org/project/bland/
- Bland University: https://university.bland.ai/
- GitHub: https://github.com/CINTELLILABS
