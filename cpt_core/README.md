# cpt_core — Shared Library

Shared Python library used by all CPT AI components (API, CLI, Dashboard).

## Modules

| Module | Purpose |
|--------|---------|
| `config.py` | Configuration dataclass, loads from `.env` |
| `data_access.py` | MCP client, OpenSearch query helpers |
| `analysis.py` | Direction-aware geomean, thresholds, severity, root-cause triage |
| `statistics.py` | Mean, median, stddev, CoV, Welch's t-test, outlier detection |
| `ai_provider.py` | AI abstraction (ABC + OpenAI-compatible implementation) |
| `orchestrator.py` | High-level pipeline: find runs → subtests → geomean → AI |
| `csv_orchestrator.py` | Same pipeline as orchestrator, but reads from CSV files |
| `csv_parser.py` | Parse Zathras CSV files (passmark, streams, fio, uperf, etc.) |
| `cli_utils.py` | Shared CLI output formatting (boxed layout, Q&A loop) |

## Usage

All components import from this library:

```python
from cpt_core import CPTConfig, RegressionAnalyzer, ComparisonResult
from cpt_core.data_access import extract_metrics, MCPClient
from cpt_core.analysis import build_geomean_info
```
