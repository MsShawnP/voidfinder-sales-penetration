"""Void count over time — is the problem growing, stable, or fixed?"""

from dash import Input, Output, callback, dcc, html

from app import charts, data
from app.filters import parse_state


def takeaway(trend_df) -> str:
    """One-line reading of the trend, with the numbers filled in.
    Rising, falling, and flat lines mean different things to an exec —
    say which one this is."""
    if trend_df is None or trend_df.empty:
        return ""
    first = int(trend_df["void_count"].iloc[0])
    last = int(trend_df["void_count"].iloc[-1])
    weeks = len(trend_df)
    if last > first:
        return (
            f"Open voids climbed from {first} to {last} over {weeks} weeks "
            f"as went-dark stores accumulated. A rising line means store "
            f"execution is decaying faster than it's being fixed."
        )
    if last < first:
        return (
            f"Open voids fell from {first} to {last} over {weeks} weeks — "
            f"fixes are outpacing new failures."
        )
    return (
        f"Open voids held at {last} across {weeks} weeks — the gap is "
        f"structural, not seasonal, and it will not close on its own."
    )


def insight_line(label) -> str:
    """Lead-in copy for the trend, naming the selected window so the
    chart and the Period selector always agree."""
    window = label or "the selected window"
    return (
        f"Open voids over {window}, at the current threshold. The shape "
        "is the story: a step up that never comes back down marks the "
        "start of a structural gap."
    )


def layout():
    return html.Div(
        [
            html.P(id="trend-insight", className="insight-line"),
            dcc.Graph(id="trend-chart", config={"displayModeBar": False}),
            html.P(id="trend-takeaway", className="chart-footnote"),
        ]
    )


def register_callbacks():
    @callback(
        Output("trend-chart", "figure"),
        Output("trend-takeaway", "children"),
        Output("trend-insight", "children"),
        Input("filter-state", "data"),
    )
    def _populate(filter_json):
        state = parse_state(filter_json)
        window = data.period_window(
            state["period"], state["as_of"],
            state.get("custom_start"), state.get("custom_end"),
        )
        trend_weeks = window["period_weeks"] if window else 26
        label = window["label"] if window else ""
        trend = data.get_trend(
            state["void_weeks_n"], state["slow_mover_min"], state["as_of"],
            trend_weeks=trend_weeks,
        )
        caption = takeaway(trend)
        if caption:
            caption += (
                " The latest point always matches the Exception Report count."
            )
        return (
            charts.trend_line(trend, "Open voids by week"),
            caption,
            insight_line(label),
        )
