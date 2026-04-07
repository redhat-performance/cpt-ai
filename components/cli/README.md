# CLI — Command-Line Tools

Interactive terminal tools for benchmark regression analysis.

## Subfolders

| Folder | Script | Data Source |
|--------|--------|-------------|
| `json/` | `regression_analyzer.py` | OpenSearch via MCP server |
| `json/` | `show_data_tree.py` | OpenSearch (direct) |
| `csv/` | `csv_regression_analyzer.py` | Local CSV files |

## Usage

```bash
source ~/ai-mcp-env/bin/activate
cd <project-root>

# OpenSearch mode (requires MCP server)
python3 components/cli/json/regression_analyzer.py
python3 components/cli/json/regression_analyzer.py --detail expert

# CSV mode (no MCP needed)
python3 components/cli/csv/csv_regression_analyzer.py --csv run1.csv run2.csv
```
