"""
Regression Service - Thin Dash adapter over cpt_core.

Provides synchronous wrappers for Dash callbacks using AsyncBridge.
All core logic (MCP, AI, geomean) lives in cpt_core.
"""

import os
import sys
import json
import asyncio
import threading
import logging
import time

# Add project root to path for cpt_core imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from cpt_core import CPTConfig, RegressionAnalyzer, OpenAICompatibleProvider, ComparisonResult
from cpt_core.data_access import extract_metrics

logger = logging.getLogger(__name__)


class AsyncBridge:
    """Runs a persistent asyncio event loop in a daemon thread.
    Provides run_async(coro) that submits coroutines and returns results synchronously."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run_async(self, coro, timeout=120):
        """Submit a coroutine to the event loop and wait for the result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)


class RegressionService:
    """Singleton service wrapping cpt_core.RegressionAnalyzer for Dash callbacks.

    Manages MCP lifecycle, dropdown caching, and sync-to-async bridging.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._bridge = AsyncBridge()
        self._analyzer = None
        self._analyzer_lock = threading.Lock()
        self._dropdown_cache = {}  # (field, filters_key) -> (timestamp, options)
        self._cache_ttl = 300  # 5 minute cache

        # Load config from env
        self._config = CPTConfig.from_env()

    def _ensure_analyzer(self):
        """Lazily initialize and connect the RegressionAnalyzer."""
        with self._analyzer_lock:
            if self._analyzer is None:
                self._analyzer = RegressionAnalyzer(self._config)
                self._bridge.run_async(self._analyzer.connect())
                logger.info("RegressionAnalyzer connected")
            return self._analyzer

    def _reconnect_analyzer(self):
        """Force reconnect the analyzer."""
        with self._analyzer_lock:
            if self._analyzer:
                try:
                    self._bridge.run_async(self._analyzer.disconnect())
                except Exception:
                    pass
            self._analyzer = RegressionAnalyzer(self._config)
            self._bridge.run_async(self._analyzer.connect())
            logger.info("RegressionAnalyzer reconnected")
            return self._analyzer

    def _cache_key(self, field, filters):
        """Create a hashable cache key from field and filters."""
        filters_str = json.dumps(filters, sort_keys=True) if filters else ''
        return (field, filters_str)

    def get_dropdown_options(self, field, filters=None):
        """Get available values for a dropdown field (cached for 5 minutes).

        Args:
            field: OpenSearch field name (e.g., 'metadata.cloud_provider')
            filters: dict of {field_name: value} to filter by

        Returns:
            list of {'label': value, 'value': value} for Dash dropdowns
        """
        # Check cache first
        key = self._cache_key(field, filters)
        if key in self._dropdown_cache:
            cached_time, cached_options = self._dropdown_cache[key]
            if time.time() - cached_time < self._cache_ttl:
                logger.info(f"get_dropdown_options CACHE HIT field={field} -> {len(cached_options)} options")
                return cached_options

        try:
            analyzer = self._ensure_analyzer()
            values = self._bridge.run_async(
                analyzer.get_filter_options(field, filters)
            )
            logger.info(f"get_dropdown_options field={field} filters={filters} -> {len(values)} values")
            options = [{'label': v[0], 'value': v[0]} for v in values]
            self._dropdown_cache[key] = (time.time(), options)
            return options
        except Exception as e:
            logger.error(f"get_dropdown_options failed: {e}")
            # Try reconnect once
            try:
                analyzer = self._reconnect_analyzer()
                values = self._bridge.run_async(
                    analyzer.get_filter_options(field, filters)
                )
                options = [{'label': v[0], 'value': v[0]} for v in values]
                self._dropdown_cache[key] = (time.time(), options)
                return options
            except Exception as e2:
                logger.error(f"get_dropdown_options failed after reconnect: {e2}")
                return []

    def run_comparison(self, run1_params, run2_params, detail_level='medium'):
        """Orchestrate full comparison flow via cpt_core.

        Returns:
            dict with comparison results or error
        """
        try:
            analyzer = self._ensure_analyzer()
            result = self._bridge.run_async(
                analyzer.compare(run1_params, run2_params, detail_level),
                timeout=120
            )

            # Convert ComparisonResult to dict for Dash compatibility
            return {
                'run1': result.run1,
                'run2': result.run2,
                'geomean': result.geomean,
                'analysis': result.analysis,
                'detail_level': result.detail_level,
            }

        except ValueError as e:
            logger.error(f"run_comparison validation error: {e}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"run_comparison failed: {e}")
            return {'error': str(e)}

    def ask_question(self, question, comparison_data, chat_history=None):
        """Multi-turn Q&A about a comparison.

        Args:
            question: user's question string
            comparison_data: the full comparison result dict from run_comparison()
            chat_history: list of {'role': str, 'content': str} dicts

        Returns:
            str: AI response
        """
        try:
            analyzer = self._ensure_analyzer()

            # Reconstruct ComparisonResult from dict
            comparison = ComparisonResult(
                run1=comparison_data['run1'],
                run2=comparison_data['run2'],
                geomean=comparison_data.get('geomean', {}),
                analysis=comparison_data.get('analysis', ''),
                detail_level=comparison_data.get('detail_level', 'medium'),
            )

            return self._bridge.run_async(
                analyzer.ask(question, comparison, chat_history),
                timeout=120
            )
        except Exception as e:
            logger.error(f"ask_question failed: {e}")
            return f"ERROR: {e}"
