"""
RHEL Multi Arch Performance Engineering Dashboard - Redesigned

Main Dash application for visualizing benchmark results with three key analyses:
1. RHEL Regression Analysis: Track version-to-version performance changes
2. Competitive Performance: Compare RHEL against peer operating systems
3. Cloud Scaling: Analyze performance across cloud instance classes
"""

import os
import json
from datetime import datetime
from io import StringIO
from dash import Dash, html, dcc, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
from dotenv import load_dotenv

# Import local modules
from src.opensearch_client import BenchmarkDataSource
from src.data_processing import BenchmarkDataProcessor, load_synthetic_data
from src.components import filters, visualizations
from src.components.summaries import (
    format_regression_summary,
    format_peer_comparison_summary,
    format_scaling_summary,
    get_status_icon,
    summarize_investigation_details,
    format_investigation_summary_text
)
from src.regression_service import RegressionService
from src.components.regression_analyzer_tab import create_regression_analyzer_layout

# Load environment variables
load_dotenv()

# Initialize app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)
app.title = "RHEL Multi Arch Performance Engineering Dashboard"

# Determine data mode
DATA_MODE = os.getenv('DATA_MODE', 'synthetic').lower()

# Initialize data processor
processor = BenchmarkDataProcessor()

# Load initial data
def load_data():
    """Load data based on configured mode."""
    if DATA_MODE == 'opensearch':
        try:
            client = BenchmarkDataSource()
            documents = client.get_all_documents(max_docs=5000)
            print(f"Loaded {len(documents)} documents from OpenSearch")
            return documents
        except Exception as e:
            print(f"Failed to load from OpenSearch: {e}")
            print("Falling back to synthetic data...")
            return load_synthetic_data()
    else:
        return load_synthetic_data()

# Load and process data
print(f"Loading data in {DATA_MODE} mode...")
raw_documents = load_data()
df = processor.documents_to_dataframe(raw_documents)
print(f"Processed {len(df)} records")

# Extract filter options
os_versions = processor.get_unique_values(df, 'os_version')
instance_types = processor.get_unique_values(df, 'instance_type')
test_names = processor.get_unique_values(df, 'test_name')
cloud_providers = processor.get_unique_values(df, 'cloud_provider')
os_distributions = processor.get_unique_values(df, 'os_distribution')
min_date = df['timestamp'].min().strftime('%Y-%m-%d') if len(df) > 0 else '2025-01-01'
max_date = df['timestamp'].max().strftime('%Y-%m-%d') if len(df) > 0 else '2025-12-31'

# Initialize regression service (singleton)
regression_service = RegressionService()

# App Layout
app.layout = dbc.Container([
    # Store for filtered data and analysis results
    dcc.Store(id='filtered-data-store'),
    dcc.Store(id='analysis-results-store'),
    dcc.Store(id='navigation-state', data={'view': 'overview', 'investigation_params': None}),

    # Regression analyzer stores
    dcc.Store(id='ra-comparison-results'),
    dcc.Store(id='ra-chat-history', data=[]),
    dcc.Store(id='ra-run1-params'),
    dcc.Store(id='ra-run2-params'),


    # Header
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H1([
                            html.Span("🔬 ", style={"fontSize": "2rem"}),
                            "RHEL Multi Arch Performance Engineering Dashboard"
                        ], className="mb-2"),
                        html.P(
                            "Benchmark Analysis & Regression Detection",
                            className="text-muted mb-0",
                            style={"fontSize": "1.1rem"}
                        ),
                    ]),
                ], width=7),
                dbc.Col([
                    html.Div([
                        html.Button(
                            id="dark-mode-toggle",
                            className="me-3",
                            style={
                                "border": "none",
                                "background": "transparent",
                                "cursor": "pointer",
                                "padding": "0"
                            },
                            **{"aria-label": "Toggle dark mode"}
                        ),
                        dbc.Badge(
                            f"📊 {len(df):,} Records",
                            color="primary",
                            className="me-2 px-3 py-2",
                            style={"fontSize": "0.9rem"}
                        ),
                        dbc.Badge(
                            f"Mode: {DATA_MODE.upper()}",
                            color="secondary",
                            className="px-3 py-2",
                            style={"fontSize": "0.9rem"}
                        ),
                    ], className="d-flex justify-content-end align-items-center h-100")
                ], width=5)
            ]),
        ], style={
            "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
            "borderRadius": "0.75rem"
        })
    ], id="dashboard-header", className="mb-4 mt-3", style={"border": "none", "boxShadow": "0 4px 12px rgba(0,0,0,0.1)"}),

    # Tab navigation
    dcc.Tabs(
        id='main-tabs',
        value='dashboard',
        children=[
            dcc.Tab(label='Dashboard', value='dashboard'),
            dcc.Tab(label='Regression Analyzer', value='regression-analyzer'),
        ],
        className="mb-3"
    ),

    # Tab content
    html.Div(id='tab-content'),

], fluid=True)


# Tab switching callback
@app.callback(
    Output('tab-content', 'children'),
    Input('main-tabs', 'value')
)
def render_tab_content(tab):
    """Render content based on selected tab."""
    if tab == 'regression-analyzer':
        return create_regression_analyzer_layout()
    else:
        # Dashboard tab - includes date range, filters, and main content
        return html.Div([
            # Date range and filter controls
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("📅 Date Range:", className="fw-bold text-muted small mb-1"),
                            dcc.DatePickerRange(
                                id='header-date-range',
                                start_date=min_date,
                                end_date=max_date,
                                display_format='YYYY-MM-DD',
                                className="mb-2"
                            ),
                        ], width=5),
                        dbc.Col([
                            dbc.Button(
                                [html.I(className="bi bi-sliders me-2"), "Advanced Filters"],
                                id="btn-show-filters",
                                size="md",
                                color="secondary",
                                className="w-100"
                            ),
                        ], width=3, className="d-flex align-items-end")
                    ])
                ])
            ], className="mb-3"),

            # Advanced Filters Collapse
            dbc.Collapse([
                dbc.Card([
                    dbc.CardBody([
                        filters.create_filter_panel(
                            os_versions=os_versions,
                            instance_types=instance_types,
                            test_names=test_names,
                            cloud_providers=cloud_providers,
                            min_date=min_date,
                            max_date=max_date
                        )
                    ])
                ], className="mb-3")
            ], id="collapse-filters", is_open=False),

            # Main Content - switches between overview and investigation
            html.Div(id="main-content")
        ])


# Clientside callback for dark mode toggle
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            // Toggle dark mode class on body
            document.body.classList.toggle('dark-mode');
            
            // Save preference to localStorage
            const isDarkMode = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDarkMode);
        } else {
            // On page load, check localStorage and apply saved preference
            const savedDarkMode = localStorage.getItem('darkMode');
            if (savedDarkMode === 'true') {
                document.body.classList.add('dark-mode');
            }
        }
        return '';
    }
    """,
    Output('dark-mode-toggle', 'data-dummy'),  # Dummy output
    Input('dark-mode-toggle', 'n_clicks')
)


def create_comparison_collapse(comparison_id, title, graph_id, summary_id):
    """Create a collapsible comparison section."""
    return dbc.Card([
        dbc.CardHeader([
            dbc.Button(
                [html.I(className="bi bi-chevron-down me-2"), title],
                id=f"btn-toggle-{comparison_id}",
                color="link",
                className="text-start w-100 text-decoration-none",
                size="sm"
            )
        ], className="p-0"),
        dbc.Collapse([
            dbc.CardBody([
                html.Div(id=summary_id, className="mb-3"),
                dcc.Loading(
                    dcc.Graph(id=graph_id),
                    type="default"
                )
            ])
        ], id=f"collapse-{comparison_id}", is_open=True)
    ], className="mb-2")


def create_overview_layout():
    """
    Create the main dashboard overview with three analysis sections:
    1. RHEL Regression Analysis - version-to-version comparisons
    2. Competitive Performance - RHEL vs peer operating systems
    3. Cloud Scaling - performance across instance sizes
    """
    return html.Div([
        # Section 1: RHEL Regression Analysis (Collapsible)
        dbc.Card([
            dbc.CardHeader([
                dbc.Button(
                    [
                        html.I(id="icon-section-rhel", className="bi bi-chevron-down me-2"),
                        html.Span("📊", style={"fontSize": "1.5rem", "marginRight": "0.75rem"}),
                        html.Span("RHEL Regression Analysis", style={"fontSize": "1.25rem", "fontWeight": "500"})
                    ],
                    id="btn-toggle-section-rhel",
                    color="link",
                    className="text-start w-100 text-decoration-none p-3",
                    style={"color": "#1e3a8a", "fontWeight": "600"}
                )
            ], style={
                "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                "borderBottom": "3px solid #3b82f6",
                "padding": "0"
            }),
            dbc.Collapse([
                dbc.CardBody([
                    html.Div(id='q1-overall-summary', className="mb-3"),
                    # Major Release Comparison (9.X vs 10.X)
                    create_comparison_collapse(
                        "major-release",
                        "Compare Latest Major Releases (9.X vs 10.X)",
                        "q1-major-graph",
                        "q1-major-summary"
                    ),
                    # RHEL 9.X Sequential Comparison
                    create_comparison_collapse(
                        "rhel9-seq",
                        "Compare RHEL 9.X Versions (Sequential)",
                        "q1-rhel9-graph",
                        "q1-rhel9-summary"
                    ),
                    # RHEL 10.X Sequential Comparison
                    create_comparison_collapse(
                        "rhel10-seq",
                        "Compare RHEL 10.X Versions (Sequential)",
                        "q1-rhel10-graph",
                        "q1-rhel10-summary"
                    )
                ])
            ], id="collapse-section-rhel", is_open=True)
        ], className="mb-4", style={
            "borderLeft": "5px solid #1e3a8a",
            "borderRadius": "0.75rem"
        }),
        
        # Section 2: Competitive Performance (Collapsible)
        dbc.Card([
            dbc.CardHeader([
                dbc.Button(
                    [
                        html.I(id="icon-section-competitive", className="bi bi-chevron-down me-2"),
                        html.Span("📈", style={"fontSize": "1.5rem", "marginRight": "0.75rem"}),
                        html.Span("Competitive Performance", style={"fontSize": "1.25rem", "fontWeight": "500"})
                    ],
                    id="btn-toggle-section-competitive",
                    color="link",
                    className="text-start w-100 text-decoration-none p-3",
                    style={"color": "#0e7490", "fontWeight": "600"}
                )
            ], style={
                "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                "borderBottom": "3px solid #3b82f6",
                "padding": "0"
            }),
            dbc.Collapse([
                dbc.CardBody([
                    html.Div([
                        html.P([
                            "Comparing RHEL performance against peer operating systems on the same hardware. ",
                            html.Strong("Showing latest available comparison.", style={"color": "#0e7490"})
                        ], className="text-muted mb-3"),
                        html.Div(id='q2-comparison-selector', className="mb-4"),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dcc.Loading(
                                dcc.Graph(id='q2-comparison'),
                                type="default"
                            )
                        ], width=12)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Div(id='q2-summary', className="mt-3")
                        ])
                    ])
                ])
            ], id="collapse-section-competitive", is_open=True)
        ], className="mb-4", style={
            "borderLeft": "5px solid #06b6d4",
            "borderRadius": "0.75rem"
        }),
        
        # Section 3: Cloud Scaling (Collapsible)
        dbc.Card([
            dbc.CardHeader([
                dbc.Button(
                    [
                        html.I(id="icon-section-cloud", className="bi bi-chevron-down me-2"),
                        html.Span("☁️", style={"fontSize": "1.5rem", "marginRight": "0.75rem"}),
                        html.Span("Cloud Scaling", style={"fontSize": "1.25rem", "fontWeight": "500"})
                    ],
                    id="btn-toggle-section-cloud",
                    color="link",
                    className="text-start w-100 text-decoration-none p-3",
                    style={"color": "#047857", "fontWeight": "600"}
                )
            ], style={
                "background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)",
                "borderBottom": "3px solid #3b82f6",
                "padding": "0"
            }),
            dbc.Collapse([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Cloud Provider:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-cloud-provider',
                                options=[{'label': cp.upper(), 'value': cp} for cp in cloud_providers],
                                value=cloud_providers[0] if cloud_providers else None,
                                clearable=False
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label("Instance Series:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-instance-series',
                                options=[],  # Populated by callback based on cloud provider and available data
                                value=None,
                                placeholder="Select instance series...",
                                clearable=True
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label("OS:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-os-distribution',
                                options=[],  # Populated by callback based on available data
                                value=None,
                                placeholder="Select OS...",
                                clearable=False
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label("OS Version:", className="fw-bold small"),
                            dcc.Dropdown(
                                id='q3-os-version',
                                options=[],  # Populated by callback based on OS distribution and available data
                                value=None,
                                placeholder="Select version...",
                                clearable=False
                            )
                        ], width=3)
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dcc.Loading(
                                dcc.Graph(id='q3-scaling'),
                                type="default"
                            )
                        ], width=12)
                    ]),
                    dbc.Row([
                        dbc.Col([
                            html.Div(id='q3-summary', className="mt-3")
                        ])
                    ])
                ])
            ], id="collapse-section-cloud", is_open=True)
        ], className="mb-4", style={
            "borderLeft": "5px solid #10b981",
            "borderRadius": "0.75rem"
        }),
        
        # Quick Links to Detailed Views
        dbc.Card([
            dbc.CardBody([
                html.H5("Detailed Analysis", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            "View All Benchmarks →",
                            id="btn-view-benchmarks",
                            color="primary",
                            outline=True,
                            className="w-100"
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Button(
                            "Compare Configurations →",
                            id="btn-view-comparisons",
                            color="primary",
                            outline=True,
                            className="w-100"
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Button(
                            "View Detailed Table →",
                            id="btn-view-table",
                            color="primary",
                            outline=True,
                            className="w-100"
                        )
                    ], width=4)
                ])
            ])
        ])
    ])


def create_investigation_layout(test_name, baseline_version, comparison_version, os_distribution='rhel'):
    """Create the investigation drill-down layout."""
    return html.Div([
        # Breadcrumb / Back button
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "← Back to Overview",
                    id="btn-back-to-overview",
                    color="link",
                    size="sm"
                ),
                html.H3(f"Investigating: {test_name}", className="mt-2"),
                html.P(f"OS: {os_distribution.upper()} | Comparing {baseline_version} → {comparison_version}", 
                       className="text-muted")
            ])
        ], className="mb-3"),
        
        # Investigation content
        dbc.Card([
            dbc.CardBody([
                html.Div(id='investigation-summary', className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            dcc.Graph(id='investigation-comparison-chart'),
                            type="default"
                        )
                    ], width=6),
                    dbc.Col([
                        dcc.Loading(
                            dcc.Graph(id='investigation-timeline-chart'),
                            type="default"
                        )
                    ], width=6)
                ]),
                html.Hr(),
                html.H5("Test Run Details", className="mt-3 mb-3"),
                dcc.Loading(
                    html.Div(id='investigation-table'),
                    type="default"
                )
            ])
        ])
    ])


# Callbacks

@app.callback(
    Output('collapse-filters', 'is_open'),
    Input('btn-show-filters', 'n_clicks'),
    State('collapse-filters', 'is_open'),
    prevent_initial_call=True
)
def toggle_filters(n_clicks, is_open):
    """Toggle advanced filters panel."""
    return not is_open


# Callbacks for major section toggles
@app.callback(
    [Output('collapse-section-rhel', 'is_open'),
     Output('icon-section-rhel', 'className')],
    Input('btn-toggle-section-rhel', 'n_clicks'),
    State('collapse-section-rhel', 'is_open'),
    prevent_initial_call=True
)
def toggle_section_rhel(n_clicks, is_open):
    """Toggle RHEL Regression Analysis section."""
    new_state = not is_open
    icon_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"
    return new_state, icon_class


@app.callback(
    [Output('collapse-section-competitive', 'is_open'),
     Output('icon-section-competitive', 'className')],
    Input('btn-toggle-section-competitive', 'n_clicks'),
    State('collapse-section-competitive', 'is_open'),
    prevent_initial_call=True
)
def toggle_section_competitive(n_clicks, is_open):
    """Toggle Competitive Performance section."""
    new_state = not is_open
    icon_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"
    return new_state, icon_class


@app.callback(
    [Output('collapse-section-cloud', 'is_open'),
     Output('icon-section-cloud', 'className')],
    Input('btn-toggle-section-cloud', 'n_clicks'),
    State('collapse-section-cloud', 'is_open'),
    prevent_initial_call=True
)
def toggle_section_cloud(n_clicks, is_open):
    """Toggle Cloud Scaling section."""
    new_state = not is_open
    icon_class = "bi bi-chevron-down me-2" if new_state else "bi bi-chevron-right me-2"
    return new_state, icon_class


# Callbacks for subsection toggles within RHEL Regression Analysis
@app.callback(
    Output('collapse-major-release', 'is_open'),
    Input('btn-toggle-major-release', 'n_clicks'),
    State('collapse-major-release', 'is_open'),
    prevent_initial_call=True
)
def toggle_major_release(n_clicks, is_open):
    """Toggle major release comparison."""
    return not is_open


@app.callback(
    Output('collapse-rhel9-seq', 'is_open'),
    Input('btn-toggle-rhel9-seq', 'n_clicks'),
    State('collapse-rhel9-seq', 'is_open'),
    prevent_initial_call=True
)
def toggle_rhel9_seq(n_clicks, is_open):
    """Toggle RHEL 9 sequential comparison."""
    return not is_open


@app.callback(
    Output('collapse-rhel10-seq', 'is_open'),
    Input('btn-toggle-rhel10-seq', 'n_clicks'),
    State('collapse-rhel10-seq', 'is_open'),
    prevent_initial_call=True
)
def toggle_rhel10_seq(n_clicks, is_open):
    """Toggle RHEL 10 sequential comparison."""
    return not is_open


@app.callback(
    Output('filtered-data-store', 'data'),
    [
        Input('filter-os-version', 'value'),
        Input('filter-instance-type', 'value'),
        Input('filter-test-name', 'value'),
        Input('filter-cloud-provider', 'value'),
        Input('header-date-range', 'start_date'),
        Input('header-date-range', 'end_date'),
        Input('filter-status', 'value'),
    ]
)
def update_filtered_data(os_vers, inst_types, tests, clouds, start_date, end_date, statuses):
    """Update the filtered dataset based on filter selections."""
    
    # Convert date strings to timezone-aware datetime objects
    date_range_param = None
    if start_date and end_date:
        from datetime import timezone, timedelta
        start_dt = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        # Set end_dt to end of day (23:59:59) to include all records on that date
        end_dt = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
        date_range_param = (start_dt, end_dt)
    
    filtered_df = processor.filter_data(
        df,
        os_versions=os_vers if os_vers else None,
        instance_types=inst_types if inst_types else None,
        test_names=tests if tests else None,
        cloud_providers=clouds if clouds else None,
        date_range=date_range_param,
        status_filter=statuses if statuses else None
    )
    
    # Convert to JSON-serializable format
    return filtered_df.to_json(date_format='iso', orient='split')


@app.callback(
    Output('analysis-results-store', 'data'),
    Input('filtered-data-store', 'data')
)
def analyze_filtered_data(filtered_data_json):
    """Perform all three analyses on filtered data."""
    import pandas as pd
    
    if not filtered_data_json:
        return {}
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    if filtered_df.empty:
        return {}
    
    # Run all three analyses
    results = {}
    
    # Section 1: RHEL Regression Analysis
    try:
        results['q1'] = processor.analyze_rhel_simplified_regressions(filtered_df)
    except Exception as e:
        print(f"Error in RHEL Regression analysis: {e}")
        results['q1'] = {
            'summary': 'Analysis error', 
            'major_release_comparison': None,
            'rhel9_sequential': None,
            'rhel10_sequential': None,
            'total_regressions': 0
        }
    
    # Section 2: Competitive Performance (computed on-demand per user selection)
    # Just store a placeholder since we'll compute this when user selects a comparison
    results['q2'] = {'computed': 'on_demand'}
    
    # Section 3: Cloud Scaling (will be done dynamically based on user selection)
    results['q3'] = {}
    
    # Serialize DataFrames to JSON
    # Q1 simplified comparisons
    for comp_key in ['major_release_comparison', 'rhel9_sequential', 'rhel10_sequential']:
        if comp_key in results['q1'] and results['q1'][comp_key]:
            comp = results['q1'][comp_key]
            if 'comparison_data' in comp and isinstance(comp['comparison_data'], pd.DataFrame):
                comp['comparison_data'] = comp['comparison_data'].to_json(orient='split')
    
    # Q2 is computed on-demand, no serialization needed
    
    return json.dumps(results)


@app.callback(
    Output('q1-overall-summary', 'children'),
    Input('analysis-results-store', 'data')
)
def update_q1_overall_summary(analysis_json):
    """Update overall Q1 summary."""
    import pandas as pd
    
    if not analysis_json:
        return "Analyzing..."
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    
    total_regressions = q1_data.get('total_regressions', 0)
    summary_text = q1_data.get('summary', 'No data available')
    icon = get_status_icon(total_regressions)
    
    return dbc.Alert([
        html.H5([icon, " Overall Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color="warning" if total_regressions > 0 else "success")


@app.callback(
    [Output('q1-major-graph', 'figure'),
     Output('q1-major-summary', 'children')],
    Input('analysis-results-store', 'data')
)
def update_major_release_comparison(analysis_json):
    """Update major release comparison (9.X vs 10.X)."""
    import pandas as pd
    
    if not analysis_json:
        return visualizations.create_empty_figure("Loading..."), ""
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    comp_data = q1_data.get('major_release_comparison')
    
    if not comp_data:
        return visualizations.create_empty_figure("No data available for this comparison"), dbc.Alert("No data available", color="info")
    
    # Recreate DataFrame from JSON
    if comp_data.get('comparison_data'):
        comparison_df = pd.read_json(StringIO(comp_data['comparison_data']), orient='split')
        fig = visualizations.create_version_comparison_bar_chart(
            comparison_df,
            comp_data['baseline_version'],
            comp_data['comparison_version']
        )
    else:
        fig = visualizations.create_empty_figure("No data available")
    
    # Format summary with hardware information
    num_regressions = comp_data.get('num_regressions', 0)
    num_comparisons = comp_data.get('num_comparisons', 0)
    summary_text = comp_data.get('summary', 'No analysis available')
    hw_summary = comp_data.get('hardware_summary', '')
    icon = get_status_icon(num_regressions)
    
    summary_component = dbc.Alert([
        html.Strong([icon, f" {num_regressions} regression(s) detected"]),
        html.Br(),
        html.Small(f"{num_comparisons} test×hardware comparison(s) | {hw_summary}", className="text-muted"),
        html.Hr(className="my-2"),
        dcc.Markdown(summary_text)
    ], color="warning" if num_regressions > 0 else "success")
    
    return fig, summary_component


@app.callback(
    [Output('q1-rhel9-graph', 'figure'),
     Output('q1-rhel9-summary', 'children')],
    Input('analysis-results-store', 'data')
)
def update_rhel9_sequential(analysis_json):
    """Update RHEL 9 sequential comparison."""
    import pandas as pd
    
    if not analysis_json:
        return visualizations.create_empty_figure("Loading..."), ""
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    comp_data = q1_data.get('rhel9_sequential')
    
    if not comp_data:
        return visualizations.create_empty_figure("No data available for this comparison"), dbc.Alert("No data available", color="info")
    
    # Recreate DataFrame from JSON
    if comp_data.get('comparison_data'):
        comparison_df = pd.read_json(StringIO(comp_data['comparison_data']), orient='split')
        fig = visualizations.create_version_comparison_bar_chart(
            comparison_df,
            comp_data['baseline_version'],
            comp_data['comparison_version']
        )
    else:
        fig = visualizations.create_empty_figure("No data available")
    
    # Format summary with hardware information
    num_regressions = comp_data.get('num_regressions', 0)
    num_comparisons = comp_data.get('num_comparisons', 0)
    summary_text = comp_data.get('summary', 'No analysis available')
    hw_summary = comp_data.get('hardware_summary', '')
    icon = get_status_icon(num_regressions)
    
    summary_component = dbc.Alert([
        html.Strong([icon, f" {num_regressions} regression(s) detected"]),
        html.Br(),
        html.Small(f"{num_comparisons} test×hardware comparison(s) | {hw_summary}", className="text-muted"),
        html.Hr(className="my-2"),
        dcc.Markdown(summary_text)
    ], color="warning" if num_regressions > 0 else "success")
    
    return fig, summary_component


@app.callback(
    [Output('q1-rhel10-graph', 'figure'),
     Output('q1-rhel10-summary', 'children')],
    Input('analysis-results-store', 'data')
)
def update_rhel10_sequential(analysis_json):
    """Update RHEL 10 sequential comparison."""
    import pandas as pd
    
    if not analysis_json:
        return visualizations.create_empty_figure("Loading..."), ""
    
    analysis = json.loads(analysis_json)
    q1_data = analysis.get('q1', {})
    comp_data = q1_data.get('rhel10_sequential')
    
    if not comp_data:
        return visualizations.create_empty_figure("No data available for this comparison"), dbc.Alert("No data available", color="info")
    
    # Recreate DataFrame from JSON
    if comp_data.get('comparison_data'):
        comparison_df = pd.read_json(StringIO(comp_data['comparison_data']), orient='split')
        fig = visualizations.create_version_comparison_bar_chart(
            comparison_df,
            comp_data['baseline_version'],
            comp_data['comparison_version']
        )
    else:
        fig = visualizations.create_empty_figure("No data available")
    
    # Format summary with hardware information
    num_regressions = comp_data.get('num_regressions', 0)
    num_comparisons = comp_data.get('num_comparisons', 0)
    summary_text = comp_data.get('summary', 'No analysis available')
    hw_summary = comp_data.get('hardware_summary', '')
    icon = get_status_icon(num_regressions)
    
    summary_component = dbc.Alert([
        html.Strong([icon, f" {num_regressions} regression(s) detected"]),
        html.Br(),
        html.Small(f"{num_comparisons} test×hardware comparison(s) | {hw_summary}", className="text-muted"),
        html.Hr(className="my-2"),
        dcc.Markdown(summary_text)
    ], color="warning" if num_regressions > 0 else "success")
    
    return fig, summary_component


@app.callback(
    Output('q2-comparison-selector', 'children'),
    Input('filtered-data-store', 'data')
)
def update_q2_comparison_selector(filtered_data_json):
    """Display the latest competitive comparison info (no selection needed)."""
    import pandas as pd
    
    if not filtered_data_json:
        return html.Div("Loading comparison...", className="text-muted")
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Get available comparisons
    available_comparisons = processor._get_available_comparisons(filtered_df, 'rhel')
    
    if not available_comparisons:
        return dbc.Alert([
            html.Strong("⚠️ No competitive comparisons available"),
            html.Br(),
            html.Small("Competitive comparisons require both RHEL and peer OS data on the same hardware.", 
                      className="text-muted")
        ], color="warning")
    
    # Use the latest comparison (first in the sorted list)
    latest_comp = available_comparisons[0]
    
    return html.Div([
        dbc.Badge("Latest", color="info", className="me-2"),
        html.Strong(latest_comp['label'], style={"color": "#0e7490"})
    ], className="mb-2 d-flex align-items-center")


@app.callback(
    [Output('q2-comparison', 'figure'),
     Output('q2-summary', 'children')],
    Input('filtered-data-store', 'data')
)
def update_question2(filtered_data_json):
    """Update Competitive Performance section with the latest comparison."""
    import pandas as pd
    
    if not filtered_data_json:
        empty_fig = visualizations.create_empty_figure("Loading comparison data...")
        return empty_fig, ""
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Get available comparisons and use the latest one
    available_comparisons = processor._get_available_comparisons(filtered_df, 'rhel')
    
    if not available_comparisons:
        empty_fig = visualizations.create_empty_figure("No competitive comparisons available")
        return empty_fig, dbc.Alert([
            html.Strong("⚠️ No competitive comparisons available"),
            html.Br(),
            html.Small("Competitive comparisons require both RHEL and peer OS data on the same hardware.", 
                      className="text-muted")
        ], color="warning")
    
    # Use the latest comparison (first in the sorted list)
    comp_config = available_comparisons[0]
    
    # Run targeted competitive analysis
    q2_result = processor.analyze_peer_os_comparison(
        filtered_df,
        baseline_os='rhel',
        peer_os_list=[comp_config['peer_os']],
        baseline_version=comp_config['baseline_version'],
        peer_version=comp_config['peer_version'],
        cloud_provider=comp_config['cloud_provider'],
        instance_type=None  # Don't filter to single HW, show all common HW
    )
    
    # Create visualization
    if not q2_result['comparison_data'].empty:
        comparison_df = q2_result['comparison_data']
        fig = visualizations.create_peer_os_comparison_chart(
            comparison_df, 
            baseline_os="RHEL",
            title=f"Performance Comparison: {comp_config['label']}"
        )
    else:
        fig = visualizations.create_empty_figure("No comparison data available for selected configuration")
    
    # Format summary
    summary_text = q2_result.get('summary', 'No summary available')
    competitive_count = q2_result.get('competitive_count', 0)
    total_benchmarks = q2_result.get('total_benchmarks', 0)
    
    # Determine status based on data availability and competitiveness
    if total_benchmarks == 0:
        # No data available - show warning status
        status_icon = "⚠️"
        alert_color = "warning"
    else:
        # Data available - check competitiveness
        is_competitive = competitive_count >= (total_benchmarks * 0.7)
        status_icon = get_status_icon(0 if is_competitive else 3)
        alert_color = "success" if is_competitive else "info"
    
    summary_component = dbc.Alert([
        html.H5([status_icon, " Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color=alert_color)
    
    return fig, summary_component


def extract_instance_series(instance_type: str, cloud_provider: str) -> str:
    """
    Extract the instance series/family from a full instance type name.
    
    Examples:
        - AWS: "m5.24xlarge" -> "m5"
        - Azure: "Standard_D96s_v3" -> "Standard_Ds_v3"
        - GCP: "c4-standard-96" -> "c4-standard"
    """
    import re
    
    if not instance_type:
        return instance_type
    
    if cloud_provider == 'aws':
        # AWS format: m5.24xlarge -> m5
        # Split on dot and take the first part (family)
        return instance_type.split('.')[0]
    
    elif cloud_provider == 'azure':
        # Azure format: Standard_D96s_v3 -> Standard_Ds_v3
        # Remove the numeric size portion but keep the series letter and version
        match = re.match(r'(Standard_[A-Z])(\d+)(s?)(_v\d+)?', instance_type)
        if match:
            prefix, _, s_suffix, version = match.groups()
            return f"{prefix}{s_suffix or ''}{version or ''}"
        return instance_type
    
    elif cloud_provider == 'gcp':
        # GCP format: c4-standard-96 -> c4-standard
        # Remove the trailing number (vCPU count)
        parts = instance_type.rsplit('-', 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
        return instance_type
    
    return instance_type


# Cascading dropdown callbacks for Cloud Scaling section
@app.callback(
    [Output('q3-instance-series', 'options'),
     Output('q3-instance-series', 'value')],
    [Input('q3-cloud-provider', 'value'),
     Input('filtered-data-store', 'data')],
    [State('q3-instance-series', 'value')]
)
def update_instance_series_options(cloud_provider, filtered_data_json, current_value):
    """Update instance series dropdown options based on selected cloud provider and available data."""
    import pandas as pd
    
    if not cloud_provider or not filtered_data_json:
        return [], None
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Filter to selected cloud provider and get available instance types
    cloud_df = filtered_df[filtered_df['cloud_provider'] == cloud_provider]
    instance_types = cloud_df['instance_type'].dropna().unique().tolist()
    
    if not instance_types:
        return [], None
    
    # Extract unique instance series from instance types
    instance_series = set()
    for it in instance_types:
        series = extract_instance_series(it, cloud_provider)
        if series:
            instance_series.add(series)
    
    instance_series = sorted(instance_series)
    
    if not instance_series:
        return [], None
    
    options = [{'label': series, 'value': series} for series in instance_series]
    
    # Keep current value if still valid, otherwise default to first
    if current_value in instance_series:
        default_value = current_value
    else:
        default_value = instance_series[0]
    
    return options, default_value


@app.callback(
    [Output('q3-os-version', 'options'),
     Output('q3-os-version', 'value')],
    [Input('q3-os-distribution', 'value'),
     Input('q3-cloud-provider', 'value'),
     Input('q3-instance-series', 'value'),
     Input('filtered-data-store', 'data')],
    [State('q3-os-version', 'value')]
)
def update_os_version_options(os_distribution, cloud_provider, instance_series, filtered_data_json, current_value):
    """Update OS version dropdown options based on selected OS and available data."""
    import pandas as pd
    
    if not os_distribution or not filtered_data_json:
        return [], None
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Apply filters to find what OS versions have data for the current selection
    os_df = filtered_df[filtered_df['os_distribution'] == os_distribution]
    
    if cloud_provider:
        os_df = os_df[os_df['cloud_provider'] == cloud_provider]
    
    if instance_series:
        # Filter by instance series (match instances that start with the series prefix)
        os_df = os_df[os_df['instance_type'].apply(
            lambda x: extract_instance_series(x, cloud_provider) == instance_series if pd.notna(x) else False
        )]
    
    versions = sorted(os_df['os_version'].dropna().unique().tolist())
    
    if not versions:
        return [], None
    
    options = [{'label': v, 'value': v} for v in versions]
    
    # Keep current value if still valid, otherwise default to latest (last in sorted list)
    if current_value in versions:
        default_value = current_value
    else:
        default_value = versions[-1]
    
    return options, default_value


@app.callback(
    [Output('q3-os-distribution', 'options'),
     Output('q3-os-distribution', 'value')],
    [Input('q3-cloud-provider', 'value'),
     Input('q3-instance-series', 'value'),
     Input('filtered-data-store', 'data')],
    [State('q3-os-distribution', 'value')]
)
def update_os_distribution_options(cloud_provider, instance_series, filtered_data_json, current_value):
    """Update OS distribution dropdown options based on available data."""
    import pandas as pd
    
    if not filtered_data_json:
        return [], None
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Apply filters to find what OS distributions have data
    if cloud_provider:
        filtered_df = filtered_df[filtered_df['cloud_provider'] == cloud_provider]
    
    if instance_series:
        # Filter by instance series (match instances that belong to this series)
        filtered_df = filtered_df[filtered_df['instance_type'].apply(
            lambda x: extract_instance_series(x, cloud_provider) == instance_series if pd.notna(x) else False
        )]
    
    distributions = sorted(filtered_df['os_distribution'].dropna().unique().tolist())
    
    if not distributions:
        return [], None
    
    options = [{'label': dist.upper(), 'value': dist} for dist in distributions]
    
    # Keep current value if still valid, otherwise default to first
    if current_value in distributions:
        default_value = current_value
    else:
        default_value = distributions[0]
    
    return options, default_value


@app.callback(
    [Output('q3-scaling', 'figure'),
     Output('q3-summary', 'children')],
    [Input('q3-cloud-provider', 'value'),
     Input('q3-instance-series', 'value'),
     Input('q3-os-distribution', 'value'),
     Input('q3-os-version', 'value'),
     Input('filtered-data-store', 'data')]
)
def update_question3(cloud_provider, instance_series, os_distribution, os_version, filtered_data_json):
    """Update Cloud Scaling section visualizations."""
    import pandas as pd
    
    if not filtered_data_json or not cloud_provider or not os_version:
        empty_fig = visualizations.create_empty_figure("Select cloud provider and OS version")
        return empty_fig, ""
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Apply additional filters for OS distribution and instance series
    if os_distribution:
        filtered_df = filtered_df[filtered_df['os_distribution'] == os_distribution]
    
    if instance_series:
        # Filter by instance series (match instances that belong to this series)
        filtered_df = filtered_df[filtered_df['instance_type'].apply(
            lambda x: extract_instance_series(x, cloud_provider) == instance_series if pd.notna(x) else False
        )]
    
    # Run scaling analysis
    q3_result = processor.analyze_cloud_scaling(
        filtered_df,
        cloud_provider=cloud_provider,
        os_version=os_version
    )
    
    # Create visualization
    if not q3_result['scaling_data'].empty:
        # Build descriptive title
        title_parts = [f"Performance Scaling: {os_distribution.upper()} {os_version}"]
        title_parts.append(f"on {cloud_provider.upper()}")
        if instance_series:
            title_parts.append(f"({instance_series})")
        chart_title = " ".join(title_parts)
        
        fig = visualizations.create_cloud_scaling_chart(
            q3_result['scaling_data'],
            title=chart_title
        )
    else:
        fig = visualizations.create_empty_figure("No scaling data available for selected configuration")
    
    # Format summary
    summary_text = format_scaling_summary(q3_result)
    linear_count = q3_result.get('linear_scaling_count', 0)
    total = q3_result.get('total_benchmarks', 0)
    
    # Determine status based on data availability and scaling quality
    if total == 0:
        # No data available - show warning status
        status_icon = "⚠️"
        alert_color = "warning"
    else:
        # Data available - check scaling quality
        good_scaling = linear_count >= (total * 0.7)
        status_icon = get_status_icon(0 if good_scaling else 2)
        alert_color = "success" if good_scaling else "info"
    
    summary_component = dbc.Alert([
        html.H5([status_icon, " Summary"], className="mb-2"),
        dcc.Markdown(summary_text)
    ], color=alert_color)
    
    return fig, summary_component


@app.callback(
    Output('main-content', 'children'),
    Input('navigation-state', 'data')
)
def render_main_content(nav_state):
    """Render main content based on navigation state."""
    if not nav_state or nav_state['view'] == 'overview':
        return create_overview_layout()
    elif nav_state['view'] == 'investigation':
        params = nav_state.get('investigation_params', {})
        return create_investigation_layout(
            test_name=params.get('test_name', 'Unknown'),
            baseline_version=params.get('baseline_version', 'N/A'),
            comparison_version=params.get('comparison_version', 'N/A'),
            os_distribution=params.get('os_distribution', 'rhel')
        )
    else:
        return create_overview_layout()


@app.callback(
    Output('navigation-state', 'data'),
    [Input('q1-major-graph', 'clickData'),
     Input('q1-rhel9-graph', 'clickData'),
     Input('q1-rhel10-graph', 'clickData'),
     Input('btn-view-benchmarks', 'n_clicks'),
     Input('btn-view-comparisons', 'n_clicks'),
     Input('btn-view-table', 'n_clicks')],
    [State('navigation-state', 'data'),
     State('analysis-results-store', 'data')],
    prevent_initial_call=True
)
def handle_navigation(major_click, rhel9_click, rhel10_click, benchmarks_click, comparisons_click, table_click, current_nav, analysis_json):
    """Handle navigation between views."""
    from dash import ctx
    
    if not ctx.triggered:
        return current_nav
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Bar chart click - drill into investigation
    if trigger_id in ['q1-major-graph', 'q1-rhel9-graph', 'q1-rhel10-graph']:
        click_data = None
        comp_key = None
        
        if trigger_id == 'q1-major-graph' and major_click:
            click_data = major_click
            comp_key = 'major_release_comparison'
        elif trigger_id == 'q1-rhel9-graph' and rhel9_click:
            click_data = rhel9_click
            comp_key = 'rhel9_sequential'
        elif trigger_id == 'q1-rhel10-graph' and rhel10_click:
            click_data = rhel10_click
            comp_key = 'rhel10_sequential'
        
        if click_data and analysis_json:
            try:
                analysis = json.loads(analysis_json)
                q1_data = analysis.get('q1', {})
                comp_data = q1_data.get(comp_key)
                
                if comp_data:
                    point = click_data['points'][0]
                    test_name = point.get('y', 'Unknown')
                    
                    return {
                        'view': 'investigation',
                        'investigation_params': {
                            'test_name': test_name,
                            'baseline_version': comp_data['baseline_version'],
                            'comparison_version': comp_data['comparison_version'],
                            'os_distribution': 'rhel'
                        }
                    }
            except Exception as e:
                print(f"Error parsing bar chart click: {e}")
                return current_nav
    
    # Other navigation buttons - stay on overview for now (future: navigate to specific tabs)
    return current_nav


@app.callback(
    Output('navigation-state', 'data', allow_duplicate=True),
    Input('btn-back-to-overview', 'n_clicks'),
    prevent_initial_call=True
)
def handle_back_to_overview(n_clicks):
    """Handle back to overview navigation."""
    return {'view': 'overview', 'investigation_params': None}


@app.callback(
    [Output('investigation-summary', 'children'),
     Output('investigation-comparison-chart', 'figure'),
     Output('investigation-timeline-chart', 'figure'),
     Output('investigation-table', 'children')],
    [Input('navigation-state', 'data'),
     Input('filtered-data-store', 'data')],
    prevent_initial_call=True
)
def update_investigation_view(nav_state, filtered_data_json):
    """Update investigation drill-down view."""
    import pandas as pd
    
    if not nav_state or nav_state['view'] != 'investigation' or not filtered_data_json:
        empty_fig = visualizations.create_empty_figure("No investigation data")
        return "", empty_fig, empty_fig, ""
    
    params = nav_state.get('investigation_params', {})
    test_name = params.get('test_name', 'Unknown')
    baseline_version = params.get('baseline_version', 'N/A')
    comparison_version = params.get('comparison_version', 'N/A')
    os_distribution = params.get('os_distribution', 'rhel')
    
    filtered_df = pd.read_json(StringIO(filtered_data_json), orient='split')
    
    # Filter data for this specific test and OS distribution
    test_df = filtered_df[
        (filtered_df['test_name'] == test_name) & 
        (filtered_df['os_distribution'].str.lower() == os_distribution.lower())
    ]
    
    if test_df.empty:
        empty_fig = visualizations.create_empty_figure(f"No data for {test_name}")
        summary = dbc.Alert("No data available for this test", color="warning")
        return summary, empty_fig, empty_fig, ""
    
    # Split into baseline and comparison
    baseline_df = test_df[test_df['os_version'] == baseline_version]
    comparison_df = test_df[test_df['os_version'] == comparison_version]
    
    # Generate summary
    summary_data = summarize_investigation_details(
        baseline_df, comparison_df, test_name, baseline_version, comparison_version
    )
    
    summary_text = format_investigation_summary_text(summary_data)
    
    # Determine alert color based on status
    alert_color = summary_data.get('status', 'info')
    status_icon = get_status_icon(1 if summary_data.get('is_regression', False) else 0)
    
    summary_component = dbc.Alert([
        html.H4([status_icon, f" {summary_data.get('status_text', 'Analysis')}"], className="mb-3"),
        dcc.Markdown(summary_text)
    ], color=alert_color)
    
    # Create comparison chart
    comparison_fig = visualizations.create_investigation_detail_chart(
        baseline_df, comparison_df, test_name, baseline_version, comparison_version
    )
    
    # Create timeline chart
    timeline_fig = visualizations.create_time_series_chart(
        test_df,
        x_col='timestamp',
        y_col='primary_metric_value',
        color_col='os_version',
        title=f"Performance Trend: {test_name}",
        use_facets=False
    )
    
    # Create detailed table
    table_df = test_df[[
        'timestamp', 'os_version', 'instance_type', 'cloud_provider',
        'primary_metric_value', 'primary_metric_unit', 'status'
    ]].sort_values('timestamp', ascending=False).head(50)
    
    table_fig = visualizations.create_metrics_table(
        table_df,
        title=f"Recent Test Runs (showing {len(table_df)} of {len(test_df)} total)"
    )
    
    table_component = dcc.Graph(figure=table_fig)
    
    return summary_component, comparison_fig, timeline_fig, table_component


@app.callback(
    [Output('filter-os-version', 'value'),
     Output('filter-instance-type', 'value'),
     Output('filter-test-name', 'value'),
     Output('filter-cloud-provider', 'value'),
     Output('filter-status', 'value')],
    Input('btn-reset-filters', 'n_clicks'),
    prevent_initial_call=True
)
def reset_filters(n_clicks):
    """Reset all filters to default values."""
    return os_versions, instance_types, test_names, cloud_providers, ['PASS', 'FAIL', 'UNKNOWN']


# ===================================================================
# Regression Analyzer Callbacks
# ===================================================================

# Field mapping for cascading dropdowns
RA_FIELD_MAP = {
    'cloud': 'metadata.cloud_provider',
    'os-vendor': 'metadata.os_vendor',
    'os-version': 'system_under_test.operating_system.version',
    'instance': 'metadata.instance_type',
    'benchmark': 'test.name',
}

# Ordered list of cascade fields
RA_CASCADE_ORDER = ['cloud', 'os-vendor', 'os-version', 'instance', 'benchmark']


def register_cascade_callbacks(app, run_prefix):
    """Register cascading dropdown callbacks for a run selector.

    Args:
        app: Dash app instance
        run_prefix: 'ra-r1' or 'ra-r2'
    """
    for i, field in enumerate(RA_CASCADE_ORDER):
        if i == 0:
            # Cloud dropdown is populated by the initial load callback, skip
            continue

        # Parent fields are all fields before the current one
        parent_fields = RA_CASCADE_ORDER[:i]
        parent_ids = [f'{run_prefix}-{pf}' for pf in parent_fields]

        # Use a closure to capture the loop variables
        def make_callback(field_key, parent_field_keys, parent_input_ids, prefix):
            @app.callback(
                [Output(f'{prefix}-{field_key}', 'options'),
                 Output(f'{prefix}-{field_key}', 'value')],
                [Input(f'{pid}', 'value') for pid in parent_input_ids],
                prevent_initial_call=True
            )
            def update_dropdown(*parent_values):
                # Check all parents have values
                if not all(parent_values):
                    return [], None

                # Build filters from parent selections
                filter_dict = {}
                for pf, pv in zip(parent_field_keys, parent_values):
                    filter_dict[RA_FIELD_MAP[pf]] = pv

                os_field = RA_FIELD_MAP[field_key]
                options = regression_service.get_dropdown_options(os_field, filter_dict)
                return options, None

        make_callback(field, parent_fields, parent_ids, run_prefix)


# Register cascade callbacks for both runs
register_cascade_callbacks(app, 'ra-r1')
register_cascade_callbacks(app, 'ra-r2')


@app.callback(
    [Output('ra-r1-cloud', 'options'),
     Output('ra-r2-cloud', 'options')],
    Input('ra-init-trigger', 'n_intervals'),
    prevent_initial_call=True
)
def load_initial_cloud_options(n_intervals):
    """Load cloud provider options once the regression analyzer layout is rendered."""
    options = regression_service.get_dropdown_options('metadata.cloud_provider')
    return options, options


@app.callback(
    [Output('ra-comparison-results', 'data'),
     Output('ra-chat-history', 'data', allow_duplicate=True)],
    Input('ra-btn-compare', 'n_clicks'),
    [State('ra-r1-cloud', 'value'),
     State('ra-r1-os-vendor', 'value'),
     State('ra-r1-os-version', 'value'),
     State('ra-r1-instance', 'value'),
     State('ra-r1-benchmark', 'value'),
     State('ra-r2-cloud', 'value'),
     State('ra-r2-os-vendor', 'value'),
     State('ra-r2-os-version', 'value'),
     State('ra-r2-instance', 'value'),
     State('ra-r2-benchmark', 'value'),
     State('ra-detail-level', 'value')],
    prevent_initial_call=True
)
def compare_runs(n_clicks, r1_cloud, r1_os_vendor, r1_os_version, r1_instance, r1_benchmark,
                 r2_cloud, r2_os_vendor, r2_os_version, r2_instance, r2_benchmark, detail_level):
    """Run comparison when button is clicked."""
    # Validate all fields are filled
    r1_vals = [r1_cloud, r1_os_vendor, r1_os_version, r1_instance, r1_benchmark]
    r2_vals = [r2_cloud, r2_os_vendor, r2_os_version, r2_instance, r2_benchmark]

    if not all(r1_vals) or not all(r2_vals):
        return {'error': 'Please select all fields for both Run 1 and Run 2.'}, []

    run1_params = {
        'cloud': r1_cloud,
        'os_vendor': r1_os_vendor,
        'os_version': r1_os_version,
        'instance': r1_instance,
        'benchmark': r1_benchmark,
    }
    run2_params = {
        'cloud': r2_cloud,
        'os_vendor': r2_os_vendor,
        'os_version': r2_os_version,
        'instance': r2_instance,
        'benchmark': r2_benchmark,
    }

    result = regression_service.run_comparison(run1_params, run2_params, detail_level or 'medium')
    return result, []  # Clear chat history on new comparison


@app.callback(
    Output('ra-results-container', 'children'),
    Input('ra-comparison-results', 'data')
)
def display_results(comparison_data):
    """Render comparison results."""
    if not comparison_data:
        return html.Div("Select runs and click 'Compare Runs' to begin.", className="text-muted p-4 text-center")

    if 'error' in comparison_data:
        return dbc.Alert(comparison_data['error'], color="danger")

    run1 = comparison_data['run1']
    run2 = comparison_data['run2']
    geomean = comparison_data['geomean']
    analysis = comparison_data['analysis']

    # Comparison summary table
    table_rows = []
    fields = [
        ('Cloud', 'cloud'),
        ('OS', lambda p: f"{p['os_vendor']} {p['os_version']}"),
        ('Instance', 'instance'),
        ('Benchmark', 'benchmark'),
    ]
    for label, key in fields:
        if callable(key):
            v1, v2 = key(run1['params']), key(run2['params'])
        else:
            v1, v2 = run1['params'][key], run2['params'][key]
        table_rows.append(html.Tr([html.Td(label, className="fw-bold"), html.Td(v1), html.Td(v2)]))

    table_rows.append(html.Tr([
        html.Td("Timestamp", className="fw-bold"),
        html.Td(run1['timestamp']),
        html.Td(run2['timestamp']),
    ]))
    table_rows.append(html.Tr([
        html.Td("Doc ID", className="fw-bold"),
        html.Td(run1['id'][:28]),
        html.Td(run2['id'][:28]),
    ]))
    summary_table = dbc.Table([
        html.Thead(html.Tr([html.Th(""), html.Th("Run 1 (Baseline)"), html.Th("Run 2 (Comparison)")])),
        html.Tbody(table_rows)
    ], bordered=True, striped=True, hover=True, size="sm", className="mb-3")

    # Geomean badge
    delta = geomean['delta_pct']
    status = geomean['status']
    if status == 'Regression':
        badge_class = 'ra-geomean-badge regression'
    elif status == 'Improvement':
        badge_class = 'ra-geomean-badge improvement'
    else:
        badge_class = 'ra-geomean-badge neutral'

    geomean_badge = html.Div(
        f"{status}: {delta:+.2f}% (geomean across {geomean['matched']} metrics)",
        className=badge_class,
    )

    return html.Div([
        html.H5("Comparison Summary", className="mb-3"),
        summary_table,
        geomean_badge,
        html.Hr(),
        html.H5("AI Analysis", className="mb-3"),
        dcc.Markdown(analysis),
    ])


@app.callback(
    Output('ra-chat-section', 'style'),
    Input('ra-comparison-results', 'data')
)
def toggle_chat_visibility(comparison_data):
    """Show chat section only after a successful comparison."""
    if comparison_data and 'error' not in comparison_data:
        return {'display': 'block'}
    return {'display': 'none'}


@app.callback(
    [Output('ra-chat-history', 'data'),
     Output('ra-chat-input', 'value')],
    Input('ra-btn-send', 'n_clicks'),
    [State('ra-chat-input', 'value'),
     State('ra-chat-history', 'data'),
     State('ra-comparison-results', 'data')],
    prevent_initial_call=True
)
def send_chat_message(n_clicks, question, chat_history, comparison_data):
    """Send a chat message and get AI response."""
    if not question or not question.strip() or not comparison_data:
        return no_update, no_update

    question = question.strip()
    chat_history = chat_history or []

    # Get AI response with full conversation history
    answer = regression_service.ask_question(question, comparison_data, chat_history)

    # Append user + assistant messages
    chat_history.append({'role': 'user', 'content': question})
    chat_history.append({'role': 'assistant', 'content': answer})

    return chat_history, ''  # Clear input


@app.callback(
    Output('ra-chat-display', 'children'),
    Input('ra-chat-history', 'data')
)
def render_chat_messages(chat_history):
    """Render chat message bubbles."""
    if not chat_history:
        return html.Div("Ask a question about the comparison above.", className="text-muted p-3 text-center")

    messages = []
    for msg in chat_history:
        role = msg['role']
        content = msg['content']

        if role == 'user':
            bubble = html.Div(
                html.Div(content, className="ra-chat-bubble user"),
                className="ra-chat-message user"
            )
        else:
            bubble = html.Div(
                html.Div(dcc.Markdown(content), className="ra-chat-bubble assistant"),
                className="ra-chat-message assistant"
            )
        messages.append(bubble)

    return messages


@app.callback(
    Output('ra-chat-history', 'data', allow_duplicate=True),
    Input('ra-btn-clear', 'n_clicks'),
    prevent_initial_call=True
)
def clear_chat(n_clicks):
    """Clear chat history."""
    return []


# Run the app
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8050))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    
    print("\n" + "="*60)
    print("RHEL Multi Arch Performance Engineering Dashboard (Redesigned)")
    print("="*60)
    print(f"Data Mode: {DATA_MODE.upper()}")
    print(f"Records Loaded: {len(df)}")
    print(f"Server: http://127.0.0.1:{port}")
    print(f"Debug Mode: {debug}")
    print("="*60 + "\n")
    
    app.run(debug=debug, port=port, host='0.0.0.0')

