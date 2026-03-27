# Airbyte — Data Pipelines for Agents

## Role in Project
**Data ingestion layer.** Pull data from 600+ sources into agent workflows.

## Key Products

### Agent Engine (Cloud)
- "Data layer for AI agents"
- Manage connectors, credentials, data replication for agents
- Structured + unstructured data support
- Automatic embedding generation
- Incremental sync + CDC (Change Data Capture)
- Built-in governance

### PyAirbyte (Open Source)
- Use Airbyte connectors directly in Python — no Airbyte Platform needed
- Open-source library for programmatic data extraction
- 600+ connectors for any data source

### Agent Connectors (NEW)
- Standalone Python SDKs for real-time fetch and search
- 10+ agent connectors available (growing weekly)
- Designed for real-time agent operations, not just batch ETL

## Use Cases for Hackathon
1. **Feed agent with real-time data**: Pull from CRM, email, databases, APIs
2. **RAG pipeline**: Extract docs -> embed -> store in Aerospike -> agent queries
3. **Data monitoring agent**: Watch for changes in data sources
4. **Multi-source research**: Agent pulls from multiple APIs to build analysis
5. **Customer data pipeline**: Sync customer data for support agent

## Quick Start
```bash
pip install airbyte
```

### PyAirbyte Example
```python
import airbyte as ab

# Configure source connector
source = ab.get_source(
    "source-github",
    config={
        "credentials": {"personal_access_token": "ghp_..."},
        "repositories": ["owner/repo"]
    }
)

# Check connection
source.check()

# Read data
for record in source.read():
    print(record)
```

### Agent Connector Example
```python
# Standalone agent connectors for real-time use
from airbyte_agent_connectors import GithubConnector

connector = GithubConnector(token="ghp_...")
results = connector.search("open issues with label:bug")
```

## Available Connectors (Selection)
| Category | Examples |
|----------|---------|
| CRM | Salesforce, HubSpot |
| Databases | PostgreSQL, MySQL, MongoDB |
| APIs | GitHub, Jira, Slack |
| Files | S3, Google Sheets, CSV |
| Analytics | Google Analytics, Mixpanel |
| Communication | Gmail, Outlook |

## Docs
- Agent Engine: https://docs.airbyte.com/ai-agents
- PyAirbyte: https://docs.airbyte.com/using-airbyte/pyairbyte/getting-started
- Connectors catalog: https://docs.airbyte.com/integrations/
- Building AI Agents guide: https://airbyte.com/agentic-data/building-ai-agents
- Airbyte for AI: https://airbyte.com/ai
