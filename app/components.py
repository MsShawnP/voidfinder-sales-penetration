"""Reusable Dash components — grid factory and KPI cards."""

import dash_ag_grid as dag
from dash import html


def data_grid(grid_id, column_defs, aria_label=None):
    """dash-ag-grid with the house configuration: sortable, filterable,
    auto-height, responsive column fit."""
    wrapper_attrs = {}
    if aria_label:
        wrapper_attrs["role"] = "region"
        wrapper_attrs["aria-label"] = aria_label
    grid = dag.AgGrid(
        id=grid_id,
        columnDefs=column_defs,
        rowData=[],
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        columnSize="responsiveSizeToFit",
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 25,
            "paginationPageSizeSelector": [25, 50, 100],
            "domLayout": "autoHeight",
            "rowSelection": {"mode": "singleRow"},
            "animateRows": True,
        },
        style={"width": "100%"},
        className="ag-theme-alpine voidfinder-grid",
    )
    return html.Div(grid, className="grid-wide", **wrapper_attrs)


def kpi_card(label, value_id):
    """Headline number card: serif value, sans uppercase label."""
    return html.Div(
        [
            html.Div("—", id=value_id, className="kpi-value"),
            html.Div(label, className="kpi-label"),
        ],
        className="kpi-card",
    )


def kpi_row(cards):
    return html.Div(cards, className="kpi-row")


def no_data_notice():
    """Branded degraded state — shown when the database is unavailable."""
    return html.Div(
        [
            html.H2("Data temporarily unavailable", className="no-data-title"),
            html.P(
                "The Cinderhaven data warehouse is not answering. "
                "The dashboard will populate automatically once the "
                "connection recovers — no action needed on your side.",
                className="no-data-body",
            ),
        ],
        id="vf-no-data",
        className="no-data-notice",
    )
