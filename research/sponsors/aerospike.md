# Aerospike for AI Agent Development -- Research Summary (March 2026)

## Executive Summary

Aerospike is a multi-model NoSQL database (key-value, document, graph, vector) that has positioned itself strongly for AI/agent workloads as of early 2026. The most significant recent development is **Aerospike NoSQL Database 8** (announced March 2026), which introduces a native **LangGraph integration** providing durable, low-latency memory for agentic AI workflows. Combined with its **Aerospike Vector Search (AVS)** product and sub-millisecond latency at scale, Aerospike is a compelling choice for hackathon projects that need persistent agent state, vector similarity search, and real-time performance.

---

## 1. Quick Setup (Hackathon-Ready)

### Option A: Docker (Recommended for Hackathons)

```bash
# Community Edition -- free, single command, no license needed
docker run -d --name aerospike \
  -p 3000:3000 -p 3001:3001 -p 3002:3002 \
  aerospike/aerospike-server

# Enterprise Edition (60-day free trial, feature key built-in for v6.1+)
docker run -d --name aerospike \
  -p 3000-3002:3000-3002 \
  container.aerospike.com/aerospike/aerospike-server-enterprise
```

### Option B: Aerospike Vector Search (AVS) via Docker

AVS runs as a **separate sidecar service** alongside the Aerospike database:

```bash
# 1. Start Aerospike DB first (see above)
# 2. Start AVS
docker run -d --name aerospike-vector-search \
  --network svc \
  -p 5000:5000 -p 5040:5040 \
  -v ./config:/etc/aerospike-vector-search \
  aerospike/aerospike-vector-search:1.0.0
```

Alternatively, clone `aerospike-vector-search-examples` repo for ready-made Docker Compose files.

### Option C: Aerospike Cloud (Fully Managed DBaaS)

- Fully managed database-as-a-service on AWS
- Sign up at [aerospike.com/products/aerospike-cloud](https://aerospike.com/products/aerospike-cloud/)
- Create cluster, download TLS certificate, get hostname from Cloud console
- Connect via standard clients using hostname + credentials
- Docs: [aerospike.com/docs/cloud/quickstart](https://aerospike.com/docs/cloud/quickstart/)

### Editions & Pricing

| Edition | Cost | Limits | Best For |
|---------|------|--------|----------|
| Community Edition | Free, open-source | Up to 8 nodes, 2.5 TB data | Hackathons, learning, single-app |
| Enterprise Edition | Licensed (data volume) | Unlimited | Production |
| Enterprise Trial | Free 60 days | Full enterprise features | Evaluation |
| Aerospike Cloud | Managed pricing | Fully managed | Zero-ops production |

---

## 2. Client Libraries

### Python Client

```bash
# Standard Aerospike client
pip install aerospike

# Vector Search client (separate package)
pip install aerospike-vector-search
```

- GitHub: [aerospike/aerospike-client-python](https://github.com/aerospike/aerospike-client-python)
- AVS Client GitHub: [aerospike/avs-client-python](https://github.com/aerospike/avs-client-python)
- AVS Python client v4.1.1+ is compatible with AVS server 0.11.0+; full features require AVS server 1.1.0+

### Node.js Client

```bash
npm install aerospike
```

- Latest release: **v6.5.2** (December 2025)
- API Docs: [aerospike.com/apidocs/nodejs](https://aerospike.com/apidocs/nodejs/)
- GitHub: [aerospike/aerospike-client-nodejs](https://github.com/aerospike/aerospike-client-nodejs)
- Follows semantic versioning

---

## 3. Agent Memory & State Management (LangGraph Integration)

This is Aerospike's flagship AI-agent feature as of March 2026.

### The Problem It Solves

Most AI agents are effectively stateless. When a process crashes, a deployment restarts, or a workflow pauses, critical execution context is lost -- making agentic systems fragile and hard to scale.

### Aerospike's Solution: LangGraph Checkpointer + Store

Two packages available from the community repo:

```bash
# Install from the aerospike-community/aerospike-langgraph GitHub repo
pip install langgraph-checkpoint-aerospike
pip install langgraph-store-aerospike
```

- **GitHub**: [aerospike-community/aerospike-langgraph](https://github.com/aerospike-community/aerospike-langgraph/tree/main/packages)

### Two Core Abstractions

| Abstraction | Purpose | Use Case |
|-------------|---------|----------|
| **Checkpointer** (`langgraph-checkpoint-aerospike`) | Persists evolving graph state during execution | Pause/resume/retry workflows from a known-good point after failures |
| **Store** (`langgraph-store-aerospike`) | General-purpose key-value persistence outside any single execution | Long-lived agent memory, cross-session data, user preferences |

### Key Benefits for Agent Developers

- **Sub-millisecond latency**: Sits in the critical path of LangGraph graph traversal without becoming a bottleneck
- **Built-in TTL**: Memory and checkpoints expire naturally, preventing unbounded growth as agent sessions come and go
- **Fault tolerance**: State remains available even as nodes fail or clusters scale
- **High concurrency**: Handles many concurrent agent workflows
- **Drop-in replacement**: Works with standard LangGraph APIs -- no changes to graph definitions needed
- **Works with Community Edition**: Can test locally for free

### Conceptual Usage Pattern

```python
from langgraph.graph import StateGraph
# Aerospike checkpointer replaces default in-memory or SQLite checkpointer
from langgraph_checkpoint_aerospike import AerospikeCheckpointer
from langgraph_store_aerospike import AerospikeStore

# Configure Aerospike connection
checkpointer = AerospikeCheckpointer(
    hosts=[("localhost", 3000)],
    namespace="test",
    # TTL for automatic cleanup
)

store = AerospikeStore(
    hosts=[("localhost", 3000)],
    namespace="test",
)

# Build your LangGraph as normal, pass Aerospike as the persistence layer
graph = StateGraph(...)
# ... define nodes and edges ...
app = graph.compile(checkpointer=checkpointer, store=store)
```

---

## 4. Vector Search Capabilities

### Architecture

- Aerospike Vector Search (AVS) uses a **self-healing HNSW (Hierarchical Navigable Small World) index**
- Data is ingested immediately while the index builds asynchronously
- Vectors are stored alongside regular Aerospike records (metadata co-located with vectors)
- One of the top 3 most popular vector DBMSs on DB-Engines

### Python Vector Search Client

```python
from aerospike_vector_search import Client

# Connect to AVS
client = Client(seeds=[("localhost", 5000)])

# Create an index
client.index_create(
    namespace="test",
    name="my_index",
    vector_field="embedding",
    dimensions=1536,  # e.g., OpenAI ada-002
)

# Upsert vectors
client.upsert(
    namespace="test",
    key="doc_1",
    record_data={
        "embedding": [0.1, 0.2, ...],  # your vector
        "text": "original document text",
        "metadata": {"source": "wiki"}
    }
)

# Search
results = client.vector_search(
    namespace="test",
    index_name="my_index",
    query=[0.1, 0.2, ...],  # query vector
    limit=10,
)
```

### Key Vector Search Features

- Sub-millisecond vector search at billion-scale
- Self-healing HNSW index (no downtime for index rebuilds)
- Vectors stored alongside structured data (no separate vector DB needed)
- Real-time ingestion with immediate availability
- Supports RAG, semantic search, recommendations, fraud detection

---

## 5. LangChain Integration

Aerospike has a native LangChain vector store integration:

```bash
pip install langchain aerospike-vector-search
```

- Docs: [LangChain Aerospike VectorStore](https://python.langchain.com/docs/integrations/vectorstores/aerospike/)
- Use Aerospike as the vector store backend in any LangChain RAG pipeline
- Works with any LangChain-compatible embedding model (OpenAI, Cohere, HuggingFace, etc.)

### Example LangChain RAG Pattern

```python
from langchain_community.vectorstores import Aerospike
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()

vectorstore = Aerospike(
    client=avs_client,
    embedding=embeddings,
    namespace="test",
    index_name="langchain_index",
)

# Add documents
vectorstore.add_texts(["doc1 text", "doc2 text"])

# Similarity search
docs = vectorstore.similarity_search("query", k=5)

# Use as retriever in a chain
retriever = vectorstore.as_retriever()
```

---

## 6. AI/LLM Integration Patterns

### Pattern 1: RAG with Aerospike Vector Search

```
User Query -> Embedding Model -> Aerospike AVS (similarity search)
    -> Top-K documents -> LLM (with context) -> Response
```

### Pattern 2: Agentic Memory with LangGraph

```
Agent Step -> LangGraph -> Aerospike Checkpointer (save state)
                        -> Aerospike Store (long-term memory)
    -> On crash/restart: resume from last checkpoint
```

### Pattern 3: Real-Time Feature Store for AI

```
Incoming event -> Aerospike (sub-ms read/write)
    -> Feature lookup -> ML model inference -> Real-time decision
```

Use cases: fraud detection (e.g., Forter), real-time bidding, ad targeting, recommendations.

### Pattern 4: Multi-Model Hybrid Search

```
Query -> Aerospike Graph (relationship traversal)
      -> Aerospike Vector (semantic similarity)
      -> Aerospike KV (metadata lookup)
      -> Combined results -> LLM
```

---

## 7. Hackathon Cheat Sheet

### Minimum Viable Setup (5 minutes)

```bash
# 1. Start Aerospike
docker run -d --name aerospike -p 3000:3000 aerospike/aerospike-server

# 2. Install Python packages
pip install aerospike langgraph langgraph-checkpoint-aerospike langgraph-store-aerospike

# 3. (Optional) For vector search, also start AVS and install:
pip install aerospike-vector-search
```

### When to Choose Aerospike for Your Hackathon

- You need **persistent agent memory** that survives restarts
- You need **sub-millisecond reads/writes** for real-time AI decisions
- You want **vector search + structured data** in one database
- You are building with **LangGraph** and need production-grade state persistence
- You need a **multi-model database** (KV + document + graph + vector)

### When NOT to Choose Aerospike

- You only need a simple SQLite-like embedded store
- You have no real-time latency requirements
- Your dataset is tiny and in-memory state is sufficient

---

## Key Links & Resources

| Resource | URL |
|----------|-----|
| Aerospike Docs - Quick Start | https://aerospike.com/docs/database/quick-start/ |
| Aerospike Cloud Quick Start | https://aerospike.com/docs/cloud/quickstart/ |
| AVS Quick Start | https://aerospike.com/docs/vector/quickstart |
| AVS Python Client Docs | https://aerospike.com/docs/vector/develop/python |
| LangGraph Integration Blog | https://aerospike.com/blog/aerospike-langgraph-memory-store-agentic-ai |
| LangGraph Packages (GitHub) | https://github.com/aerospike-community/aerospike-langgraph/tree/main/packages |
| LangChain Vector Store Docs | https://python.langchain.com/docs/integrations/vectorstores/aerospike/ |
| Node.js Client API Docs | https://aerospike.com/apidocs/nodejs/ |
| Docker Hub (Official Image) | https://hub.docker.com/_/aerospike |
| AVS Docker Install | https://aerospike.com/docs/vector/install/docker |
| Tutorials | https://aerospike.com/docs/develop/tutorials |

---

*Research conducted March 26, 2026. Aerospike Database 8 with LangGraph integration was announced March 25, 2026.*
