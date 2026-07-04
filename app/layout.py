"""Layout assembly — brand frame, tab navigation, filter bar, content."""

import json
import logging

from dash import Input, Output, callback, dcc, html

from app import data, lailara_frame
from app.app import app
from app.filters import (
    DEFAULT_FILTER_STATE,
    build_filter_bar,
    parse_state,
    register_filter_callbacks,
)
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


def build_hero(voids):
    """Executive hero: one number, one sentence of meaning, one action.
    Built from the unfiltered void list so it always describes the whole
    brand. Returns None when there is no data to summarize."""
    if voids is None or voids.empty:
        return None
    total = voids["void_dollars"].sum()
    stores = voids["store_id"].nunique()

    children = [
        html.H1(
            [
                html.Span(f"${total:,.0f}", className="hero-number"),
                " in lost sales — from stores that already approved your "
                "product.",
            ],
            className="hero-headline",
        ),
        html.P(
            f"In {stores:,} stores, the retailer said yes: Cinderhaven's "
            "items are authorized for the shelf. But they're not selling "
            "there — not stocked, or not scanning. You're losing sales you "
            "should already be getting, with no new deal to close. The fix "
            "is just getting the product back on the shelf.",
            className="hero-subhead",
        ),
    ]

    clustered = voids[voids["cluster_id"].notna()]
    if not clustered.empty:
        top_id = (
            clustered.groupby("cluster_id", observed=True)["void_dollars"]
            .sum()
            .idxmax()
        )
        top = clustered[clustered["cluster_id"] == top_id]
        chain = top["chain_name"].iloc[0]
        region = top["region"].iloc[0]
        children.append(
            html.P(
                [
                    "The largest single pattern — ",
                    html.Strong(
                        f"{len(top)} never-scanned voids clustered in "
                        f"{chain}'s {region} region "
                        f"(${top['void_dollars'].sum():,.0f})"
                    ),
                    " — is the signature of a botched shelf reset, not "
                    "random bad luck. That's one phone call to one broker, "
                    f"not {stores}.",
                ],
                className="hero-action",
            )
        )
    return children


def _build_why_panel():
    return html.Details(
        [
            html.Summary(
                "Why this list makes money",
                className="narrative-toggle",
            ),
            html.Div(
                [
                    html.P(
                        "A void is the cleanest line on your P&L, because "
                        "the hard part is already done.",
                        className="narrative-body",
                    ),
                    html.P(
                        "A deduction you have to dispute. A slow seller you "
                        "have to fix with price, placement, or promotion. A "
                        "void you just have to put back on the shelf — you "
                        "already won the authorization and paid the "
                        "slotting. At a 3–5% net margin, recovering $366K "
                        "of fully-authorized, unsold distribution is worth "
                        "more than several million in new top-line revenue "
                        "you'd have to win from scratch.",
                        className="narrative-body",
                    ),
                    html.P(
                        "And voids compound silently. Every week an "
                        "authorized item isn't scanning is revenue that "
                        "never comes back — there's no dispute window, no "
                        "make-good. The only variable is how long before "
                        "someone notices. $366,175 is 0.37% of Cinderhaven's "
                        "sales sitting in distribution it already owns — and "
                        "the first time most brands measure this, the number "
                        "is bigger than they expect.",
                        className="narrative-body",
                    ),
                ],
                className="narrative-content",
            ),
        ],
        className="narrative-details",
    )


_GLOSSARY = [
    (
        "Void",
        "A store authorized to carry an item where it isn't scanning: "
        "zero sales for a set number of consecutive weeks. Not the same "
        "as a slow mover — a store selling one unit a month isn't a "
        "void; a store selling nothing while authorized is.",
    ),
    (
        "Never-scanned void",
        "Authorized, but never scanned even once. Almost always means "
        "the product was never physically set on the shelf — a botched "
        "planogram reset or a failed new-item setup. These cluster (one "
        "region, one reset), which is why they're the highest-leverage "
        "fix.",
    ),
    (
        "Went-dark void",
        "Was scanning, then stopped. Usually a multi-week out-of-stock, "
        "a lost shelf tag, or an item deleted locally at the store. "
        "These tend to be scattered rather than clustered.",
    ),
    (
        "Dollarized opportunity",
        "What each void is costing you: the median weekly sales of "
        "comparable scanning stores (same size tier and region) "
        "multiplied by the number of weeks the store has been void. In "
        "plain terms — \"stores like this one that are selling move "
        "this much, so this void is costing you that much.\"",
    ),
    (
        "Why median, not average",
        "A few unusually high-volume stores would inflate the average "
        "and overstate the opportunity. The median keeps the figure "
        "conservative and defensible, so it holds up when your broker "
        "checks it.",
    ),
    (
        "Void threshold",
        "The number of consecutive zero-scan weeks that separates a "
        "real void from a temporary blip. Adjustable: stricter finds "
        "only long-dead stores, looser catches problems earlier.",
    ),
    (
        "Priority rank",
        "Voids are ordered by dollar opportunity and fixability, so "
        "the top of the list returns the most recoverable money "
        "fastest.",
    ),
]


def _build_glossary_panel():
    entries = []
    for term, definition in _GLOSSARY:
        entries.append(html.Dt(term, className="glossary-term"))
        entries.append(html.Dd(definition, className="glossary-def"))
    return html.Details(
        [
            html.Summary(
                "What a void is",
                className="narrative-toggle",
            ),
            html.Div(html.Dl(entries), className="narrative-content"),
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
                    html.Div(id="hero-summary", className="hero"),
                    _build_tabs(),
                    build_filter_bar(retailer_options, region_options),
                    _build_content_area(),
                ],
                className="lailara-container",
            ),
            _build_why_panel(),
            _build_glossary_panel(),
        ]
    )

    app.layout = lailara_frame.wrap(
        inner_layout,
        tool_name="Void Finder",
        footer_note="Void detection and dollarization for CPG brands — where are we authorized but not selling?",
        no_container=True,
        disclosure=(
            "Built on Cinderhaven Provisions, a synthetic ~$99M specialty "
            "food brand (50 SKUs, 6 retailers, 640 doors). The company is "
            "invented; the void-detection logic, the comparable-store "
            "dollarization, and the math are exactly what a real "
            "engagement uses."
        ),
    )

    register_filter_callbacks()
    exceptions.register_callbacks()
    rollup.register_callbacks()
    trend.register_callbacks()

    from app.export import register_export_callback

    register_export_callback()

    @callback(
        Output("hero-summary", "children"),
        Input("filter-state", "data"),
    )
    def _populate_hero(filter_json):
        # Whole-brand statement: honors the analytical dials (void
        # window, slow-mover floor) but ignores retailer/region display
        # filters — the hero always describes the full picture.
        state = parse_state(filter_json)
        voids = data.get_voids(state["void_weeks_n"], state["slow_mover_min"])
        return build_hero(voids)

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
