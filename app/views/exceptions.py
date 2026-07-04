"""Void exception report — the ranked, dollarized work list."""

import pandas as pd
from dash import Input, Output, callback, dcc, html

from app import charts, data
from app.components import data_grid, kpi_card, kpi_row, no_data_notice
from app.filters import apply_display_filters, parse_state

_COLUMN_DEFS = [
    {"field": "chain_name", "headerName": "Retailer", "width": 120, "pinned": "left"},
    {"field": "store_id", "headerName": "Store", "width": 150},
    {"field": "region", "headerName": "Region", "width": 110},
    {"field": "volume_tier", "headerName": "Tier", "width": 90},
    {"field": "sku", "headerName": "SKU", "width": 120},
    {
        "field": "product_name",
        "headerName": "Item",
        "minWidth": 150,
        "flex": 1,
        "tooltipField": "product_name",
        "cellStyle": {"textOverflow": "ellipsis", "overflow": "hidden", "whiteSpace": "nowrap"},
    },
    {
        "field": "void_type",
        "headerName": "Void type",
        "width": 130,
        "valueFormatter": {
            "function": "params.value === 'never_scanned' ? 'Never scanned' : 'Went dark'"
        },
    },
    {"field": "void_weeks", "headerName": "Weeks dark", "width": 110},
    {
        "field": "void_dollars",
        "headerName": "Opportunity",
        "width": 130,
        "sort": "desc",
        "valueFormatter": {"function": "d3.format('$,.0f')(params.value)"},
        "cellStyle": {"fontWeight": "bold"},
        "headerTooltip": "Median weekly dollars of comparable scanning stores x weeks dark",
    },
    {
        "field": "fixability",
        "headerName": "Fixability",
        "width": 105,
        "valueFormatter": {"function": "d3.format('.2f')(params.value)"},
        "headerTooltip": "Weight that a broker visit fixes it — never-scanned highest",
    },
    {
        "field": "priority",
        "headerName": "Priority",
        "width": 115,
        "valueFormatter": {"function": "d3.format('$,.0f')(params.value)"},
        "headerTooltip": "Opportunity x fixability",
    },
    {
        "field": "cluster_id",
        "headerName": "Cluster",
        "width": 170,
        "valueFormatter": {"function": "params.value == null ? '—' : params.value"},
        "headerTooltip": "Never-scanned voids concentrated in one retailer+region — one reset call fixes many",
    },
]


def layout():
    return html.Div(
        [
            kpi_row(
                [
                    kpi_card(
                        "Total void opportunity", "kpi-total-dollars",
                        tooltip=(
                            "Estimated annual sales lost to voids: the sum "
                            "of every void's dollarized opportunity. "
                            "Deliberately conservative — built on the median "
                            "velocity of comparable scanning stores, not the "
                            "average."
                        ),
                    ),
                    kpi_card(
                        "Open voids", "kpi-void-count",
                        tooltip=(
                            "Item-and-store combinations currently "
                            "authorized but not scanning past the void "
                            "threshold."
                        ),
                    ),
                    kpi_card(
                        "Stores affected", "kpi-store-count",
                        tooltip="Distinct stores with at least one open void.",
                    ),
                    kpi_card(
                        "Never-scanned share", "kpi-never-share",
                        tooltip=(
                            "The share of open voids that have never scanned "
                            "even once. A high share points at setup or "
                            "reset failures — product that never made it "
                            "onto the shelf — rather than everyday "
                            "out-of-stocks."
                        ),
                    ),
                ]
            ),
            html.Div(id="cluster-callout"),
            dcc.Graph(id="void-map", config={"displayModeBar": False}),
            html.P(
                "Where the money sits geographically. A tall bar "
                "concentrated in one state usually means a single reset or "
                "distribution failure — one root cause, one fix — not "
                "scattered store-level noise.",
                className="chart-footnote",
            ),
            html.P(
                "Every void, ranked by what it's costing you. Work "
                "top-down — the top of this list is where a single broker "
                "visit pays back fastest. Export it and each row is a store "
                "number and address your field team can act on this week.",
                className="insight-line",
            ),
            data_grid("void-grid", _COLUMN_DEFS, aria_label="Void exception report"),
            html.Div(
                [
                    html.Button(
                        "Download broker work list (Excel)",
                        id="btn-download-workbook",
                        className="primary-button",
                    ),
                    dcc.Download(id="download-workbook"),
                ],
                className="export-row",
            ),
            html.P(id="methodology-note", className="chart-footnote"),
        ]
    )


def register_callbacks():
    @callback(
        Output("void-grid", "rowData"),
        Output("kpi-total-dollars", "children"),
        Output("kpi-void-count", "children"),
        Output("kpi-store-count", "children"),
        Output("kpi-never-share", "children"),
        Output("cluster-callout", "children"),
        Output("void-map", "figure"),
        Output("methodology-note", "children"),
        Input("filter-state", "data"),
    )
    def _populate(filter_json):
        state = parse_state(filter_json)
        voids = data.get_voids(state["void_weeks_n"], state["slow_mover_min"])
        if voids.empty and not data.data_available():
            empty_map = charts.state_choropleth(None, "Void dollars by state")
            return [], "—", "—", "—", "—", no_data_notice(), empty_map, ""

        shown = apply_display_filters(voids, state)

        total = shown["void_dollars"].sum() if not shown.empty else 0.0
        count = len(shown)
        stores = shown["store_id"].nunique() if not shown.empty else 0
        never_share = (
            f"{(shown['void_type'] == 'never_scanned').mean():.0%}" if count else "0%"
        )

        callout = _cluster_callout(shown)
        void_map = charts.state_choropleth(
            state_dollars(shown), "Void dollars by state"
        )

        as_of = data.as_of_week()
        as_of_str = as_of.strftime("%Y-%m-%d") if as_of is not None else "—"
        note = (
            f"Methodology: a void is an authorized item with zero scans for "
            f"{state['void_weeks_n']}+ consecutive weeks as of {as_of_str}. "
            f"Opportunity = median weekly dollars of comparable scanning stores "
            f"(same volume tier + region; basis widens when fewer than 3 "
            f"comparables) × weeks dark. Median, not mean — one hot store "
            f"cannot inflate the number. Items whose comparables move fewer "
            f"than {state['slow_mover_min']} units/week are excluded as slow "
            f"movers. Priority = opportunity × fixability."
        )

        rows = shown.to_dict("records")
        for r in rows:
            ls = r.get("last_scan_week")
            r["last_scan_week"] = None if ls is None or str(ls) == "NaT" else str(ls)[:10]
            r["authorized_date"] = str(r.get("authorized_date"))[:10]

        return (
            rows,
            f"${total:,.0f}",
            f"{count:,}",
            f"{stores:,}",
            never_share,
            callout,
            void_map,
            note,
        )


def state_dollars(shown):
    """Aggregate void dollars by store state for the map. The void
    frame carries state from the store universe. Returns an empty
    frame when there is nothing to map."""
    if shown.empty or "state" not in shown.columns:
        return pd.DataFrame(columns=["state", "void_dollars"])
    return (
        shown.dropna(subset=["state"])
        .groupby("state", as_index=False)["void_dollars"]
        .sum()
    )


def _cluster_callout(shown):
    """Surface the mod-reset story when a cluster is present."""
    if shown.empty or shown["cluster_id"].isna().all():
        return None
    clusters = (
        shown[shown["cluster_id"].notna()]
        .groupby("cluster_id", observed=True)
        .agg(
            dollars=("void_dollars", "sum"),
            pairs=("sku", "size"),
            stores=("store_id", "nunique"),
            chain=("chain_name", "first"),
            region=("region", "first"),
        )
        .sort_values("dollars", ascending=False)
    )
    top = clusters.iloc[0]
    return html.Div(
        [
            html.Strong("Cluster detected: "),
            html.Span(
                f"{top['chain']} · {top['region']} has {int(top['pairs'])} "
                f"never-scanned voids across {int(top['stores'])} stores — "
                f"${top['dollars']:,.0f} in opportunity. This pattern is a "
                f"botched shelf reset, not random noise: one reset call "
                f"covers every store on the list."
            ),
        ],
        className="cluster-callout",
    )
