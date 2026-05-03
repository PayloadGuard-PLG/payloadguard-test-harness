#!/usr/bin/env python3
"""
PayloadGuard Results Dashboard

Usage:
    python tools/dashboard.py
    python tools/dashboard.py --db tools/db/results.db --port 8050
"""
import argparse
import json
import re
import sqlite3
from pathlib import Path

# Must stay in sync with analyze.py _SECURITY_CRITICAL_PATTERNS
_SECURITY_CRITICAL_PATTERNS = [
    r"(^|/)auth[^/]*\.(py|js|ts)$",
    r"(^|/)security[^/]*\.(py|js|ts)$",
    r"(^|/)permission[^/]*\.(py|js|ts)$",
    r"(^|/)authorization[^/]*\.(py|js|ts)$",
]

import dash
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, callback, dash_table, dcc, html

TOOLS_DIR = Path(__file__).parent
DEFAULT_DB = TOOLS_DIR / "db" / "results.db"
TEST_CASES_FILE = TOOLS_DIR / "test_cases.json"

TEST_CASES = json.loads(TEST_CASES_FILE.read_text())
# id → branch  (reverse map for labels)
ID_TO_BRANCH = {v["id"]: k for k, v in TEST_CASES.items()}
# id → expected_exit_code
EXPECTED = {v["id"]: v["expected_exit_code"] for v in TEST_CASES.values()}

VERDICT_COLOUR = {
    "SAFE":        "#28a745",
    "REVIEW":      "#17a2b8",
    "CAUTION":     "#ffc107",
    "DESTRUCTIVE": "#dc3545",
    None:          "#6c757d",
}

CATEGORY_ORDER = ["safe", "boundary", "semantic", "multilang", "destructive", "adversarial"]

# ── DB helpers ────────────────────────────────────────────────────────────────

DB_PATH = str(DEFAULT_DB)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql, params=()):
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def scalar(sql, params=()):
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return row[0] if row else None


# ── Data loaders ──────────────────────────────────────────────────────────────

def load_summary():
    total  = scalar("SELECT COUNT(DISTINCT test_case_id) FROM scan_runs WHERE test_case_id IS NOT NULL") or 0
    passed = scalar("""
        SELECT COUNT(*) FROM (
            SELECT s.test_case_id, s.exit_code, e.expected_exit_code
            FROM scan_runs s
            JOIN expected_verdicts e ON s.test_case_id = e.test_case_id
            WHERE s.run_at = (
                SELECT MAX(s2.run_at) FROM scan_runs s2
                WHERE s2.test_case_id = s.test_case_id
            )
        ) WHERE exit_code = expected_exit_code
    """) or 0
    runs   = scalar("SELECT COUNT(DISTINCT workflow_run_id) FROM scan_runs") or 0
    row = query("""
        SELECT run_at, workflow_run_id FROM scan_runs
        ORDER BY run_at DESC LIMIT 1
    """)
    last_ts  = row[0]["run_at"][:16].replace("T", " ") if row else "—"
    last_run = row[0]["workflow_run_id"] if row else None
    return total, passed, runs, last_ts, last_run


def load_matrix():
    """Returns list of dicts: {test_case_id, category, run_date, verdict, pass}"""
    rows = query("""
        SELECT
            s.test_case_id,
            s.category,
            substr(s.run_at, 1, 10)  AS run_date,
            s.verdict_status,
            s.exit_code,
            e.expected_exit_code
        FROM scan_runs s
        LEFT JOIN expected_verdicts e ON s.test_case_id = e.test_case_id
        ORDER BY s.run_at
    """)
    for r in rows:
        r["pass"] = (r["exit_code"] == r["expected_exit_code"])
    return rows


def load_history(test_case_id):
    return query("""
        SELECT
            substr(run_at, 1, 19) AS ts,
            verdict_status,
            verdict_score,
            files_deleted,
            lines_deleted,
            deletion_ratio_pct,
            structural_severity,
            structural_max_ratio,
            semantic_status,
            exit_code,
            workflow_run_id
        FROM scan_runs
        WHERE test_case_id = ?
        ORDER BY run_at
    """, (test_case_id,))


def load_layer_detail(workflow_run_id):
    row = scalar(
        "SELECT raw_json FROM scan_runs WHERE workflow_run_id = ?",
        (workflow_run_id,),
    )
    if not row:
        return None
    return json.loads(row)


def load_all_raw():
    """Load all raw_json rows for threshold simulation."""
    rows = query("""
        SELECT test_case_id, category, exit_code, raw_json
        FROM scan_runs
        WHERE raw_json IS NOT NULL
        ORDER BY test_case_id, run_at
    """)
    for r in rows:
        r["report"] = json.loads(r["raw_json"])
    return rows


# ── Threshold simulator ───────────────────────────────────────────────────────

def simulate_verdict(report, structural_ratio, min_nodes, stale_threshold, dangerous_threshold,
                     destructive_threshold=5, caution_threshold=3):
    """Re-score a report with current analyze.py logic and adjustable thresholds."""
    files_deleted  = report.get("files", {}).get("deleted", 0)
    lines_deleted  = report.get("lines", {}).get("deleted", 0)
    deletion_ratio = report.get("lines", {}).get("deletion_ratio_percent", 0)
    branch_age     = report.get("temporal", {}).get("branch_age_days", 0)

    score = 0.0

    # Age
    if branch_age > 365:   score += 3
    elif branch_age > 180: score += 2
    elif branch_age > 90:  score += 1

    # Critical and security file deletions
    deleted_critical = report.get("deleted_files", {}).get("critical", [])
    deleted_all      = report.get("deleted_files", {}).get("all", [])
    crit_files = len(deleted_critical)
    security_files = [f for f in deleted_all
                      if any(re.search(p, f) for p in _SECURITY_CRITICAL_PATTERNS)]

    # Deletion dimensions — ratio floor drops to 0 when critical files present
    ratio_min_lines = 0 if crit_files > 0 else 100
    files_score = 3 if files_deleted > 50 else (2 if files_deleted > 20 else (1 if files_deleted > 10 else 0))
    ratio_score = 0
    if lines_deleted >= ratio_min_lines:
        ratio_score = 3 if deletion_ratio > 90 else (2 if deletion_ratio > 70 else (1 if deletion_ratio > 50 else 0))
    lines_score = 3 if lines_deleted > 50000 else (2 if lines_deleted > 10000 else (1 if lines_deleted > 5000 else 0))
    nonzero = sum(1 for s in (files_score, ratio_score, lines_score) if s > 0)
    score += min(4, max(files_score, ratio_score, lines_score) + (1 if nonzero >= 2 else 0))

    # Structural — re-evaluate per-file with slider thresholds, then cross-file aggregation
    flagged = report.get("structural", {}).get("flagged_files", [])
    struct_critical = any(
        m.get("structural_deletion_ratio", 0) / 100 > structural_ratio
        and m.get("deleted_node_count", 0) >= min_nodes
        for flag in flagged
        for m in [flag.get("metrics", {})]
    )
    if not struct_critical and len(flagged) >= 2:
        total_deleted = sum(f.get("metrics", {}).get("deleted_node_count", 0) for f in flagged)
        if total_deleted >= min_nodes:
            struct_critical = True
    if struct_critical:
        score += 5

    # Critical path files (+2 regardless of count)
    score += 2 if crit_files > 0 else 0

    # Security-critical file deletions (+5)
    if security_files:
        score += 5

    if score >= destructive_threshold:   return "DESTRUCTIVE", score
    elif score >= caution_threshold:     return "CAUTION", score
    elif score >= 1:                     return "REVIEW", score
    return "SAFE", score


# ── Layout helpers ────────────────────────────────────────────────────────────

def stat_card(label, value, colour="primary"):
    return dbc.Card(
        dbc.CardBody([
            html.H2(str(value), className=f"text-{colour} mb-0"),
            html.Small(label, className="text-muted"),
        ]),
        className="text-center shadow-sm",
    )


# ── App ───────────────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="PayloadGuard Dashboard",
)

# Test case dropdown options, sorted by category then ID
_sorted_tcs = sorted(
    [(v["id"], k, v["category"], v["description"]) for k, v in TEST_CASES.items()],
    key=lambda x: (CATEGORY_ORDER.index(x[2]) if x[2] in CATEGORY_ORDER else 99, x[0]),
)
TC_OPTIONS = [
    {"label": f"{tc_id} — {desc[:60]}", "value": tc_id}
    for tc_id, branch, cat, desc in _sorted_tcs
]

app.layout = dbc.Container(
    fluid=True,
    children=[
        dbc.Row(dbc.Col(html.H3("PayloadGuard Results", className="my-3 text-dark"))),

        # ── Summary cards ─────────────────────────────────────────────────────
        dbc.Row(id="summary-row", className="mb-4 g-3"),

        dbc.Tabs([

            # ── Tab 1: Regression matrix ─────────────────────────────────────
            dbc.Tab(label="Regression Matrix", children=[
                dbc.Row(dbc.Col(
                    html.Div(id="matrix-container", className="mt-3")
                )),
            ]),

            # ── Tab 2: Per-test history ────────────────────────────────────────
            dbc.Tab(label="Test History", children=[
                dbc.Row([
                    dbc.Col(
                        dcc.Dropdown(
                            id="tc-select",
                            options=TC_OPTIONS,
                            value=TC_OPTIONS[0]["value"] if TC_OPTIONS else None,
                            clearable=False,
                            className="mt-3",
                        ),
                        width=4,
                    ),
                ]),
                dbc.Row([
                    dbc.Col(dcc.Graph(id="history-chart"), width=7),
                    dbc.Col(html.Div(id="layer-detail"), width=5),
                ], className="mt-2"),
            ]),

            # ── Tab 3: Threshold simulator ────────────────────────────────────
            dbc.Tab(label="Threshold Simulator", children=[
                dbc.Row([
                    dbc.Col([
                        html.H6("Structural deletion ratio threshold (%)", className="mt-3"),
                        dcc.Slider(
                            id="sim-struct-ratio",
                            min=5, max=50, step=5, value=20,
                            marks={i: f"{i}%" for i in range(5, 55, 5)},
                        ),
                        html.H6("Min structural deletions", className="mt-3"),
                        dcc.Slider(
                            id="sim-min-nodes",
                            min=1, max=10, step=1, value=3,
                            marks={i: str(i) for i in range(1, 11)},
                        ),
                        html.H6("Temporal stale threshold (drift score)", className="mt-3"),
                        dcc.Slider(
                            id="sim-stale",
                            min=50, max=500, step=50, value=250,
                            marks={i: str(i) for i in range(50, 550, 100)},
                        ),
                        html.H6("Temporal dangerous threshold", className="mt-3"),
                        dcc.Slider(
                            id="sim-dangerous",
                            min=200, max=2000, step=100, value=1000,
                            marks={i: str(i) for i in range(200, 2200, 400)},
                        ),
                        html.Hr(),
                        html.H6("DESTRUCTIVE score threshold", className="mt-3 text-danger"),
                        dcc.Slider(
                            id="sim-destructive-threshold",
                            min=2, max=7, step=1, value=5,
                            marks={i: str(i) for i in range(2, 8)},
                        ),
                        html.H6("CAUTION score threshold", className="mt-3 text-warning"),
                        dcc.Slider(
                            id="sim-caution-threshold",
                            min=1, max=5, step=1, value=3,
                            marks={i: str(i) for i in range(1, 6)},
                        ),
                    ], width=4),
                    dbc.Col(html.Div(id="sim-results"), width=8),
                ], className="mt-3"),
            ]),
        ]),
    ],
)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@callback(Output("summary-row", "children"), Input("summary-row", "id"))
def update_summary(_):
    if not Path(DB_PATH).exists():
        return [dbc.Col(dbc.Alert("No database found. Run ingest.py first.", color="warning"))]
    total, passed, runs, last_ts, last_run_id = load_summary()
    rate = f"{passed/total*100:.0f}%" if total else "—"
    gh_url = (
        f"https://github.com/PayloadGuard-PLG/payloadguard-test-harness/actions/runs/{last_run_id}"
        if last_run_id else None
    )
    last_card = dbc.Card(
        dbc.CardBody([
            html.H2(
                html.A(last_ts, href=gh_url, target="_blank", style={"fontSize": "1.4rem"})
                if gh_url else last_ts,
                className="text-primary mb-0",
            ),
            html.Small("Last run", className="text-muted"),
        ]),
        className="text-center shadow-sm",
    )
    return [
        dbc.Col(stat_card("Total scans", total), width=3),
        dbc.Col(stat_card("Pass rate", rate, "success" if total and passed == total else "warning"), width=3),
        dbc.Col(stat_card("Regression runs", runs), width=3),
        dbc.Col(last_card, width=3),
    ]


@callback(Output("matrix-container", "children"), Input("matrix-container", "id"))
def update_matrix(_):
    if not Path(DB_PATH).exists():
        return dbc.Alert("No database found. Run ingest.py first.", color="warning")

    rows = load_matrix()
    if not rows:
        return dbc.Alert("No scan results yet.", color="info")

    # Build: {tc_id → {run_date → (verdict, pass)}}
    dates = sorted({r["run_date"] for r in rows})
    tcs   = sorted(
        {r["test_case_id"] for r in rows if r["test_case_id"]},
        key=lambda x: (
            CATEGORY_ORDER.index(
                next((v["category"] for v in TEST_CASES.values() if v["id"] == x), "")
            ) if any(v["id"] == x for v in TEST_CASES.values()) else 99,
            x,
        ),
    )

    data_map = {}
    for r in rows:
        tc = r["test_case_id"]
        if tc:
            data_map.setdefault(tc, {})[r["run_date"]] = (r["verdict_status"], r["pass"])

    columns = [{"name": "Test Case", "id": "tc"}] + [{"name": d, "id": d} for d in dates]
    table_data = []
    for tc in tcs:
        row_dict = {"tc": tc}
        for d in dates:
            entry = data_map.get(tc, {}).get(d)
            if entry:
                verdict, passed = entry
                row_dict[d] = f"{'✅' if passed else '❌'} {verdict or '—'}"
            else:
                row_dict[d] = "—"
        table_data.append(row_dict)

    return dash_table.DataTable(
        data=table_data,
        columns=columns,
        style_cell={"textAlign": "center", "padding": "6px", "fontSize": "13px"},
        style_header={"backgroundColor": "#343a40", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"filter_query": f'{{{d}}} contains "✅"', "column_id": d},
             "backgroundColor": "#d4edda"} for d in dates
        ] + [
            {"if": {"filter_query": f'{{{d}}} contains "❌"', "column_id": d},
             "backgroundColor": "#f8d7da"} for d in dates
        ],
        page_size=25,
    )


@callback(
    Output("history-chart", "figure"),
    Output("layer-detail", "children"),
    Input("tc-select", "value"),
)
def update_history(tc_id):
    if not tc_id or not Path(DB_PATH).exists():
        empty = go.Figure()
        empty.update_layout(title="No data")
        return empty, html.Div()

    rows = load_history(tc_id)
    if not rows:
        empty = go.Figure()
        empty.update_layout(title=f"No data for {tc_id}")
        return empty, dbc.Alert(f"No runs yet for {tc_id}", color="info")

    timestamps = [r["ts"] for r in rows]
    scores = [r["verdict_score"] or 0 for r in rows]
    verdicts = [r["verdict_status"] or "?" for r in rows]
    colours = [VERDICT_COLOUR.get(v, "#6c757d") for v in verdicts]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=scores,
        mode="lines+markers",
        marker=dict(color=colours, size=10),
        line=dict(color="#dee2e6"),
        text=verdicts,
        hovertemplate="%{x}<br>Score: %{y}<br>%{text}<extra></extra>",
    ))
    expected_exit = EXPECTED.get(tc_id, 0)
    threshold_line = 5 if expected_exit == 2 else 3
    fig.add_hline(
        y=threshold_line,
        line_dash="dash",
        line_color="#dc3545",
        annotation_text="DESTRUCTIVE threshold",
    )
    fig.update_layout(
        title=f"{tc_id} — verdict score over time",
        xaxis_title="Run",
        yaxis_title="Severity score",
        template="plotly_white",
        margin=dict(l=40, r=20, t=40, b=40),
    )

    # Layer detail for most recent run
    latest = rows[-1]
    detail = dbc.Card(dbc.CardBody([
        html.H6(f"Latest: {latest['verdict_status']} [{latest['ts'][:10]}]"),
        dbc.Table([
            html.Tbody([
                html.Tr([html.Td("Files deleted"), html.Td(latest.get("files_deleted") or 0)]),
                html.Tr([html.Td("Lines deleted"), html.Td(latest.get("lines_deleted") or 0)]),
                html.Tr([html.Td("Deletion ratio"), html.Td(f"{latest.get('deletion_ratio_pct') or 0:.1f}%")]),
                html.Tr([html.Td("Structural"), html.Td(latest.get("structural_severity") or "—")]),
                html.Tr([html.Td("Struct ratio"), html.Td(f"{latest.get('structural_max_ratio') or 0:.1f}%")]),
                html.Tr([html.Td("Semantic"), html.Td(latest.get("semantic_status") or "—")]),
                html.Tr([html.Td("Verdict score"), html.Td(latest.get("verdict_score") or 0)]),
            ])
        ], size="sm", bordered=True, striped=True),
    ]), className="mt-2")

    return fig, detail


@callback(
    Output("sim-results", "children"),
    Input("sim-struct-ratio", "value"),
    Input("sim-min-nodes", "value"),
    Input("sim-stale", "value"),
    Input("sim-dangerous", "value"),
    Input("sim-destructive-threshold", "value"),
    Input("sim-caution-threshold", "value"),
)
def update_simulator(struct_ratio, min_nodes, stale_th, dangerous_th, destructive_th, caution_th):
    if not Path(DB_PATH).exists():
        return dbc.Alert("No database. Run ingest.py first.", color="warning")

    rows = load_all_raw()
    if not rows:
        return dbc.Alert("No data yet.", color="info")

    struct_ratio_f  = (struct_ratio or 20) / 100
    min_nodes_i     = min_nodes or 3
    stale_f         = float(stale_th or 250)
    dangerous_f     = float(dangerous_th or 1000)
    destructive_th  = destructive_th or 5
    caution_th      = caution_th or 3

    # Deduplicate: keep latest run per test case
    seen = {}
    for row in rows:
        tc = row["test_case_id"]
        if tc and tc not in seen:
            seen[tc] = row
    rows = list(seen.values())

    table_rows = []
    flips = 0

    for row in rows:
        tc_id = row["test_case_id"]
        if not tc_id:
            continue
        report    = row["report"]
        orig_exit = row["exit_code"]
        expected  = EXPECTED.get(tc_id, 0)

        new_status, new_score = simulate_verdict(
            report, struct_ratio_f, min_nodes_i, stale_f, dangerous_f,
            destructive_th, caution_th,
        )
        new_exit = 2 if new_status == "DESTRUCTIVE" else 0
        orig_status = report.get("verdict", {}).get("status", "?")

        changed = new_status != orig_status
        now_pass = new_exit == expected
        was_pass = orig_exit == expected
        if changed:
            flips += 1

        table_rows.append(html.Tr([
            html.Td(tc_id),
            html.Td(orig_status, style={"color": VERDICT_COLOUR.get(orig_status)}),
            html.Td(new_status,  style={"color": VERDICT_COLOUR.get(new_status)}),
            html.Td("→" if changed else "="),
            html.Td("✅" if now_pass else "❌"),
        ], style={"backgroundColor": "#fff3cd" if changed else ""}))

    badge = dbc.Badge(f"{flips} verdict(s) would flip", color="warning" if flips else "success")

    return html.Div([
        html.P([badge], className="mt-2"),
        dbc.Table(
            [
                html.Thead(html.Tr([
                    html.Th("Test case"),
                    html.Th("Current"),
                    html.Th("Simulated"),
                    html.Th(""),
                    html.Th("Pass?"),
                ])),
                html.Tbody(table_rows),
            ],
            size="sm", bordered=True, striped=True, hover=True,
        ),
    ])


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PayloadGuard results dashboard")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    global DB_PATH
    DB_PATH = args.db

    if not Path(DB_PATH).exists():
        print(f"Warning: database not found at {DB_PATH}")
        print("Run `python tools/ingest.py` first to populate it.")

    print(f"Dashboard running at http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
