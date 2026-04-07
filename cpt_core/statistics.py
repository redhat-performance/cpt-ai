"""
Multi-run statistical analysis for benchmark results.

Pure math functions: mean, median, standard deviation, coefficient of variation,
outlier detection, standard error of the mean, and Welch's t-test.

No I/O, no config dependencies.
"""

import math
from typing import List, Dict, Tuple, Optional


def mean(values: List[float]) -> float:
    """Arithmetic mean: sum(xi) / n"""
    if not values:
        return 0.0
    return sum(values) / len(values)


def median(values: List[float]) -> float:
    """Median: middle value (or average of two middle values) of sorted data."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2
    return s[mid]


def stddev(values: List[float], sample: bool = True) -> float:
    """Standard deviation.

    Formula: sigma = sqrt( sum((xi - mean)^2) / (n-1) )   [sample]
             sigma = sqrt( sum((xi - mean)^2) / n )        [population]

    Args:
        values: list of numeric values
        sample: if True, use n-1 (Bessel's correction); if False, use n
    """
    n = len(values)
    if n < 2:
        return 0.0
    m = mean(values)
    ss = sum((x - m) ** 2 for x in values)
    divisor = (n - 1) if sample else n
    return math.sqrt(ss / divisor)


def coefficient_of_variation(values: List[float]) -> float:
    """Coefficient of Variation: (stddev / mean) * 100%.

    Returns percentage. Typical ranges:
      < 2%   = low variance (stable)
      2-5%   = moderate variance (typical for cloud)
      > 5%   = high variance (noisy)
    """
    m = mean(values)
    if m == 0:
        return 0.0
    return (stddev(values) / m) * 100


def detect_outliers(values: List[float], sigma_threshold: float = 1.5
                    ) -> List[Dict]:
    """Detect outliers using sigma boundaries.

    Returns list of dicts with index, value, deviation, and severity:
      - 'mild' if between 1.5sigma and 2sigma
      - 'strong' if beyond 2sigma

    Args:
        values: list of numeric values
        sigma_threshold: sigma multiplier for mild outlier boundary (default 1.5)
    """
    if len(values) < 3:
        return []

    m = mean(values)
    s = stddev(values)
    if s == 0:
        return []

    outliers = []
    for i, v in enumerate(values):
        deviation = (v - m) / s
        abs_dev = abs(deviation)

        if abs_dev >= sigma_threshold:
            severity = 'strong' if abs_dev >= 2.0 else 'mild'
            outliers.append({
                'index': i,
                'value': v,
                'deviation_sigma': round(deviation, 2),
                'severity': severity,
                'direction': 'high' if v > m else 'low',
            })

    return outliers


def standard_error(values: List[float]) -> float:
    """Standard Error of the Mean: SEM = stddev / sqrt(n)

    Tells how precisely the sample mean estimates the true population mean.
    """
    n = len(values)
    if n < 2:
        return 0.0
    return stddev(values) / math.sqrt(n)


def welch_t_test(group1: List[float], group2: List[float]
                 ) -> Dict[str, float]:
    """Welch's t-test for unequal variances.

    Tests whether the means of two groups are statistically different.

    Returns dict with:
        t_statistic: the t value
        degrees_of_freedom: Welch-Satterthwaite df
        delta_means: group2_mean - group1_mean
        delta_pct: percentage difference relative to group1 mean
        se_diff: standard error of the difference
        significant_p05: True if |t| > critical value for p<0.05
    """
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return {
            't_statistic': 0.0,
            'degrees_of_freedom': 0,
            'delta_means': 0.0,
            'delta_pct': 0.0,
            'se_diff': 0.0,
            'significant_p05': False,
        }

    m1, m2 = mean(group1), mean(group2)
    s1, s2 = stddev(group1), stddev(group2)
    sem1 = s1 ** 2 / n1
    sem2 = s2 ** 2 / n2
    se_diff = math.sqrt(sem1 + sem2)

    if se_diff == 0:
        return {
            't_statistic': 0.0,
            'degrees_of_freedom': n1 + n2 - 2,
            'delta_means': m2 - m1,
            'delta_pct': 0.0,
            'se_diff': 0.0,
            'significant_p05': False,
        }

    t_stat = (m2 - m1) / se_diff

    # Welch-Satterthwaite degrees of freedom
    numerator = (sem1 + sem2) ** 2
    denominator = (sem1 ** 2 / (n1 - 1)) + (sem2 ** 2 / (n2 - 1))
    df = numerator / denominator if denominator > 0 else n1 + n2 - 2

    delta_pct = ((m2 - m1) / m1 * 100) if m1 != 0 else 0.0

    # Approximate critical t-values for two-tailed p<0.05
    # Using simplified lookup (exact values need scipy)
    t_crit = _t_critical_p05(df)
    significant = abs(t_stat) > t_crit

    return {
        't_statistic': round(t_stat, 4),
        'degrees_of_freedom': round(df, 1),
        'delta_means': round(m2 - m1, 2),
        'delta_pct': round(delta_pct, 4),
        'se_diff': round(se_diff, 2),
        'significant_p05': significant,
    }


def minimum_detectable_difference(cov_pct: float, n: int,
                                  confidence: float = 0.95) -> float:
    """Minimum detectable difference given CoV and sample size.

    Formula: delta_min = t_crit * sqrt(2) * CoV / sqrt(n)

    Returns percentage.
    """
    if n < 2 or cov_pct == 0:
        return 0.0
    df = 2 * (n - 1)
    t_crit = _t_critical_p05(df)
    return t_crit * math.sqrt(2) * cov_pct / math.sqrt(n)


def required_sample_size(cov_pct: float, target_delta_pct: float,
                         confidence: float = 0.95) -> int:
    """Required sample size per group to detect a given delta.

    Formula: n = (2 * z * CoV / delta)^2
    Uses z=1.96 for 95% confidence.
    """
    if target_delta_pct == 0 or cov_pct == 0:
        return 0
    z = 1.96  # 95% confidence
    n = (2 * z * cov_pct / target_delta_pct) ** 2
    return math.ceil(n)


def compute_group_stats(values: List[float]) -> Dict:
    """Compute all descriptive statistics for a group of values.

    Returns dict with mean, median, stddev, cov, sem, n, min, max, outliers.
    """
    if not values:
        return {
            'n': 0, 'mean': 0, 'median': 0, 'stddev': 0,
            'cov': 0, 'sem': 0, 'min': 0, 'max': 0, 'outliers': [],
        }

    return {
        'n': len(values),
        'mean': round(mean(values), 2),
        'median': round(median(values), 2),
        'stddev': round(stddev(values), 2),
        'cov': round(coefficient_of_variation(values), 2),
        'sem': round(standard_error(values), 2),
        'min': min(values),
        'max': max(values),
        'outliers': detect_outliers(values),
    }


def _t_critical_p05(df: float) -> float:
    """Approximate two-tailed t critical value for p < 0.05.

    Uses linear interpolation between known values.
    For large df, approaches 1.96 (z-value).
    """
    # Table of (df, t_crit) for two-tailed p=0.05
    table = [
        (1, 12.706), (2, 4.303), (3, 3.182), (4, 2.776), (5, 2.571),
        (6, 2.447), (7, 2.365), (8, 2.306), (9, 2.262), (10, 2.228),
        (12, 2.179), (14, 2.145), (16, 2.120), (18, 2.101), (20, 2.086),
        (25, 2.060), (28, 2.048), (30, 2.042), (40, 2.021), (50, 2.009),
        (60, 2.000), (80, 1.990), (100, 1.984), (200, 1.972),
    ]

    if df >= 200:
        return 1.96
    if df <= 1:
        return 12.706

    # Find bracketing entries and interpolate
    for i in range(len(table) - 1):
        if table[i][0] <= df <= table[i + 1][0]:
            df1, t1 = table[i]
            df2, t2 = table[i + 1]
            frac = (df - df1) / (df2 - df1)
            return t1 + frac * (t2 - t1)

    return 1.96
