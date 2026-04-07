# Components

Application components that provide different interfaces to the CPT AI system.

| Component | Path | Description | Port |
|-----------|------|-------------|------|
| **API** | `api/` | FastAPI REST API for programmatic access | 8000 |
| **CLI** | `cli/` | Interactive command-line tools | — |
| **Dashboard** | `dashboard/` | Dash web applications | 8050, 8060 |

All components share the `cpt_core` library at the project root.
