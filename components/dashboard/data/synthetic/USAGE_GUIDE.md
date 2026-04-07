# Synthetic Data Usage Guide

Quick reference for working with the enhanced synthetic benchmark dataset.

## Quick Stats

- **Documents**: 800 benchmark test results
- **File Size**: ~3.0 MB (~103,000 lines)
- **Date Range**: June 2025 - December 2025 (6 months)
- **Success Rate**: ~93% (varies by run)
- **Test Coverage**: 12 benchmark types × 100 unique scenarios
- **OS Coverage**: 4 distributions (RHEL, Ubuntu, Amazon Linux, SLES) with 13 versions

## Loading the Data

### Python

```python
import json

# Load all documents
with open('data/synthetic/benchmark_results.json', 'r') as f:
    documents = json.load(f)

print(f"Loaded {len(documents)} benchmark results")
```

### Pandas

```python
import pandas as pd
import json

# Load and flatten for analysis
with open('data/synthetic/benchmark_results.json', 'r') as f:
    documents = json.load(f)

# Extract key fields
df = pd.DataFrame([{
    'test_name': d['test']['name'],
    'os_distribution': d['system_under_test']['operating_system']['distribution'],
    'os_version': d['system_under_test']['operating_system']['version'],
    'cloud_provider': d['metadata']['cloud_provider'],
    'instance_type': d['metadata']['instance_type'],
    'status': d['results']['status'],
    'timestamp': d['metadata']['test_timestamp'],
    'primary_metric_value': d['results']['primary_metric']['value'],
    'primary_metric_unit': d['results']['primary_metric']['unit']
} for d in documents])

print(df.head())
```

## Common Queries

### Filter by Test Type

```python
# Get all CoreMark results
coremark_results = [d for d in documents if d['test']['name'] == 'coremark']
print(f"Found {len(coremark_results)} CoreMark tests")
```

### Filter by OS Distribution and Version

```python
# Get RHEL 9.5 results
rhel95_results = [d for d in documents 
                  if d['system_under_test']['operating_system']['distribution'] == 'rhel'
                  and d['system_under_test']['operating_system']['version'] == '9.5']
print(f"Found {len(rhel95_results)} RHEL 9.5 tests")

# Get all Ubuntu results
ubuntu_results = [d for d in documents 
                  if d['system_under_test']['operating_system']['distribution'] == 'ubuntu']
print(f"Found {len(ubuntu_results)} Ubuntu tests")

# Get Amazon Linux 2023 results
al2023_results = [d for d in documents 
                  if d['system_under_test']['operating_system']['distribution'] == 'amazon'
                  and d['system_under_test']['operating_system']['version'] == '2023']
print(f"Found {len(al2023_results)} Amazon Linux 2023 tests")
```

### Get All Failures

```python
# Analyze failures
failures = [d for d in documents if d['results']['status'] == 'FAIL']

failure_types = {}
for doc in failures:
    reason = doc['results'].get('failure_reason', 'unknown')
    failure_types[reason] = failure_types.get(reason, 0) + 1

print("Failure breakdown:")
for reason, count in sorted(failure_types.items(), key=lambda x: x[1], reverse=True):
    print(f"  {reason}: {count}")
```

### Compare OS Distributions and Versions

```python
# Compare performance across OS distributions for same test and hardware
test_type = 'streams'
instance = 'm5.24xlarge'

results_by_os = {}
for doc in documents:
    if (doc['test']['name'] == test_type and 
        doc['metadata']['instance_type'] == instance and
        doc['results']['status'] == 'PASS'):
        
        os_dist = doc['system_under_test']['operating_system']['distribution']
        os_ver = doc['system_under_test']['operating_system']['version']
        os_key = f"{os_dist} {os_ver}"
        metric_value = doc['results']['primary_metric']['value']
        
        if os_key not in results_by_os:
            results_by_os[os_key] = []
        results_by_os[os_key].append(metric_value)

# Calculate averages
for os_key in sorted(results_by_os.keys()):
    values = results_by_os[os_key]
    avg = sum(values) / len(values)
    print(f"{os_key}: {avg:.2f} (n={len(values)})")
```

### Extract Time Series

```python
from datetime import datetime
import pandas as pd

# Get time series for a specific configuration
test_type = 'auto_hpl'
os_version = '9.5'

time_series = []
for doc in documents:
    if (doc['test']['name'] == test_type and
        doc['system_under_test']['operating_system']['version'] == os_version and
        doc['results']['status'] == 'PASS'):
        
        time_series.append({
            'timestamp': datetime.fromisoformat(doc['metadata']['test_timestamp'].replace('Z', '+00:00')),
            'value': doc['results']['primary_metric']['value'],
            'instance': doc['metadata']['instance_type']
        })

df_ts = pd.DataFrame(time_series).sort_values('timestamp')
print(df_ts.head())
```

## Data Structure Navigation

### Accessing Key Fields

```python
# Example document structure access
doc = documents[0]

# Test information
test_name = doc['test']['name']
test_version = doc['test']['version']

# System information
os_version = doc['system_under_test']['operating_system']['version']
cpu_cores = doc['system_under_test']['hardware']['cpu']['cores']
cpu_model = doc['system_under_test']['hardware']['cpu']['model']
memory_gb = doc['system_under_test']['hardware']['memory']['total_gb']

# Cloud/hardware info
cloud = doc['metadata']['cloud_provider']
instance = doc['metadata']['instance_type']
timestamp = doc['metadata']['test_timestamp']

# Results
status = doc['results']['status']
primary_metric = doc['results']['primary_metric']

# Detailed metrics (for PASS results)
if status == 'PASS' and 'run_0' in doc['results']['runs']:
    metrics = doc['results']['runs']['run_0']['metrics']
    # metrics is a dict with all test-specific measurements
```

### Handling Failures

```python
doc = next(d for d in documents if d['results']['status'] == 'FAIL')

# Failure information
failure_reason = doc['results'].get('failure_reason', 'N/A')
error_message = doc['results'].get('error_message', 'N/A')

print(f"Failure: {failure_reason}")
print(f"Error: {error_message}")
```

## Dashboard Integration

### Mode Switching Example

```python
import os
from opensearchpy import OpenSearch

def load_data(mode='synthetic'):
    """Load data from synthetic file or OpenSearch."""
    
    if mode == 'synthetic':
        with open('data/synthetic/benchmark_results.json', 'r') as f:
            return json.load(f)
    
    elif mode == 'opensearch':
        client = OpenSearch(
            hosts=[os.getenv('OPENSEARCH_HOST')],
            http_auth=(os.getenv('OPENSEARCH_USER'), os.getenv('OPENSEARCH_PASS')),
            use_ssl=True,
            verify_certs=True
        )
        
        # Query OpenSearch
        response = client.search(
            index='zathras-results',
            body={'query': {'match_all': {}}, 'size': 10000}
        )
        
        return [hit['_source'] for hit in response['hits']['hits']]
    
    else:
        raise ValueError(f"Unknown mode: {mode}")

# Use in dashboard
DATA_MODE = os.getenv('DATA_MODE', 'synthetic')  # 'synthetic' or 'opensearch'
documents = load_data(DATA_MODE)
```

## Analysis Examples

### Calculate Performance Regression

```python
def calculate_regression(baseline_docs, test_docs):
    """Compare two sets of documents for regression."""
    
    baseline_values = [d['results']['primary_metric']['value'] 
                       for d in baseline_docs if d['results']['status'] == 'PASS']
    test_values = [d['results']['primary_metric']['value']
                   for d in test_docs if d['results']['status'] == 'PASS']
    
    if not baseline_values or not test_values:
        return None
    
    baseline_avg = sum(baseline_values) / len(baseline_values)
    test_avg = sum(test_values) / len(test_values)
    
    change_pct = ((test_avg - baseline_avg) / baseline_avg) * 100
    
    return {
        'baseline_avg': baseline_avg,
        'test_avg': test_avg,
        'change_pct': change_pct,
        'regression': change_pct < -10  # >10% decrease
    }

# Example usage
baseline = [d for d in documents if 
            d['system_under_test']['operating_system']['version'] == '9.4' and
            d['test']['name'] == 'coremark']

test = [d for d in documents if
        d['system_under_test']['operating_system']['version'] == '9.5' and
        d['test']['name'] == 'coremark']

result = calculate_regression(baseline, test)
if result:
    print(f"Change: {result['change_pct']:.2f}%")
    print(f"Regression detected: {result['regression']}")
```

### Generate Summary Statistics

```python
import statistics

def summarize_test_type(documents, test_type):
    """Generate summary statistics for a test type."""
    
    test_docs = [d for d in documents if 
                 d['test']['name'] == test_type and 
                 d['results']['status'] == 'PASS']
    
    if not test_docs:
        return None
    
    values = [d['results']['primary_metric']['value'] for d in test_docs]
    
    return {
        'count': len(test_docs),
        'mean': statistics.mean(values),
        'median': statistics.median(values),
        'stdev': statistics.stdev(values) if len(values) > 1 else 0,
        'min': min(values),
        'max': max(values),
        'unit': test_docs[0]['results']['primary_metric']['unit']
    }

# Generate for all test types
test_types = set(d['test']['name'] for d in documents)

for test_type in sorted(test_types):
    stats = summarize_test_type(documents, test_type)
    if stats:
        print(f"\n{test_type}:")
        print(f"  Count: {stats['count']}")
        print(f"  Mean: {stats['mean']:.2f} {stats['unit']}")
        print(f"  Range: {stats['min']:.2f} - {stats['max']:.2f}")
        print(f"  StdDev: {stats['stdev']:.2f}")
```

## Visualization Examples

### Plot Time Series with Plotly

```python
import plotly.graph_objects as go
from datetime import datetime

# Extract time series data
test_type = 'streams'
instance_type = 'm5.24xlarge'

data = []
for doc in documents:
    if (doc['test']['name'] == test_type and
        doc['metadata']['instance_type'] == instance_type and
        doc['results']['status'] == 'PASS'):
        
        data.append({
            'timestamp': datetime.fromisoformat(doc['metadata']['test_timestamp'].replace('Z', '+00:00')),
            'value': doc['results']['primary_metric']['value'],
            'os_version': doc['system_under_test']['operating_system']['version']
        })

# Sort by timestamp
data.sort(key=lambda x: x['timestamp'])

# Group by OS version
os_versions = set(d['os_version'] for d in data)
fig = go.Figure()

for os_ver in sorted(os_versions):
    os_data = [d for d in data if d['os_version'] == os_ver]
    
    fig.add_trace(go.Scatter(
        x=[d['timestamp'] for d in os_data],
        y=[d['value'] for d in os_data],
        mode='lines+markers',
        name=f'RHEL {os_ver}'
    ))

fig.update_layout(
    title=f'{test_type} Performance Over Time ({instance_type})',
    xaxis_title='Date',
    yaxis_title='Performance',
    hovermode='x unified'
)

fig.show()
```

## Tips and Best Practices

1. **Always check status**: Filter out FAIL results when calculating performance metrics
2. **Account for hardware differences**: Normalize or group by instance type
3. **Handle missing fields**: Use `.get()` for optional fields
4. **Temporal analysis**: Sort by timestamp for time-series analysis
5. **Statistical significance**: Use multiple iterations for robust comparisons
6. **Unit awareness**: Check `primary_metric['unit']` for correct interpretation

## Troubleshooting

### Issue: Empty results when filtering

**Check**: Verify filter values match exactly (case-sensitive)

```python
# Get available values
os_versions = set(d['system_under_test']['operating_system']['version'] for d in documents)
print("Available OS versions:", os_versions)
```

### Issue: Mixed metric types

**Solution**: Different test types have different metrics. Filter by test type first.

```python
# Check what metrics are available for a test type
test_type = 'coremark'
sample = next(d for d in documents if d['test']['name'] == test_type)
if sample['results']['status'] == 'PASS':
    metrics = sample['results']['runs']['run_0']['metrics']
    print(f"Available metrics for {test_type}:", list(metrics.keys()))
```

### Issue: Timestamp parsing errors

**Solution**: Handle ISO 8601 format with timezone

```python
from datetime import datetime

timestamp_str = doc['metadata']['test_timestamp']
# Remove 'Z' and add timezone info
timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
```

## Need More Data?

To regenerate with different parameters:

```bash
python src/synthetic_data.py
```

Or see `README.md` for programmatic generation with custom parameters.

