"""
CPT AI Regression Analyzer - Standalone Dash App

Minimal dashboard with only the Regression Analyzer tab.
No dependency on the full dashboard's data processing, synthetic data,
or other tabs.

Requires:
    - OpenSearch MCP Server running on port 9900
    - AI model endpoint configured in .env

Usage:
    python ra_app.py
"""

import os
import sys
from dash import Dash, html, dcc, Input, Output, State, no_update
import dash_bootstrap_components as dbc
from dotenv import load_dotenv

# Add project root to path for cpt_core imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.regression_service import RegressionService
from src.components.regression_analyzer_tab import create_regression_analyzer_layout

load_dotenv()

# Initialize app
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.title = "CPT AI - Regression Analyzer"

# Initialize regression service
regression_service = RegressionService()

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------
app.layout = dbc.Container([
    # Stores for state management
    dcc.Store(id='ra-comparison-results'),
    dcc.Store(id='ra-chat-history', data=[]),

    # Header
    dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand("CPT AI — Regression Analyzer", className="fs-4 fw-bold"),
        ]),
        color="dark",
        dark=True,
        className="mb-4",
    ),

    # Main content
    create_regression_analyzer_layout(),

], fluid=True)


# ---------------------------------------------------------------------------
# Field mapping and cascade logic
# ---------------------------------------------------------------------------
RA_FIELD_MAP = {
    'cloud': 'metadata.cloud_provider',
    'os-vendor': 'metadata.os_vendor',
    'os-version': 'system_under_test.operating_system.version',
    'instance': 'metadata.instance_type',
    'benchmark': 'test.name',
}

RA_CASCADE_ORDER = ['cloud', 'os-vendor', 'os-version', 'instance', 'benchmark']


def register_cascade_callbacks(dash_app, run_prefix):
    """Register cascading dropdown callbacks for a run selector."""
    for i, field in enumerate(RA_CASCADE_ORDER):
        if i == 0:
            continue

        parent_fields = RA_CASCADE_ORDER[:i]
        parent_ids = [f'{run_prefix}-{pf}' for pf in parent_fields]

        def make_callback(field_key, parent_field_keys, parent_input_ids, prefix):
            @dash_app.callback(
                [Output(f'{prefix}-{field_key}', 'options'),
                 Output(f'{prefix}-{field_key}', 'value')],
                [Input(f'{pid}', 'value') for pid in parent_input_ids],
                prevent_initial_call=True
            )
            def update_dropdown(*parent_values):
                if not all(parent_values):
                    return [], None
                filter_dict = {}
                for pf, pv in zip(parent_field_keys, parent_values):
                    filter_dict[RA_FIELD_MAP[pf]] = pv
                os_field = RA_FIELD_MAP[field_key]
                options = regression_service.get_dropdown_options(os_field, filter_dict)
                return options, None

        make_callback(field, parent_fields, parent_ids, run_prefix)


register_cascade_callbacks(app, 'ra-r1')
register_cascade_callbacks(app, 'ra-r2')


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@app.callback(
    [Output('ra-r1-cloud', 'options'),
     Output('ra-r2-cloud', 'options')],
    Input('ra-init-trigger', 'n_intervals'),
    prevent_initial_call=True
)
def load_initial_cloud_options(n_intervals):
    """Load cloud provider options on page load."""
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
    r1_vals = [r1_cloud, r1_os_vendor, r1_os_version, r1_instance, r1_benchmark]
    r2_vals = [r2_cloud, r2_os_vendor, r2_os_version, r2_instance, r2_benchmark]

    if not all(r1_vals) or not all(r2_vals):
        return {'error': 'Please select all fields for both Run 1 and Run 2.'}, []

    run1_params = {
        'cloud': r1_cloud, 'os_vendor': r1_os_vendor, 'os_version': r1_os_version,
        'instance': r1_instance, 'benchmark': r1_benchmark,
    }
    run2_params = {
        'cloud': r2_cloud, 'os_vendor': r2_os_vendor, 'os_version': r2_os_version,
        'instance': r2_instance, 'benchmark': r2_benchmark,
    }

    result = regression_service.run_comparison(run1_params, run2_params, detail_level or 'medium')
    return result, []


@app.callback(
    Output('ra-results-container', 'children'),
    Input('ra-comparison-results', 'data')
)
def display_results(comparison_data):
    """Render comparison results."""
    if not comparison_data:
        return html.Div("Select runs and click 'Compare Runs' to begin.",
                        className="text-muted p-4 text-center")

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

    answer = regression_service.ask_question(question, comparison_data, chat_history)

    chat_history.append({'role': 'user', 'content': question})
    chat_history.append({'role': 'assistant', 'content': answer})

    return chat_history, ''


@app.callback(
    Output('ra-chat-display', 'children'),
    Input('ra-chat-history', 'data')
)
def render_chat_messages(chat_history):
    """Render chat message bubbles."""
    if not chat_history:
        return html.Div("Ask a question about the comparison above.",
                        className="text-muted p-3 text-center")

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


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8060))
    debug = os.getenv('DEBUG', 'True').lower() == 'true'

    print("\n" + "=" * 60)
    print("CPT AI - Regression Analyzer (Standalone)")
    print("=" * 60)
    print(f"Server: http://127.0.0.1:{port}")
    print(f"Debug:  {debug}")
    print("=" * 60 + "\n")

    app.run(debug=debug, port=port, host='0.0.0.0')
