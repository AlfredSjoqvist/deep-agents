# AWS — Cloud Infrastructure

## Role in Project
The **infrastructure backbone**. Deploy, scale, and run the agent system.
Jon Turdiev (AWS SA of the Year) is a judge — use AWS services meaningfully.

## Key Services for Agent Hackathon

### Amazon Bedrock
- Managed service for foundation models (Claude Sonnet 4/4.5, Haiku 3.5, Llama, Nova, etc.)
- **Bedrock Agents**: built-in agent framework with action groups + knowledge bases
- InvokeAgent API for programmatic access
- Can use Claude via Bedrock (set `CLAUDE_CODE_USE_BEDROCK=1`)
- **Pricing**: Claude Sonnet 4.5 — $3/1M input tokens, $15/1M output tokens

### Bedrock Agents — Step-by-step
1. Open Bedrock console → Agents → Create Agent
2. Name agent, select model (e.g., Claude Sonnet 4)
3. Write natural language instruction
4. Define **Action Groups** — callable actions backed by Lambda, defined via OpenAPI specs
5. Attach **Knowledge Bases** (RAG over docs in S3)
6. Test in built-in console
7. Deploy with versioned alias
8. Invoke programmatically via Boto3

**Built-in capabilities:**
- Memory retention across sessions (short-term + long-term)
- Guardrails for safety
- Code interpretation (agent writes and runs code)
- User input solicitation (agent asks clarifying questions)

### Multi-Agent Collaboration (GA since March 2025)
Bedrock supports multi-agent with **supervisor agent** architecture:
- **Supervisor Mode**: Breaks down requests, delegates to sub-agents (parallel/sequential), consolidates results
- **Supervisor with Routing**: Simple requests → single sub-agent; complex → full orchestration
- Existing standalone agents compose as sub-agents without modification

### Bedrock AgentCore (New — re:Invent 2025)
"Fargate for AI agents" — bring container + agent logic, AWS handles the rest.

| Service | Purpose |
|---------|---------|
| AgentCore Runtime | Low-latency serverless execution with session isolation |
| AgentCore Memory | Session memory + episodic (long-term) memory |
| AgentCore Identity | Secure auth for agents accessing AWS + third-party tools |
| AgentCore Gateway | Connects agents to external tools with policy enforcement |
| AgentCore Observability | Step-by-step visualization of agent execution |
| AgentCore Policy | Natural language guardrails enforced deterministically |
| AgentCore Evaluations | 13 built-in evaluators + custom scoring |

**Framework-agnostic** — works with LangChain, CrewAI, AutoGen, or custom code.

### AWS Lambda
- Serverless functions for agent "tools" / action handlers
- Bridge between agent and data stores / external services
- Pay-per-invocation, scales automatically
- **Lambda Durable Functions** (NEW): automatic checkpointing, suspend up to 1 year, built-in retry + parallelism — perfect for chaining LLM calls

### AWS Step Functions
- Orchestrate multi-step agent workflows visually
- **AIAgentMap state type** — extends Map with AI-specific capabilities
- Intelligent Retry with AdaptiveScaling
- Distributed Map — up to 10,000 parallel child workflows
- Use when you need deterministic workflow control vs. LLM-driven routing

### Other Useful Services
- **DynamoDB**: Agent state / conversation history (millisecond latency)
- **S3**: Object storage for documents, audio, agent artifacts
- **SQS/SNS/EventBridge**: Async, event-driven agent communication
- **Amazon Q Developer**: AI coding assistant — use during hackathon to build faster

## Architecture Patterns

### Simplest MVP (30 minutes)
```
Bedrock Agent (Claude Sonnet 4)
  + Action Group → Lambda function(s)
  + Knowledge Base → S3 bucket with docs
```

### Multi-Agent (2-3 hours)
```
Supervisor Agent (Bedrock)
  ├── Sub-Agent A (domain specialist) → Lambda actions
  ├── Sub-Agent B (domain specialist) → Lambda actions
  └── Knowledge Base (shared RAG)
```

### Full Hackathon Architecture
```
User → API Gateway → Lambda (orchestrator)
                       |
                  Bedrock (Claude) ←→ Lambda (tools)
                       |                    |
                  Step Functions       Aerospike (memory)
                       |                    |
                  Bland AI (voice)    Auth0 (identity)
                       |
                  S3 (artifacts) + Airbyte (data)
```

## Free Tier & Credits (IMPORTANT)

| Program | What You Get |
|---------|-------------|
| **New AWS Account** | Up to $200 in credits ($100 signup + $100 activities) |
| **AWS Activate (Startups)** | Up to $100K in credits; redeemable on Bedrock |
| **Hackathon credits** | Usually $100 credit codes (first-come) |
| **Bedrock Free Tier** | Limited free allowances for new accounts |

**Strategy**: Create a fresh AWS account to get $200 new-user credits.

## Quick Setup
```bash
# Install AWS CLI + SDK
pip install awscli boto3

# Configure credentials
aws configure

# Node.js SDK
npm install @aws-sdk/client-bedrock-runtime
```

## Code Examples

### Invoke Bedrock Agent
```python
import boto3
client = boto3.client('bedrock-agent-runtime')
response = client.invoke_agent(
    agentId='YOUR_AGENT_ID',
    agentAliasId='YOUR_ALIAS_ID',
    sessionId='unique-session-id',
    inputText='Your prompt here'
)
```

### Direct Bedrock Model Call
```python
import boto3, json
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
response = bedrock.invoke_model(
    modelId='anthropic.claude-sonnet-4-20250514-v1:0',
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": "Your prompt"}]
    })
)
```

### Create Agent via CLI
```bash
aws bedrock-agent create-agent \
  --agent-name "my-agent" \
  --foundation-model "anthropic.claude-sonnet-4-20250514-v1:0" \
  --instruction "You are a helpful assistant that..."
```

## Decision Matrix

| Need | Use This |
|------|----------|
| Single agent with tools | Bedrock Agents + Lambda |
| Multiple cooperating agents | Bedrock Multi-Agent Collaboration |
| Complex deterministic workflows | Step Functions |
| Async/event-driven agents | SQS + SNS + EventBridge |
| Framework-agnostic deployment | AgentCore Runtime |
| Agent memory across sessions | AgentCore Memory |
| RAG over documents | Bedrock Knowledge Bases + S3 |
| Fastest hackathon MVP | Bedrock Agent + inline code action group (no Lambda needed) |

## Docs
- Bedrock: https://docs.aws.amazon.com/bedrock/
- Bedrock Agents: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- AgentCore: https://aws.amazon.com/bedrock/agentcore/
- Multi-Agent Collaboration: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-multi-agent-collaboration.html
- Lambda: https://docs.aws.amazon.com/lambda/
- Step Functions: https://docs.aws.amazon.com/step-functions/
- Bedrock Pricing: https://aws.amazon.com/bedrock/pricing/
- Agent Tutorial: https://docs.aws.amazon.com/bedrock/latest/userguide/agent-tutorial.html
- Quickstart (GitHub): https://github.com/build-on-aws/amazon-bedrock-agents-quickstart
