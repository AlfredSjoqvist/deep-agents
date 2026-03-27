# Anthropic Agent-Building Capabilities (Early 2026)

A comprehensive hackathon-ready guide covering the Claude Agent SDK, tool use, MCP, models, pricing, and best practices.

---

## Table of Contents

1. [Claude Agent SDK](#1-claude-agent-sdk)
2. [Tool Use / Function Calling API](#2-tool-use--function-calling-api)
3. [Computer Use](#3-computer-use)
4. [Deep Agent / Multi-Step Reasoning](#4-deep-agent--multi-step-reasoning)
5. [MCP (Model Context Protocol)](#5-mcp-model-context-protocol)
6. [Latest Claude Models & Pricing](#6-latest-claude-models--pricing)
7. [Best Practices for Autonomous Agents](#7-best-practices-for-autonomous-agents)
8. [Hackathon Quick-Reference](#8-hackathon-quick-reference)

---

## 1. Claude Agent SDK

The **Claude Agent SDK** (formerly "Claude Code SDK") is Anthropic's official framework for building autonomous agents. It wraps the full Claude API into an agentic loop that handles tool execution, context management, retries, and streaming -- so you just consume a message stream.

### Installation

```bash
# TypeScript
npm install @anthropic-ai/claude-agent-sdk

# Python (uv -- recommended)
uv init && uv add claude-agent-sdk

# Python (pip)
pip install claude-agent-sdk
```

### Quickstart (Python)

```python
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async def main():
    async for message in query(
        prompt="Review utils.py for bugs that would cause crashes. Fix any issues you find.",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob"],   # what the agent can do
            permission_mode="acceptEdits",              # auto-approve file edits
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")

asyncio.run(main())
```

### Quickstart (TypeScript)

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Review utils.py for bugs. Fix any issues you find.",
  options: {
    allowedTools: ["Read", "Edit", "Glob"],
    permissionMode: "acceptEdits",
  },
})) {
  if (message.type === "assistant" && message.message?.content) {
    for (const block of message.message.content) {
      if ("text" in block) console.log(block.text);
      else if ("name" in block) console.log(`Tool: ${block.name}`);
    }
  } else if (message.type === "result") {
    console.log(`Done: ${message.subtype}`);
  }
}
```

### Key Configuration Options

| Option | Description |
|--------|-------------|
| `allowed_tools` | List of tools: `Read`, `Edit`, `Glob`, `Grep`, `Bash`, `WebSearch`, `WebFetch` |
| `permission_mode` | `acceptEdits` (auto-approve files), `bypassPermissions` (sandboxed CI), `dontAsk` (deny unlisted), `default` (callback) |
| `system_prompt` | Custom system instructions |
| `mcp_servers` | Connect MCP servers for external tools |
| Model selection | Optional -- defaults are sensible; can specify `claude-opus-4-6`, `claude-sonnet-4-6`, etc. |

### Permission Modes at a Glance

| Mode | Behavior | Best For |
|------|----------|----------|
| `acceptEdits` | Auto-approve file edits, ask for others | Dev workflows |
| `dontAsk` | Deny anything not in `allowedTools` | Locked-down headless agents |
| `bypassPermissions` | Run everything without prompts | Sandboxed CI/CD |
| `default` | Custom `canUseTool` callback | Custom approval flows |

### Tool Capability Profiles

| Tools | Agent Can Do |
|-------|-------------|
| `Read`, `Glob`, `Grep` | Read-only analysis |
| `Read`, `Edit`, `Glob` | Analyze and modify code |
| `Read`, `Edit`, `Bash`, `Glob`, `Grep` | Full automation |
| Add `WebSearch` | + Web research |

### Authentication

```bash
# Direct Anthropic API
export ANTHROPIC_API_KEY=your-api-key

# AWS Bedrock
export CLAUDE_CODE_USE_BEDROCK=1
# + configure AWS credentials

# Google Vertex AI
export CLAUDE_CODE_USE_VERTEX=1
# + configure GCP credentials

# Microsoft Azure AI Foundry
export CLAUDE_CODE_USE_FOUNDRY=1
# + configure Azure credentials
```

---

## 2. Tool Use / Function Calling API

Claude's tool use lets you define functions that Claude can call. There are two categories:

- **Client tools** -- run in YOUR code. Claude returns a `tool_use` block, you execute it, send back `tool_result`.
- **Server tools** -- run on Anthropic's infrastructure (web_search, code_execution, web_fetch, tool_search). Results come back directly.

### Simplest Example (Server Tool -- Web Search)

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[{"type": "web_search_20260209", "name": "web_search"}],
    messages=[{"role": "user", "content": "What's the latest on the Mars rover?"}],
)
print(response.content)
```

### Custom Client Tool (Function Calling)

```python
import anthropic
import json

client = anthropic.Anthropic()

# Define your tool
tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City and state, e.g. San Francisco, CA"},
                "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
            },
            "required": ["location"]
        }
    }
]

# First call -- Claude decides to use the tool
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": "What's the weather in San Francisco?"}]
)

# Check if Claude wants to use a tool
for block in response.content:
    if block.type == "tool_use":
        tool_name = block.name
        tool_input = block.input
        tool_use_id = block.id

        # Execute the tool (your logic here)
        result = {"temperature": 72, "conditions": "sunny"}

        # Send result back
        followup = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=[
                {"role": "user", "content": "What's the weather in San Francisco?"},
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": tool_use_id, "content": json.dumps(result)}
                ]}
            ]
        )
        print(followup.content[0].text)
```

### Strict Tool Use

Add `strict: true` to tool definitions to guarantee Claude's tool calls always match your schema exactly:

```python
tools = [{
    "name": "get_weather",
    "description": "Get weather for a location",
    "strict": True,  # Guarantees schema conformance
    "input_schema": { ... }
}]
```

### Advanced Tool Use Features (Beta)

Enable with header `advanced-tool-use-2025-11-20`:

- **Tool Search Tool** -- discovers tools on-demand instead of loading all definitions upfront. Reduces context window consumption when you have many tools.
- **Programmatic Tool Calling** -- Claude invokes tools inside a code execution sandbox, useful for spreadsheet manipulation or data processing without overloading context.
- **Token-efficient tool use** -- Claude 4 models have built-in optimizations and improved parallel tool calling.

### Server-Side Tools Reference

| Tool | Type | Extra Cost |
|------|------|-----------|
| `web_search_20260209` | Server | $10 / 1,000 searches |
| `web_fetch_20260209` | Server | Free (token costs only) |
| `code_execution` | Server | Free with web_search/web_fetch; otherwise $0.05/hr after 1,550 free hrs/mo |
| `tool_search` | Server | Token costs only |
| `text_editor_20250429` | Client (Anthropic-schema) | 700 tokens overhead |
| `bash_20250124` | Client (Anthropic-schema) | 245 tokens overhead |
| `computer_20251124` | Client (Anthropic-schema) | 735 tokens overhead |

---

## 3. Computer Use

Computer use is a **beta** feature that lets Claude interact with desktop environments -- seeing the screen via screenshots and controlling mouse/keyboard.

### Supported Models

Claude Opus 4.6, Claude Sonnet 4.6, Claude Opus 4.5

### Key Capabilities

- Screenshot capture to see what is displayed
- Mouse actions: click, double-click, triple_click, left_mouse_down, left_mouse_up, scroll
- Keyboard actions: type text, key combinations, hold_key
- **Zoom action** -- inspect small UI elements at high resolution before clicking (new in `computer_20251124`)
- Wait action for page loads

### API Example

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=4096,
    tools=[{
        "type": "computer_20251124",
        "name": "computer",
        "display_width_px": 1920,
        "display_height_px": 1080,
        "display_number": 0,
    }],
    messages=[{"role": "user", "content": "Open the browser and search for 'Anthropic MCP'"}]
)
```

### Limitations

- Works from still frames, not live video
- Drag-and-drop and smooth scrolling remain unreliable
- Precision clicking on very small targets can be difficult
- Currently works best on Mac (Windows/Linux support is limited)

### Pricing

Standard tool use pricing applies. Screenshots are billed as vision input tokens. The computer use beta adds ~466-499 tokens to the system prompt plus 735 tokens per tool definition.

---

## 4. Deep Agent / Multi-Step Reasoning

### Adaptive Thinking (Recommended for Opus 4.6 / Sonnet 4.6)

Adaptive thinking replaces the older "extended thinking" with a dynamic approach -- Claude decides when and how much to think based on task complexity.

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=16000,
    thinking={
        "type": "adaptive",          # Use adaptive (not "enabled")
        "effort": "high"             # low | medium | high (default) | max
    },
    messages=[{"role": "user", "content": "Analyze this complex codebase..."}]
)

# Response includes thinking summary
for block in response.content:
    if block.type == "thinking":
        print("Thinking:", block.thinking)
    elif block.type == "text":
        print("Answer:", block.text)
```

### Effort Levels

| Level | Use Case | Cost Impact |
|-------|----------|-------------|
| `low` | Simple lookups, formatting | Minimal thinking tokens |
| `medium` | Standard tasks | Moderate thinking |
| `high` (default) | Complex reasoning, coding | Significant thinking |
| `max` | Hardest problems, research | Maximum thinking budget |

### Agentic Multi-Step Loops

Claude Code now averages **21.2 independent tool calls per task** (up 116% in 6 months), including file editing and terminal commands. Key enablers:

- **Auto-Accept Mode** (shift+tab in Claude Code): autonomous loops where Claude writes code, runs tests, iterates until tests pass
- **Progress files + git history**: for multi-context-window agents, an initializer agent sets up the environment, then a coding agent makes incremental progress while leaving artifacts for the next session
- **57% of organizations** now deploy multi-step agent workflows (Agent A identifies issue, Agent B patches, Agent C runs regression tests)

### Extended Thinking (Legacy -- Deprecated in 4.6)

```python
# DEPRECATED -- migrate to adaptive thinking
response = client.messages.create(
    model="claude-opus-4-5",  # Use with older models
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    messages=[...]
)
```

---

## 5. MCP (Model Context Protocol)

MCP is an **open standard** (donated to the Linux Foundation's Agentic AI Foundation in Dec 2025) for connecting AI agents to external tools and data sources. As of early 2026: **97M+ monthly SDK downloads**, **6,400+ registered MCP servers**, backed by Anthropic, OpenAI, Google, and Microsoft.

### What MCP Provides

- **Standardized tool interface** -- one protocol for databases, APIs, file systems, browsers
- **Server ecosystem** -- thousands of pre-built servers for GitHub, Slack, PostgreSQL, etc.
- **Transport flexibility** -- stdio (local processes), SSE (remote), HTTP

### Using MCP with Claude Agent SDK

#### Project Configuration (.mcp.json)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed"],
      "env": {
        "ALLOWED_PATHS": "/path/to/allowed"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "remote-api": {
      "type": "sse",
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${API_TOKEN}"
      }
    }
  }
}
```

#### In-Code MCP Server (Python)

```python
from claude_agent_sdk import query, ClaudeAgentOptions

# MCP servers can also be defined inline in SDK options
async for message in query(
    prompt="Query the database for recent orders",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Bash"],
        mcp_servers={
            "postgres": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-postgres"],
                "env": {"DATABASE_URL": "postgresql://..."}
            }
        },
        permission_mode="acceptEdits",
    ),
):
    # handle messages...
    pass
```

### Key MCP Resources

- Official registry: [https://github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
- Spec & client docs: [https://modelcontextprotocol.io](https://modelcontextprotocol.io)
- When many MCP tools are configured, **Tool Search** automatically withholds definitions from context and loads only what Claude needs per turn

---

## 6. Latest Claude Models & Pricing

### Current Models (March 2026)

| | Opus 4.6 | Sonnet 4.6 | Haiku 4.5 |
|---|---|---|---|
| **API ID** | `claude-opus-4-6` | `claude-sonnet-4-6` | `claude-haiku-4-5` |
| **Input** | $5 / MTok | $3 / MTok | $1 / MTok |
| **Output** | $25 / MTok | $15 / MTok | $5 / MTok |
| **Context** | 1M tokens | 1M tokens | 200K tokens |
| **Max Output** | 128K tokens | 64K tokens | 64K tokens |
| **Extended Thinking** | Yes (adaptive) | Yes (adaptive) | Yes |
| **Adaptive Thinking** | Yes | Yes | No |
| **Best For** | Hardest tasks, agents, coding | 90%+ coding tasks, fast + smart | Simple tasks, high volume |
| **Knowledge Cutoff** | May 2025 | Aug 2025 | Feb 2025 |

### Pricing Summary

| Model | Standard Input | Standard Output | Batch Input | Batch Output | Cache Hit |
|-------|---------------|----------------|------------|-------------|-----------|
| Opus 4.6 | $5/MTok | $25/MTok | $2.50/MTok | $12.50/MTok | $0.50/MTok |
| Sonnet 4.6 | $3/MTok | $15/MTok | $1.50/MTok | $7.50/MTok | $0.30/MTok |
| Haiku 4.5 | $1/MTok | $5/MTok | $0.50/MTok | $2.50/MTok | $0.10/MTok |

### Cost-Saving Features

- **Prompt Caching**: Cache hits cost 10% of standard input price. Pays for itself after 1 read (5-min cache) or 2 reads (1-hr cache).
- **Batch API**: 50% discount on both input and output tokens for async processing.
- **1M context at standard pricing**: Opus 4.6 and Sonnet 4.6 do NOT charge extra for long context (unlike older Sonnet models).
- **Fast Mode** (Opus 4.6 only): 6x standard pricing ($30/$150 per MTok) for significantly faster output.

### Server Tool Costs

| Tool | Cost |
|------|------|
| Web Search | $10 per 1,000 searches |
| Web Fetch | Free (token costs only) |
| Code Execution | Free with web_search/web_fetch; $0.05/hr after 1,550 free hrs/mo otherwise |

### Legacy Models Still Available

| Model | Input/Output | Context | Notes |
|-------|-------------|---------|-------|
| Opus 4.5 | $5/$25 | 200K | Predecessor to 4.6 |
| Opus 4.1 | $15/$75 | 200K | Expensive, older gen |
| Opus 4.0 | $15/$75 | 200K | Expensive, older gen |
| Sonnet 4.5 | $3/$15 | 1M (beta) | Good value |
| Sonnet 4.0 | $3/$15 | 1M (beta) | Good value |
| Haiku 3.5 | $0.80/$4 | 200K | Budget option |

### Hackathon Cost Estimate

A typical agent task with ~3,700 tokens per conversation on Sonnet 4.6:
- Single task: ~$0.003-$0.06 depending on complexity
- 1,000 agent runs: ~$3-$60
- Budget $5-$20 of API credits for a hackathon project using Sonnet 4.6

---

## 7. Best Practices for Autonomous Agents

### Anthropic's Official Agent Patterns

From Anthropic's ["Building Effective Agents"](https://www.anthropic.com/research/building-effective-agents) guide:

#### Workflows (Predefined Orchestration)

1. **Prompt Chaining** -- break tasks into sequential steps, each LLM call processes the output of the previous one
2. **Routing** -- classify input and route to specialized handlers
3. **Parallelization** -- run multiple LLM calls simultaneously and aggregate results
4. **Orchestrator-Workers** -- a central LLM dynamically dispatches subtasks to worker LLMs
5. **Evaluator-Optimizer** -- one LLM generates, another evaluates, loop until quality threshold met

#### Agents (Dynamic Self-Direction)

True agents dynamically decide their own tool usage and process flow. The core pattern is the **agentic loop**:

```
while not done:
    1. Observe (read files, see screen, get tool results)
    2. Think (reason about what to do next)
    3. Act (call a tool, write code, execute command)
    4. Evaluate (check results, decide if done)
```

### Key Design Principles

1. **Start simple** -- use the simplest pattern that works. Don't over-engineer multi-agent systems when a single prompt chain suffices.

2. **Write clear prompts** -- the #1 failure mode is poorly written prompts. If a human unfamiliar with the domain can't follow the instructions, neither can Claude.

3. **Give Claude the right tools** -- tool access is the highest-leverage primitive. Even basic tools produce outsized capability gains on benchmarks.

4. **Use verification loops** -- prompt Claude to verify its own work end-to-end (e.g., run tests, use browser automation to check UI).

5. **Handle long-running agents** -- for multi-context-window tasks:
   - Use a **progress file** alongside git history
   - An **initializer agent** sets up the environment on first run
   - A **coding agent** makes incremental progress and leaves artifacts for the next session

6. **Use Agent Skills** -- organized folders of instructions, scripts, and resources that Claude loads dynamically based on what the task needs. Skills stack together automatically.

### Production Architecture Tips

```
Project Root/
  .mcp.json              # MCP server configs
  CLAUDE.md              # Project-level instructions for Claude
  .claude/
    settings.json        # Agent SDK settings
    skills/              # Custom agent skills
  src/
    agent.py             # Your agent entry point
```

### Multi-Agent Patterns (2026 Trend)

57% of organizations now use multi-step agent workflows:

```python
# Conceptual multi-agent pattern
agents = {
    "analyzer": ClaudeAgentOptions(
        system_prompt="You identify bugs and issues.",
        allowed_tools=["Read", "Glob", "Grep"],
    ),
    "fixer": ClaudeAgentOptions(
        system_prompt="You fix identified bugs.",
        allowed_tools=["Read", "Edit", "Bash"],
        permission_mode="acceptEdits",
    ),
    "tester": ClaudeAgentOptions(
        system_prompt="You write and run tests.",
        allowed_tools=["Read", "Edit", "Bash"],
        permission_mode="acceptEdits",
    ),
}
```

---

## 8. Hackathon Quick-Reference

### 5-Minute Setup Checklist

```bash
# 1. Get API key from https://platform.claude.com/
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Install SDK
npm install @anthropic-ai/claude-agent-sdk    # TypeScript
# OR
pip install claude-agent-sdk                    # Python

# 3. Also install the raw API SDK if needed
npm install @anthropic-ai/sdk                  # TypeScript
# OR
pip install anthropic                           # Python
```

### Which Model to Use?

| Scenario | Model | Why |
|----------|-------|-----|
| Most hackathon tasks | `claude-sonnet-4-6` | Best speed/intelligence ratio, $3/$15 |
| Hardest reasoning/coding | `claude-opus-4-6` | Most capable, $5/$25 |
| High-volume simple tasks | `claude-haiku-4-5` | Cheapest at $1/$5 |
| Budget-constrained | `claude-haiku-4-5` + Batch API | $0.50/$2.50 per MTok |

### Agent SDK vs Raw API -- When to Use Which

| Use Agent SDK when... | Use Raw API when... |
|----------------------|-------------------|
| Building autonomous coding agents | Building chatbots or simple Q&A |
| Need file system access | Need fine-grained control over messages |
| Want built-in tool execution | Integrating into existing frameworks |
| Rapid prototyping of agent workflows | Building custom agentic loops |

### Minimal Raw API Agent Loop (Python)

```python
import anthropic

client = anthropic.Anthropic()
tools = [...]  # your tool definitions
messages = [{"role": "user", "content": "Your task here"}]

while True:
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=tools,
        messages=messages,
    )

    # Check if Claude is done
    if response.stop_reason == "end_turn":
        print(response.content[0].text)
        break

    # Process tool calls
    messages.append({"role": "assistant", "content": response.content})
    tool_results = []
    for block in response.content:
        if block.type == "tool_use":
            result = execute_tool(block.name, block.input)  # your logic
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result),
            })
    messages.append({"role": "user", "content": tool_results})
```

### Key Links

| Resource | URL |
|----------|-----|
| Agent SDK Quickstart | https://platform.claude.com/docs/en/agent-sdk/quickstart |
| Agent SDK Python (GitHub) | https://github.com/anthropics/claude-agent-sdk-python |
| Agent SDK npm | https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk |
| Tool Use Docs | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| MCP Specification | https://modelcontextprotocol.io |
| MCP Server Registry | https://github.com/modelcontextprotocol/servers |
| Models Overview | https://platform.claude.com/docs/en/about-claude/models/overview |
| Pricing | https://platform.claude.com/docs/en/about-claude/pricing |
| Building Effective Agents | https://www.anthropic.com/research/building-effective-agents |
| Example Agent Demos | https://github.com/anthropics/claude-agent-sdk-demos |
| Computer Use Docs | https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool |

---

## Sources

- [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Agent SDK Quickstart](https://platform.claude.com/docs/en/agent-sdk/quickstart)
- [Building Agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude Agent SDK (npm)](https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk)
- [Claude Agent SDK Python (GitHub)](https://github.com/anthropics/claude-agent-sdk-python)
- [Tool Use Overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)
- [Programmatic Tool Calling](https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling)
- [Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)
- [Computer Use Tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)
- [Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview)
- [Pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [Building Effective Agents](https://www.anthropic.com/research/building-effective-agents)
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [MCP Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol)
- [Donating MCP to AAIF](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)
- [A Year of MCP](https://www.pento.ai/blog/a-year-of-mcp-2025-review)
- [Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)
- [Extended Thinking Docs](https://platform.claude.com/docs/en/build-with-claude/extended-thinking)
- [Adaptive Thinking Docs](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)
- [Claude Opus 4.6 Announcement](https://www.anthropic.com/news/claude-opus-4-6)
- [MCP Connect in Agent SDK](https://platform.claude.com/docs/en/agent-sdk/mcp)
- [Claude Agent SDK Tutorial (DataCamp)](https://www.datacamp.com/tutorial/how-to-use-claude-agent-sdk)
- [2026 Agentic Coding Trends Report](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf)
