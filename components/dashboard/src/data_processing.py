"""
Data processing and transformation logic for benchmark results.

Handles conversion of raw OpenSearch/synthetic data into formats
suitable for visualization and analysis.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BenchmarkDataProcessor:
    """Process and transform benchmark results for visualization."""
    
    # Benchmark categorization for grouping
    BENCHMARK_GROUPS = {
        'Networking': ['uperf'],
        'Storage/IO': ['fio'],
        'HPC/Compute': ['streams', 'specjbb', 'auto_hpl'],
        'System': ['sysbench', 'coremark_pro', 'pig', 'coremark', 'phoronix', 'passmark']
    }
    
    def __init__(self):
        """Initialize the data processor."""
        pass
    
    def get_benchmark_category(self, test_name: str) -> str:
        """
        Get the category for a benchmark test.
        
        Args:
            test_name: Name of the test
            
        Returns:
            Category name or 'Other'
        """
        if not test_name:
            return 'Other'
        
        test_lower = test_name.lower()
        for category, tests in self.BENCHMARK_GROUPS.items():
            if any(test.lower() in test_lower or test_lower in test.lower() for test in tests):
                return category
        return 'Other'
    
    def add_benchmark_categories(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add benchmark category column to DataFrame.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with 'benchmark_category' column added
        """
        df_copy = df.copy()
        df_copy['benchmark_category'] = df_copy['test_name'].apply(self.get_benchmark_category)
        return df_copy
    
    def documents_to_dataframe(self, documents: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert list of document dictionaries to a pandas DataFrame.
        
        Args:
            documents: List of benchmark result documents
            
        Returns:
            DataFrame with flattened and processed fields
        """
        if not documents:
            return pd.DataFrame()
        
        records = []
        for doc in documents:
            try:
                record = self._extract_record(doc)
                records.append(record)
            except Exception as e:
                logger.warning(f"Failed to process document: {e}")
                continue
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp
        if 'timestamp' in df.columns:
            df = df.sort_values('timestamp')
        
        logger.info(f"Processed {len(df)} documents into DataFrame")
        return df
    
    def _extract_record(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract a flat record from a nested document.
        
        Args:
            doc: Benchmark result document
            
        Returns:
            Flattened dictionary of key fields
        """
        metadata = doc.get('metadata', {})
        test = doc.get('test', {})
        system = doc.get('system_under_test', {})
        os_info = system.get('operating_system', {})
        hardware = system.get('hardware', {})
        cpu = hardware.get('cpu', {})
        results = doc.get('results', {})
        primary_metric = results.get('primary_metric', {})
        
        # Extract run metrics if available
        runs = results.get('runs', {})
        run_0_metrics = {}
        if runs:
            first_run_key = list(runs.keys())[0]
            run_0_metrics = runs[first_run_key].get('metrics', {})
        
        record = {
            # Identifiers
            'document_id': metadata.get('document_id'),
            'test_name': test.get('name'),
            'test_version': test.get('version'),
            
            # Temporal
            'timestamp': metadata.get('test_timestamp'),
            
            # System Configuration
            'os_vendor': metadata.get('os_vendor'),
            'os_distribution': os_info.get('distribution'),
            'os_version': os_info.get('version'),
            'kernel_version': os_info.get('kernel_version'),
            
            # Hardware
            'cloud_provider': metadata.get('cloud_provider'),
            'instance_type': metadata.get('instance_type'),
            'cpu_model': cpu.get('model'),
            'cpu_cores': cpu.get('cores'),
            'cpu_architecture': cpu.get('architecture'),
            'memory_gb': hardware.get('memory', {}).get('total_gb'),
            
            # Test Configuration
            'scenario_name': metadata.get('scenario_name'),
            'iteration': metadata.get('iteration'),
            
            # Results
            'status': results.get('status'),
            'primary_metric_name': primary_metric.get('name'),
            'primary_metric_value': primary_metric.get('value'),
            'primary_metric_unit': primary_metric.get('unit'),
        }
        
        # Add additional metrics from run_0 (flatten key ones)
        # Only add if they don't conflict with existing keys
        for key, value in run_0_metrics.items():
            if key not in record and isinstance(value, (int, float)):
                record[f'metric_{key}'] = value
        
        return record
    
    def filter_data(
        self,
        df: pd.DataFrame,
        os_versions: Optional[List[str]] = None,
        instance_types: Optional[List[str]] = None,
        test_names: Optional[List[str]] = None,
        cloud_providers: Optional[List[str]] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        status_filter: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Filter DataFrame based on multiple criteria.
        
        Args:
            df: Input DataFrame
            os_versions: List of OS versions to include
            instance_types: List of instance types to include
            test_names: List of test names to include
            cloud_providers: List of cloud providers to include
            date_range: Tuple of (start_date, end_date)
            status_filter: List of status values to include
            
        Returns:
            Filtered DataFrame
        """
        filtered = df.copy()
        
        if os_versions:
            filtered = filtered[filtered['os_version'].isin(os_versions)]
        
        if instance_types:
            filtered = filtered[filtered['instance_type'].isin(instance_types)]
        
        if test_names:
            filtered = filtered[filtered['test_name'].isin(test_names)]
        
        if cloud_providers:
            filtered = filtered[filtered['cloud_provider'].isin(cloud_providers)]
        
        if status_filter:
            filtered = filtered[filtered['status'].isin(status_filter)]
        
        if date_range and 'timestamp' in filtered.columns:
            start_date, end_date = date_range
            filtered = filtered[
                (filtered['timestamp'] >= start_date) &
                (filtered['timestamp'] <= end_date)
            ]
        
        logger.info(f"Filtered from {len(df)} to {len(filtered)} records")
        return filtered
    
    def calculate_comparison(
        self,
        df: pd.DataFrame,
        baseline_filters: Dict[str, Any],
        comparison_filters: Dict[str, Any],
        group_by: str = 'test_name'
    ) -> pd.DataFrame:
        """
        Calculate performance comparison between two configurations.
        
        Args:
            df: Input DataFrame
            baseline_filters: Filters to select baseline data
            comparison_filters: Filters to select comparison data
            group_by: Field to group results by
            
        Returns:
            DataFrame with comparison statistics
        """
        # Filter baseline and comparison data
        baseline_df = self.filter_data(df, **baseline_filters)
        comparison_df = self.filter_data(df, **comparison_filters)
        
        # Group and aggregate
        baseline_agg = baseline_df.groupby(group_by).agg({
            'primary_metric_value': ['mean', 'std', 'count']
        }).reset_index()
        baseline_agg.columns = [group_by, 'baseline_mean', 'baseline_std', 'baseline_count']
        
        comparison_agg = comparison_df.groupby(group_by).agg({
            'primary_metric_value': ['mean', 'std', 'count']
        }).reset_index()
        comparison_agg.columns = [group_by, 'comparison_mean', 'comparison_std', 'comparison_count']
        
        # Merge and calculate differences
        result = baseline_agg.merge(comparison_agg, on=group_by, how='outer')
        
        result['delta'] = result['comparison_mean'] - result['baseline_mean']
        result['percent_change'] = (
            (result['comparison_mean'] - result['baseline_mean']) / 
            result['baseline_mean'] * 100
        )
        
        # Classify change magnitude
        result['change_category'] = result['percent_change'].apply(
            lambda x: 'Regression' if x < -10 else (
                'Improvement' if x > 10 else 'Stable'
            )
        )
        
        return result
    
    def aggregate_by_time(
        self,
        df: pd.DataFrame,
        time_freq: str = 'D',
        agg_func: str = 'mean'
    ) -> pd.DataFrame:
        """
        Aggregate metrics by time period.
        
        Args:
            df: Input DataFrame
            time_freq: Pandas time frequency ('D'=day, 'W'=week, 'M'=month)
            agg_func: Aggregation function ('mean', 'median', 'max', 'min')
            
        Returns:
            Time-aggregated DataFrame
        """
        if 'timestamp' not in df.columns:
            logger.warning("No timestamp column found")
            return df
        
        df_copy = df.copy()
        df_copy.set_index('timestamp', inplace=True)
        
        numeric_cols = df_copy.select_dtypes(include=['float64', 'int64']).columns
        
        aggregated = df_copy[numeric_cols].resample(time_freq).agg(agg_func)
        aggregated.reset_index(inplace=True)
        
        return aggregated
    
    def get_unique_values(self, df: pd.DataFrame, column: str) -> List[Any]:
        """
        Get sorted list of unique values in a column.
        
        Args:
            df: Input DataFrame
            column: Column name
            
        Returns:
            Sorted list of unique values
        """
        if column not in df.columns:
            return []
        
        unique_vals = df[column].dropna().unique().tolist()
        try:
            return sorted(unique_vals)
        except TypeError:
            return unique_vals
    
    def create_regression_matrix(
        self,
        df: pd.DataFrame,
        row_dimension: str = 'os_version',
        col_dimension: str = 'instance_type',
        metric: str = 'primary_metric_value'
    ) -> pd.DataFrame:
        """
        Create a heatmap matrix for regression analysis.
        
        Args:
            df: Input DataFrame
            row_dimension: Field to use for rows
            col_dimension: Field to use for columns
            metric: Metric to aggregate
            
        Returns:
            Pivot table suitable for heatmap visualization
        """
        pivot = df.pivot_table(
            values=metric,
            index=row_dimension,
            columns=col_dimension,
            aggfunc='mean'
        )
        
        return pivot
    
    def calculate_statistics(
        self,
        df: pd.DataFrame,
        group_by: List[str],
        metric: str = 'primary_metric_value'
    ) -> pd.DataFrame:
        """
        Calculate detailed statistics for groups.
        
        Args:
            df: Input DataFrame
            group_by: List of columns to group by
            metric: Metric column to analyze
            
        Returns:
            DataFrame with statistics
        """
        if metric not in df.columns:
            logger.warning(f"Metric '{metric}' not found in DataFrame")
            return pd.DataFrame()
        
        stats = df.groupby(group_by)[metric].agg([
            ('count', 'count'),
            ('mean', 'mean'),
            ('median', 'median'),
            ('std', 'std'),
            ('min', 'min'),
            ('max', 'max'),
            ('q25', lambda x: x.quantile(0.25)),
            ('q75', lambda x: x.quantile(0.75))
        ]).reset_index()
        
        # Calculate coefficient of variation
        stats['cv'] = (stats['std'] / stats['mean'] * 100).round(2)
        
        return stats
    
    def detect_outliers(
        self,
        df: pd.DataFrame,
        metric: str = 'primary_metric_value',
        method: str = 'iqr',
        threshold: float = 1.5
    ) -> pd.DataFrame:
        """
        Detect outliers in the data.
        
        Args:
            df: Input DataFrame
            metric: Metric column to check
            method: Detection method ('iqr' or 'zscore')
            threshold: Threshold for outlier detection
            
        Returns:
            DataFrame with outlier flag added
        """
        if metric not in df.columns:
            return df
        
        df_copy = df.copy()
        
        if method == 'iqr':
            Q1 = df_copy[metric].quantile(0.25)
            Q3 = df_copy[metric].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            df_copy['is_outlier'] = (
                (df_copy[metric] < lower_bound) | 
                (df_copy[metric] > upper_bound)
            )
        elif method == 'zscore':
            mean = df_copy[metric].mean()
            std = df_copy[metric].std()
            df_copy['is_outlier'] = (
                abs((df_copy[metric] - mean) / std) > threshold
            )
        
        outlier_count = df_copy['is_outlier'].sum()
        logger.info(f"Detected {outlier_count} outliers using {method} method")
        
        return df_copy
    
    def _sort_versions(self, versions: List[str]) -> List[str]:
        """
        Sort OS versions in natural order (e.g., 9.2, 9.3, ..., 9.6, 10.0, 10.1).
        
        Args:
            versions: List of version strings (or numeric values that will be converted)
            
        Returns:
            Sorted list of version strings
        """
        def version_key(version):
            """Convert version string to tuple for natural sorting."""
            try:
                # Convert to string first (in case it's a number)
                version_str = str(version)
                # Split on '.' and convert each part to int
                parts = version_str.split('.')
                return tuple(int(part) for part in parts)
            except (ValueError, AttributeError):
                # If conversion fails, return a tuple that sorts last
                return (999, 999, str(version))
        
        # Convert all versions to strings for consistent output
        return sorted([str(v) for v in versions], key=version_key)
    
    def analyze_rhel_simplified_regressions(
        self,
        df: pd.DataFrame,
        regression_threshold: float = -5.0
    ) -> Dict[str, Any]:
        """
        Simplified RHEL regression analysis with three specific comparisons:
        1. Latest 9.X vs Latest 10.X (major release comparison)
        2. Latest 9.X vs Previous 9.X (9.X sequential)
        3. Latest 10.X vs Previous 10.X (10.X sequential)
        
        Args:
            df: Input DataFrame
            regression_threshold: Percentage threshold for regression detection (negative)
            
        Returns:
            Dictionary with three comparison groups
        """
        df_with_cats = self.add_benchmark_categories(df)
        
        # Filter to only RHEL
        df_rhel = df_with_cats[df_with_cats['os_distribution'].str.lower() == 'rhel'].copy()
        
        if df_rhel.empty:
            return {
                'major_release_comparison': None,
                'rhel9_sequential': None,
                'rhel10_sequential': None,
                'summary': 'No RHEL data available',
                'total_regressions': 0
            }
        
        # Ensure os_version is string type (may be float after JSON deserialization)
        df_rhel['os_version'] = df_rhel['os_version'].astype(str)
        
        # Get sorted versions
        all_versions = self._sort_versions(df_rhel['os_version'].dropna().unique())
        
        # Separate into 9.X and 10.X versions
        rhel9_versions = [v for v in all_versions if v.startswith('9.')]
        rhel10_versions = [v for v in all_versions if v.startswith('10.')]
        
        result = {
            'major_release_comparison': None,
            'rhel9_sequential': None,
            'rhel10_sequential': None,
            'summary': ''
        }
        
        # Comparison 1: Latest 9.X vs Latest 10.X
        if rhel9_versions and rhel10_versions:
            latest_9 = rhel9_versions[-1]
            latest_10 = rhel10_versions[-1]
            result['major_release_comparison'] = self._compare_two_versions(
                df_rhel, latest_9, latest_10, regression_threshold,
                label=f"RHEL {latest_9} vs {latest_10} (Major Release)"
            )
        
        # Comparison 2: Latest 9.X vs Previous 9.X
        if len(rhel9_versions) >= 2:
            prev_9 = rhel9_versions[-2]
            latest_9 = rhel9_versions[-1]
            result['rhel9_sequential'] = self._compare_two_versions(
                df_rhel, prev_9, latest_9, regression_threshold,
                label=f"RHEL {prev_9} vs {latest_9}"
            )
        
        # Comparison 3: Latest 10.X vs Previous 10.X
        if len(rhel10_versions) >= 2:
            prev_10 = rhel10_versions[-2]
            latest_10 = rhel10_versions[-1]
            result['rhel10_sequential'] = self._compare_two_versions(
                df_rhel, prev_10, latest_10, regression_threshold,
                label=f"RHEL {prev_10} vs {latest_10}"
            )
        
        # Generate overall summary
        total_regressions = 0
        summaries = []
        
        for key in ['major_release_comparison', 'rhel9_sequential', 'rhel10_sequential']:
            comp = result[key]
            if comp and comp['num_regressions'] > 0:
                total_regressions += comp['num_regressions']
                summaries.append(f"{comp['label']}: {comp['num_regressions']} regression(s)")
        
        if total_regressions > 0:
            result['summary'] = f"Total: {total_regressions} regression(s) detected\n" + "\n".join(summaries)
        else:
            result['summary'] = "No significant regressions detected"
        
        result['total_regressions'] = total_regressions
        
        return result
    
    def _compare_two_versions(
        self,
        df: pd.DataFrame,
        baseline_version: str,
        comparison_version: str,
        regression_threshold: float,
        label: str = ""
    ) -> Dict[str, Any]:
        """
        Compare performance between two specific OS versions.
        
        IMPORTANT: Only compares tests that ran on the same hardware configuration
        (same cloud_provider + instance_type combination).
        
        Args:
            df: Input DataFrame (already filtered to OS distribution)
            baseline_version: Baseline version
            comparison_version: Version to compare against baseline
            regression_threshold: Percentage threshold for regression
            label: Human-readable label for this comparison
            
        Returns:
            Dictionary with comparison results including hardware configurations used
        """
        test_names = sorted(df['test_name'].dropna().unique())
        comparison_results = []
        hardware_configs = set()
        
        for test in test_names:
            # Get baseline data for this test
            baseline_test_df = df[
                (df['os_version'] == baseline_version) & 
                (df['test_name'] == test)
            ]
            
            # Get comparison data for this test
            comparison_test_df = df[
                (df['os_version'] == comparison_version) & 
                (df['test_name'] == test)
            ]
            
            if baseline_test_df.empty or comparison_test_df.empty:
                continue
            
            # Find hardware configurations that exist in BOTH versions
            baseline_hw_configs = set(
                zip(baseline_test_df['cloud_provider'], baseline_test_df['instance_type'])
            )
            comparison_hw_configs = set(
                zip(comparison_test_df['cloud_provider'], comparison_test_df['instance_type'])
            )
            
            # Only use hardware configs that exist in both datasets
            common_hw_configs = baseline_hw_configs & comparison_hw_configs
            
            if not common_hw_configs:
                # No matching hardware configurations for this test
                continue
            
            # For each matching hardware config, compute comparison
            for cloud_provider, instance_type in common_hw_configs:
                hardware_configs.add((cloud_provider, instance_type))
                
                baseline_hw_data = baseline_test_df[
                    (baseline_test_df['cloud_provider'] == cloud_provider) &
                    (baseline_test_df['instance_type'] == instance_type)
                ]['primary_metric_value']
                
                comparison_hw_data = comparison_test_df[
                    (comparison_test_df['cloud_provider'] == cloud_provider) &
                    (comparison_test_df['instance_type'] == instance_type)
                ]['primary_metric_value']
                
                if len(baseline_hw_data) > 0 and len(comparison_hw_data) > 0:
                    baseline_mean = baseline_hw_data.mean()
                    comparison_mean = comparison_hw_data.mean()
                    pct_change = ((comparison_mean - baseline_mean) / baseline_mean) * 100
                    
                    comparison_results.append({
                        'test_name': test,
                        'cloud_provider': cloud_provider,
                        'instance_type': instance_type,
                        'hardware_config': f"{cloud_provider}/{instance_type}",
                        'benchmark_category': df[df['test_name'] == test]['benchmark_category'].iloc[0] if 'benchmark_category' in df.columns else 'Unknown',
                        'baseline_version': baseline_version,
                        'comparison_version': comparison_version,
                        'baseline_mean': baseline_mean,
                        'baseline_count': len(baseline_hw_data),
                        'comparison_mean': comparison_mean,
                        'comparison_count': len(comparison_hw_data),
                        'percent_change': pct_change,
                        'is_regression': pct_change < regression_threshold
                    })
        
        comparison_df = pd.DataFrame(comparison_results)
        
        # Identify regressions
        regressions = comparison_df[comparison_df['is_regression']].sort_values('percent_change') if not comparison_df.empty else pd.DataFrame()
        
        # Generate summary for this comparison
        num_regressions = len(regressions)
        num_hardware_configs = len(hardware_configs)
        
        if num_regressions > 0:
            top_regressions = regressions.head(3)
            summary_lines = []
            for _, row in top_regressions.iterrows():
                summary_lines.append(
                    f"• {row['test_name']} on {row['hardware_config']}: {row['percent_change']:.1f}%"
                )
            summary = '\n'.join(summary_lines)
        else:
            summary = "No significant regressions detected"
        
        # Create hardware config summary
        hw_config_list = sorted([f"{cloud}/{inst}" for cloud, inst in hardware_configs])
        hw_summary = f"Compared on {num_hardware_configs} hardware configuration(s): " + ", ".join(hw_config_list[:3])
        if num_hardware_configs > 3:
            hw_summary += f" and {num_hardware_configs - 3} more"
        
        return {
            'label': label,
            'baseline_version': baseline_version,
            'comparison_version': comparison_version,
            'comparison_data': comparison_df,
            'regressions': regressions.to_dict('records') if not regressions.empty else [],
            'num_regressions': num_regressions,
            'num_comparisons': len(comparison_results),
            'num_hardware_configs': num_hardware_configs,
            'hardware_configs': hw_config_list,
            'hardware_summary': hw_summary,
            'summary': summary
        }
    
    def analyze_os_version_regressions(
        self,
        df: pd.DataFrame,
        os_distribution: str = 'rhel',
        os_versions: Optional[List[str]] = None,
        regression_threshold: float = -5.0
    ) -> Dict[str, Any]:
        """
        Analyze performance regressions across OS versions within a single OS distribution.
        
        Args:
            df: Input DataFrame
            os_distribution: OS distribution to analyze (e.g., 'rhel', 'ubuntu', 'sles')
            os_versions: List of OS versions to analyze (in order), or None for auto-detect
            regression_threshold: Percentage threshold for regression detection (negative)
            
        Returns:
            Dictionary with regression analysis results
        """
        df_with_cats = self.add_benchmark_categories(df)
        
        # Filter to only the specified OS distribution
        df_os = df_with_cats[df_with_cats['os_distribution'].str.lower() == os_distribution.lower()].copy()
        
        if df_os.empty:
            return {
                'regressions': [],
                'summary': f'No data available for {os_distribution.upper()}',
                'heatmap_data': pd.DataFrame(),
                'num_regressions': 0,
                'comparison_data': pd.DataFrame()
            }
        
        # Auto-detect OS versions if not provided
        if not os_versions:
            os_versions = self._sort_versions(df_os['os_version'].dropna().unique())
        
        if len(os_versions) < 2:
            return {
                'regressions': [],
                'summary': f'Insufficient {os_distribution.upper()} versions for comparison (found {len(os_versions)})',
                'heatmap_data': pd.DataFrame(),
                'num_regressions': 0,
                'comparison_data': pd.DataFrame()
            }
        
        # Create comparison matrix: benchmark × OS version (within the same distribution)
        comparison_results = []
        test_names = sorted(df_os['test_name'].dropna().unique())
        
        for i in range(1, len(os_versions)):
            baseline_ver = os_versions[i-1]
            current_ver = os_versions[i]
            
            for test in test_names:
                baseline_data = df_os[
                    (df_os['os_version'] == baseline_ver) & 
                    (df_os['test_name'] == test)
                ]['primary_metric_value']
                
                current_data = df_os[
                    (df_os['os_version'] == current_ver) & 
                    (df_os['test_name'] == test)
                ]['primary_metric_value']
                
                if len(baseline_data) > 0 and len(current_data) > 0:
                    baseline_mean = baseline_data.mean()
                    current_mean = current_data.mean()
                    pct_change = ((current_mean - baseline_mean) / baseline_mean) * 100
                    
                    comparison_results.append({
                        'test_name': test,
                        'benchmark_category': df_os[df_os['test_name'] == test]['benchmark_category'].iloc[0],
                        'baseline_version': baseline_ver,
                        'current_version': current_ver,
                        'baseline_mean': baseline_mean,
                        'current_mean': current_mean,
                        'percent_change': pct_change,
                        'is_regression': pct_change < regression_threshold
                    })
        
        comparison_df = pd.DataFrame(comparison_results)
        
        # Identify regressions
        regressions = comparison_df[comparison_df['is_regression']].sort_values('percent_change')
        
        # Create heatmap data (pivot table) - only for the specified OS distribution
        heatmap_data = df_os.pivot_table(
            values='primary_metric_value',
            index='test_name',
            columns='os_version',
            aggfunc='mean'
        )
        
        # Calculate percent change for heatmap
        pct_change_data = pd.DataFrame(index=heatmap_data.index)
        for i in range(1, len(os_versions)):
            if os_versions[i-1] in heatmap_data.columns and os_versions[i] in heatmap_data.columns:
                col_name = f"{os_versions[i-1]}→{os_versions[i]}"
                pct_change_data[col_name] = (
                    (heatmap_data[os_versions[i]] - heatmap_data[os_versions[i-1]]) / 
                    heatmap_data[os_versions[i-1]] * 100
                )
        
        # Generate summary
        num_regressions = len(regressions)
        if num_regressions > 0:
            top_regressions = regressions.head(3)
            summary_lines = [f"{num_regressions} regression(s) detected"]
            for _, row in top_regressions.iterrows():
                summary_lines.append(
                    f"• {row['test_name']}: {row['percent_change']:.1f}% in {row['current_version']} vs {row['baseline_version']}"
                )
            summary = '\n'.join(summary_lines)
        else:
            summary = "No significant regressions detected"
        
        return {
            'regressions': regressions.to_dict('records') if not regressions.empty else [],
            'summary': summary,
            'heatmap_data': pct_change_data,
            'comparison_data': comparison_df,
            'num_regressions': num_regressions
        }
    
    def analyze_peer_os_comparison(
        self,
        df: pd.DataFrame,
        baseline_os: str = 'RHEL',
        peer_os_list: Optional[List[str]] = None,
        baseline_version: Optional[str] = None,
        peer_version: Optional[str] = None,
        cloud_provider: Optional[str] = None,
        instance_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare RHEL performance against peer operating systems.
        
        Args:
            df: Input DataFrame
            baseline_os: OS to use as baseline (default: RHEL)
            peer_os_list: List of peer OS vendors to compare, or None for auto-detect
            baseline_version: Specific baseline OS version (e.g., "10.1")
            peer_version: Specific peer OS version (e.g., "24.04")
            cloud_provider: Specific cloud provider to filter by
            instance_type: Specific instance type for hardware-specific comparison
            
        Returns:
            Dictionary with peer comparison results including hardware-aware comparisons
        """
        df_with_cats = self.add_benchmark_categories(df)
        
        # Apply version filters if specified
        if baseline_version:
            df_with_cats = df_with_cats[
                (df_with_cats['os_vendor'] != baseline_os) | 
                (df_with_cats['os_version'] == baseline_version)
            ]
        
        if peer_version and peer_os_list and len(peer_os_list) == 1:
            # Filter peer OS to specific version
            df_with_cats = df_with_cats[
                (df_with_cats['os_vendor'] != peer_os_list[0]) | 
                (df_with_cats['os_version'] == peer_version)
            ]
        
        # Apply cloud provider filter if specified
        if cloud_provider:
            df_with_cats = df_with_cats[df_with_cats['cloud_provider'] == cloud_provider]
        
        # Apply instance type filter if specified
        if instance_type:
            df_with_cats = df_with_cats[df_with_cats['instance_type'] == instance_type]
        
        # Auto-detect OS vendors if not provided
        if not peer_os_list:
            all_os = df_with_cats['os_vendor'].dropna().unique()
            peer_os_list = [os for os in all_os if os != baseline_os]
        
        if len(peer_os_list) == 0:
            return {
                'comparison_data': pd.DataFrame(),
                'summary': 'No peer operating systems found for comparison',
                'competitive_count': 0,
                'total_benchmarks': 0,
                'available_comparisons': []
            }
        
        # Group by benchmark category, hardware, and compare
        comparison_results = []
        
        for category in df_with_cats['benchmark_category'].unique():
            category_df = df_with_cats[df_with_cats['benchmark_category'] == category]
            
            for test in category_df['test_name'].unique():
                test_df = category_df[category_df['test_name'] == test]
                
                # Group by hardware to ensure apples-to-apples comparison
                for hw in test_df['instance_type'].dropna().unique():
                    hw_test_df = test_df[test_df['instance_type'] == hw]
                    
                    baseline_data = hw_test_df[hw_test_df['os_vendor'] == baseline_os]['primary_metric_value']
                    
                    if len(baseline_data) > 0:
                        baseline_mean = baseline_data.mean()
                        baseline_std = baseline_data.std()
                        baseline_count = len(baseline_data)
                        
                        for peer_os in peer_os_list:
                            peer_data = hw_test_df[hw_test_df['os_vendor'] == peer_os]['primary_metric_value']
                            
                            if len(peer_data) > 0:
                                peer_mean = peer_data.mean()
                                peer_std = peer_data.std()
                                peer_count = len(peer_data)
                                relative_perf = (peer_mean / baseline_mean) * 100 if baseline_mean > 0 else 100
                                
                                # Get actual versions used in comparison (convert to strings)
                                baseline_versions = [str(v) for v in hw_test_df[hw_test_df['os_vendor'] == baseline_os]['os_version'].unique()]
                                peer_versions = [str(v) for v in hw_test_df[hw_test_df['os_vendor'] == peer_os]['os_version'].unique()]
                                
                                comparison_results.append({
                                    'benchmark_category': category,
                                    'test_name': test,
                                    'baseline_os': baseline_os,
                                    'peer_os': peer_os,
                                    'baseline_version': ', '.join(sorted(baseline_versions)),
                                    'peer_version': ', '.join(sorted(peer_versions)),
                                    'instance_type': hw,
                                    'cloud_provider': hw_test_df['cloud_provider'].iloc[0],
                                    'baseline_value': baseline_mean,
                                    'baseline_std': baseline_std,
                                    'baseline_count': baseline_count,
                                    'peer_value': peer_mean,
                                    'peer_std': peer_std,
                                    'peer_count': peer_count,
                                    'relative_performance': relative_perf,
                                    'is_competitive': relative_perf >= 90  # Within 10%
                                })
        
        comparison_df = pd.DataFrame(comparison_results)
        
        # Get available comparison combinations
        available_comparisons = self._get_available_comparisons(df_with_cats, baseline_os)
        
        # Generate summary
        if not comparison_df.empty:
            total_comparisons = len(comparison_df)
            competitive_count = comparison_df['is_competitive'].sum()
            
            # Find areas where RHEL wins
            rhel_advantages = comparison_df[comparison_df['relative_performance'] < 85].sort_values('relative_performance')
            
            # Find areas where peers are significantly better
            peer_advantages = comparison_df[comparison_df['relative_performance'] > 115].sort_values('relative_performance', ascending=False)
            
            summary_lines = [f"**{baseline_os} competitive in {competitive_count}/{total_comparisons} benchmark×hardware comparisons**"]
            
            if len(rhel_advantages) > 0:
                summary_lines.append(f"\n**{baseline_os} Performance Advantages:**")
                for _, row in rhel_advantages.head(3).iterrows():
                    advantage = 100 - row['relative_performance']
                    summary_lines.append(
                        f"✓ {advantage:.0f}% faster than {row['peer_os']} in {row['test_name']} on {row['instance_type']}"
                    )
            
            if len(peer_advantages) > 0:
                summary_lines.append(f"\n**Areas for Improvement:**")
                for _, row in peer_advantages.head(3).iterrows():
                    advantage = row['relative_performance'] - 100
                    summary_lines.append(
                        f"⚠️ {row['peer_os']} {advantage:.0f}% faster in {row['test_name']} on {row['instance_type']}"
                    )
            
            summary = '\n'.join(summary_lines)
        else:
            summary = "⚠️ **No competitive comparison data available**\n\nPlease adjust filters or ensure test data exists for the selected configuration."
            competitive_count = 0
            total_comparisons = 0
        
        return {
            'comparison_data': comparison_df,
            'summary': summary,
            'competitive_count': competitive_count,
            'total_benchmarks': total_comparisons,
            'available_comparisons': available_comparisons
        }
    
    def _get_available_comparisons(self, df: pd.DataFrame, baseline_os: str) -> List[Dict[str, Any]]:
        """
        Get list of available competitive comparisons based on data.
        
        Returns list of dicts with comparison metadata for UI toggles.
        Generates comparisons for latest minor version of each MAJOR version.
        """
        from packaging import version
        
        comparisons = []
        
        # Find all unique combinations that have both baseline and peer data
        peer_os_list = [os for os in df['os_vendor'].dropna().unique() if os != baseline_os]
        
        # Get baseline OS versions and group by major version
        baseline_data = df[df['os_vendor'] == baseline_os]
        baseline_versions = baseline_data['os_version'].dropna().unique()
        
        # Group baseline versions by major version (e.g., 9.x and 10.x)
        baseline_by_major = {}
        for ver in baseline_versions:
            try:
                major = str(ver).split('.')[0]
                if major not in baseline_by_major:
                    baseline_by_major[major] = []
                baseline_by_major[major].append(ver)
            except:
                continue
        
        # For each major version, get the latest minor version
        baseline_versions_to_compare = []
        for major, versions in baseline_by_major.items():
            try:
                latest_minor = sorted(versions, 
                                    key=lambda v: version.parse(str(v)), 
                                    reverse=True)[0]
                baseline_versions_to_compare.append(latest_minor)
            except:
                # Fallback to string sort
                latest_minor = sorted(versions, reverse=True)[0]
                baseline_versions_to_compare.append(latest_minor)
        
        # Generate comparisons for each baseline version
        for baseline_ver in baseline_versions_to_compare:
            for peer_os in peer_os_list:
                for cloud in df['cloud_provider'].dropna().unique():
                    # Get data for this specific baseline version and cloud
                    cloud_baseline = df[
                        (df['os_vendor'] == baseline_os) & 
                        (df['os_version'] == baseline_ver) &
                        (df['cloud_provider'] == cloud)
                    ]
                    peer_data = df[
                        (df['os_vendor'] == peer_os) &
                        (df['cloud_provider'] == cloud)
                    ]
                    
                    if len(cloud_baseline) > 0 and len(peer_data) > 0:
                        # Find common hardware
                        baseline_hw = set(cloud_baseline['instance_type'].dropna().unique())
                        peer_hw = set(peer_data['instance_type'].dropna().unique())
                        common_hw = baseline_hw.intersection(peer_hw)
                        
                        if common_hw:
                            # Get latest peer version
                            peer_versions = peer_data['os_version'].dropna().unique()
                            
                            if len(peer_versions) > 0:
                                try:
                                    peer_latest = sorted(peer_versions, 
                                                        key=lambda v: version.parse(str(v)), 
                                                        reverse=True)[0]
                                except:
                                    peer_latest = sorted(peer_versions, reverse=True)[0]
                                
                                comparisons.append({
                                    'baseline_os': baseline_os,
                                    'baseline_version': baseline_ver,
                                    'peer_os': peer_os,
                                    'peer_version': peer_latest,
                                    'cloud_provider': cloud,
                                    'common_hardware': sorted(list(common_hw)),
                                    'label': f"{baseline_os.upper()} {baseline_ver} vs {peer_os.upper()} {peer_latest} on {cloud.upper()}"
                                })
        
        # Sort comparisons by baseline version (descending) then by cloud
        try:
            comparisons.sort(key=lambda c: (
                -version.parse(str(c['baseline_version'])),
                c['cloud_provider'],
                c['peer_os']
            ))
        except:
            # Fallback to simple sort
            comparisons.sort(key=lambda c: (c['baseline_version'], c['cloud_provider'], c['peer_os']), reverse=True)
        
        return comparisons
    
    def analyze_cloud_scaling(
        self,
        df: pd.DataFrame,
        cloud_provider: str,
        os_version: str,
        instance_family: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze how performance scales across cloud instance sizes.
        
        Args:
            df: Input DataFrame
            cloud_provider: Cloud provider to analyze
            os_version: OS version to analyze
            instance_family: Instance family pattern to filter (e.g., 'c2-standard'), or None for all
            
        Returns:
            Dictionary with scaling analysis results
        """
        df_with_cats = self.add_benchmark_categories(df)
        
        # Filter data
        filtered_df = df_with_cats[
            (df_with_cats['cloud_provider'] == cloud_provider) &
            (df_with_cats['os_version'] == os_version)
        ]
        
        if instance_family:
            filtered_df = filtered_df[filtered_df['instance_type'].str.contains(instance_family, na=False)]
        
        if filtered_df.empty:
            return {
                'scaling_data': pd.DataFrame(),
                'summary': 'No data available for selected configuration',
                'linear_scaling_count': 0,
                'total_benchmarks': 0
            }
        
        # Group by instance type and benchmark
        scaling_results = []
        
        instance_types = sorted(filtered_df['instance_type'].unique())
        
        for category in filtered_df['benchmark_category'].unique():
            category_df = filtered_df[filtered_df['benchmark_category'] == category]
            
            for test in category_df['test_name'].unique():
                test_df = category_df[category_df['test_name'] == test]
                
                for instance in instance_types:
                    instance_rows = test_df[test_df['instance_type'] == instance]
                    instance_data = instance_rows['primary_metric_value']
                    
                    if len(instance_data) > 0:
                        # Extract CPU cores if available
                        cores_data = instance_rows['cpu_cores']
                        cores = cores_data.iloc[0] if len(cores_data) > 0 and not pd.isna(cores_data.iloc[0]) else None
                        
                        # Extract memory_gb if available
                        memory_gb = None
                        if 'memory_gb' in instance_rows.columns:
                            mem_data = instance_rows['memory_gb']
                            memory_gb = mem_data.iloc[0] if len(mem_data) > 0 and not pd.isna(mem_data.iloc[0]) else None
                        
                        scaling_results.append({
                            'benchmark_category': category,
                            'test_name': test,
                            'instance_type': instance,
                            'cpu_cores': cores,
                            'memory_gb': memory_gb,
                            'mean_performance': instance_data.mean(),
                            'std_performance': instance_data.std()
                        })
        
        scaling_df = pd.DataFrame(scaling_results)
        
        # Analyze scaling efficiency
        summary_lines = []
        linear_scaling_count = 0
        total_benchmarks = len(scaling_df['test_name'].unique()) if not scaling_df.empty else 0
        
        if not scaling_df.empty and len(instance_types) >= 2:
            for test in scaling_df['test_name'].unique():
                test_data = scaling_df[scaling_df['test_name'] == test].sort_values('cpu_cores')
                
                if len(test_data) >= 2:
                    # Check if performance scales linearly with cores
                    first_perf = test_data.iloc[0]['mean_performance']
                    first_cores = test_data.iloc[0]['cpu_cores']
                    last_perf = test_data.iloc[-1]['mean_performance']
                    last_cores = test_data.iloc[-1]['cpu_cores']
                    
                    if first_cores and last_cores and first_cores > 0 and first_perf > 0:
                        expected_scaling = last_cores / first_cores
                        actual_scaling = last_perf / first_perf
                        scaling_efficiency = (actual_scaling / expected_scaling) * 100
                        
                        if scaling_efficiency >= 85:  # Within 15% of linear
                            linear_scaling_count += 1
                        elif scaling_efficiency < 70:  # Poor scaling
                            summary_lines.append(
                                f"⚠️ {test} shows diminishing returns (scaling efficiency: {scaling_efficiency:.0f}%)"
                            )
            
            summary = f"✅ Linear scaling observed for {linear_scaling_count}/{total_benchmarks} workloads\n" + '\n'.join(summary_lines)
        else:
            summary = "Insufficient data for scaling analysis"
        
        return {
            'scaling_data': scaling_df,
            'summary': summary,
            'linear_scaling_count': linear_scaling_count,
            'total_benchmarks': total_benchmarks
        }


def load_synthetic_data(filepath: str = "data/synthetic/benchmark_results.json") -> List[Dict[str, Any]]:
    """
    Load synthetic data from JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        List of document dictionaries
    """
    import json
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    logger.info(f"Loaded {len(data)} documents from {filepath}")
    return data


def main():
    """Test the data processing functionality."""
    
    print("Testing BenchmarkDataProcessor")
    print("=" * 60)
    
    # Load synthetic data
    print("\n1. Loading synthetic data...")
    documents = load_synthetic_data()
    print(f"   Loaded {len(documents)} documents")
    
    # Initialize processor
    processor = BenchmarkDataProcessor()
    
    # Convert to DataFrame
    print("\n2. Converting to DataFrame...")
    df = processor.documents_to_dataframe(documents)
    print(f"   DataFrame shape: {df.shape}")
    print(f"   Columns: {list(df.columns[:10])}...")
    
    # Show unique values for key dimensions
    print("\n3. Filter Dimensions:")
    print(f"   OS Versions: {processor.get_unique_values(df, 'os_version')}")
    print(f"   Instance Types: {processor.get_unique_values(df, 'instance_type')[:5]}...")
    print(f"   Test Types: {processor.get_unique_values(df, 'test_name')}")
    print(f"   Cloud Providers: {processor.get_unique_values(df, 'cloud_provider')}")
    
    # Calculate statistics
    print("\n4. Statistics by Test Type:")
    stats = processor.calculate_statistics(
        df,
        group_by=['test_name'],
        metric='primary_metric_value'
    )
    print(stats.to_string(index=False))
    
    # Test filtering
    print("\n5. Testing filters...")
    filtered = processor.filter_data(
        df,
        os_versions=['9.5'],
        test_names=['coremark', 'streams']
    )
    print(f"   Filtered to {len(filtered)} records (OS 9.5, CoreMark/STREAM only)")
    
    # Test comparison
    print("\n6. Testing comparison (RHEL 9.5 vs 9.4)...")
    if len(df[df['os_version'] == '9.5']) > 0 and len(df[df['os_version'] == '9.4']) > 0:
        comparison = processor.calculate_comparison(
            df,
            baseline_filters={'os_versions': ['9.4']},
            comparison_filters={'os_versions': ['9.5']},
            group_by='test_name'
        )
        print(comparison[['test_name', 'baseline_mean', 'comparison_mean', 'percent_change', 'change_category']].to_string(index=False))
    else:
        print("   Insufficient data for comparison")
    
    print("\n✓ Data processing tests complete!")


if __name__ == "__main__":
    main()

