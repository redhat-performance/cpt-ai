#!/usr/bin/env python3
"""
Setup Validation Script
Tests MCP/OpenSearch connectivity, LLM API access, and available benchmarks
"""

import asyncio
import json
import os
import sys
from dotenv import load_dotenv
import warnings

warnings.filterwarnings('ignore', message='Unverified HTTPS request')
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except:
    pass

GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_test(name: str, status: str, message: str = ""):
    symbol = "✅" if status == "pass" else "❌" if status == "fail" else "⚠️"
    color = GREEN if status == "pass" else RED if status == "fail" else YELLOW
    print(f"{symbol} {color}{name}{RESET}", end="")
    if message:
        print(f": {message}")
    else:
        print()


async def test_mcp_connection():
    """TEST 1: Connect to MCP server and list tools"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 1: MCP Server Connection{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        host = os.getenv("MCP_SERVER_HOST", "localhost")
        port = int(os.getenv("MCP_SERVER_PORT", 9900))
        url = f"http://{host}:{port}/sse"

        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print_test("MCP Server", "pass", f"Connected to {url}")

                tools_response = await session.list_tools()
                tool_names = [t.name for t in tools_response.tools]
                print_test("MCP Tools", "pass", f"{len(tool_names)} tools: {', '.join(tool_names)}")

                return True

    except ConnectionRefusedError:
        print_test("MCP Server", "fail", "Connection refused — is the MCP server running?")
        return False
    except Exception as e:
        print_test("MCP Server", "fail", str(e))
        return False


async def test_opensearch_access():
    """TEST 2: Verify OpenSearch clusters and indices are accessible via MCP"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 2: OpenSearch Data Access{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        host = os.getenv("MCP_SERVER_HOST", "localhost")
        port = int(os.getenv("MCP_SERVER_PORT", 9900))
        url = f"http://{host}:{port}/sse"

        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List indices on zathras cluster
                result = await session.call_tool(
                    "ListIndexTool",
                    arguments={"opensearch_cluster_name": "zathras"}
                )

                indices_text = result.content[0].text if result.content else ""
                print_test("Cluster: zathras", "pass", "Accessible")

                # Check for expected indices
                for index_name in ["zathras-results", "zathras-timeseries"]:
                    if index_name in indices_text:
                        print_test(f"  Index: {index_name}", "pass", "Found")
                    else:
                        print_test(f"  Index: {index_name}", "fail", "Not found")

                return True

    except Exception as e:
        print_test("OpenSearch Access", "fail", str(e))
        return False


async def test_llm_api():
    """TEST 3: Verify LLM API is reachable and which model is configured"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 3: LLM API Connection{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    try:
        import httpx

        endpoint = os.getenv("MODELS_CORP_ENDPOINT")
        api_key = os.getenv("MODELS_CORP_API_KEY")
        model_name = os.getenv("MODEL_NAME")

        if not all([endpoint, api_key, model_name]):
            print_test("LLM Config", "fail", "Missing MODELS_CORP_ENDPOINT, MODELS_CORP_API_KEY, or MODEL_NAME in .env")
            return False

        is_gemini = "gemini" in model_name.lower()
        provider = "Google Gemini" if is_gemini else "models.corp Granite"
        print_test("Active Model", "pass", f"{model_name} ({provider})")

        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            response = await client.post(
                f"{endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": "Say 'Hello' if you receive this message."}
                    ],
                    "max_tokens": 50,
                    "temperature": 0.1
                }
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                print_test("API Response", "pass", f"{content[:50]}")
                return True
            else:
                print_test("API Response", "fail", f"HTTP {response.status_code}: {response.text[:100]}")
                return False

    except Exception as e:
        print_test("LLM API", "fail", str(e))
        return False


async def test_available_benchmarks():
    """TEST 4: Discover which benchmarks have data in OpenSearch"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}TEST 4: Available Benchmarks{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        host = os.getenv("MCP_SERVER_HOST", "localhost")
        port = int(os.getenv("MCP_SERVER_PORT", 9900))
        url = f"http://{host}:{port}/sse"

        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Aggregate on test.name.keyword to find all benchmarks with data
                agg_query = json.dumps({
                    "size": 0,
                    "aggs": {
                        "benchmarks": {
                            "terms": {
                                "field": "test.name.keyword",
                                "size": 50
                            }
                        }
                    }
                })

                result = await session.call_tool(
                    "SearchIndexTool",
                    arguments={
                        "opensearch_cluster_name": "zathras",
                        "index": "zathras-results",
                        "query": agg_query,
                        "size": 0
                    }
                )

                if result.content:
                    text = result.content[0].text
                    json_start = text.find('{')
                    if json_start != -1:
                        data = json.loads(text[json_start:])
                    else:
                        data = json.loads(text)

                    buckets = data.get("aggregations", {}).get("benchmarks", {}).get("buckets", [])

                    if buckets:
                        print(f"Found {len(buckets)} benchmarks with data in zathras-results:\n")
                        for bucket in buckets:
                            name = bucket["key"]
                            count = bucket["doc_count"]
                            print(f"  {GREEN}{name:<25}{RESET} {count:>6} documents")
                        return True
                    else:
                        print_test("Benchmarks", "warn", "No benchmark data found in zathras-results")
                        return True

                print_test("Benchmarks", "fail", "Empty response from OpenSearch")
                return False

    except Exception as e:
        print_test("Available Benchmarks", "fail", str(e))
        return False


async def main():
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}CPT Regression Analysis - Setup Validation{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")

    load_dotenv()

    results = []
    results.append(("MCP Server", await test_mcp_connection()))
    results.append(("OpenSearch Data", await test_opensearch_access()))
    results.append(("LLM API", await test_llm_api()))
    results.append(("Benchmarks", await test_available_benchmarks()))

    passed = sum(1 for _, r in results if r)
    total = len(results)
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
