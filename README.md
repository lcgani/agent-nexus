# Agent Nexus

**Automatically convert any API into AI-ready tools in 30 seconds**

Agent Nexus eliminates the need for manual API integration code. Point it at any API URL and get production-ready Python tools that AI agents can use immediately.

## What It Does

Developers spend hours writing integration code for every API their AI agents need to use. Agent Nexus automates this entirely.

Give it an API URL → Get working Python code + searchable catalog entry in under 30 seconds.

## How It Works

Agent Nexus uses 4 specialized agents working together:

1. **API Introspector** - Discovers API endpoints automatically (OpenAPI spec or intelligent probing)
2. **Tool Generator** - Creates clean Python integration code with authentication
3. **Catalog Search** - Indexes tools with AI embeddings for semantic search
4. **Tool Orchestrator** - Coordinates multi-tool workflows

## Tech Stack

- Python 3.11+
- Elasticsearch 8.15+ (storage, vector search, ES|QL)
- sentence-transformers (AI embeddings)
- Click (CLI)
- Docker & Docker Compose

## Installation

```bash
# Install from PyPI
pip install agent-nexus

# Or install from source
git clone https://github.com/lcgani/agent-nexus
cd agent-nexus
pip install -e .
```

## Quick Start

```bash
# 1. Start Elasticsearch (optional - use --skip-index for faster generation)
docker-compose up -d

# 2. Generate your first tool
agent-nexus generate https://api.github.com

# 3. Use the generated tool
python your_script.py
```

## Usage Examples

### Generate Tool from Any API

```bash
# GitHub
agent-nexus generate https://api.github.com

# Stripe
agent-nexus generate https://api.stripe.com

# Fast mode (skip Elasticsearch indexing)
agent-nexus generate https://api.github.com --skip-index
```

### Search with Natural Language

```bash
# Find payment APIs
python -m src.cli search "payment processing credit cards"

# Find weather APIs
python -m src.cli search "weather forecast temperature"

# Find code hosting APIs
python -m src.cli search "git repositories version control"
```

### Use Generated Tools

```python
# Import auto-generated tool
exec(open('generated_tools/api.github.com.py').read())
github = ApiGithubCom()

# Make API calls
import requests
response = requests.get(
    f"{github.base_url}/users/octocat",
    headers=github._headers()
)
print(response.json())
```

## Architecture

```
API URL Input
     ↓
Agent 1: Introspector (discovers endpoints)
     ↓
Elasticsearch (stores discovery data)
     ↓
Agent 2: Generator (creates Python code)
     ↓
Elasticsearch (stores tool + embeddings)
     ↓
Agent 3: Search (semantic search)
     ↓
Agent 4: Orchestrator (multi-tool workflows)
```

## Project Structure

```
agent-nexus/
├── src/
│   ├── agents/
│   │   ├── introspector.py    # API discovery
│   │   ├── generator.py       # Code generation
│   │   ├── search.py          # Vector search
│   │   └── orchestrator.py    # Workflow coordination
│   ├── elasticsearch/
│   │   ├── client.py          # ES connection
│   │   └── schemas.py         # Index mappings
│   ├── cli.py                 # CLI interface
│   └── config.py              # Configuration
├── generated_tools/           # Auto-generated tools
├── docker-compose.yml         # Elasticsearch setup
├── requirements.txt
└── README.md
```

## Performance Targets

- Tool generation: <30 seconds per API
- Search relevance: >90% accuracy
- Catalog size: 50+ tools tested
- End-to-end: <1 minute from URL to working tool

## Commands

```bash
# Setup Elasticsearch indexes
python -m src.cli setup

# Generate tool from API
python -m src.cli generate <API_URL>

# Search tool catalog
python -m src.cli search "<query>"
```

## License

Apache-2.0
