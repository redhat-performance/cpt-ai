"""
Regression detection methodology - direction-aware geomean, per-benchmark
thresholds, and root-cause triage.

No I/O, no config dependencies. Pure math + domain knowledge.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, Optional


@dataclass
class ComparisonResult:
    """Result of a full comparison pipeline."""
    run1: dict
    run2: dict
    geomean: dict
    analysis: str
    detail_level: str


# ── Metric direction ────────────────────────────────────────────────
# Metrics where a LOWER value is better (latency, time, etc.)
# Everything else is assumed higher-is-better.
LOWER_IS_BETTER_METRICS = {
    # fio latency metrics
    'clat', 'lat', 'slat',
    # uperf latency
    'usec',
    # passmark latency
    'me_latency',
    # auto_hpl
    'time',
    # pyperf (average execution time)
    'avg',
    # speccpu
    'est__base_run_time', 'run_time', 'est_base_run_time',
}

# Patterns in metric names that indicate lower-is-better
LOWER_IS_BETTER_PATTERNS = [
    'latency', 'time', 'second', '_ms', '_us', '_ns',
    'clat', 'slat',
]


def is_lower_better(metric_name: str) -> bool:
    """Determine if a metric is lower-is-better based on name."""
    name_lower = metric_name.lower()
    if name_lower in LOWER_IS_BETTER_METRICS:
        return True
    return any(pat in name_lower for pat in LOWER_IS_BETTER_PATTERNS)


# ── Per-benchmark regression thresholds ─────────────────────────────
# Category -> (benchmarks, threshold_pct)
BENCHMARK_THRESHOLDS = {
    'cpu_compute': {
        'benchmarks': {
            'coremark', 'coremark_pro', 'coremark-pro',
            'passmark', 'speccpu', 'speccpu2017',
            'auto_hpl', 'phoronix',
        },
        'threshold': 3.0,
        'label': 'CPU compute (low noise)',
    },
    'memory_scheduler': {
        'benchmarks': {'streams', 'pig'},
        'threshold': 3.0,
        'label': 'Memory / scheduler',
    },
    'io': {
        'benchmarks': {'fio'},
        'threshold': 5.0,
        'label': 'I/O',
    },
    'network': {
        'benchmarks': {'uperf'},
        'threshold': 5.0,
        'label': 'Network',
    },
    'database': {
        'benchmarks': {
            'hammerdb', 'hammerdb_mariadb', 'hammerdb_postgres',
            'hammerdb_mssql',
        },
        'threshold': 5.0,
        'label': 'Database',
    },
    'python_runtime': {
        'benchmarks': {'pyperf'},
        'threshold': 3.0,
        'label': 'Python runtime',
    },
    'java_runtime': {
        'benchmarks': {'specjbb'},
        'threshold': 5.0,
        'label': 'Java runtime',
    },
}


def get_threshold(benchmark: str) -> float:
    """Get regression threshold for a benchmark. Default 5%."""
    bench_lower = benchmark.lower().replace('-', '_')
    for cat in BENCHMARK_THRESHOLDS.values():
        if bench_lower in cat['benchmarks']:
            return cat['threshold']
    return 5.0


def get_benchmark_category(benchmark: str) -> str:
    """Get the category label for a benchmark."""
    bench_lower = benchmark.lower().replace('-', '_')
    for cat in BENCHMARK_THRESHOLDS.values():
        if bench_lower in cat['benchmarks']:
            return cat['label']
    return 'Other'


# ── Root-cause triage patterns ──────────────────────────────────────
ROOT_CAUSE_PATTERNS = [
    {
        'pattern': 'CPU benchmarks down',
        'benchmarks': ['coremark', 'passmark', 'speccpu', 'auto_hpl', 'phoronix'],
        'metrics': ['cpu', 'integer', 'float', 'math', 'gflops'],
        'likely_causes': [
            'CPU frequency change or governor setting',
            'Microcode update',
            'Scheduler change in kernel',
            'CPU security mitigations (spectre/meltdown)',
        ],
    },
    {
        'pattern': 'Memory benchmarks down',
        'benchmarks': ['streams'],
        'metrics': ['copy', 'scale', 'add', 'triad', 'memory', 'me_'],
        'likely_causes': [
            'NUMA configuration change',
            'Memory frequency change',
            'Kernel memory subsystem change',
            'Huge pages configuration',
        ],
    },
    {
        'pattern': 'I/O benchmarks down',
        'benchmarks': ['fio'],
        'metrics': ['bw', 'iops'],
        'likely_causes': [
            'Storage driver change',
            'I/O scheduler change (mq-deadline, none, bfq)',
            'Block layer kernel changes',
            'Disk firmware or virtualization overhead',
        ],
    },
    {
        'pattern': 'Network benchmarks down',
        'benchmarks': ['uperf'],
        'metrics': ['gb_sec', 'trans_sec'],
        'likely_causes': [
            'Network driver update',
            'TCP stack or sysctl changes',
            'MTU or offloading settings',
            'Virtualization network overhead',
        ],
    },
    {
        'pattern': 'Database benchmarks down',
        'benchmarks': ['hammerdb'],
        'metrics': ['tpm'],
        'likely_causes': [
            'Combination of CPU + memory + I/O regressions',
            'Database engine version change',
            'Kernel scheduler impact on multi-threaded workload',
        ],
    },
    {
        'pattern': 'All benchmarks down',
        'benchmarks': [],  # empty = matches when all are regressed
        'metrics': [],
        'likely_causes': [
            'Kernel version change',
            'Tuned profile change',
            'Security mitigations enabled',
            'Hypervisor/instance generation change',
        ],
    },
]


# ── Geomean computation (direction-aware) ───────────────────────────
# Skip patterns for non-metric fields
_SKIP_PATTERNS = [
    'complete', 'status', 'count', 'error', 'fail', 'pass', 'skip',
    'total_subtests', 'total_configurations', 'total_processes',
    'num_samples', 'loops', 'description', 'benchmark_name',
    'process_grid', 'matrix_size', 'block_size',
]
_REDUNDANT_SUFFIXES = ('_max', '_min', '_stddev', '_stdev')


def compute_geomean_delta(run1_subtests, run2_subtests, benchmark=''):
    """Compute direction-aware geometric mean of ratios across matched metrics.

    For higher-is-better metrics: ratio = Run_B / Run_A  (>1 = improvement)
    For lower-is-better metrics:  ratio = Run_A / Run_B  (>1 = improvement)

    This normalizes all ratios so that:
      geomean > 1.0 → overall improvement
      geomean < 1.0 → overall regression
      geomean = 1.0 → no change

    Returns:
        (delta_pct, matched_count, total_run1, total_run2,
         lower_is_better_dominant, details, threshold)
    """
    ratios = []
    details = []
    threshold = get_threshold(benchmark)

    for name in sorted(run1_subtests):
        if name not in run2_subtests:
            continue

        m1 = run1_subtests[name]
        m2 = run2_subtests[name]

        has_mean_variants = any(k.endswith('_mean') for k in m1)

        for key in sorted(m1.keys()):
            if key not in m2:
                continue
            if not isinstance(m1[key], (int, float)) or not isinstance(m2[key], (int, float)):
                continue
            if m1[key] == 0 or not m1[key] or not m2[key]:
                continue
            if any(pat in key.lower() for pat in _SKIP_PATTERNS):
                continue
            if has_mean_variants and any(key.endswith(s) for s in _REDUNDANT_SUFFIXES):
                continue

            v1 = m1[key]
            v2 = m2[key]
            lower_better = is_lower_better(key)

            # Raw % change: ((Run_B - Run_A) / Run_A) * 100
            raw_pct = ((v2 - v1) / v1) * 100

            # Direction-normalized % change (negative = regression for all)
            if lower_better:
                normalized_pct = -raw_pct  # flip: increase in latency = regression
            else:
                normalized_pct = raw_pct   # decrease in throughput = regression

            # Direction-aware ratio for geomean
            if lower_better:
                ratio = v1 / v2  # <1 means v2 is worse (higher latency)
            else:
                ratio = v2 / v1  # <1 means v2 is worse (lower throughput)

            ratios.append(ratio)
            details.append({
                'subtest': name,
                'metric': key,
                'run1': v1,
                'run2': v2,
                'raw_pct': raw_pct,
                'normalized_pct': normalized_pct,
                'ratio': ratio,
                'lower_is_better': lower_better,
                'direction': 'lower-is-better' if lower_better else 'higher-is-better',
            })

    if not ratios:
        return 0.0, 0, len(run1_subtests), len(run2_subtests), False, [], threshold

    # Geometric mean of direction-normalized ratios
    geomean = math.exp(sum(math.log(abs(r)) for r in ratios) / len(ratios))
    delta_pct = (geomean - 1) * 100

    lower_count = sum(1 for d in details if d['lower_is_better'])
    lower_is_better_dominant = lower_count > len(details) / 2

    return (delta_pct, len(ratios), len(run1_subtests), len(run2_subtests),
            lower_is_better_dominant, details, threshold)


def determine_status(delta_pct, threshold=5.0, **_kwargs):
    """Determine regression status from direction-normalized geomean delta.

    Since ratios are direction-normalized:
      delta_pct > 0  → improvement (geomean > 1)
      delta_pct < 0  → regression  (geomean < 1)

    Args:
        delta_pct: geomean delta percentage (positive=better, negative=worse)
        threshold: regression threshold percentage (default 5%)

    Returns:
        One of: 'Regression', 'Improvement', 'No regression'
    """
    if delta_pct < -threshold:
        return "Regression"
    elif delta_pct > threshold:
        return "Improvement"
    else:
        return "No regression"


def classify_details(details, threshold=5.0):
    """Classify each metric detail as regression, improvement, or neutral.

    Returns (regressions, improvements, neutral) lists.
    """
    regressions = []
    improvements = []
    neutral = []

    for d in details:
        npct = d['normalized_pct']
        if npct < -threshold:
            regressions.append(d)
        elif npct > threshold:
            improvements.append(d)
        else:
            neutral.append(d)

    # Sort by severity (most regressed first)
    regressions.sort(key=lambda d: d['normalized_pct'])
    improvements.sort(key=lambda d: d['normalized_pct'], reverse=True)

    return regressions, improvements, neutral


def get_severity(delta_pct):
    """Get severity label from delta percentage.

    Uses absolute value since direction is already normalized.
    """
    abs_delta = abs(delta_pct)
    if abs_delta > 20:
        return "CRITICAL"
    elif abs_delta > 10:
        return "MAJOR"
    elif abs_delta > 5:
        return "MINOR"
    return "NONE"


def suggest_root_causes(benchmark, details):
    """Suggest root causes based on regression patterns.

    Returns list of likely cause strings.
    """
    regressions, _, _ = classify_details(details)
    if not regressions:
        return []

    regressed_metrics = {d['metric'].lower() for d in regressions}
    bench_lower = benchmark.lower()

    causes = []
    for pattern in ROOT_CAUSE_PATTERNS:
        # Check if benchmark matches this pattern
        if pattern['benchmarks']:
            bench_match = any(b in bench_lower for b in pattern['benchmarks'])
        else:
            # "All benchmarks down" pattern — only match if called explicitly
            continue

        metric_match = not pattern['metrics'] or any(
            any(m in metric for m in pattern['metrics'])
            for metric in regressed_metrics
        )

        if bench_match and metric_match:
            causes.extend(pattern['likely_causes'])

    return causes if causes else ROOT_CAUSE_PATTERNS[-1]['likely_causes']


def build_report_summary(benchmark, geomean_info, details):
    """Build a structured per-benchmark report summary.

    Returns a formatted string with geomean, regressions, improvements.
    """
    threshold = geomean_info.get('threshold', 5.0)
    regressions, improvements, neutral = classify_details(details, threshold)

    lines = []
    lines.append(f"Benchmark: {benchmark}")
    lines.append(f"Category: {get_benchmark_category(benchmark)}")
    lines.append(f"Regression Threshold: {threshold}%")
    lines.append(f"Overall Geomean: {geomean_info.get('geomean_value', 0):.6f} "
                 f"({geomean_info['delta_pct']:+.2f}%)")
    lines.append(f"Status: {geomean_info['status']}")

    if geomean_info['status'] == 'Regression':
        lines.append(f"Severity: {get_severity(geomean_info['delta_pct'])}")

    lines.append(f"\nMetrics: {len(details)} matched, "
                 f"{len(regressions)} regressed, "
                 f"{len(improvements)} improved, "
                 f"{len(neutral)} neutral")

    if regressions:
        lines.append(f"\nRegressions (> {threshold}% degradation):")
        for d in regressions[:15]:
            direction = d['direction']
            lines.append(
                f"  {d['metric']} @ {d['subtest']}")
            lines.append(
                f"    Run_A = {d['run1']:.6g}  Run_B = {d['run2']:.6g}")
            lines.append(
                f"    % change = {d['normalized_pct']:+.2f}% [{direction}]")

    if improvements:
        lines.append(f"\nImprovements (> {threshold}%):")
        for d in improvements[:10]:
            direction = d['direction']
            lines.append(
                f"  {d['metric']} @ {d['subtest']}")
            lines.append(
                f"    Run_A = {d['run1']:.6g}  Run_B = {d['run2']:.6g}")
            lines.append(
                f"    % change = {d['normalized_pct']:+.2f}% [{direction}]")

    return "\n".join(lines)


def build_geomean_info(run1_subtests, run2_subtests, benchmark=''):
    """Compute geomean and build the info dict used by AI and reporting.

    This is the shared computation used by both OpenSearch and CSV pipelines.
    Pure math — no I/O, no MCP, no file access.
    """
    delta_pct, matched, total_r1, total_r2, lower_is_better, details, threshold = \
        compute_geomean_delta(run1_subtests, run2_subtests, benchmark)

    status = determine_status(delta_pct, threshold)
    primary_metric = details[0]['metric'] if details else 'unknown'
    geomean_value = (delta_pct / 100) + 1

    regressions, improvements, neutral = classify_details(details, threshold)
    root_causes = suggest_root_causes(benchmark, details) if status == 'Regression' else []

    return {
        'delta_pct': delta_pct,
        'geomean_value': geomean_value,
        'status': status,
        'severity': get_severity(delta_pct) if status == 'Regression' else 'NONE',
        'matched': matched,
        'total_run1': total_r1,
        'total_run2': total_r2,
        'lower_is_better': lower_is_better,
        'primary_metric': primary_metric,
        'threshold': threshold,
        'benchmark': benchmark,
        'category': get_benchmark_category(benchmark),
        'details': details,
        'regressions_count': len(regressions),
        'improvements_count': len(improvements),
        'neutral_count': len(neutral),
        'root_causes': root_causes,
        'report_summary': build_report_summary(benchmark, {
            'delta_pct': delta_pct,
            'geomean_value': geomean_value,
            'status': status,
            'threshold': threshold,
        }, details),
    }
