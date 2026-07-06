"""Parameter and filter bar.

Two knobs change the math (N consecutive zero-scan weeks, slow-mover
floor) and recompute the void list. Three filters (retailer, region,
void type) slice the computed list for display only.
"""

import json

from dash import Input, Output, State, callback, dcc, html, no_update

from app.calculations import (
    DEFAULT_PERIOD,
    DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
    DEFAULT_VOID_WEEKS_N,
)

DEFAULT_FILTER_STATE = {
    "void_weeks_n": DEFAULT_VOID_WEEKS_N,
    "slow_mover_min": DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
    "as_of": None,  # None = latest available week
    "period": DEFAULT_PERIOD,
    "custom_start": None,
    "custom_end": None,
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
PERIOD_OPTIONS = [
    {"label": "Last 13 weeks", "value": "13w"},
    {"label": "Last 26 weeks", "value": "26w"},
    {"label": "Last 6 months", "value": "6mo"},
    {"label": "Year to date", "value": "ytd"},
    {"label": "Last full year", "value": "full_year"},
    {"label": "All history", "value": "all"},
    {"label": "Custom", "value": "custom"},
]
VOID_TYPE_OPTIONS = [
    {"label": "Never scanned", "value": "never_scanned"},
    {"label": "Went dark", "value": "went_dark"},
]


def _fmt_day(d):
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def build_filter_bar(retailer_options, region_options, week_bounds=None):
    """Two visual clusters: the measurement dials that change the math
    (as-of, threshold, floor) and the display filters that slice the
    result (retailer, region, type)."""
    first_week, last_week = week_bounds if week_bounds else (None, None)
    # Every bound and the tooltip's example dates derive from the data
    # at startup — nothing here is hardcoded, so the picker can't drift
    # out of step with a re-seeded dataset.
    if first_week is not None and last_week is not None:
        as_of_title = (
            "The week this snapshot is calculated as of. Move it back to "
            "see the void picture at an earlier point in time — every "
            "number on the page recomputes to that date. Defaults to the "
            f"latest available data ({_fmt_day(last_week)}). Data runs "
            f"from {first_week.strftime('%b %Y')}."
        )
    else:
        as_of_title = (
            "The week this snapshot is calculated as of. Move it back to "
            "see the void picture at an earlier point in time — every "
            "number on the page recomputes to that date. Defaults to the "
            "latest available data."
        )
    measurement = html.Div(
        [
            html.Div(
                [
                    html.Label(
                        "Measured through", htmlFor="param-as-of",
                        title=as_of_title,
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
                ],
                className="filter-group",
            ),
            html.Div(
                [
                    html.Label(
                        "Period", htmlFor="param-period",
                        title=(
                            "The window the trend chart and the accrued-"
                            "dollar totals cover, ending at the "
                            "\"Measured through\" date. \"Lost so far\" and "
                            "the rollup charts count only the void dollars "
                            "that built up inside this window; open-void "
                            "counts stay a snapshot at the end date."
                        ),
                    ),
                    dcc.Dropdown(
                        id="param-period",
                        options=PERIOD_OPTIONS,
                        value=DEFAULT_PERIOD,
                        clearable=False,
                        searchable=False,
                    ),
                ],
                className="filter-group",
            ),
            html.Div(
                [
                    html.Label(
                        "Void threshold", htmlFor="param-n",
                        title=(
                            "Weeks without a scan. How many consecutive "
                            "zero-scan weeks before a store counts as a "
                            "void. Higher is stricter (only long-dead "
                            "stores); lower catches problems earlier."
                        ),
                    ),
                    dcc.Dropdown(
                        id="param-n",
                        options=[{"label": f"{n} weeks", "value": n} for n in N_OPTIONS],
                        value=DEFAULT_VOID_WEEKS_N,
                        clearable=False,
                    ),
                ],
                className="filter-group",
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
                className="filter-group",
            ),
            html.Div(
                [
                    html.Label(
                        "Custom range", htmlFor="param-custom-range",
                        title=(
                            "Pick any start and end week. The end week "
                            "becomes the \"Measured through\" date."
                        ),
                    ),
                    dcc.DatePickerRange(
                        id="param-custom-range",
                        min_date_allowed=first_week,
                        max_date_allowed=last_week,
                        initial_visible_month=last_week,
                        start_date=None,
                        end_date=None,
                        display_format="MMM D, YYYY",
                        clearable=True,
                    ),
                ],
                id="custom-range-group",
                className="filter-group filter-group--wide",
                style={"display": "none"},
            ),
            html.Span(
                "Drag the date back to watch how the voids — and "
                "the dollars — built up over time.",
                className="filter-hint",
            ),
        ],
        className="filter-cluster",
    )
    display = html.Div(
        [
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
                className="filter-group",
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
                className="filter-group",
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
                className="filter-group",
            ),
        ],
        className="filter-cluster filter-cluster--display",
    )
    return html.Div([measurement, display], className="filter-bar")


def register_filter_callbacks():
    @callback(
        Output("filter-state", "data"),
        Input("param-n", "value"),
        Input("param-floor", "value"),
        Input("param-as-of", "date"),
        Input("param-period", "value"),
        Input("param-custom-range", "start_date"),
        Input("param-custom-range", "end_date"),
        Input("filter-retailer", "value"),
        Input("filter-region", "value"),
        Input("filter-void-type", "value"),
    )
    def _update_filter_state(
        n, floor, as_of, period, custom_start, custom_end,
        retailers, regions, void_types,
    ):
        return json.dumps(
            {
                "void_weeks_n": n or DEFAULT_VOID_WEEKS_N,
                "slow_mover_min": floor or DEFAULT_SLOW_MOVER_MIN_WEEKLY_UNITS,
                "as_of": as_of,
                "period": period or DEFAULT_PERIOD,
                "custom_start": custom_start,
                "custom_end": custom_end,
                "retailers": retailers or [],
                "regions": regions or [],
                "void_types": void_types or [],
            }
        )

    @callback(
        Output("custom-range-group", "style"),
        Input("param-period", "value"),
    )
    def _toggle_custom_range(period):
        return {} if period == "custom" else {"display": "none"}

    @callback(
        Output("param-as-of", "date"),
        Input("param-custom-range", "end_date"),
        State("param-period", "value"),
        prevent_initial_call=True,
    )
    def _sync_as_of_to_custom_end(end_date, period):
        synced = custom_end_as_of(end_date, period)
        return synced if synced is not None else no_update


def custom_end_as_of(end_date, period):
    """The as-of date a Custom range implies: its end week is the
    endpoint, so it drives the as-of. Presets leave the user's as-of
    alone (returns None → the callback issues no_update)."""
    if period == "custom" and end_date:
        return end_date
    return None


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
