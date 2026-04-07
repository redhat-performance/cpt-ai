# Setup

One-command setup for CPT AI on any server.

## Quick Start

```bash
./setup/setup.sh
```

The script handles everything:
1. Pre-flight checks (Python 3.12+, pip, sudo, systemd, network)
2. Prompts for OpenSearch credentials and AI model API key
3. Creates virtual environment and installs all dependencies
4. Generates `.env` and MCP config files
5. Installs and starts 4 systemd services (MCP, API, Dashboard, Regression)
6. Verifies all services are running

## Contents

| File | Purpose |
|------|---------|
| `setup.sh` | Main setup script |
| `test_setup.py` | Validate MCP connectivity and LLM API access |
| `systemd/` | Templated systemd unit files |

## Systemd Services

| Service | Unit File | Port |
|---------|-----------|------|
| MCP Server | `cpt-ai-mcp.service` | 9900 |
| REST API | `cpt-ai-api.service` | 8000 |
| Full Dashboard | `cpt-ai-dashboard.service` | 8050 |
| Regression Dashboard | `cpt-ai-regression.service` | 8060 |

## OUTPUT
[sbhavsar@n42-h30-000-r650 cpt-ai-clean]$ ./setup/setup.sh

══════════════════════════════════════════
  CPT AI Setup — Pre-flight Checks
══════════════════════════════════════════

✓ Python 3.12
✓ pip available
✓ git 2.43.0
[sudo] password for sbhavsar: 
Sorry, try again.
[sudo] password for sbhavsar: 
✓ sudo access (password may be required)
✓ systemd available
✓ Network connectivity (pypi.org reachable)
✓ User: sbhavsar
✓ Repo: /home/sbhavsar/cpt-ai-clean

✓ All pre-flight checks passed!

══════════════════════════════════════════
  OpenSearch Configuration
══════════════════════════════════════════

? OpenSearch host (e.g. opensearch.example.com): osv3.app.intlab.redhat.com
? OpenSearch port [443]: 443
? OpenSearch username: sbhavsar
? OpenSearch password: 

══════════════════════════════════════════
  AI Model Configuration
══════════════════════════════════════════

  1) Google Gemini (gemini-2.0-flash)
  2) Red Hat Granite (granite-3-3-8b-instruct)

? Choose AI model [1]: 1
? Gemini API key: 

══════════════════════════════════════════
  Creating Virtual Environment
══════════════════════════════════════════

✓ Created virtual environment at /home/sbhavsar/ai-mcp-env
✓ Upgraded pip

══════════════════════════════════════════
  Installing Dependencies
══════════════════════════════════════════

✓ Installed core + API + CLI dependencies
✓ Installed dashboard dependencies

══════════════════════════════════════════
  Writing Configuration
══════════════════════════════════════════

✓ Wrote /home/sbhavsar/cpt-ai-clean/.env
✓ Wrote /home/sbhavsar/opensearch_mcp_config.yml

══════════════════════════════════════════
  Installing Systemd Services
══════════════════════════════════════════

✓ Installed and patched unit files for user=sbhavsar
✓ Enabled and started cpt-ai-mcp
✓ Enabled and started cpt-ai-api
✓ Enabled and started cpt-ai-dashboard
✓ Enabled and started cpt-ai-regression

══════════════════════════════════════════
  Verifying Services
══════════════════════════════════════════

✓ cpt-ai-mcp is running
✗ cpt-ai-api failed to start — check: sudo journalctl -u cpt-ai-api -n 20
✓ cpt-ai-dashboard is running
✓ cpt-ai-regression is running

══════════════════════════════════════════
  Setup Complete (with warnings)
══════════════════════════════════════════

  MCP Server   http://localhost:9900
  API          http://localhost:8000      (Swagger: /docs)
  Dashboard    http://localhost:8050
  Regression   http://localhost:8060

  CLI usage:
    source ~/ai-mcp-env/bin/activate
    cd /home/sbhavsar/cpt-ai-clean
    python3 components/cli/json/regression_analyzer.py
    python3 components/cli/csv/csv_regression_analyzer.py --csv file1.csv file2.csv

  Service management:
    sudo systemctl status cpt-ai-api
    sudo systemctl restart cpt-ai-api
    sudo journalctl -u cpt-ai-api -f

  Stop everything:
    sudo systemctl stop cpt-ai-mcp cpt-ai-api cpt-ai-dashboard cpt-ai-regression
