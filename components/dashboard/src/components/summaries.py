"""
Summary text generation for dashboard insights.

Provides human-readable summaries of analysis results.
"""

from typing import Dict, Any, List
import pandas as pd


def format_regression_summary(analysis_result: Dict[str, Any]) -> str:
    """
    Format regression analysis into a readable summary.
    
    Args:
        analysis_result: Result from analyze_os_version_regressions
        
    Returns:
        Formatted summary string
    """
    if not analysis_result or 'summary' not in analysis_result:
        return "No regression analysis available"
    
    return analysis_result['summary']


def format_peer_comparison_summary(analysis_result: Dict[str, Any]) -> str:
    """
    Format peer OS comparison into a readable summary.
    
    Args:
        analysis_result: Result from analyze_peer_os_comparison
        
    Returns:
        Formatted summary string
    """
    if not analysis_result or 'summary' not in analysis_result:
        return "No peer comparison data available"
    
    return analysis_result['summary']


def format_scaling_summary(analysis_result: Dict[str, Any]) -> str:
    """
    Format cloud scaling analysis into a readable summary.
    
    Args:
        analysis_result: Result from analyze_cloud_scaling
        
    Returns:
        Formatted summary string
    """
    if not analysis_result or 'summary' not in analysis_result:
        return "No scaling analysis available"
    
    return analysis_result['summary']


def get_status_icon(num_issues: int) -> str:
    """
    Get an appropriate status icon based on number of issues.
    
    Args:
        num_issues: Number of issues detected
        
    Returns:
        Status icon (emoji or symbol)
    """
    if num_issues == 0:
        return "✅"
    elif num_issues <= 2:
        return "⚠️"
    else:
        return "🔴"


def create_alert_badge(text: str, severity: str = "warning") -> str:
    """
    Create an alert badge for display.
    
    Args:
        text: Alert text
        severity: One of "success", "warning", "danger", "info"
        
    Returns:
        Formatted badge HTML class
    """
    severity_map = {
        "success": "success",
        "warning": "warning",
        "danger": "danger",
        "info": "info"
    }
    
    return severity_map.get(severity, "info")


def summarize_investigation_details(
    baseline_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    test_name: str,
    baseline_label: str,
    comparison_label: str
) -> Dict[str, Any]:
    """
    Create a detailed summary for investigation view.
    
    Args:
        baseline_df: Baseline data
        comparison_df: Comparison data
        test_name: Test name
        baseline_label: Label for baseline
        comparison_label: Label for comparison
        
    Returns:
        Dictionary with summary details
    """
    summary = {
        'test_name': test_name,
        'baseline_label': baseline_label,
        'comparison_label': comparison_label,
        'baseline_count': len(baseline_df),
        'comparison_count': len(comparison_df)
    }
    
    if not baseline_df.empty and 'primary_metric_value' in baseline_df.columns:
        summary['baseline_mean'] = baseline_df['primary_metric_value'].mean()
        summary['baseline_std'] = baseline_df['primary_metric_value'].std()
        summary['baseline_min'] = baseline_df['primary_metric_value'].min()
        summary['baseline_max'] = baseline_df['primary_metric_value'].max()
    
    if not comparison_df.empty and 'primary_metric_value' in comparison_df.columns:
        summary['comparison_mean'] = comparison_df['primary_metric_value'].mean()
        summary['comparison_std'] = comparison_df['primary_metric_value'].std()
        summary['comparison_min'] = comparison_df['primary_metric_value'].min()
        summary['comparison_max'] = comparison_df['primary_metric_value'].max()
    
    # Calculate regression metrics
    if 'baseline_mean' in summary and 'comparison_mean' in summary and summary['baseline_mean'] > 0:
        summary['percent_change'] = ((summary['comparison_mean'] - summary['baseline_mean']) / summary['baseline_mean']) * 100
        summary['is_regression'] = summary['percent_change'] < -5
        summary['is_improvement'] = summary['percent_change'] > 10
        
        if summary['is_regression']:
            summary['status'] = 'danger'
            summary['status_text'] = 'Regression Detected'
        elif summary['is_improvement']:
            summary['status'] = 'success'
            summary['status_text'] = 'Performance Improvement'
        else:
            summary['status'] = 'info'
            summary['status_text'] = 'Stable Performance'
    
    return summary


def format_investigation_summary_text(summary: Dict[str, Any]) -> str:
    """
    Format investigation summary as readable text.
    
    Args:
        summary: Summary dictionary from summarize_investigation_details
        
    Returns:
        Formatted text summary
    """
    lines = []
    
    if 'baseline_mean' in summary and 'comparison_mean' in summary:
        lines.append(f"**{summary['baseline_label']}**: {summary['baseline_mean']:,.1f} (avg)")
        lines.append(f"**{summary['comparison_label']}**: {summary['comparison_mean']:,.1f} (avg)")
        
        if 'percent_change' in summary:
            direction = "↑" if summary['percent_change'] > 0 else "↓"
            lines.append(f"**Change**: {direction} {abs(summary['percent_change']):.1f}%")
    
    if 'baseline_count' in summary:
        lines.append(f"**Sample sizes**: {summary['baseline_count']} vs {summary['comparison_count']} tests")
    
    return "\n\n".join(lines)

