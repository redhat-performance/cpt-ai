#!/usr/bin/env python3
"""
Show zathras data as a hierarchical tree
"""

import json
from opensearchpy import OpenSearch
import urllib3
from collections import defaultdict

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_opensearch_client():
    """Create OpenSearch client with credentials from environment."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    host = os.getenv("OPENSEARCH_HOST", "localhost")
    port = int(os.getenv("OPENSEARCH_PORT", "9200"))
    username = os.getenv("OPENSEARCH_USERNAME", "")
    password = os.getenv("OPENSEARCH_PASSWORD", "")

    client = OpenSearch(
        hosts=[{'host': host, 'port': port}],
        http_auth=(username, password) if username else None,
        use_ssl=port == 443,
        verify_certs=False,
        ssl_show_warn=False,
        timeout=30
    )
    return client

def get_nested_aggregations(client, index_name):
    """Get nested aggregations for hierarchical data"""

    try:
        response = client.search(
            index=index_name,
            body={
                "size": 0,
                "aggs": {
                    # Level 1: Cloud providers
                    "clouds": {
                        "terms": {"field": "metadata.cloud_provider.keyword", "size": 10},
                        "aggs": {
                            # Level 2: OS vendors within each cloud
                            "os_vendors": {
                                "terms": {"field": "metadata.os_vendor.keyword", "size": 10},
                                "aggs": {
                                    # Level 3: OS versions within each OS vendor
                                    "os_versions": {
                                        "terms": {"field": "system_under_test.operating_system.version.keyword", "size": 50},
                                        "aggs": {
                                            # Level 4: Instance types within each OS version
                                            "instance_types": {
                                                "terms": {"field": "metadata.instance_type.keyword", "size": 100},
                                                "aggs": {
                                                    # Level 5: Benchmarks within each instance type
                                                    "benchmarks": {
                                                        "terms": {"field": "test.name.keyword", "size": 50}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    # Top level aggregation for all benchmarks
                    "all_benchmarks": {
                        "terms": {"field": "test.name.keyword", "size": 50}
                    }
                }
            }
        )

        return response['aggregations']
    except Exception as e:
        print(f"Error getting aggregations: {e}")
        return None

def print_tree(client, index_name):
    """Print hierarchical tree structure"""

    # Get index stats first
    try:
        stats = client.indices.stats(index=index_name)
        total_docs = stats['_all']['primaries']['docs']['count']
    except:
        total_docs = 0

    print(f"\n{'=' * 80}")
    print(f"OpenSearch Dataset: {index_name} ({total_docs:,} Documents)")
    print(f"{'=' * 80}")

    aggs = get_nested_aggregations(client, index_name)

    if not aggs:
        print("ERROR: Could not retrieve data")
        return

    print("|")

    # Level 1: Cloud providers
    clouds = aggs['clouds']['buckets']

    for cloud_idx, cloud in enumerate(clouds):
        is_last_cloud = cloud_idx == len(clouds) - 1
        cloud_prefix = "+--" if is_last_cloud else "+--"
        cloud_cont = "    " if is_last_cloud else "|   "

        print(f"{cloud_prefix} CLOUD: {cloud['key'].upper()} ({cloud['doc_count']:,})")
        print(f"{cloud_cont}|")

        # Level 2: OS vendors within this cloud
        os_vendors = cloud['os_vendors']['buckets']

        for vendor_idx, vendor in enumerate(os_vendors):
            is_last_vendor = vendor_idx == len(os_vendors) - 1
            vendor_prefix = f"{cloud_cont}+--" if is_last_vendor else f"{cloud_cont}+--"
            vendor_cont = f"{cloud_cont}    " if is_last_vendor else f"{cloud_cont}|   "

            print(f"{vendor_prefix} OS Vendor: {vendor['key']} ({vendor['doc_count']:,})")
            print(f"{vendor_cont}|")

            # Level 3: OS Versions within this vendor
            os_versions = vendor['os_versions']['buckets']

            for version_idx, version in enumerate(os_versions[:15]):  # Top 15 versions
                is_last_version = version_idx == len(os_versions[:15]) - 1
                version_prefix = f"{vendor_cont}+--" if is_last_version else f"{vendor_cont}+--"
                version_cont = f"{vendor_cont}    " if is_last_version else f"{vendor_cont}|   "

                version_display = version['key'] if version['key'] else 'N/A'
                print(f"{version_prefix} OS Version: RHEL {version_display} ({version['doc_count']:,})")
                print(f"{version_cont}|")

                # Level 4: Instance Types within this OS version
                instance_types = version['instance_types']['buckets']

                for inst_idx, instance in enumerate(instance_types[:20]):  # Top 20 instances
                    is_last_instance = inst_idx == len(instance_types[:20]) - 1
                    instance_prefix = f"{version_cont}+--" if is_last_instance else f"{version_cont}+--"
                    instance_cont = f"{version_cont}    " if is_last_instance else f"{version_cont}|   "

                    print(f"{instance_prefix} Instance: {instance['key']} ({instance['doc_count']:,})")
                    print(f"{instance_cont}|")

                    # Level 5: Benchmarks within this instance type
                    benchmarks = instance['benchmarks']['buckets']

                    for bench_idx, benchmark in enumerate(benchmarks):
                        is_last_bench = bench_idx == len(benchmarks) - 1
                        bench_prefix = f"{instance_cont}+--" if is_last_bench else f"{instance_cont}+--"

                        print(f"{bench_prefix} Benchmark: {benchmark['key']} ({benchmark['doc_count']:,})")

                    if not is_last_instance:
                        print(f"{instance_cont}")

                if len(instance_types) > 20:
                    print(f"{version_cont}+-- ... and {len(instance_types) - 20} more instance types")

                if not is_last_version:
                    print(f"{version_cont}")

            if len(os_versions) > 15:
                print(f"{vendor_cont}+-- ... and {len(os_versions) - 15} more OS versions")

            if not is_last_vendor:
                print(f"{vendor_cont}")

        if not is_last_cloud:
            print(f"{cloud_cont}")
            print("|")

    # All benchmarks summary at the bottom
    all_benchmarks = aggs['all_benchmarks']['buckets']

    print("|")
    print(f"+-- ALL BENCHMARKS (Combined - {total_docs:,} Total)")
    print("    |")

    for bench_idx, benchmark in enumerate(all_benchmarks):
        is_last = bench_idx == len(all_benchmarks) - 1
        bench_prefix = "    +--" if is_last else "    +--"

        print(f"{bench_prefix} {benchmark['key']} ({benchmark['doc_count']:,})")

    print()

def main():
    """Main function"""

    print("\n" + "=" * 80)
    print("ZATHRAS DATA TREE - Hierarchical View")
    print("=" * 80)

    client = create_opensearch_client()

    # Check connection
    try:
        info = client.info()
        print(f"\nOK: Connected to OpenSearch cluster: {info.get('cluster_name', 'N/A')}")
    except Exception as e:
        print(f"\nERROR: Failed to connect: {e}")
        return

    # Show tree for each index
    indices = ["zathras-results", "zathras-timeseries"]

    for index_name in indices:
        try:
            if not client.indices.exists(index=index_name):
                print(f"\nWARNING: Index {index_name} does not exist")
                continue

            print_tree(client, index_name)

        except Exception as e:
            print(f"\nERROR: Error processing {index_name}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
