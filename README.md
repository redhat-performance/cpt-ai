# CPT AI — Benchmark Regression Analyzer

AI-powered regression analysis for cloud performance benchmarks. Compares two benchmark runs from OpenSearch (or local CSV files), computes a direction-aware geometric mean across matched metrics, and sends the results to an AI model for verdict and root-cause analysis. Supports follow-up Q&A.

Four interfaces share the same `cpt_core` library:

| Interface | Path | Description |
|-----------|------|-------------|
| **CLI (OpenSearch)** | `components/cli/json/regression_analyzer.py` | Interactive terminal — select runs from OpenSearch, compare, Q&A |
| **CLI (CSV)** | `components/cli/csv/csv_regression_analyzer.py` | Compare two local CSV files — no OpenSearch needed |
| **REST API** | `components/api/api.py` | FastAPI server for programmatic access |
| **Dashboard** | `components/dashboard/ra_app.py` | Standalone Dash web app for regression analysis |

## Quick Start — For Users (No Setup Required)

You only need **VPN / network access** to the Red Hat lab network (`rdu3.labs.perfscale.redhat.com`). No Python, no venv, no files, no installation.

| Service | URL |
|---------|-----|
| **Regression Analyzer** | http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8060 |
| **REST API (Swagger)** | http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/docs |

- **Dashboard** — open the URL in any browser
- **API** — use `curl`, Postman, or any HTTP client
- No credentials needed — OpenSearch auth is handled server-side

Example API call:
```bash
curl -s -X POST http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/filters \
  -H "Content-Type: application/json" \
  -d '{"field": "cloud"}' | jq
```

The zathras server runs everything. Users just consume it over HTTP.

---

## Quick Start — For Admins (Server Setup)

```bash
./setup/setup.sh
```

One command — answers a few prompts (OpenSearch creds, AI API key), then installs everything and starts all services automatically. See [Setup](#setup) for details.

## Table of Contents

- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Components](#components)
  - [1. OpenSearch Database](#1-opensearch-database)
  - [2. OpenSearch MCP Server](#2-opensearch-mcp-server)
  - [3. AI Model](#3-ai-model)
  - [4. cpt_core Library](#4-cpt_core-library)
  - [5. CLI Tools](#5-cli-tools)
  - [6. REST API](#6-rest-api)
  - [7. Dashboard](#7-dashboard)
- [Setup](#setup)
  - [Automated Setup](#automated-setup)
  - [Manual Setup](#manual-setup)
- [Usage](#usage)
  - [Run CLI (OpenSearch)](#run-cli-opensearch)
  - [Run CLI (CSV)](#run-cli-csv)
  - [Run REST API](#run-rest-api)
  - [Run Dashboard](#run-dashboard)
- [Systemd Services](#systemd-services)
- [CLI Examples](#cli-examples)
- [API Examples](#api-examples)
- [Logs](#logs)

---

## Project Structure

```
cpt-ai-clean/
├── cpt_core/                          # Shared library (all components use this)
│   ├── config.py                      # Configuration, loads .env
│   ├── data_access.py                 # MCP client, OpenSearch queries
│   ├── analysis.py                    # Geomean, thresholds, severity, triage
│   ├── statistics.py                  # Stats: mean, t-test, outlier detection
│   ├── ai_provider.py                 # AI abstraction (OpenAI-compatible)
│   ├── orchestrator.py                # Pipeline: find runs → geomean → AI
│   ├── csv_orchestrator.py            # Same pipeline, reads CSV files
│   ├── csv_parser.py                  # Parse Zathras CSV formats
│   └── cli_utils.py                   # CLI output formatting, Q&A loop
│
├── components/
│   ├── api/
│   │   └── api.py                     # FastAPI REST API (:8000)
│   ├── cli/
│   │   ├── json/                      # OpenSearch-based CLI tools
│   │   │   ├── regression_analyzer.py
│   │   │   └── show_data_tree.py
│   │   └── csv/                       # CSV file-based CLI tools
│   │       └── csv_regression_analyzer.py
│   └── dashboard/
│       ├── app.py                     # Full multi-tab dashboard (:8050)
│       ├── ra_app.py                  # Standalone regression dashboard (:8060)
│       ├── requirements.txt           # Dashboard-specific deps (dash, pandas)
│       ├── assets/                    # CSS/JS
│       ├── src/                       # Dashboard modules
│       └── tests/
│
├── setup/
│   ├── setup.sh                       # One-command setup script
│   ├── test_setup.py                  # Validate MCP + LLM connectivity
│   └── systemd/                       # Templated systemd unit files
│       ├── cpt-ai-mcp.service
│       ├── cpt-ai-api.service
│       ├── cpt-ai-dashboard.service
│       └── cpt-ai-regression.service
│
├── examples/
│   ├── api/                           # Captured API request/response samples
│   └── cli/
│       ├── json/                      # Recorded OpenSearch CLI sessions
│       └── csv/                       # Sample CSV files for testing
│
├── logs/                              # Runtime logs (auto-created)
├── docs/                              # Architecture documentation
├── requirements.txt                   # Core + API + CLI dependencies
├── .env.example                       # Environment variable template
└── LICENSE
```

---

## Architecture

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   CLI            │  │  REST API        │  │  Dashboard       │
│  components/     │  │  components/     │  │  components/     │
│  cli/json/       │  │  api/api.py      │  │  dashboard/      │
│  cli/csv/        │  │  (:8000)         │  │  (:8050, :8060)  │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                        ┌──────▼──────┐
                        │  cpt_core   │
                        │  library    │
                        └──────┬──────┘
                               │
              ┌────────────────┼────────────────┐
              │ MCP (SSE)                       │ REST API
              ▼                                 ▼
    ┌──────────────────┐              ┌───────────────────┐
    │  OpenSearch MCP  │              │  AI Model         │
    │  Server (:9900)  │              │  (Gemini/Granite) │
    │                  │              │                   │
    │  - SearchIndex   │              │  /chat/completions│
    │  - ListIndex     │              │  OpenAI-compatible│
    │  - GetIndexInfo  │              └───────────────────┘
    │  - Count         │
    │  - ClusterHealth │
    └────────┬─────────┘
             │ REST API
             ▼
  ┌────────────────────┐
  │  OpenSearch        │
  │                    │
  │  zathras-results   │  ← one doc per benchmark run
  │ zathras-timeseries │  ← metrics by timestamp
  └────────────────────┘
```

All interfaces talk to OpenSearch through the MCP server, never directly. Regression math (direction-aware geomean, thresholds, severity classification) is computed in `cpt_core/analysis.py`. The AI model receives pre-computed results and produces the narrative analysis.

---

## Components

### 1. OpenSearch Database

Zathras post-processing stores benchmark data in two indices:

| Index | Purpose |
|---|---|
| `zathras-results` | One document per benchmark run with final aggregated scores |
| `zathras-timeseries` | Same metrics indexed by timestamp for trend plotting |

Verify access:
```bash
curl -k -u user:pass "https://$OPENSEARCH_HOST/_cat/indices?v" | grep -i zathras
```

### 2. OpenSearch MCP Server

Middleware bridge between Python scripts and OpenSearch. Exposes operations as MCP tools over SSE:

| MCP Tool | Purpose |
|---|---|
| `SearchIndexTool` | Run queries / aggregations against an index |
| `ListIndexTool` | List available indices on a cluster |
| `GetIndexInfoTool` | Get index metadata / mappings |
| `CountTool` | Count documents matching criteria |
| `ClusterHealthTool` | Check cluster health status |

Required permissions (read-only):
- Read access to `zathras-results` and `zathras-timeseries` indices
- Index listing permission
- Cluster health read permission

No write/delete/admin permissions are used.

### 3. AI Model

Called via OpenAI-compatible `/chat/completions` REST endpoint using `httpx`. Supports any provider with an OpenAI-compatible API (switchable via `.env`):

| Provider | Model | Endpoint |
|---|---|---|
| models.corp | `granite-3-3-8b-instruct` | Red Hat internal API |
| Google Gemini | `gemini-2.0-flash` | `generativelanguage.googleapis.com` |

### 4. cpt_core Library

Shared library used by all interfaces (`cpt_core/`):

| Module | Purpose |
|---|---|
| `config.py` | Configuration dataclass, loads from `.env` |
| `data_access.py` | MCP client, OpenSearch query helpers |
| `analysis.py` | Direction-aware geomean, thresholds, severity, root-cause triage |
| `statistics.py` | Mean, median, stddev, CoV, Welch's t-test, outlier detection |
| `ai_provider.py` | AI abstraction (ABC + OpenAI-compatible implementation) |
| `orchestrator.py` | High-level pipeline: find runs → subtests → geomean → AI |
| `csv_parser.py` | Parse Zathras CSV files (passmark, streams, fio, uperf, etc.) |
| `csv_orchestrator.py` | Same pipeline as orchestrator, but reads from CSV files |
| `cli_utils.py` | Shared CLI output formatting (boxed layout, Q&A loop) |

### 5. CLI Tools

Located in `components/cli/`:

| Folder | Script | Purpose |
|---|---|---|
| `json/` | `regression_analyzer.py` | CLI (OpenSearch) — select two runs, compare, follow-up Q&A |
| `json/` | `show_data_tree.py` | Browse benchmark data hierarchy (cloud → OS → instance → benchmark) |
| `csv/` | `csv_regression_analyzer.py` | CLI (CSV) — compare two local CSV files, no MCP needed |

### 6. REST API

`components/api/api.py` — FastAPI wrapper around `cpt_core` for programmatic access.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/compare` | Compare two benchmark runs and get AI regression analysis |
| `POST` | `/ask` | Ask a follow-up question about a comparison |
| `POST` | `/filters` | Get available dropdown values for filter fields |
| `GET` | `/health` | Health check |

**Filter field names** (short API names mapped to OpenSearch paths):

| API field | OpenSearch path |
|-----------|----------------|
| `cloud` | `metadata.cloud_provider` |
| `os_vendor` | `metadata.os_vendor` |
| `os_version` | `system_under_test.operating_system.version` |
| `instance` | `metadata.instance_type` |
| `benchmark` | `test.name` |

### 7. Dashboard

`components/dashboard/ra_app.py` — Standalone Dash web app for regression analysis:
- Cascading dropdowns for run selection (cloud → OS → instance → benchmark)
- Side-by-side comparison results with geomean badge
- Multi-turn Q&A chat interface

The full dashboard (`components/dashboard/app.py`) includes additional tabs (overview, heatmap, time series, etc.) and supports synthetic data mode.

---

## Setup

### Automated Setup

The setup script handles everything — venv, dependencies, configuration, and systemd services:

```bash
./setup/setup.sh
```

**Prerequisites:**

| Requirement | Why |
|-------------|-----|
| Python 3.12+ | Runs all components |
| sudo access | Installs systemd services |
| Network access | pip install, OpenSearch, AI API |

**Credentials needed:**

| Credential | Example |
|------------|---------|
| OpenSearch host | `opensearch.example.com` |
| OpenSearch port | `443` (default) |
| OpenSearch username/password | Read-only access |
| AI API key | Gemini or Granite |

The script will:
1. Run pre-flight checks (Python, pip, sudo, systemd, network)
2. Prompt for OpenSearch and AI credentials
3. Create `~/ai-mcp-env` virtual environment
4. Install all dependencies (`requirements.txt` + `components/dashboard/requirements.txt`)
5. Generate `.env` and `~/opensearch_mcp_config.yml`
6. Install and start 4 systemd services
7. Verify all services are running

### Manual Setup

If you prefer to set up manually:

#### Step 1: Create Virtual Environment

```bash
python3 -m venv ~/ai-mcp-env
source ~/ai-mcp-env/bin/activate
```

#### Step 2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install -r components/dashboard/requirements.txt
```

#### Step 3: Configure Environment

```bash
cp .env.example .env
# Edit .env with your values
```

Key settings in `.env`:

```ini
# AI Model (uncomment one provider)
MODEL_NAME=gemini-2.0-flash
MODELS_CORP_API_KEY=<your-api-key>
MODELS_CORP_ENDPOINT=https://generativelanguage.googleapis.com/v1beta/openai

# MCP Server
MCP_URL=http://localhost:9900/sse

# OpenSearch
OPENSEARCH_HOST=your-opensearch-host.example.com
OPENSEARCH_PORT=443
OPENSEARCH_USERNAME=<username>
OPENSEARCH_PASSWORD=<password>
```

#### Step 4: Configure OpenSearch MCP

Create `~/opensearch_mcp_config.yml`:

```yaml
clusters:
  zathras:
    opensearch_url: "https://your-opensearch-host.example.com"
    opensearch_username: "<username>"
    opensearch_password: "<password>"
    max_response_size: 5242880
```

---

## Usage

### Start MCP Server (manual mode only)

If not using systemd services, start the MCP server first:
```bash
source ~/ai-mcp-env/bin/activate
opensearch-mcp-server-py \
  --mode multi \
  --config ~/opensearch_mcp_config.yml \
  --transport stream \
  --port 9900
```

### Run CLI (OpenSearch)

```bash
source ~/ai-mcp-env/bin/activate
python3 components/cli/json/regression_analyzer.py
python3 components/cli/json/regression_analyzer.py --detail expert
```

The interactive CLI walks you through:
1. Select Run 1 parameters (cloud, OS, instance, benchmark)
2. Select Run 2 parameters
3. Choose analysis detail level (Basic / Medium / Expert)
4. Review AI regression verdict
5. Ask follow-up questions in Q&A loop

### Run CLI (CSV)

No MCP server needed — compares two local CSV files directly:
```bash
source ~/ai-mcp-env/bin/activate
python3 components/cli/csv/csv_regression_analyzer.py --csv run1.csv run2.csv
python3 components/cli/csv/csv_regression_analyzer.py --csv run1.csv run2.csv --detail expert
```

Sample CSV files are in `examples/cli/csv/`.

### Run REST API

If not using systemd:
```bash
source ~/ai-mcp-env/bin/activate
cd components/api
uvicorn api:app --host 0.0.0.0 --port 8000
```

Interactive Swagger docs at http://localhost:8000/docs

### Run Dashboard

Standalone regression analyzer dashboard:
```bash
source ~/ai-mcp-env/bin/activate
cd components/dashboard
python ra_app.py    # http://localhost:8060
```

Full multi-tab dashboard (requires OpenSearch or synthetic data):
```bash
cd components/dashboard
python app.py       # http://localhost:8050
```

---

## Systemd Services

The setup script (`setup/setup.sh`) automatically installs and starts all services. Unit files are in `setup/systemd/` with templated paths that get patched at install time.

| Service | Unit File | Port | Description |
|---------|-----------|------|-------------|
| `cpt-ai-mcp` | `cpt-ai-mcp.service` | 9900 | OpenSearch MCP server |
| `cpt-ai-api` | `cpt-ai-api.service` | 8000 | REST API |
| `cpt-ai-dashboard` | `cpt-ai-dashboard.service` | 8050 | Full multi-tab dashboard |
| `cpt-ai-regression` | `cpt-ai-regression.service` | 8060 | Standalone regression dashboard |

MCP starts first — API and dashboards depend on it (`After=cpt-ai-mcp.service`). All services auto-restart on failure and start on boot.

### Service management

```bash
# Check status
sudo systemctl status cpt-ai-api

# View logs
sudo journalctl -u cpt-ai-api -f

# Restart a service
sudo systemctl restart cpt-ai-api

# Stop everything
sudo systemctl stop cpt-ai-mcp cpt-ai-api cpt-ai-dashboard cpt-ai-regression
```

---

## CLI Examples

One doc = one benchmark test run. 90 docs for pyperf means it was run 90 times; 1 doc for streams means once.

#### PassMark (Azure — instance scale-up)

```
RUN 1 (Baseline):                    RUN 2 (Comparison):
Cloud:     azure                     Cloud:     azure
OS:        rhel 9.6                  OS:        rhel 9.6
Instance:  Standard_D16ds_v6         Instance:  Standard_D32ds_v6
Benchmark: passmark                  Benchmark: passmark
```

Sample follow-up questions:
- "You say Run2 is 79% better than Run1. Show me the mathematical calculation."
- "Is the D32ds_v6 worth 2x the cost of D16ds_v6 based on these PassMark results?"

#### STREAMS (Azure — memory bandwidth comparison)

```
RUN 1 (Baseline):                    RUN 2 (Comparison):
Cloud:     azure                     Cloud:     azure
OS:        rhel 9.6                  OS:        rhel 9.6
Instance:  Standard_D8ds_v6          Instance:  Standard_D64ds_v6
Benchmark: streams                   Benchmark: streams
```

Sample follow-up questions:
- "Show maths behind the key metrics (Copy, Scale, Add, Triad) that contributed to the analysis."
- "Are there stddev values available — how much variance is there across iterations?"

#### CSV comparison (no OpenSearch needed)

```bash
python3 components/cli/csv/csv_regression_analyzer.py \
  --csv examples/cli/csv/streams9.5.csv examples/cli/csv/streams9.6.csv \
  --detail medium
```

Recorded CLI session outputs are in `examples/cli/json/`.

---

## API Examples

#### Filters
```bash
# List all clouds
curl -s -X POST http://localhost:8000/filters \
  -H "Content-Type: application/json" \
  -d '{"field": "cloud"}' | jq

# List all OS vendors
curl -s -X POST http://localhost:8000/filters \
  -H "Content-Type: application/json" \
  -d '{"field": "os_vendor"}' | jq

# List OS versions for a specific vendor
curl -s -X POST http://localhost:8000/filters \
  -H "Content-Type: application/json" \
  -d '{"field": "os_version", "filters": {"os_vendor": "rhel"}}' | jq

# List instances for azure + rhel + 9.6
curl -s -X POST http://localhost:8000/filters \
  -H "Content-Type: application/json" \
  -d '{"field": "instance", "filters": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6"}}' | jq

# List benchmarks for a specific instance
curl -s -X POST http://localhost:8000/filters \
  -H "Content-Type: application/json" \
  -d '{"field": "benchmark", "filters": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6"}}' | jq
```

#### Compare

```bash
# PassMark: D96 vs D64 on Azure
curl -s -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{
    "run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6", "benchmark": "passmark"},
    "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D64ds_v6", "benchmark": "passmark"},
    "detail_level": "medium"
  }' | jq
```

Detail levels: `basic` (1-2 lines), `medium` (5-10 lines), `expert` (comprehensive).

#### Ask (follow-up questions)

```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6", "benchmark": "passmark"},
    "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D64ds_v6", "benchmark": "passmark"},
    "detail_level": "medium",
    "question": "Show me the math behind the geomean calculation"
  }' | jq
```

For **multi-turn conversations**, pass previous exchanges in `chat_history`:

```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D96ds_v6", "benchmark": "passmark"},
    "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D64ds_v6", "benchmark": "passmark"},
    "detail_level": "medium",
    "question": "Which CPU metrics improved the most?",
    "chat_history": [
      {"role": "user", "content": "Show me the math behind the geomean calculation"},
      {"role": "assistant", "content": "The geomean is calculated using exp(sum(log(ratio_i)) / N)..."}
    ]
  }' | jq
```

Captured API examples are in `examples/api/`.

---

## Logs

All logs are written to the `logs/` directory:

| Log File | Contents |
|---|---|
| `session.log` | User's interactive selections (Run 1/Run 2 parameters), matched document IDs, timestamps, metrics |
| `csv_session.log` | Same as session.log but for CSV-based comparisons |
| `opensearch_mcp_queries.log` | Full JSON query bodies with filters, query results (hits, IDs, metrics) |
| `prompt.log` | Detail level chosen, full system/user prompts sent to AI, AI responses |
| `qa_queries.log` | Follow-up Q&A questions, constructed prompts, AI responses |

Systemd service logs are available via journalctl:
```bash
sudo journalctl -u cpt-ai-api -f
sudo journalctl -u cpt-ai-mcp -f
```

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
