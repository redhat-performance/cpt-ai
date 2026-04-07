"""
Visualization components for the dashboard.

Provides Plotly-based visualizations for benchmark data.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Optional, List


def create_comparison_chart(
    df: pd.DataFrame,
    group_by: str = 'test_name',
    title: str = "Performance Comparison"
) -> go.Figure:
    """
    Create a side-by-side bar chart for comparing configurations.
    
    Args:
        df: DataFrame with comparison data (must have baseline_mean, comparison_mean)
        group_by: Column used for grouping
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for comparison")
    
    fig = go.Figure()
    
    # Baseline bars
    fig.add_trace(go.Bar(
        x=df[group_by],
        y=df['baseline_mean'],
        name='Baseline',
        marker_color='lightblue',
        error_y=dict(type='data', array=df['baseline_std']) if 'baseline_std' in df.columns else None
    ))
    
    # Comparison bars
    fig.add_trace(go.Bar(
        x=df[group_by],
        y=df['comparison_mean'],
        name='Comparison',
        marker_color='lightcoral',
        error_y=dict(type='data', array=df['comparison_std']) if 'comparison_std' in df.columns else None
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=group_by.replace('_', ' ').title(),
        yaxis_title="Performance Metric",
        barmode='group',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    return fig


def create_time_series_chart(
    df: pd.DataFrame,
    x_col: str = 'timestamp',
    y_col: str = 'primary_metric_value',
    color_col: Optional[str] = 'test_name',
    title: str = "Performance Trends Over Time",
    use_facets: bool = False
) -> go.Figure:
    """
    Create a time series line chart.
    
    Args:
        df: DataFrame with time series data
        x_col: Column for x-axis (timestamp)
        y_col: Column for y-axis (metric values)
        color_col: Column to use for line colors
        title: Chart title
        use_facets: If True and color_col='test_name', create separate subplots with independent y-axes
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No time series data available")
    
    # If color_col is test_name and we have multiple tests with different scales, use facets
    if use_facets and color_col == 'test_name' and len(df[color_col].unique()) > 1:
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            markers=True,
            title=title,
            template='plotly_white',
            facet_row=color_col,
            facet_row_spacing=0.05
        )
        
        # Update each facet to have independent y-axis
        fig.update_yaxes(matches=None, showticklabels=True, title_text="")
        
        fig.update_layout(
            xaxis_title="Date",
            hovermode='x unified',
            height=max(500, len(df[color_col].unique()) * 200),
            showlegend=False  # Legend is redundant with facet labels
        )
    else:
        fig = px.line(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            markers=True,
            title=title,
            template='plotly_white'
        )
        
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Performance Metric",
            hovermode='x unified',
            height=500
        )
    
    fig.update_traces(mode='lines+markers')
    
    return fig


def create_heatmap(
    df: pd.DataFrame,
    row_dim: str = 'os_version',
    col_dim: str = 'instance_type',
    value_col: str = 'primary_metric_value',
    title: str = "Performance Heatmap",
    normalize_by_test: bool = True
) -> go.Figure:
    """
    Create a heatmap for regression analysis.
    
    Args:
        df: DataFrame with benchmark data
        row_dim: Dimension for rows
        col_dim: Dimension for columns
        value_col: Column containing values for heatmap
        title: Chart title
        normalize_by_test: If True and data contains multiple test types, normalize within each test
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for heatmap")
    
    # If we have multiple test types with different scales, normalize within each test
    if normalize_by_test and 'test_name' in df.columns and len(df['test_name'].unique()) > 1:
        # Calculate mean baseline for each test
        df_normalized = df.copy()
        for test_name in df_normalized['test_name'].unique():
            test_mask = df_normalized['test_name'] == test_name
            test_mean = df_normalized.loc[test_mask, value_col].mean()
            if test_mean > 0:
                # Convert to percentage of mean (100 = average performance)
                df_normalized.loc[test_mask, value_col] = (df_normalized.loc[test_mask, value_col] / test_mean) * 100
        
        # Create pivot table from normalized data
        pivot = df_normalized.pivot_table(
            values=value_col,
            index=row_dim,
            columns=col_dim,
            aggfunc='mean'
        )
        
        colorbar_title = "% of Avg"
        text_suffix = "%"
    else:
        # Create pivot table
        pivot = df.pivot_table(
            values=value_col,
            index=row_dim,
            columns=col_dim,
            aggfunc='mean'
        )
        colorbar_title = "Metric Value"
        text_suffix = ""
    
    if pivot.empty:
        return create_empty_figure("Insufficient data for heatmap")
    
    # Create hover text with formatted values
    hover_text = [[f"{val:.1f}{text_suffix}" for val in row] for row in pivot.values]
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale='RdYlGn',
        text=pivot.values.round(1),
        hovertext=hover_text,
        hovertemplate='%{y} × %{x}<br>%{hovertext}<extra></extra>',
        texttemplate='%{text}' + text_suffix,
        textfont={"size": 10},
        colorbar=dict(title=colorbar_title)
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=col_dim.replace('_', ' ').title(),
        yaxis_title=row_dim.replace('_', ' ').title(),
        template='plotly_white',
        height=500
    )
    
    return fig


def create_box_plot(
    df: pd.DataFrame,
    x_col: str = 'test_name',
    y_col: str = 'primary_metric_value',
    color_col: Optional[str] = None,
    title: str = "Performance Distribution",
    use_facets: bool = False
) -> go.Figure:
    """
    Create a box plot showing distribution of performance metrics.
    
    Args:
        df: DataFrame with benchmark data
        x_col: Column for x-axis categories
        y_col: Column for y-axis values
        color_col: Optional column for color grouping
        title: Chart title
        use_facets: If True and x_col='test_name', create separate subplots with independent y-axes
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for distribution plot")
    
    # If x_col is test_name and we have multiple tests with different scales, use facets
    if use_facets and x_col == 'test_name' and len(df[x_col].unique()) > 1:
        fig = px.box(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            template='plotly_white',
            points='all',
            facet_col=x_col,
            facet_col_wrap=3
        )
        
        # Update each facet to have independent y-axis
        fig.update_yaxes(matches=None, showticklabels=True)
        
        fig.update_layout(
            height=500,
            showlegend=True
        )
    else:
        fig = px.box(
            df,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            template='plotly_white',
            points='all'
        )
        
        fig.update_layout(
            xaxis_title=x_col.replace('_', ' ').title(),
            yaxis_title="Performance Metric",
            height=500
        )
    
    return fig


def create_scatter_plot(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    color_col: Optional[str] = None,
    size_col: Optional[str] = None,
    hover_data: Optional[List[str]] = None,
    title: str = "Performance Scatter Plot"
) -> go.Figure:
    """
    Create a scatter plot for exploring relationships.
    
    Args:
        df: DataFrame with benchmark data
        x_col: Column for x-axis
        y_col: Column for y-axis
        color_col: Optional column for point colors
        size_col: Optional column for point sizes
        hover_data: Additional columns to show in hover
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if df.empty:
        return create_empty_figure("No data available for scatter plot")
    
    fig = px.scatter(
        df,
        x=x_col,
        y=y_col,
        color=color_col,
        size=size_col,
        hover_data=hover_data,
        title=title,
        template='plotly_white'
    )
    
    fig.update_layout(
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title=y_col.replace('_', ' ').title(),
        height=500
    )
    
    return fig


def create_performance_delta_chart(
    df: pd.DataFrame,
    x_col: str = 'test_name',
    title: str = "Performance Change (%)"
) -> go.Figure:
    """
    Create a bar chart showing percentage changes with color coding.
    
    Uses the same 5-color + pattern scheme as version comparison charts
    when is_regression data is available.
    
    Args:
        df: DataFrame with percent_change column (and optionally is_regression)
        x_col: Column for x-axis labels
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if df.empty or 'percent_change' not in df.columns:
        return create_empty_figure("No comparison data available")
    
    # Determine colors and patterns
    # If we have is_regression info, use the 5-color scheme
    if 'is_regression' in df.columns:
        colors = []
        patterns = []
        for _, row in df.iterrows():
            pct = row['percent_change']
            is_reg = row['is_regression']
            # For simple delta chart, assume single config (any == all)
            color, pattern = _get_regression_color_and_pattern(pct, is_reg, is_reg)
            colors.append(color)
            patterns.append(pattern)
        
        marker_config = dict(
            color=colors,
            pattern_shape=patterns,
            pattern_fillmode='overlay',
            pattern_size=8,
            pattern_solidity=0.3
        )
    else:
        # Fallback to simple color coding
        colors = ['#d73027' if x < -5 else '#1a9850' if x > 5 else '#e0e0e0' 
                  for x in df['percent_change']]
        marker_config = dict(color=colors)
    
    fig = go.Figure(data=[
        go.Bar(
            x=df[x_col],
            y=df['percent_change'],
            marker=marker_config,
            text=df['percent_change'].round(1).astype(str) + '%',
            textposition='outside'
        )
    ])
    
    fig.update_layout(
        title=title,
        xaxis_title=x_col.replace('_', ' ').title(),
        yaxis_title="Percent Change (%)",
        template='plotly_white',
        height=500
    )
    
    # Add reference line at 0
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    
    # Add stable zone
    fig.add_hrect(y0=-5, y1=5, fillcolor="gray", opacity=0.1, line_width=0,
                  annotation_text="Stable zone (±5%)", annotation_position="top right")
    
    return fig


def create_metrics_table(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    title: str = "Detailed Metrics"
) -> go.Figure:
    """
    Create a table visualization for detailed metrics.
    
    Args:
        df: DataFrame with metric data
        columns: Specific columns to display (None = all)
        title: Table title
        
    Returns:
        Plotly Figure with table
    """
    if df.empty:
        return create_empty_figure("No data available for table")
    
    if columns:
        display_df = df[columns].copy()
    else:
        display_df = df.copy()
    
    # Round numeric columns
    numeric_cols = display_df.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_cols:
        display_df[col] = display_df[col].round(2)
    
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{col}</b>" for col in display_df.columns],
            fill_color='paleturquoise',
            align='left',
            font=dict(size=12)
        ),
        cells=dict(
            values=[display_df[col] for col in display_df.columns],
            fill_color='lavender',
            align='left',
            font=dict(size=11)
        )
    )])
    
    fig.update_layout(
        title=title,
        height=400
    )
    
    return fig


def create_empty_figure(message: str = "No data available") -> go.Figure:
    """
    Create an empty figure with a message.
    
    Args:
        message: Message to display
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=20, color="gray")
    )
    
    fig.update_layout(
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        height=400,
        template='plotly_white'
    )
    
    return fig


def create_separate_test_charts(
    df: pd.DataFrame,
    chart_type: str = 'box',
    x_col: str = 'os_version',
    y_col: str = 'primary_metric_value',
    color_col: Optional[str] = None,
    title_prefix: str = "Performance"
) -> List[go.Figure]:
    """
    Create separate charts for each test type to handle different scales.
    
    Args:
        df: DataFrame with benchmark data
        chart_type: Type of chart ('box', 'time_series')
        x_col: Column for x-axis
        y_col: Column for y-axis values
        color_col: Optional column for color grouping
        title_prefix: Prefix for chart titles
        
    Returns:
        List of Plotly Figures, one per test type
    """
    if df.empty or 'test_name' not in df.columns:
        return [create_empty_figure("No data available")]
    
    figures = []
    test_names = sorted(df['test_name'].unique())
    
    for test_name in test_names:
        test_df = df[df['test_name'] == test_name]
        
        if chart_type == 'box':
            fig = create_box_plot(
                test_df,
                x_col=x_col,
                y_col=y_col,
                color_col=color_col if color_col != 'test_name' else None,
                title=f"{title_prefix}: {test_name}",
                use_facets=False
            )
        elif chart_type == 'time_series':
            fig = create_time_series_chart(
                test_df,
                x_col=x_col,
                y_col=y_col,
                color_col=color_col if color_col != 'test_name' else None,
                title=f"{title_prefix}: {test_name}",
                use_facets=False
            )
        else:
            fig = create_empty_figure(f"Unknown chart type: {chart_type}")
        
        figures.append(fig)
    
    return figures


def create_summary_cards_data(df: pd.DataFrame) -> dict:
    """
    Calculate summary statistics for dashboard cards.
    
    Args:
        df: DataFrame with benchmark data
        
    Returns:
        Dictionary with summary statistics
    """
    if df.empty:
        return {
            'total_tests': 0,
            'unique_configs': 0,
            'pass_rate': 0,
            'avg_metric': 0
        }
    
    summary = {
        'total_tests': len(df),
        'unique_configs': df[['os_version', 'instance_type']].drop_duplicates().shape[0],
        'pass_rate': (df['status'] == 'PASS').sum() / len(df) * 100 if len(df) > 0 else 0,
        'avg_metric': df['primary_metric_value'].mean() if 'primary_metric_value' in df.columns else 0,
        'date_range': f"{df['timestamp'].min().strftime('%Y-%m-%d')} to {df['timestamp'].max().strftime('%Y-%m-%d')}" if 'timestamp' in df.columns else "N/A"
    }
    
    return summary


def create_regression_heatmap(
    pct_change_df: pd.DataFrame,
    title: str = "OS Version Regressions by Benchmark"
) -> go.Figure:
    """
    Create a heatmap showing percentage changes between OS versions.
    
    Args:
        pct_change_df: DataFrame with test_name as index, version transitions as columns
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if pct_change_df.empty:
        return create_empty_figure("No regression data available")
    
    # Define color scale: red for regressions, green for improvements, gray for stable
    colorscale = [
        [0.0, '#d73027'],    # Strong regression (red)
        [0.4, '#fee090'],    # Mild regression (yellow)
        [0.5, '#e0e0e0'],    # Stable (gray)
        [0.6, '#e0f3db'],    # Mild improvement (light green)
        [1.0, '#1a9850']     # Strong improvement (green)
    ]
    
    # Create hover text
    hover_text = []
    for i, row_name in enumerate(pct_change_df.index):
        hover_row = []
        for j, col_name in enumerate(pct_change_df.columns):
            val = pct_change_df.iloc[i, j]
            if pd.isna(val):
                hover_row.append("No data")
            else:
                direction = "↑" if val > 0 else "↓" if val < 0 else "→"
                hover_row.append(f"{row_name}<br>{col_name}<br>{direction} {abs(val):.1f}%")
        hover_text.append(hover_row)
    
    # Create text annotations for cells
    text_values = []
    for i, row_name in enumerate(pct_change_df.index):
        text_row = []
        for j, col_name in enumerate(pct_change_df.columns):
            val = pct_change_df.iloc[i, j]
            if pd.isna(val):
                text_row.append("")
            else:
                text_row.append(f"{val:.1f}%")
        text_values.append(text_row)
    
    fig = go.Figure(data=go.Heatmap(
        z=pct_change_df.values,
        x=pct_change_df.columns,
        y=pct_change_df.index,
        colorscale=colorscale,
        zmid=0,  # Center the color scale at 0
        text=text_values,
        hovertext=hover_text,
        hovertemplate='%{hovertext}<extra></extra>',
        texttemplate='%{text}',
        textfont={"size": 11, "color": "black"},
        colorbar=dict(
            title="% Change",
            ticksuffix="%"
        )
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="OS Version Transition",
        yaxis_title="Benchmark",
        template='plotly_white',
        height=max(400, len(pct_change_df.index) * 40),
        xaxis={'side': 'bottom'},
        yaxis={'autorange': 'reversed'}  # Top to bottom
    )
    
    return fig


def _get_regression_color_and_pattern(
    percent_change: float,
    is_any_regression: bool,
    is_all_regression: bool,
    stable_threshold: float = 5.0
) -> tuple:
    """
    Determine bar color and pattern based on change and consistency across runs.
    
    Returns a 5-color + pattern scheme:
    - Solid Dark Red: All runs regressed, average is negative
    - Striped Orange: Mixed results, net regression  
    - Gray: Stable (within threshold)
    - Striped Amber: Mixed results, net improvement
    - Solid Green: All runs improved, average is positive
    
    Args:
        percent_change: Average percent change across runs
        is_any_regression: True if ANY run showed regression
        is_all_regression: True if ALL runs showed regression
        stable_threshold: Threshold for stable zone (default ±5%)
        
    Returns:
        Tuple of (color hex, pattern shape or empty string)
    """
    # Stable zone: within threshold
    if abs(percent_change) <= stable_threshold:
        return '#e0e0e0', ''  # Gray, no pattern
    
    if percent_change < 0:
        # Net regression
        if is_all_regression:
            return '#d73027', ''  # Dark red, solid - unanimous regression
        else:
            return '#f46d43', '/'  # Orange, striped - mixed, net regression
    else:
        # Net improvement
        if not is_any_regression:
            return '#1a9850', ''  # Green, solid - unanimous improvement
        else:
            return '#fdae61', '/'  # Amber, striped - mixed, net improvement


def create_version_comparison_bar_chart(
    comparison_df: pd.DataFrame,
    baseline_version: str,
    comparison_version: str,
    title: Optional[str] = None
) -> go.Figure:
    """
    Create a bar chart comparing performance between two OS versions.
    
    Uses a 5-color + pattern scheme to communicate both the net result AND
    consistency across hardware configurations:
    - Solid Dark Red: All configs regressed
    - Striped Orange: Mixed results, net regression
    - Gray: Stable (within ±5%)
    - Striped Amber: Mixed results, net improvement
    - Solid Green: All configs improved
    
    Args:
        comparison_df: DataFrame with comparison data (must have columns:
                      test_name, baseline_mean, comparison_mean, percent_change, is_regression,
                      hardware_config (optional))
        baseline_version: Baseline version name
        comparison_version: Comparison version name
        title: Chart title (auto-generated if None)
        
    Returns:
        Plotly Figure
    """
    if comparison_df.empty:
        return create_empty_figure("No comparison data available")
    
    if title is None:
        title = f"Performance Comparison: {baseline_version} vs {comparison_version}"
    
    # Check if we have multiple hardware configs per test
    has_hardware = 'hardware_config' in comparison_df.columns
    if has_hardware:
        # Group by test name and show average, but include hardware in hover
        grouped = comparison_df.groupby('test_name').agg({
            'percent_change': 'mean',
            'is_regression': ['any', 'all'],  # Track both any and all regression
            'baseline_mean': 'mean',
            'comparison_mean': 'mean'
        }).reset_index()
        
        # Flatten multi-level column names
        grouped.columns = ['test_name', 'percent_change', 'is_any_regression', 
                          'is_all_regression', 'baseline_mean', 'comparison_mean']
        
        # Count configs for labels
        config_counts = comparison_df.groupby('test_name')['hardware_config'].nunique()
        
        # Create labels that include hardware info
        test_labels = []
        for test_name in grouped['test_name']:
            hw_configs = comparison_df[comparison_df['test_name'] == test_name]['hardware_config'].unique()
            if len(hw_configs) > 1:
                test_labels.append(f"{test_name} (avg across {len(hw_configs)} configs)")
            else:
                test_labels.append(f"{test_name} ({hw_configs[0]})")
        
        grouped['test_label'] = test_labels
        comparison_df_sorted = grouped.sort_values('percent_change')
    else:
        # No hardware config info, use as-is
        comparison_df_sorted = comparison_df.sort_values('percent_change').copy()
        comparison_df_sorted['test_label'] = comparison_df_sorted['test_name']
        # For single-config case, any == all
        comparison_df_sorted['is_any_regression'] = comparison_df_sorted['is_regression']
        comparison_df_sorted['is_all_regression'] = comparison_df_sorted['is_regression']
    
    # Determine colors and patterns based on the 5-color scheme
    colors = []
    patterns = []
    for _, row in comparison_df_sorted.iterrows():
        color, pattern = _get_regression_color_and_pattern(
            row['percent_change'],
            row['is_any_regression'],
            row['is_all_regression']
        )
        colors.append(color)
        patterns.append(pattern)
    
    # Build hover template with consistency info
    hover_texts = []
    for idx, row in comparison_df_sorted.iterrows():
        test_name = row['test_name']
        
        # Determine consistency status for hover
        if row['is_all_regression']:
            consistency = "All configs regressed"
        elif row['is_any_regression']:
            consistency = "Mixed results (some configs regressed)"
        elif row['percent_change'] > 5:
            consistency = "All configs improved"
        else:
            consistency = "Stable across configs"
        
        if has_hardware:
            # Show all hardware configs for this test
            test_hw_data = comparison_df[comparison_df['test_name'] == test_name]
            hw_lines = []
            for _, hw_row in test_hw_data.iterrows():
                status_icon = "🔴" if hw_row['is_regression'] else "🟢" if hw_row['percent_change'] > 5 else "⚪"
                hw_lines.append(
                    f"  {status_icon} {hw_row['hardware_config']}: {hw_row['percent_change']:+.1f}% "
                    f"({hw_row['baseline_mean']:.2f} → {hw_row['comparison_mean']:.2f})"
                )
            hw_detail = "<br>".join(hw_lines)
            hover_text = (
                f"<b>{test_name}</b><br>"
                f"Average change: {row['percent_change']:+.1f}%<br>"
                f"<i>{consistency}</i><br>"
                f"<br><b>By Hardware:</b><br>{hw_detail}"
            )
        else:
            hover_text = (
                f"<b>{test_name}</b><br>"
                f"Change: {row['percent_change']:+.1f}%<br>"
                f"{baseline_version}: {row['baseline_mean']:.2f}<br>"
                f"{comparison_version}: {row['comparison_mean']:.2f}"
            )
        hover_texts.append(hover_text)
    
    fig = go.Figure(data=[
        go.Bar(
            y=comparison_df_sorted['test_label'],
            x=comparison_df_sorted['percent_change'],
            orientation='h',
            marker=dict(
                color=colors,
                pattern_shape=patterns,
                pattern_fillmode='overlay',
                pattern_size=8,
                pattern_solidity=0.3,
                line=dict(width=1, color='rgba(0,0,0,0.3)')
            ),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts,
            text=comparison_df_sorted['percent_change'].apply(lambda x: f'{x:+.1f}%'),
            textposition='outside'
        )
    ])
    
    # Add legend annotation explaining the color/pattern scheme
    legend_text = (
        "<b>Legend:</b><br>"
        "■ <span style='color:#d73027'>Dark Red</span>: All configs regressed<br>"
        "▤ <span style='color:#f46d43'>Orange striped</span>: Mixed, net regression<br>"
        "■ <span style='color:#e0e0e0'>Gray</span>: Stable (±5%)<br>"
        "▤ <span style='color:#fdae61'>Amber striped</span>: Mixed, net improvement<br>"
        "■ <span style='color:#1a9850'>Green</span>: All configs improved"
    )
    
    fig.add_annotation(
        text=legend_text,
        xref="paper", yref="paper",
        x=1.02, y=1.0,
        showarrow=False,
        font=dict(size=10),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="rgba(200, 200, 200, 0.5)",
        borderwidth=1,
        borderpad=6,
        xanchor="left",
        yanchor="top"
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Performance Change (%)",
        yaxis_title="Benchmark",
        template='plotly_white',
        height=max(400, len(comparison_df_sorted) * 30),
        showlegend=False,
        xaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='black'),
        margin=dict(r=220)  # Extra right margin for legend
    )
    
    return fig


def create_peer_os_comparison_chart(
    comparison_df: pd.DataFrame,
    baseline_os: str = "RHEL",
    title: str = "RHEL vs Peer Operating Systems"
) -> go.Figure:
    """
    Create a grouped bar chart comparing RHEL against peer OSes.
    
    Args:
        comparison_df: DataFrame with comparison data
        baseline_os: Name of baseline OS
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if comparison_df.empty:
        return create_empty_figure("No peer comparison data available")
    
    # Benchmark category to benchmarks mapping (for hover tooltips)
    # This should match BENCHMARK_GROUPS in data_processing.py
    BENCHMARK_GROUPS = {
        'Networking': ['uperf'],
        'Storage/IO': ['fio'],
        'HPC/Compute': ['streams', 'specjbb', 'auto_hpl'],
        'System': ['sysbench', 'coremark_pro', 'pig', 'coremark', 'phoronix', 'passmark']
    }
    
    # Group by benchmark category
    fig = go.Figure()
    
    peer_os_list = sorted(comparison_df['peer_os'].unique())
    categories = sorted(comparison_df['benchmark_category'].unique())
    
    # Create grouped bars by benchmark category
    for peer_os in peer_os_list:
        peer_data = comparison_df[comparison_df['peer_os'] == peer_os]
        
        y_values = []
        x_labels = []
        colors = []
        hover_texts = []
        
        for category in categories:
            cat_data = peer_data[peer_data['benchmark_category'] == category]
            if not cat_data.empty:
                # Average relative performance for this category
                avg_rel_perf = cat_data['relative_performance'].mean()
                y_values.append(avg_rel_perf)
                x_labels.append(category)
                
                # Color: green if within 10%, yellow if within 20%, red otherwise
                if avg_rel_perf >= 90 and avg_rel_perf <= 110:
                    colors.append('#1a9850')  # Green - competitive
                elif avg_rel_perf >= 80 and avg_rel_perf <= 120:
                    colors.append('#fee090')  # Yellow - moderate difference
                else:
                    colors.append('#d73027')  # Red - significant difference
                
                # Build hover text with benchmark list
                benchmarks_in_category = BENCHMARK_GROUPS.get(category, ['Unknown'])
                # Also show which benchmarks actually have data in this category
                actual_tests = cat_data['test_name'].unique().tolist()
                hover_text = (
                    f"<b>{category}</b><br>"
                    f"Relative Performance: {avg_rel_perf:.1f}%<br>"
                    f"<br><b>Benchmarks in category:</b><br>"
                    f"{', '.join(benchmarks_in_category)}<br>"
                    f"<br><b>Tests with data:</b><br>"
                    f"{', '.join(actual_tests)}"
                )
                hover_texts.append(hover_text)
        
        fig.add_trace(go.Bar(
            name=peer_os,
            x=x_labels,
            y=y_values,
            text=[f"{v:.0f}%" for v in y_values],
            textposition='outside',
            marker_color=colors,
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts
        ))
    
    # Add baseline reference line at 100%
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="gray",
        annotation_text=f"{baseline_os} baseline (100%)",
        annotation_position="right"
    )
    
    # Add competitive zone (90-110%)
    fig.add_hrect(
        y0=90, y1=110,
        fillcolor="green",
        opacity=0.1,
        line_width=0,
        annotation_text="Competitive zone",
        annotation_position="top right"
    )
    
    # Add legend annotation explaining the color scheme
    legend_text = (
        "<b>Color Legend:</b><br>"
        "■ <span style='color:#1a9850'>Green</span>: Competitive (90-110%)<br>"
        "■ <span style='color:#fee090'>Yellow</span>: Moderate diff (80-120%)<br>"
        "■ <span style='color:#d73027'>Red</span>: Significant diff (<80% or >120%)"
    )
    
    fig.add_annotation(
        text=legend_text,
        xref="paper", yref="paper",
        x=1.02, y=0.5,
        showarrow=False,
        font=dict(size=10),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.9)",
        bordercolor="rgba(200, 200, 200, 0.5)",
        borderwidth=1,
        borderpad=6,
        xanchor="left",
        yanchor="middle"
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="Benchmark Category",
        yaxis_title=f"Performance Relative to {baseline_os} (%)",
        barmode='group',
        template='plotly_white',
        height=500,
        hovermode='x unified',
        legend=dict(
            title="Peer OS",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(r=200)  # Extra right margin for color legend
    )
    
    return fig


def create_cloud_scaling_chart(
    scaling_df: pd.DataFrame,
    title: str = "Performance Scaling Across Instance Sizes"
) -> go.Figure:
    """
    Create a line chart showing how performance scales with instance size.
    
    Shows scaling efficiency as a percentage of ideal linear scaling, making it
    easy to compare different benchmarks regardless of their native units.
    
    - 100% = Perfect linear scaling (performance doubles when cores double)
    - >100% = Super-linear scaling (better than expected)
    - <100% = Sub-linear scaling (diminishing returns)
    
    Uses evenly-spaced categorical X-axis for readability (not linear by CPU cores).
    
    Args:
        scaling_df: DataFrame with scaling analysis data
        title: Chart title
        
    Returns:
        Plotly Figure
    """
    if scaling_df.empty:
        return create_empty_figure("No scaling data available")
    
    fig = go.Figure()
    
    # Group by benchmark category or test name
    if 'benchmark_category' in scaling_df.columns:
        group_col = 'benchmark_category'
    else:
        group_col = 'test_name'
    
    categories = sorted(scaling_df[group_col].unique())
    x_title = "Instance Type"
    
    # Check if we have CPU cores data
    has_cpu_cores = 'cpu_cores' in scaling_df.columns and scaling_df['cpu_cores'].notna().any()
    
    # Build ordered list of unique instances sorted by CPU cores for even spacing
    # This creates categorical X-axis labels instead of numeric
    if has_cpu_cores and 'instance_type' in scaling_df.columns:
        # Get unique instances sorted by CPU cores
        instance_order_df = scaling_df[['instance_type', 'cpu_cores', 'memory_gb']].drop_duplicates()
        instance_order_df = instance_order_df.sort_values('cpu_cores')
        
        # Create tick labels with instance name, cores, and RAM
        tick_labels = []
        for _, row in instance_order_df.iterrows():
            inst_name = row['instance_type']
            cores = int(row['cpu_cores'])
            memory = row.get('memory_gb', None)
            if memory and not pd.isna(memory):
                label = f"{inst_name}<br>{cores} vCPU, {int(memory)} GB"
            else:
                label = f"{inst_name}<br>{cores} vCPU"
            tick_labels.append(label)
        
        # Map instance types to their index position (0, 1, 2, ...) for even spacing
        instance_to_index = {row['instance_type']: i for i, (_, row) in enumerate(instance_order_df.iterrows())}
        cores_list = instance_order_df['cpu_cores'].tolist()
    else:
        instance_to_index = {}
        tick_labels = []
        cores_list = []
    
    for category in categories:
        cat_data = scaling_df[scaling_df[group_col] == category].copy()
        
        # Sort by CPU cores or instance type
        if has_cpu_cores:
            cat_data = cat_data.sort_values('cpu_cores')
            # Use index positions for X values (evenly spaced)
            x_values = [instance_to_index.get(inst, 0) for inst in cat_data['instance_type']]
            cores_values = cat_data['cpu_cores'].tolist()
            instance_types = cat_data['instance_type'].tolist() if 'instance_type' in cat_data.columns else []
            memory_values = cat_data['memory_gb'].tolist() if 'memory_gb' in cat_data.columns else []
        else:
            cat_data = cat_data.sort_values('instance_type')
            x_values = list(range(len(cat_data)))
            cores_values = [None] * len(cat_data)
            instance_types = cat_data['instance_type'].tolist()
            memory_values = cat_data['memory_gb'].tolist() if 'memory_gb' in cat_data.columns else []
        
        # Get performance values
        if 'mean_performance' in cat_data.columns:
            perf_values = cat_data['mean_performance'].tolist()
        else:
            continue
        
        # Calculate scaling efficiency as percentage of ideal linear scaling
        if has_cpu_cores and len(cores_values) > 0 and len(perf_values) > 0:
            baseline_perf = perf_values[0]
            baseline_cores = cores_values[0]
            
            if baseline_cores and baseline_cores > 0 and baseline_perf and baseline_perf > 0:
                # Calculate efficiency: (actual / expected) * 100
                # Expected = baseline_perf * (current_cores / baseline_cores)
                efficiency_values = []
                hover_texts = []
                
                for i, (perf, cores) in enumerate(zip(perf_values, cores_values)):
                    if cores and cores > 0:
                        expected_perf = baseline_perf * (cores / baseline_cores)
                        efficiency = (perf / expected_perf) * 100
                        efficiency_values.append(efficiency)
                        
                        # Get instance info for hover
                        inst_name = instance_types[i] if i < len(instance_types) else "Unknown"
                        mem_gb = memory_values[i] if i < len(memory_values) and memory_values[i] else None
                        mem_str = f"<br>Memory: {mem_gb:.0f} GB" if mem_gb else ""
                        
                        # Create detailed hover text
                        hover_texts.append(
                            f"<b>{category}</b><br>"
                            f"Instance: {inst_name}<br>"
                            f"CPU Cores: {int(cores)}{mem_str}<br>"
                            f"Scaling Efficiency: {efficiency:.1f}%<br>"
                            f"Raw Performance: {perf:,.0f}<br>"
                            f"Expected (linear): {expected_perf:,.0f}"
                        )
                    else:
                        efficiency_values.append(None)
                        hover_texts.append("")
                
                y_values = efficiency_values
            else:
                # Fallback to raw values if baseline is invalid
                y_values = perf_values
                hover_texts = [f"{category}: {v:,.0f}" for v in perf_values]
        else:
            # For non-CPU-cores case, normalize to first value = 100%
            if len(perf_values) > 0 and perf_values[0] > 0:
                baseline = perf_values[0]
                y_values = [(v / baseline) * 100 for v in perf_values]
                hover_texts = [
                    f"<b>{category}</b><br>"
                    f"Instance: {inst}<br>"
                    f"Relative Performance: {(v/baseline)*100:.1f}%<br>"
                    f"Raw Value: {v:,.0f}"
                    for inst, v in zip(instance_types, perf_values)
                ]
            else:
                y_values = perf_values
                hover_texts = [f"{category}: {v:,.0f}" for v in perf_values]
        
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode='lines+markers',
            name=category,
            line=dict(width=3),
            marker=dict(size=10),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=hover_texts
        ))
    
    # Add ideal linear scaling reference line at 100%
    if has_cpu_cores and len(instance_to_index) > 0:
        # Span the full width of the categorical axis
        fig.add_trace(go.Scatter(
            x=[0, len(instance_to_index) - 1],
            y=[100, 100],
            mode='lines',
            name='Ideal Linear (100%)',
            line=dict(dash='dash', color='rgba(100, 100, 100, 0.7)', width=2),
            showlegend=True,
            hoverinfo='skip'
        ))
        
        # Add shaded regions for context
        fig.add_hrect(
            y0=85, y1=115,
            fillcolor="rgba(76, 175, 80, 0.1)",
            line_width=0,
            annotation_text="Good scaling (85-115%)",
            annotation_position="top right",
            annotation=dict(font_size=10, font_color="rgba(76, 175, 80, 0.8)")
        )
    
    # Add annotation explaining the metric
    fig.add_annotation(
        text=(
            "<b>How to read this chart:</b><br>"
            "100% = ideal linear scaling<br>"
            ">100% = super-linear (great!)<br>"
            "<100% = diminishing returns"
        ),
        xref="paper", yref="paper",
        x=0.02, y=0.98,
        showarrow=False,
        font=dict(size=10, color="gray"),
        align="left",
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(200, 200, 200, 0.5)",
        borderwidth=1,
        borderpad=4
    )
    
    # Configure evenly-spaced categorical X-axis with instance labels
    if tick_labels:
        fig.update_layout(
            xaxis=dict(
                tickmode='array',
                tickvals=list(range(len(tick_labels))),
                ticktext=tick_labels,
                tickangle=45,
                tickfont=dict(size=9)
            )
        )
    
    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="Scaling Efficiency (% of ideal linear)",
        template='plotly_white',
        height=600,  # Increased height for rotated labels
        hovermode='x unified',
        legend=dict(
            title="Benchmark Category",
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99,
            bgcolor="rgba(255,255,255,0.9)"
        ),
        yaxis=dict(
            ticksuffix="%",
            range=[0, max(150, 120)]  # Ensure we show at least 0-150%
        ),
        margin=dict(b=120)  # Extra bottom margin for rotated labels
    )
    
    return fig


def create_investigation_detail_chart(
    baseline_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    test_name: str,
    baseline_label: str,
    comparison_label: str
) -> go.Figure:
    """
    Create a detailed comparison chart for investigation drill-down.
    
    Args:
        baseline_df: DataFrame with baseline data
        comparison_df: DataFrame with comparison data
        test_name: Name of the test being investigated
        baseline_label: Label for baseline data
        comparison_label: Label for comparison data
        
    Returns:
        Plotly Figure with side-by-side box plots
    """
    fig = go.Figure()
    
    # Baseline box plot
    if not baseline_df.empty and 'primary_metric_value' in baseline_df.columns:
        fig.add_trace(go.Box(
            y=baseline_df['primary_metric_value'],
            name=baseline_label,
            marker_color='lightblue',
            boxmean='sd'
        ))
    
    # Comparison box plot
    if not comparison_df.empty and 'primary_metric_value' in comparison_df.columns:
        fig.add_trace(go.Box(
            y=comparison_df['primary_metric_value'],
            name=comparison_label,
            marker_color='lightcoral',
            boxmean='sd'
        ))
    
    fig.update_layout(
        title=f"Performance Distribution: {test_name}",
        yaxis_title="Performance Metric",
        template='plotly_white',
        height=400,
        showlegend=True
    )
    
    return fig

