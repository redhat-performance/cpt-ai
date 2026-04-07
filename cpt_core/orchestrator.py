"""
RegressionAnalyzer orchestrator - high-level API for the comparison pipeline.

Wires together MCPClient, data access helpers, analysis functions, and AI provider.
"""

import logging

from .config import CPTConfig
from .data_access import MCPClient, find_run, find_all_subtests, get_available_values, extract_metrics
from .analysis import ComparisonResult, build_geomean_info
from .ai_provider import AIProvider, OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class RegressionAnalyzer:
    """High-level orchestrator for regression analysis.

    Usage:
        config = CPTConfig.from_env()
        analyzer = RegressionAnalyzer(config)
        await analyzer.connect()
        result = await analyzer.compare(run1_params, run2_params, 'medium')
        answer = await analyzer.ask("Why did throughput drop?", result)
        await analyzer.disconnect()
    """

    def __init__(self, config: CPTConfig, ai_provider: AIProvider = None):
        self.config = config
        self._mcp = MCPClient(config.mcp_url)
        self._ai = ai_provider or OpenAICompatibleProvider(
            endpoint=config.ai_endpoint,
            api_key=config.ai_api_key,
            model_name=config.ai_model,
            ssl_verify=config.ssl_verify,
        )

    async def connect(self):
        """Connect to the MCP server."""
        await self._mcp.connect()

    async def disconnect(self):
        """Disconnect from the MCP server."""
        await self._mcp.disconnect()

    async def get_filter_options(self, field, filters=None):
        """Get available dropdown values for a field.

        Returns list of (value, doc_count) tuples.
        """
        return await get_available_values(self._mcp, self.config, field, filters)

    async def compare(self, run1_params, run2_params, detail_level='medium') -> ComparisonResult:
        """Full comparison pipeline: find runs -> subtests -> geomean -> AI analysis.

        Args:
            run1_params: dict with cloud, os_vendor, os_version, instance, benchmark
            run2_params: same structure
            detail_level: 'basic', 'medium', or 'expert'

        Returns:
            ComparisonResult

        Raises:
            ValueError: if a run is not found
        """
        # Find runs
        run1 = await find_run(
            self._mcp, self.config,
            run1_params['cloud'], run1_params['os_vendor'], run1_params['os_version'],
            run1_params['instance'], run1_params['benchmark'],
        )
        if not run1:
            raise ValueError(f"No valid run found for Run 1: {run1_params}")

        run2 = await find_run(
            self._mcp, self.config,
            run2_params['cloud'], run2_params['os_vendor'], run2_params['os_version'],
            run2_params['instance'], run2_params['benchmark'],
        )
        if not run2:
            raise ValueError(f"No valid run found for Run 2: {run2_params}")

        # Fetch subtests
        run1_subtests = await find_all_subtests(
            self._mcp, self.config,
            run1_params['cloud'], run1_params['os_vendor'], run1_params['os_version'],
            run1_params['instance'], run1_params['benchmark'],
        )
        run2_subtests = await find_all_subtests(
            self._mcp, self.config,
            run2_params['cloud'], run2_params['os_vendor'], run2_params['os_version'],
            run2_params['instance'], run2_params['benchmark'],
        )

        benchmark = run1_params.get('benchmark', '')
        geomean_info = build_geomean_info(run1_subtests, run2_subtests, benchmark)

        # AI analysis
        analysis = await self._ai.analyze(
            run1_params, run1['data'],
            run2_params, run2['data'],
            detail_level, geomean_info,
        )

        return ComparisonResult(
            run1={
                'params': run1_params,
                'id': run1['id'],
                'timestamp': run1['timestamp'],
                'data': run1['data'],
            },
            run2={
                'params': run2_params,
                'id': run2['id'],
                'timestamp': run2['timestamp'],
                'data': run2['data'],
            },
            geomean=geomean_info,
            analysis=analysis,
            detail_level=detail_level,
        )

    async def ask(self, question, comparison: ComparisonResult,
                  chat_history=None) -> str:
        """Ask a follow-up question about a comparison.

        Args:
            question: user's question
            comparison: ComparisonResult from compare()
            chat_history: list of {'role': str, 'content': str}

        Returns:
            AI answer string
        """
        return await self._ai.ask(
            question,
            comparison.run1['params'], comparison.run1['data'],
            comparison.run2['params'], comparison.run2['data'],
            comparison.geomean,
            chat_history,
        )
