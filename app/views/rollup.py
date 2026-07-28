"""Summary rollup — total void dollars by retailer, region, and item.

The retailer chart is the exec-slide number; the by-type split shows
whether the money is in shelf sets that never happened (never-scanned)
or distribution quietly decaying (went-dark).
"""

from dash import Input, Output, callback, dcc, html

from app import calculations, charts, data
from app.calculations import rollup
from app.filters import apply_display_filters, parse_state


def layout():
    return html.Div(
        [
            html.P(
                "The leak, aggregated — by item, banner, region, and void "
                "type. Use this to find the one pattern worth fixing first, "
                "before you touch the store-level list.",
                className="insight-line",
            ),
            dcc.Graph(id="rollup-item", config={"displayModeBar": False}),
            html.P(
                "Which products are leaking most. A few items carrying the "
                "bulk of the dollars means the fix is narrower than it "
                "looks.",
                className="chart-footnote",
            ),
            dcc.Graph(id="rollup-retailer", config={"displayModeBar": False}),
            html.P(
                "Which retailers your voids sit in. Concentration in one "
                "banner often traces to that retailer's reset or item-setup "
                "process.",
                className="chart-footnote",
            ),
            dcc.Graph(id="rollup-region", config={"displayModeBar": False}),
            html.P(
                "Where voids cluster geographically — the strongest signal "
                "that a gap is structural rather than random.",
                className="chart-footnote",
            ),
            dcc.Graph(id="rollup-type", config={"displayModeBar": False}),
            html.P(
                "Never-scanned versus went-dark. A never-scanned-heavy mix "
                "points at setup failures; a went-dark-heavy mix points at "
                "out-of-stocks and lost tags.",
                className="chart-footnote",
            ),
        ]
    )


def register_callbacks():
    @callback(
        Output("rollup-item", "figure"),
        Output("rollup-retailer", "figure"),
        Output("rollup-region", "figure"),
        Output("rollup-type", "figure"),
        Input("filter-state", "data"),
    )
    def _populate(filter_json):
        state = parse_state(filter_json)
        voids = data.get_voids(state["void_weeks_n"], state["slow_mover_min"])
        shown = apply_display_filters(voids, state)

        # The rollup counts only the void dollars that accrued inside the
        # selected period — a void opened before the window still counts,
        # but only for its in-period weeks.
        window = data.period_window(
            state["period"], state.get("custom_start"), state.get("custom_end"),
        )
        if window:
            shown = calculations.apply_period(shown, window["period_weeks"])

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

        by_retailer = charts.split_bars_by_type(
            shown, "chain_name", "Void dollars by retailer and type"
        )

        region_agg = rollup(shown, "region")
        by_region = charts.hbar_dollars(
            region_agg, "region", "void_dollars", "Void dollars by region"
        )

        type_agg = rollup(shown, "void_type")
        if not type_agg.empty:
            type_agg["label"] = type_agg["void_type"].map(
                {"never_scanned": "Never scanned", "went_dark": "Went dark"}
            )
        else:
            type_agg["label"] = ""
        by_type = charts.hbar_dollars(
            type_agg, "label", "void_dollars", "Void dollars by void type",
            # Same two series as the retailer split above, so the same
            # paired-palette slots 1-2 (Chicago-20 / Chicago-70).
            color_map={
                "Never scanned": charts.LL_CHICAGO,
                "Went dark": charts.LL_CHICAGO_LIGHT,
            },
        )

        return by_item, by_retailer, by_region, by_type
