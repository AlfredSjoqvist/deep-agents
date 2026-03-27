# Airbyte for AI Agent Development -- Hackathon Reference Guide

> Research compiled March 2026. Covers Airbyte's offerings for AI/agent data pipelines, including the new Agent Engine, PyAirbyte, connector ecosystem, and RAG/LLM integration patterns.

---

## Table of Contents

1. [Overview: Why Airbyte for AI Agents](#1-overview)
2. [Two Products, Two Use Cases](#2-products)
3. [Agent Engine (New -- Public Beta)](#3-agent-engine)
4. [PyAirbyte -- Programmatic Data Extraction](#4-pyairbyte)
5. [Key Connectors for Agent Builders](#5-connectors)
6. [RAG / LLM Integration Patterns](#6-rag-llm)
7. [Cloud vs OSS Quick Start](#7-cloud-vs-oss)
8. [Hackathon Quick-Start Recipes](#8-hackathon-recipes)
9. [Pricing and Free Tier](#9-pricing)
10. [Architecture Patterns for Agents](#10-architecture)

---

## 1. Overview: Why Airbyte for AI Agents <a name="1-overview"></a>

Airbyte is an open-source data integration platform with **600+ connectors** for structured and unstructured data. As of early 2026, Airbyte has pivoted hard toward AI/agent use cases with two key offerings:

- **Agent Engine** (public beta): A purpose-built data layer for AI agents with real-time connectors, automatic embedding generation, and governance.
- **PyAirbyte**: A Python library (`pip install airbyte`) that gives any Python script access to all 600+ connectors, with built-in caching (DuckDB by default) and LangChain/LlamaIndex integration.

**Why it matters for hackathons:** Instead of writing custom API integrations for each data source (Salesforce, HubSpot, Jira, Stripe, Gmail, databases, etc.), Airbyte gives you a single abstraction layer. Your agent can pull data from dozens of sources with minimal code.

---

## 2. Two Products, Two Use Cases <a name="2-products"></a>

| Feature | PyAirbyte | Agent Engine + Agent Connectors |
|---|---|---|
| **What** | Python library for batch/incremental data extraction | Real-time, tool-callable connectors for AI agents |
| **Install** | `pip install airbyte` | `pip install airbyte-agent-hubspot` (per connector) |
| **Data pattern** | Extract -> Cache (DuckDB/Postgres) -> Transform | Agent calls connector as a tool in real-time |
| **Best for** | RAG pipelines, data preprocessing, batch ingestion | Live agent interactions, tool-calling LLMs |
| **Connectors** | 600+ (all Airbyte connectors) | 10+ agent-native connectors (growing weekly) |
| **Framework support** | LangChain, LlamaIndex, Pandas | PydanticAI, LangChain, any custom agent loop, MCP |

---

## 3. Agent Engine (New -- Public Beta) <a name="3-agent-engine"></a>

The Agent Engine is Airbyte's newest offering, specifically designed for agentic AI applications.

### What It Provides

- **Agent Connectors**: Standalone Python SDKs that wrap operational APIs with strongly-typed interfaces
- **Real-time access**: Sub-second query latency, sub-minute data freshness
- **Governance**: Permission-aware access to external systems
- **Automatic embedding generation** for vector database destinations
- **CDC (Change Data Capture)** and incremental sync to keep agents grounded in current data

### Available Agent Connectors (as of early 2026)

Each is an independent `pip`-installable Python package:

| Connector | Package | Category |
|---|---|---|
| **HubSpot** | `airbyte-agent-hubspot` | CRM |
| **Salesforce** | `airbyte-agent-salesforce` | CRM |
| **GitHub** | `airbyte-agent-github` | Dev Tools |
| **Jira** | `airbyte-agent-jira` | Project Mgmt |
| **Asana** | `airbyte-agent-asana` | Project Mgmt |
| **Stripe** | `airbyte-agent-stripe` | Payments |
| **Zendesk Support** | `airbyte-agent-zendesk` | Support |
| **Gong** | `airbyte-agent-gong` | Sales Intelligence |
| **Greenhouse** | `airbyte-agent-greenhouse` | Recruiting |
| **Linear** | `airbyte-agent-linear` | Project Mgmt |
| **WooCommerce** | `airbyte-agent-woocommerce` | E-commerce |

New connectors are released weekly.

### Usage with PydanticAI (Example Pattern)

```python
# Install: pip install airbyte-agent-hubspot pydantic-ai
from airbyte_agent_hubspot import HubSpotConnector
from pydantic_ai import Agent

# Initialize connector with credentials
hubspot = HubSpotConnector(api_key="your-key")

# Create a PydanticAI agent with the connector as a tool
agent = Agent("openai:gpt-4o", tools=[hubspot.as_tools()])

# Query in natural language
result = await agent.run("List all deals closed this quarter over $50k")
```

Each connector ships with a `REFERENCE.md` documenting all available operations (list, fetch, search, create, update).

### Usage Options

1. **Cloud Platform (Agent Engine)**: Managed connectors, credentials, and data replication
2. **Open Source SDKs**: Import directly into your Python agents, manage storage/credentials yourself
3. **MCP Integration**: Expose connectors through MCP-based interfaces for tool-calling LLMs

---

## 4. PyAirbyte -- Programmatic Data Extraction <a name="4-pyairbyte"></a>

PyAirbyte is the more established library, ideal for batch data extraction and RAG preprocessing.

### Installation

```bash
pip install airbyte
# Requires Python >= 3.9
# As of v0.29.0, uses uv instead of pip for connector installation (much faster)
```

### Quick Start Example

```python
import airbyte as ab

# Configure a source (e.g., faker for testing, or any real connector)
source = ab.get_source(
    "source-faker",
    config={"count": 5_000},
    install_if_missing=True,  # Auto-installs the connector
)

# Verify connection
source.check()

# Select streams to read
source.select_all_streams()
# Or select specific streams:
# source.select_streams(["contacts", "deals"])

# Read data (auto-cached in local DuckDB by default)
result = source.read()

# Access data
for name, records in result.streams.items():
    print(f"Stream {name}: {len(list(records))} records")
```

### Cache Options

By default, PyAirbyte caches extracted data in a **local DuckDB file**. You can also use:

- **Postgres**
- **Snowflake**
- **BigQuery**

```python
# Custom cache example
cache = ab.new_local_cache(cache_name="my_agent_cache")
result = source.read(cache=cache)
```

### Converting to LangChain Documents

```python
import airbyte as ab

source = ab.get_source("source-github", config={...})
source.select_streams(["issues", "pull_requests"])
result = source.read()

# Convert to LangChain documents for RAG
documents = result.streams["issues"].to_documents()

# Now pass to any vector store
from langchain_pinecone import PineconeVectorStore
vectorstore = PineconeVectorStore.from_documents(documents, embedding_model)
```

### Key PyAirbyte Features

- **350-600+ source connectors** available
- **Incremental sync**: Only fetch new/changed records
- **Schema discovery**: Automatically detects available streams and fields
- **Type-safe**: Strongly typed records
- **AI framework integration**: Native `.to_documents()` for LangChain, works with Pandas (`to_pandas()`)

---

## 5. Key Connectors for Agent Builders <a name="5-connectors"></a>

### CRM & Sales
- **Salesforce** (certified) -- contacts, opportunities, accounts, custom objects
- **HubSpot** (certified) -- contacts, companies, deals, tickets, marketing events
- **Pipedrive**, **Zoho CRM**, **Close.com**

### Communication & Email
- **Gmail**, **Microsoft Outlook**
- **Slack**, **Microsoft Teams**
- **Intercom**, **Zendesk**

### Databases
- **PostgreSQL** (certified, CDC support)
- **MySQL** (certified, CDC support)
- **MongoDB** (certified)
- **Microsoft SQL Server**
- **Snowflake**, **BigQuery**, **Redshift**

### Dev & Project Management
- **GitHub** -- repos, issues, PRs, commits
- **Jira** -- issues, projects, sprints
- **Linear**, **Asana**, **Notion**
- **Confluence**

### Business & Finance
- **Stripe** -- payments, customers, subscriptions, invoices
- **QuickBooks**, **Xero**
- **Shopify** -- products, orders, customers

### Documents & Files
- **Google Drive**, **Microsoft SharePoint**
- **S3**, **GCS**, **Azure Blob Storage**

### Marketing & Analytics
- **Google Analytics**, **Google Ads**
- **Facebook Ads**, **LinkedIn Ads**
- **Marketo**, **Mailchimp**

### Vector Database Destinations (for RAG)

| Destination | Tier | Notes |
|---|---|---|
| **Pinecone** | Certified | Full RAG transformation support |
| **Weaviate** | Certified | Auto-chunking and embedding |
| **Milvus / Zilliz** | Certified | End-to-end RAG pipeline tutorials available |
| **Qdrant** | Community | Cloud and OSS |
| **Chroma** | Community | OSS only |
| **Vectara** | Community | Managed RAG platform |
| **LangChain destination** | Community | Direct LangChain vector store loading |

---

## 6. RAG / LLM Integration Patterns <a name="6-rag-llm"></a>

### Pattern 1: PyAirbyte -> Vector DB -> RAG Agent

The most common pattern for hackathons. Extract data, embed it, query with an LLM.

```
[Data Sources] -> PyAirbyte -> DuckDB Cache -> Chunking/Embedding -> Vector DB -> LLM Agent
     |                                              |
  Salesforce                                    OpenAI / Cohere
  GitHub                                        embeddings
  Notion
  Postgres
```

```python
import airbyte as ab
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

# Step 1: Extract data
source = ab.get_source("source-notion", config={...})
source.select_streams(["pages"])
result = source.read()

# Step 2: Convert to documents
docs = result.streams["pages"].to_documents()

# Step 3: Embed and store
vectorstore = PineconeVectorStore.from_documents(
    docs, OpenAIEmbeddings(), index_name="my-index"
)

# Step 4: Query with RAG
qa = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o"),
    retriever=vectorstore.as_retriever()
)
answer = qa.invoke("What are our top priorities this quarter?")
```

### Pattern 2: Airbyte Cloud -> Vector DB (No Code)

Use Airbyte Cloud UI to set up a connection from any source to a vector database destination. Airbyte handles:
- **Automatic chunking** of text fields
- **Embedding generation** (via OpenAI, Cohere, or other providers)
- **Incremental updates** on a schedule

Then point your agent's retriever at the vector DB.

### Pattern 3: Agent Connectors for Real-Time Tool Use

Instead of pre-loading data into a vector DB, let the agent query sources directly:

```python
from airbyte_agent_salesforce import SalesforceConnector
from airbyte_agent_stripe import StripeConnector

# Agent has real-time access to both systems
salesforce = SalesforceConnector(credentials={...})
stripe = StripeConnector(api_key="sk-...")

# Use as tools in your agent framework
agent = Agent(
    model="gpt-4o",
    tools=[
        salesforce.as_tools(),
        stripe.as_tools(),
    ]
)
```

### Pattern 4: Hybrid (RAG + Real-Time Tools)

Combine patterns 1 and 3: Use RAG for historical/bulk data (docs, emails, past tickets) and agent connectors for real-time lookups (current deals, live payment status).

---

## 7. Cloud vs OSS Quick Start <a name="7-cloud-vs-oss"></a>

### Airbyte Cloud (Recommended for Hackathons)

- **Sign up**: https://cloud.airbyte.com/signup
- **Free trial**: 400 credits, 14-30 days, no credit card required
- **Setup time**: Minutes (fully managed)
- **What you get**: Web UI, managed connectors, scheduling, monitoring

**Steps:**
1. Sign up at cloud.airbyte.com
2. Add a source (e.g., HubSpot, GitHub, Postgres)
3. Add a destination (e.g., Pinecone, a local Postgres, or BigQuery)
4. Configure sync schedule
5. Run your first sync

### Airbyte OSS (Self-Hosted)

**Option A: abctl (Recommended for local)**

```bash
# Install abctl (Airbyte's CLI tool)
# Uses kind to create a Kubernetes cluster inside Docker
# Requires: Docker, 4+ CPUs, 8+ GB RAM

# Install and start Airbyte
abctl local install

# Access at http://localhost:8000
# Note: Initial install can take up to 30 minutes
```

**Option B: PyAirbyte Only (Lightest Weight)**

For hackathons, you may not need the full Airbyte platform. PyAirbyte alone gives you connector access with zero infrastructure:

```bash
pip install airbyte
# That's it. No Docker, no Kubernetes, no server.
```

### Decision Matrix for Hackathons

| Scenario | Recommendation |
|---|---|
| Need a quick RAG pipeline | PyAirbyte (`pip install airbyte`) |
| Agent needs real-time CRM/API access | Agent Connectors (`pip install airbyte-agent-*`) |
| Want a UI to configure syncs visually | Airbyte Cloud (free trial) |
| Need scheduled ongoing data sync | Airbyte Cloud |
| Want full self-hosted control | abctl + Docker |
| Just exploring / prototyping | PyAirbyte + DuckDB (zero infra) |

---

## 8. Hackathon Quick-Start Recipes <a name="8-hackathon-recipes"></a>

### Recipe 1: "Talk to Your CRM" Agent (30 min)

```bash
pip install airbyte-agent-hubspot pydantic-ai openai
```

```python
from airbyte_agent_hubspot import HubSpotConnector
from pydantic_ai import Agent

connector = HubSpotConnector(api_key="...")
agent = Agent("openai:gpt-4o", tools=[connector.as_tools()])
result = await agent.run("Show me all deals in the pipeline worth over $10k")
```

### Recipe 2: Multi-Source RAG Knowledge Base (1 hour)

```bash
pip install airbyte langchain langchain-openai langchain-pinecone pinecone-client
```

```python
import airbyte as ab

# Pull from multiple sources
sources = {
    "notion": ab.get_source("source-notion", config={...}),
    "github": ab.get_source("source-github", config={...}),
    "slack": ab.get_source("source-slack", config={...}),
}

all_docs = []
for name, source in sources.items():
    source.check()
    source.select_all_streams()
    result = source.read()
    for stream_name, stream in result.streams.items():
        all_docs.extend(stream.to_documents())

# Load into vector store and build RAG chain
# ... (standard LangChain RAG setup)
```

### Recipe 3: Customer Support Agent with Live Data (1 hour)

```bash
pip install airbyte-agent-zendesk airbyte-agent-stripe pydantic-ai
```

Give your agent access to Zendesk tickets AND Stripe payment data so it can answer questions like "Has this customer paid? What's their ticket history?"

### Recipe 4: Database-Aware Agent (30 min)

```bash
pip install airbyte
```

```python
import airbyte as ab

# Connect to your production DB (read-only!)
source = ab.get_source("source-postgres", config={
    "host": "your-db.example.com",
    "port": 5432,
    "database": "production",
    "username": "readonly_user",
    "password": "...",
    "ssl_mode": {"mode": "require"},
})

source.check()
source.select_streams(["customers", "orders", "products"])
result = source.read()

# Now your agent can query this cached data via DuckDB
# Or convert to documents for RAG
```

---

## 9. Pricing and Free Tier <a name="9-pricing"></a>

### Airbyte Cloud

| Tier | Cost | Notes |
|---|---|---|
| **Free Trial** | $0 (400 credits) | 14-30 days, no credit card |
| **Standard** | From $10/month | $2.50 per additional credit |
| **Plus/Pro** | Capacity-based | Data Workers model |
| **Enterprise** | Custom | SSO, RBAC, dedicated support |

### Open Source / Free Options

| Option | Cost | Infrastructure Needed |
|---|---|---|
| **PyAirbyte** | Free (MIT license) | None (pure Python) |
| **Agent Connectors** | Free (open source) | None (pure Python) |
| **Airbyte OSS (abctl)** | Free | Docker, 4 CPUs, 8GB RAM |

**For hackathons**: PyAirbyte and Agent Connectors are completely free and require zero infrastructure. Airbyte Cloud's free trial gives 400 credits if you want the managed experience.

---

## 10. Architecture Patterns for Agents <a name="10-architecture"></a>

### Pattern A: Lightweight Agent (No Infrastructure)

```
Agent (Python)
  |-- Agent Connector (HubSpot, Salesforce, etc.)  <-- real-time tool calls
  |-- LLM (OpenAI, Anthropic, etc.)
  |-- No database needed
```

### Pattern B: RAG-Enhanced Agent

```
[Periodic Sync]
  Data Sources --> PyAirbyte --> Vector DB (Pinecone/Chroma)
                                     |
[Runtime]                            v
  User Query --> LLM Agent --> Retriever --> Context --> LLM --> Response
```

### Pattern C: Full Data Platform

```
[Airbyte Cloud/OSS]
  Sources (600+) --> Airbyte --> Warehouse (Snowflake/BQ)
                            \-> Vector DB (Pinecone/Weaviate)
                            \-> Cache (DuckDB)
                                     |
[Agent Layer]                        v
  Agent Framework --> Tools (Agent Connectors for live data)
                  --> RAG (Vector DB for historical context)
                  --> SQL (Warehouse for analytics)
```

---

## Key Links

| Resource | URL |
|---|---|
| Agent Engine Docs | https://docs.airbyte.com/ai-agents |
| Agent Connectors (GitHub) | https://github.com/airbytehq/airbyte-agent-connectors |
| PyAirbyte Getting Started | https://docs.airbyte.com/platform/using-airbyte/pyairbyte/getting-started |
| PyAirbyte on PyPI | https://pypi.org/project/airbyte/ |
| Airbyte Cloud Signup | https://cloud.airbyte.com/signup |
| Airbyte Pricing | https://airbyte.com/pricing |
| PydanticAI Tutorial | https://docs.airbyte.com/ai-agents/tutorials/quickstarts/tutorial-pydantic |
| RAG + LangChain Notebook | https://github.com/airbytehq/quickstarts/blob/main/pyairbyte_notebooks/PyAirbyte_Document_Creation_RAG_with_Langchain_Demo.ipynb |
| Airbyte for AI Landing Page | https://airbyte.com/ai |
| Connector Catalog | https://airbyte.com/connectors |

---

## Sources

- [Airbyte for AI Agents](https://airbyte.com/ai)
- [Agent Engine Docs](https://docs.airbyte.com/ai-agents)
- [Introducing Agent Connectors from Airbyte](https://airbyte.com/blog/agent-connectors)
- [PyAirbyte Product Page](https://airbyte.com/product/pyairbyte)
- [PyAirbyte Getting Started](https://docs.airbyte.com/platform/using-airbyte/pyairbyte/getting-started)
- [A Guide to Building AI Agents](https://airbyte.com/agentic-data/building-ai-agents)
- [A Guide to Scaling Agentic AI](https://airbyte.com/agentic-data/scaling-agentic-ai)
- [AI Connectors: Use Cases and Benefits](https://airbyte.com/agentic-data/ai-connector)
- [How to Build an AI Data Pipeline Using Airbyte](https://airbyte.com/data-engineering-resources/ai-data-pipeline)
- [Building a RAG Architecture with Generative AI](https://airbyte.com/data-engineering-resources/rag-architecure-with-generative-ai)
- [Airbyte Cloud vs. Open Source vs Enterprise](https://airbyte.com/blog/airbyte-cloud-vs-open-source-vs-enterprise)
- [Airbyte OSS Quickstart](https://docs.airbyte.com/platform/using-airbyte/getting-started/oss-quickstart)
- [Airbyte Pricing](https://airbyte.com/pricing)
- [Airbyte Agent Connectors GitHub](https://github.com/airbytehq/airbyte-agent-connectors)
- [PydanticAI Agent Tutorial](https://docs.airbyte.com/ai-agents/tutorials/quickstarts/tutorial-pydantic)
- [PyAirbyte + LangChain RAG Demo Notebook](https://github.com/airbytehq/quickstarts/blob/main/pyairbyte_notebooks/PyAirbyte_Document_Creation_RAG_with_Langchain_Demo.ipynb)
- [Airbyte Vector Database Connectors Announcement](https://www.businesswire.com/news/home/20231017608302/en/Airbyte-Announces-Additional-Vector-Database-Connectors-Making-Hundreds-of-Data-Sources-Available-for-Artificial-Intelligence-Applications)
- [Pinecone Vector Database Features with Airbyte](https://airbyte.com/data-engineering-resources/pinecone-vector-database-features)
- [End-to-end RAG with Airbyte Cloud, SharePoint, and Milvus](https://airbyte.com/tutorials/end-to-end-rag-with-airbyte-cloud-microsoft-sharepoint-and-milvus-zilliz)
- [Integrating Vector Databases with LLM](https://airbyte.com/data-engineering-resources/integrating-vector-databases-with-llm)
- [abctl Documentation](https://docs.airbyte.com/platform/deploying-airbyte/abctl)
- [airbyte PyPI](https://pypi.org/project/airbyte/)
