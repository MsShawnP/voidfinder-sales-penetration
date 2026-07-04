"""Parameter and filter bar.

Two knobs change the math (N consecutive zero-scan weeks, slow-mover
floor) and recompute the void list. Three filters (retailer, region,
void type) slice the computed list for display only.
"""

import json

from dash import Input, Output, callback, dcc, html

from app.calculations import (
    DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
    DEFAULT_VOID_WEEKS_N,
)

DEFAULT_FILTER_STATE = {
    "void_weeks_n": DEFAULT_VOID_WEEKS_N,
    "slow_mover_min": DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
    "as_of": None,  # None = latest available week
    "retailers": [],
    "regions": [],
    "void_types": [],
}

N_OPTIONS = [4, 6, 8, 12]
FLOOR_OPTIONS = [
    {"label": "0.25 / wk (1 unit a month)", "value": 0.25},
    {"label": "0.5 / wk (default)", "value": 0.5},
    {"label": "1.0 / wk", "value": 1.0},
]
VOID_TYPE_OPTIONS = [
    {"label": "Never scanned", "value": "never_scanned"},
    {"label": "Went dark", "value": "went_dark"},
]


def build_filter_bar(retailer_options, region_options, week_bounds=None):
    first_week, last_week = week_bounds if week_bounds else (None, None)
    return html.Div(
        [
            html.Div(
                [
                    html.Label(
                        "Measured through", htmlFor="param-as-of",
                        title=(
                            "The week this snapshot is calculated as of. "
                            "Move it back to see the void picture at an "
                            "earlier point in time — every number on the "
                            "page recomputes to that date. Defaults to the "
                            "latest available data (Dec 27, 2025). Data "
                            "runs from Jan 2023."
                        ),
                    ),
                    dcc.DatePickerSingle(
                        id="param-as-of",
                        min_date_allowed=first_week,
                        max_date_allowed=last_week,
                        initial_visible_month=last_week,
                        date=None,
                        placeholder="Latest week",
                        display_format="MMM D, YYYY",
                        clearable=True,
                    ),
                    html.Span(
                        "Drag the date back to watch how the voids — and "
                        "the dollars — built up over time.",
                        className="filter-hint",
                    ),
                ],
                className="filter-item",
            ),
            html.Div(
                [
                    html.Label(
                        "Void threshold (weeks without a scan)", htmlFor="param-n",
                        title=(
                            "How many consecutive zero-scan weeks before a "
                            "store counts as a void. Higher is stricter (only "
                            "long-dead stores); lower catches problems earlier."
                        ),
                    ),
                    dcc.Dropdown(
                        id="param-n",
                        options=[{"label": f"{n} weeks", "value": n} for n in N_OPTIONS],
                        value=DEFAULT_VOID_WEEKS_N,
                        clearable=False,
                    ),
                ],
                className="filter-item",
            ),
            html.Div(
                [
                    html.Label(
                        "Slow-mover floor", htmlFor="param-floor",
                        title=(
                            "The minimum weekly velocity a store would need to "
                            "sell this item. Screens out stores too small to "
                            "ever move it, so a genuine non-seller isn't "
                            "mistaken for a void."
                        ),
                    ),
                    dcc.Dropdown(
                        id="param-floor",
                        options=FLOOR_OPTIONS,
                        value=DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
                        clearable=False,
                    ),
                ],
                className="filter-item",
            ),
            html.Div(
                [
                    html.Label(
                        "Retailer", htmlFor="filter-retailer",
                        title="Narrow the view to one banner.",
                    ),
                    dcc.Dropdown(
                        id="filter-retailer",
                        options=retailer_options,
                        multi=True,
                        placeholder="All retailers",
                    ),
                ],
                className="filter-item",
            ),
            html.Div(
                [
                    html.Label(
                        "Region", htmlFor="filter-region",
                        title=(
                            "Narrow the view to one region. Leave on \"All "
                            "regions\" to see where voids concentrate."
                        ),
                    ),
                    dcc.Dropdown(
                        id="filter-region",
                        options=region_options,
                        multi=True,
                        placeholder="All regions",
                    ),
                ],
                className="filter-item",
            ),
            html.Div(
                [
                    html.Label(
                        "Void type", htmlFor="filter-void-type",
                        title=(
                            "Never-scanned (likely never set on the shelf) "
                            "versus went-dark (was selling, then stopped). The "
                            "fix differs by type, so the split is worth "
                            "watching."
                        ),
                    ),
                    dcc.Dropdown(
                        id="filter-void-type",
                        options=VOID_TYPE_OPTIONS,
                        multi=True,
                        placeholder="Both types",
                    ),
                ],
                className="filter-item",
            ),
        ],
        className="filter-bar",
    )


def register_filter_callbacks():
    @callback(
        Output("filter-state", "data"),
        Input("param-n", "value"),
        Input("param-floor", "value"),
        Input("param-as-of", "date"),
        Input("filter-retailer", "value"),
        Input("filter-region", "value"),
        Input("filter-void-type", "value"),
    )
    def _update_filter_state(n, floor, as_of, retailers, regions, void_types):
        return json.dumps(
            {
                "void_weeks_n": n or DEFAULT_VOID_WEEKS_N,
                "slow_mover_min": floor or DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
                "as_of": as_of,
                "retailers": retailers or [],
                "regions": regions or [],
                "void_types": void_types or [],
            }
        )


def parse_state(filter_json):
    if not filter_json:
        return dict(DEFAULT_FILTER_STATE)
    state = dict(DEFAULT_FILTER_STATE)
    state.update(json.loads(filter_json))
    return state


def apply_display_filters(voids, state):
    """Slice the computed void list by retailer / region / void type."""
    out = voids
    if state["retailers"]:
        out = out[out["chain_name"].isin(state["retailers"])]
    if state["regions"]:
        out = out[out["region"].isin(state["regions"])]
    if state["void_types"]:
        out = out[out["void_type"].isin(state["void_types"])]
    return out
