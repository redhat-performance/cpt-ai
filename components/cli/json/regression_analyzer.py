#!/usr/bin/env python3
"""
Regression Analyzer - Compare Run1 vs Run2 (OpenSearch Mode)

REGRESSION = RUN1 vs RUN2

CLI frontend using the cpt_core library for data access, analysis, and AI.
Reads benchmark data from OpenSearch via MCP server.

For CSV-based comparison, use csv_regression_analyzer.py instead.

Usage:
    python regression_analyzer.py
    python regression_analyzer.py --detail expert
"""

import argparse
import json
import os
import sys
import logging
import asyncio
import urllib3
from dotenv import load_dotenv

# Add project root to path for cpt_core imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from cpt_core import CPTConfig, RegressionAnalyzer, ComparisonResult
from cpt_core.data_access import extract_metrics, get_available_values, MCPClient
from cpt_core.cli_utils import print_result, qa_loop

# Load environment variables from .env
load_dotenv()

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Logging setup - 3 separate log files
_log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'logs')
os.makedirs(_log_dir, exist_ok=True)
_log_formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')

def _make_logger(name, filename):
    lg = logging.getLogger(name)
    lg.setLevel(logging.INFO)
    fh = logging.FileHandler(os.path.join(_log_dir, filename))
    fh.setFormatter(_log_formatter)
    lg.addHandler(fh)
    return lg

# opensearch_mcp_queries.log - OpenSearch queries sent via MCP
mcp_logger = _make_logger('opensearch_mcp', 'opensearch_mcp_queries.log')

# session.log - Selected filters and fetched run data
session_logger = _make_logger('session', 'session.log')

# prompt.log - AI prompts fed and responses received
prompt_logger = _make_logger('prompt', 'prompt.log')

# qa_queries.log - Interactive Q&A questions and answers
qa_logger = _make_logger('qa_queries', 'qa_queries.log')

CACHE_FILE = os.path.join(os.path.expanduser("~"), ".cache", "regression_last_comparison.json")


def save_comparison(run1_params, run1_data, run2_params, run2_data):
    """Save comparison to cache for quick Q&A access"""
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump({
            'run1_params': run1_params,
            'run1_data': run1_data,
            'run2_params': run2_params,
            'run2_data': run2_data
        }, f)
    print(f"\nComparison saved to {CACHE_FILE} for quick Q&A access.")


async def select_run(mcp_client, config, run_name):
    """Interactive selection of a run (5 parameters) with numbered input"""

    print(f"\n{'=' * 80}")
    print(f"SELECT {run_name}")
    print("=" * 80)

    # Define steps: (step_label, field_key, os_field, display_prefix)
    steps = [
        ("Step 1/5: Cloud Provider",  "cloud",      "metadata.cloud_provider", None),
        ("Step 2/5: OS Vendor",       "os_vendor",   "metadata.os_vendor", None),
        ("Step 3/5: OS Version",      "os_version",  "system_under_test.operating_system.version", "RHEL "),
        ("Step 4/5: Instance Type",   "instance",    "metadata.instance_type", None),
        ("Step 5/5: Benchmark",       "benchmark",   "test.name", None),
    ]

    # Map field_key to the OpenSearch filter field name
    filter_fields = {
        "cloud": "metadata.cloud_provider",
        "os_vendor": "metadata.os_vendor",
        "os_version": "system_under_test.operating_system.version",
        "instance": "metadata.instance_type",
    }

    run_params = {}

    for label, field_key, os_field, prefix in steps:
        # Build filters from previously selected params
        filters = {}
        for prev_key in list(filter_fields.keys()):
            if prev_key in run_params:
                filters[filter_fields[prev_key]] = run_params[prev_key]
            else:
                break

        options = await get_available_values(
            mcp_client, config, os_field, filters if filters else None
        )

        if not options:
            print(f"\n  ERROR: No options found for {label}.")
            return None

        print(f"\n  {label}:")
        for i, (value, count) in enumerate(options, 1):
            display = f"{prefix}{value}" if prefix else value
            print(f"    {i}. {display}  ({count:,} docs)")

        while True:
            choice = input(f"  Select [1-{len(options)}]: ").strip()
            try:
                idx = int(choice)
                if 1 <= idx <= len(options):
                    run_params[field_key] = options[idx - 1][0]
                    break
                print(f"  Invalid: enter a number between 1 and {len(options)}")
            except ValueError:
                print(f"  Invalid: enter a number between 1 and {len(options)}")

    session_logger.info(f"{run_name} SELECTED: Cloud={run_params['cloud']}, OS={run_params['os_vendor']} {run_params['os_version']}, Instance={run_params['instance']}, Benchmark={run_params['benchmark']}")

    return run_params


async def main_opensearch(detail_level=None):
    """OpenSearch mode - interactive selection from MCP server."""

    print("=" * 80)
    print("Regression Analyzer (using OpenSearch MCP Server)")
    print("=" * 80)
    print("\nREGRESSION = RUN1 vs RUN2")
    print("=" * 80)

    config = CPTConfig.from_env()
    print(f"\nUsing model: {config.ai_model}")

    analyzer = RegressionAnalyzer(config)

    try:
        print("\nConnecting to OpenSearch MCP Server...")
        await analyzer.connect()
        print("Connected successfully!")

        run1_params = await select_run(analyzer._mcp, config, "RUN 1 (Baseline)")
        if not run1_params:
            print("ERROR: Run 1 selection cancelled or no options available.")
            return

        run2_params = await select_run(analyzer._mcp, config, "RUN 2 (Comparison)")
        if not run2_params:
            print("ERROR: Run 2 selection cancelled or no options available.")
            return

        # Use CLI flag if provided, otherwise prompt interactively
        if not detail_level:
            print("\nSelect Analysis Detail Level")
            print("\n  1. Basic   (1-2 lines)")
            print("  2. Medium  (5-10 lines)")
            print("  3. Expert  (Comprehensive)")

            level_choice = input("\nSelect [1-3]: ").strip()
            detail_levels = {"1": "basic", "2": "medium", "3": "expert"}
            detail_level = detail_levels.get(level_choice, "medium")

        print("\n" + "=" * 80)
        print("ANALYZING REGRESSION...")
        print("=" * 80)

        result = await analyzer.compare(run1_params, run2_params, detail_level)

        save_comparison(
            run1_params, result.run1['data'],
            run2_params, result.run2['data'],
        )

        print_result(result, detail_level, logger=session_logger)
        await qa_loop(analyzer, result)

    finally:
        await analyzer.disconnect()


async def main():
    """Main entry point — OpenSearch interactive mode."""
    parser = argparse.ArgumentParser(
        description="Regression Analyzer - Compare benchmark runs from OpenSearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python regression_analyzer.py
  python regression_analyzer.py --detail expert

For CSV-based comparison, use csv_regression_analyzer.py instead.
        """,
    )
    parser.add_argument(
        '--detail', choices=['basic', 'medium', 'expert'], default=None,
        help='Analysis detail level (skips interactive prompt if provided)',
    )

    args = parser.parse_args()
    await main_opensearch(detail_level=args.detail)


if __name__ == "__main__":
    asyncio.run(main())
