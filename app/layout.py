"""Layout assembly — brand frame, tab navigation, filter bar, content."""

import json
import logging

from dash import Input, Output, callback, dcc, html

from app import data, lailara_frame
from app.app import app
from app.filters import DEFAULT_FILTER_STATE, build_filter_bar, register_filter_callbacks
from app.views import exceptions, rollup, trend

logger = logging.getLogger(__name__)

TAB_LABELS = ["Exception Report", "Summary Rollup", "Trend"]
TAB_IDS = ["exceptions", "rollup", "trend"]


def _build_tabs():
    return dcc.Tabs(
        id="main-tabs",
        value="exceptions",
        children=[
            dcc.Tab(
                label=label,
                value=value,
                className="custom-tab",
                selected_className="custom-tab--selected",
            )
            for label, value in zip(TAB_LABELS, TAB_IDS)
        ],
        className="custom-tabs",
    )


def _build_content_area():
    """Pre-rendered tab panels; a callback toggles display so data
    callbacks always find their targets."""
    return html.Div(
        [
            html.Div(exceptions.layout(), id="tab-panel-exceptions", style={"display": "block"}),
            html.Div(rollup.layout(), id="tab-panel-rollup", style={"display": "none"}),
            html.Div(trend.layout(), id="tab-panel-trend", style={"display": "none"}),
        ]
    )


def _build_narrative_section():
    return html.Details(
        [
            html.Summary("What a void is, and why this list makes money", className="narrative-toggle"),
            html.Div(
                [
                    html.H2("Authorized but not selling", className="narrative-title"),
                    html.P(
                        "Every retailer authorization your brand wins is a store "
                        "that agreed to carry an item. A void is a store where "
                        "that agreement produces no revenue: the item is "
                        "authorized, but it is not scanning. Distribution "
                        "reports count the authorization; the register never "
                        "sees the item. The gap is invisible in top-line "
                        "numbers because nothing declined — the sales simply "
                        "never started.",
                        className="narrative-body",
                    ),
                    html.P(
                        "Void Finder separates two failure modes that need "
                        "different fixes. A never-scanned void is an item that "
                        "was authorized and never sold a unit — usually a "
                        "shelf set that never happened. When never-scanned "
                        "voids cluster in one retailer and region, the cause "
                        "is almost always a single botched mod reset, and one "
                        "broker call covers every store on the list. A "
                        "went-dark void was selling and stopped — a lost "
                        "facing, a phantom out-of-stock, a quiet delist.",
                        className="narrative-body",
                    ),
                    html.P(
                        "Each void is priced from the median weekly velocity "
                        "of comparable scanning stores — same volume tier, "
                        "same region — times the weeks it has been dark. "
                        "Median, not mean, so one hot store cannot inflate "
                        "the claim. The result is a ranked work list: store "
                        "numbers, dollar opportunity, and how fixable each "
                        "gap is. Send the export to your broker and start at "
                        "the top.",
                        className="narrative-body",
                    ),
                ],
                className="narrative-content",
            ),
        ],
        className="narrative-details",
    )


def register_layout():
    """Set app.layout and register all callbacks."""
    stores = data.get_stores() if data.data_available() else None
    if stores is not None and not stores.empty:
        retailer_options = sorted(stores["chain_name"].dropna().unique())
        region_options = sorted(stores["region"].dropna().unique())
    else:
        retailer_options = []
        region_options = []

    inner_layout = html.Div(
        [
            dcc.Store(
                id="filter-state", storage_type="session",
                data=json.dumps(DEFAULT_FILTER_STATE),
            ),
            html.Div(
                [
                    _build_tabs(),
                    build_filter_bar(retailer_options, region_options),
                    _build_content_area(),
                ],
                className="lailara-container",
            ),
            _build_narrative_section(),
        ]
    )

    app.layout = lailara_frame.wrap(
        inner_layout,
        tool_name="Void Finder",
        footer_note="Void detection and dollarization for CPG brands — where are we authorized but not selling?",
        no_container=True,
    )

    register_filter_callbacks()
    exceptions.register_callbacks()
    rollup.register_callbacks()
    trend.register_callbacks()

    from app.export import register_export_callback

    register_export_callback()

    @callback(
        Output("tab-panel-exceptions", "style"),
        Output("tab-panel-rollup", "style"),
        Output("tab-panel-trend", "style"),
        Input("main-tabs", "value"),
    )
    def _toggle_tab_visibility(tab_value):
        show = {"display": "block"}
        hide = {"display": "none"}
        return (
            show if tab_value == "exceptions" else hide,
            show if tab_value == "rollup" else hide,
            show if tab_value == "trend" else hide,
        )
