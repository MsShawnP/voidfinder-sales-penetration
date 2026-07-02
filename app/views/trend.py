"""Void count over time — is the problem growing, stable, or fixed?"""

from dash import Input, Output, callback, dcc, html

from app import charts, data
from app.filters import parse_state


def layout():
    return html.Div(
        [
            dcc.Graph(id="trend-chart", config={"displayModeBar": False}),
            html.P(
                "Open voids per week over the trailing 26 weeks, at the "
                "selected void threshold. A step up that never comes back "
                "down marks the start of a structural gap — the exception "
                "report names the stores behind it. Slow-mover eligibility "
                "is evaluated on current comparables, so the latest point "
                "always matches the exception report count. Retailer and "
                "region display filters do not apply to this view.",
                className="chart-footnote",
            ),
        ]
    )


def register_callbacks():
    @callback(
        Output("trend-chart", "figure"),
        Input("filter-state", "data"),
    )
    def _populate(filter_json):
        state = parse_state(filter_json)
        trend = data.get_trend(state["void_weeks_n"], state["slow_mover_min"])
        return charts.trend_line(trend, "Open voids by week")
