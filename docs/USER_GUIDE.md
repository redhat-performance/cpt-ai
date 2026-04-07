# CPT AI — User Guide

## Prerequisites

- VPN / network access to the Red Hat lab network
- A browser (for dashboard)
- `curl` and `jq` (for API)

No installation, no Python, no credentials needed.

---

## Dashboard

Open in your browser:

**Regression Analyzer:** http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8060

- Select cloud, OS, instance, and benchmark from dropdowns
- Compare two runs side by side
- Ask follow-up questions in the chat interface

---

## REST API

Base URL: `http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000`

Swagger docs: http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/docs

### 1. Health Check

```bash
curl -s http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/health | jq
```

### 2. List Clouds

```bash
curl -s -X POST http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/filters \
  -H "Content-Type: application/json" \
  -d '{"field": "cloud"}' | jq
```

### 3. List Benchmarks for a Specific Instance

```bash
curl -s -X POST http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/filters \
  -H "Content-Type: application/json" \
  -d '{"field": "benchmark", "filters": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D16ds_v6"}}' | jq
```

### 4. Compare Two Runs (PassMark — D16 vs D32)

```bash
curl -s -X POST http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/compare \
  -H "Content-Type: application/json" \
  -d '{
    "run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D16ds_v6", "benchmark": "passmark"},
    "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D32ds_v6", "benchmark": "passmark"},
    "detail_level": "medium"
  }' | jq
```

### 5. Ask a Follow-up Question

```bash
curl -s -X POST http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D16ds_v6", "benchmark": "passmark"},
    "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D32ds_v6", "benchmark": "passmark"},
    "detail_level": "medium",
    "question": "Which metrics improved the most and why?"
  }' | jq
```

### 6. Multi-turn Conversation

```bash
curl -s -X POST http://n42-h30-000-r650.rdu3.labs.perfscale.redhat.com:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "run1": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D16ds_v6", "benchmark": "passmark"},
    "run2": {"cloud": "azure", "os_vendor": "rhel", "os_version": "9.6", "instance": "Standard_D32ds_v6", "benchmark": "passmark"},
    "detail_level": "expert",
    "question": "Is the D32 worth 2x the cost of D16?",
    "chat_history": [
      {"role": "user", "content": "Which metrics improved the most and why?"},
      {"role": "assistant", "content": "The CPU-related metrics showed the largest improvements..."}
    ]
  }' | jq
```

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/filters` | List available values for a field (cloud, os_vendor, os_version, instance, benchmark) |
| `POST` | `/compare` | Compare two benchmark runs with AI analysis |
| `POST` | `/ask` | Ask follow-up questions about a comparison |

## Detail Levels

| Level | Output |
|-------|--------|
| `basic` | 1-2 line verdict |
| `medium` | 5-10 line analysis |
| `expert` | Comprehensive breakdown with per-metric details |
