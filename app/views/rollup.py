"""Summary rollup — total void dollars by retailer, region, and item.

The retailer chart is the exec-slide number; the by-type split shows
whether the money is in shelf sets that never happened (never-scanned)
or distribution quietly decaying (went-dark).
"""

from dash import Input, Output, callback, dcc, html

from app import charts, data
from app.calculations import rollup
from app.filters import apply_display_filters, parse_state


def layout():
    return html.Div(
        [
            dcc.Graph(id="rollup-retailer", config={"displayModeBar": False}),
            html.P(
                "Void dollars split by type per retailer. Source: Cinderhaven "
                "POS scans vs. authorization matrix; excludes slow movers.",
                className="chart-footnote",
            ),
            dcc.Graph(id="rollup-region", config={"displayModeBar": False}),
            html.P(
                "Total void dollars by region. A single region towering over "
                "the rest is the signature of a clustered reset failure.",
                className="chart-footnote",
            ),
            dcc.Graph(id="rollup-item", config={"displayModeBar": False}),
            html.P(
                "Top items by void dollars. Source: Cinderhaven POS scans vs. "
                "authorization matrix; comparable-store median dollarization.",
                className="chart-footnote",
            ),
        ]
    )


def register_callbacks():
    @callback(
        Output("rollup-retailer", "figure"),
        Output("rollup-region", "figure"),
        Output("rollup-item", "figure"),
        Input("filter-state", "data"),
    )
    def _populate(filter_json):
        state = parse_state(filter_json)
        voids = data.get_voids(state["void_weeks_n"], state["slow_mover_min"])
        shown = apply_display_filters(voids, state)

        by_retailer = charts.split_bars_by_type(
            shown, "chain_name", "Void dollars by retailer and type"
        )

        region_agg = rollup(shown, "region")
        by_region = charts.hbar_dollars(
            region_agg, "region", "void_dollars", "Void dollars by region"
        )

        item_agg = rollup(shown, "sku")
        if not shown.empty and "product_name" in shown.columns:
            names = shown[["sku", "product_name"]].drop_duplicates()
            item_agg = item_agg.merge(names, on="sku", how="left")
            item_agg["label"] = item_agg["product_name"].fillna(item_agg["sku"])
        else:
            item_agg["label"] = item_agg.get("sku", "")
        by_item = charts.hbar_dollars(
            item_agg.head(15), "label", "void_dollars", "Top items by void dollars"
        )

        return by_retailer, by_region, by_item
