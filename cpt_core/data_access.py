"""
Data access layer - MCP client and OpenSearch query helpers.

All functions accept a CPTConfig to parameterize cluster/index instead of
hard-coding values.
"""

import json
import logging
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

from .config import CPTConfig

logger = logging.getLogger(__name__)


class MCPClient:
    """OpenSearch MCP Client using SSE transport."""

    def __init__(self, url: str = "http://localhost:9900/sse"):
        self.url = url
        self.session = None
        self._client_context = None
        self._session_context = None

    async def connect(self):
        """Connect to MCP server via SSE."""
        self._client_context = sse_client(self.url)
        read, write = await self._client_context.__aenter__()
        self._session_context = ClientSession(read, write)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()

    async def disconnect(self):
        """Disconnect from MCP server."""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._client_context:
            await self._client_context.__aexit__(None, None, None)

    async def call_tool(self, tool_name, arguments):
        """Call an MCP tool and return parsed JSON result."""
        result = await self.session.call_tool(tool_name, arguments)
        if result.content:
            for content in result.content:
                if hasattr(content, 'text') and content.text:
                    text = content.text
                    json_start = text.find('{')
                    if json_start != -1:
                        return json.loads(text[json_start:])
                    return json.loads(text)
        return None


async def get_available_values(mcp_client: MCPClient, config: CPTConfig, field: str, filters=None):
    """Get available values for a field using MCP aggregation.

    Args:
        mcp_client: connected MCPClient
        config: CPTConfig with cluster/index
        field: OpenSearch field name
        filters: optional dict of {field_name: value}

    Returns:
        list of (value, doc_count) tuples
    """
    query = {"match_all": {}}
    if filters:
        query = {"bool": {"must": [
            {"term": {fn: fv}} for fn, fv in filters.items()
        ]}}

    agg_query = {
        "size": 0,
        "query": query,
        "aggs": {"values": {"terms": {"field": field, "size": 100}}},
    }

    try:
        result = await mcp_client.call_tool(
            "SearchIndexTool",
            {
                "opensearch_cluster_name": config.opensearch_cluster,
                "index": config.opensearch_index,
                "query_dsl": json.dumps(agg_query),
                "size": 0,
            },
        )
        if result and 'aggregations' in result:
            buckets = result['aggregations']['values']['buckets']
            return [(b['key'], b['doc_count']) for b in buckets]
        return []
    except Exception as e:
        logger.error(f"get_available_values failed: {e}")
        return []


async def find_run(mcp_client: MCPClient, config: CPTConfig,
                   cloud, os_vendor, os_version, instance, benchmark):
    """Find most recent run matching the 5 parameters.

    Returns dict with 'id', 'timestamp', 'data' keys, or None.
    """
    search_query = {
        "size": 10,
        "query": {
            "bool": {
                "must": [
                    {"term": {"metadata.cloud_provider": cloud}},
                    {"term": {"metadata.os_vendor": os_vendor}},
                    {"term": {"system_under_test.operating_system.version": os_version}},
                    {"term": {"metadata.instance_type": instance}},
                    {"term": {"test.name": benchmark}},
                ],
                "must_not": [{"term": {"results.status": "UNKNOWN"}}],
            }
        },
        "sort": [{"metadata.test_timestamp": {"order": "desc"}}],
    }

    try:
        logger.info(f"find_run: cloud={cloud}, os={os_vendor} {os_version}, "
                     f"instance={instance}, benchmark={benchmark}")

        result = await mcp_client.call_tool(
            "SearchIndexTool",
            {
                "opensearch_cluster_name": config.opensearch_cluster,
                "index": config.opensearch_index,
                "query_dsl": json.dumps(search_query),
                "size": 10,
            },
        )

        if result and 'hits' in result and 'hits' in result['hits']:
            for hit in result['hits']['hits']:
                run_data = hit['_source']
                metrics = extract_metrics(run_data)
                if metrics:
                    return {
                        'id': hit['_id'],
                        'timestamp': run_data.get('metadata', {}).get('test_timestamp', 'N/A'),
                        'data': run_data,
                    }
        return None
    except Exception as e:
        logger.error(f"find_run failed: {e}")
        return None


def extract_metrics(run_data):
    """Extract performance metrics from a run document."""
    results = run_data.get('results', {})
    runs = results.get('runs', {})
    if not runs:
        return None
    first_run_key = list(runs.keys())[0]
    return runs[first_run_key].get('metrics', {})


async def find_all_subtests(mcp_client: MCPClient, config: CPTConfig,
                            cloud, os_vendor, os_version, instance, benchmark):
    """Fetch ALL subtest documents for a benchmark configuration.

    Returns dict of {subtest_name: metrics_dict}.
    """
    search_query = {
        "size": 500,
        "query": {
            "bool": {
                "must": [
                    {"term": {"metadata.cloud_provider": cloud}},
                    {"term": {"metadata.os_vendor": os_vendor}},
                    {"term": {"system_under_test.operating_system.version": os_version}},
                    {"term": {"metadata.instance_type": instance}},
                    {"term": {"test.name": benchmark}},
                ],
                "must_not": [{"term": {"results.status": "UNKNOWN"}}],
            }
        },
        "sort": [{"metadata.test_timestamp": {"order": "desc"}}],
    }

    try:
        result = await mcp_client.call_tool(
            "SearchIndexTool",
            {
                "opensearch_cluster_name": config.opensearch_cluster,
                "index": config.opensearch_index,
                "query_dsl": json.dumps(search_query),
                "size": 500,
            },
        )

        subtests = {}
        if result and 'hits' in result and 'hits' in result['hits']:
            for hit in result['hits']['hits']:
                run_data = hit['_source']
                runs = run_data.get('results', {}).get('runs', {})
                if not runs:
                    continue
                for subtest_name, subtest_data in runs.items():
                    metrics = subtest_data.get('metrics', {})
                    if metrics and subtest_name not in subtests:
                        subtests[subtest_name] = metrics

        logger.info(f"find_all_subtests: {len(subtests)} subtests for {instance}/{benchmark}")
        return subtests
    except Exception as e:
        logger.error(f"find_all_subtests failed: {e}")
        return {}
