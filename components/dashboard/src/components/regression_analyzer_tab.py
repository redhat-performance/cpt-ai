"""
Regression Analyzer Tab - UI layout for the regression analyzer integration.

Provides cascading dropdowns for run selection, comparison results display,
and multi-turn Q&A chat interface.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc


def _create_run_selector(prefix, title):
    """Create a run selector card with 5 cascading dropdowns.

    Args:
        prefix: ID prefix ('ra-r1' or 'ra-r2')
        title: Card title ('Run 1 (Baseline)' or 'Run 2 (Comparison)')
    """
    fields = [
        ('cloud', 'Cloud Provider'),
        ('os-vendor', 'OS Vendor'),
        ('os-version', 'OS Version'),
        ('instance', 'Instance Type'),
        ('benchmark', 'Benchmark'),
    ]

    dropdowns = []
    for field_id, label in fields:
        dropdowns.append(
            html.Div([
                html.Label(label, className="fw-bold small mb-1"),
                dcc.Loading(
                    dcc.Dropdown(
                        id=f'{prefix}-{field_id}',
                        options=[],
                        value=None,
                        placeholder=f"Select {label.lower()}...",
                        clearable=False,
                    ),
                    type="dot",
                    target_components={f'{prefix}-{field_id}': 'options'},
                ),
            ], className="mb-2")
        )

    return dbc.Card([
        dbc.CardHeader(
            html.H5(title, className="mb-0"),
            style={"background": "linear-gradient(135deg, #ffffff 0%, #f9fafb 100%)"}
        ),
        dbc.CardBody(dropdowns)
    ])


def create_regression_analyzer_layout():
    """Create the full regression analyzer tab layout."""
    return html.Div([
        # Trigger to load initial cloud options once the layout is rendered
        dcc.Interval(id='ra-init-trigger', interval=500, max_intervals=1),

        # Section A: Run Selection
        html.H4("Select Runs to Compare", className="mb-3"),
        dbc.Row([
            dbc.Col(
                _create_run_selector('ra-r1', 'Run 1 (Baseline)'),
                width=6
            ),
            dbc.Col(
                _create_run_selector('ra-r2', 'Run 2 (Comparison)'),
                width=6
            ),
        ], className="mb-3"),

        # Detail level + Compare button
        dbc.Row([
            dbc.Col([
                html.Label("Analysis Detail Level:", className="fw-bold small mb-1"),
                dbc.RadioItems(
                    id='ra-detail-level',
                    options=[
                        {'label': 'Basic', 'value': 'basic'},
                        {'label': 'Medium', 'value': 'medium'},
                        {'label': 'Expert', 'value': 'expert'},
                    ],
                    value='medium',
                    inline=True,
                    className="mb-2"
                ),
            ], width=6),
            dbc.Col([
                dbc.Button(
                    "Compare Runs",
                    id='ra-btn-compare',
                    color='primary',
                    size='lg',
                    className="w-100 mt-3",
                ),
            ], width=6),
        ], className="mb-4"),

        # Section B: Analysis Results
        dcc.Loading(
            html.Div(id='ra-results-container'),
            type="default",
        ),

        # Section C: Q&A Chat (hidden until comparison is done)
        html.Div(
            id='ra-chat-section',
            children=[
                html.Hr(),
                html.H4("Ask Questions About This Comparison", className="mb-3"),
                html.Div(
                    id='ra-chat-display',
                    className="ra-chat-container mb-3",
                ),
                dbc.InputGroup([
                    dbc.Input(
                        id='ra-chat-input',
                        type='text',
                        placeholder='Ask a question about the comparison...',
                        debounce=True,
                    ),
                    dbc.Button("Send", id='ra-btn-send', color='primary'),
                    dbc.Button("Clear", id='ra-btn-clear', color='secondary', outline=True),
                ]),
            ],
            style={'display': 'none'},
        ),
    ])
