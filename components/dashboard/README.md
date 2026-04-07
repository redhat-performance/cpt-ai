# Dashboard — Web Applications

Dash-based web dashboards for benchmark visualization and regression analysis.

## Apps

| App | File | Port | Description |
|-----|------|------|-------------|
| Full Dashboard | `app.py` | 8050 | Multi-tab dashboard (overview, heatmap, time series, regression) |
| Regression Analyzer | `ra_app.py` | 8060 | Standalone regression analysis with Q&A |

## Running

Managed by systemd after setup. For manual use:

```bash
source ~/ai-mcp-env/bin/activate
cd components/dashboard
python app.py       # http://localhost:8050
python ra_app.py    # http://localhost:8060
```

## Dependencies

Dashboard-specific dependencies are in `requirements.txt` (dash, pandas, numpy). Installed automatically by `setup/setup.sh`.
