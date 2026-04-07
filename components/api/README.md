# API — REST API

FastAPI server for programmatic access to CPT AI regression analysis.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/compare` | Compare two benchmark runs |
| `POST` | `/ask` | Follow-up question about a comparison |
| `POST` | `/filters` | Get available dropdown values |
| `GET` | `/health` | Health check |

## Running

Managed by systemd (`cpt-ai-api.service`) after setup. For manual use:

```bash
source ~/ai-mcp-env/bin/activate
cd components/api
uvicorn api:app --host 0.0.0.0 --port 8000
```

Swagger docs at http://localhost:8000/docs
