"""Plotly figure factories following the Lailara chart rules:
horizontal gridlines only, every data point labeled, compact axis
formats, footnote handled by the surrounding layout."""

import math

import plotly.graph_objects as go

from app.constants import (
    LL_CANVAS,
    LL_CHICAGO,
    LL_GRIDLINE,
    LL_HK,
    LL_INK,
    LL_SANS_FAMILY,
    LL_SEQ_TOKYO,
    LL_SERIF_FAMILY,
    LL_SURFACE,
    LL_TEXT,
    LL_TEXT_SEC,
    LL_TOKYO,
)


# Shared axis defaults. automargin is the truncation kill switch: the
# margin grows to fit whatever the tick labels need, so long category
# names and legend text never ellipsize. Every chart's axis dict MUST
# come from these helpers — per-chart overrides that rebuild the dict
# from scratch are how the truncation bug kept coming back.


def _value_axis(**overrides):
    axis = dict(
        showgrid=True, gridcolor=LL_GRIDLINE, zeroline=False,
        color=LL_TEXT_SEC, automargin=True,
    )
    axis.update(overrides)
    return axis


def _category_axis(**overrides):
    axis = dict(
        showgrid=False, zeroline=False, color=LL_TEXT_SEC, automargin=True,
    )
    axis.update(overrides)
    return axis


def _bold_dollars(values):
    """Bold data labels for dollar bars."""
    return [f"<b>${v:,.0f}</b>" for v in values]


# ── Dollar axis ticks ───────────────────────────────────────────────
# The old "$,.0s" tickformat rounded to ONE significant figure, so
# $120k and $150k both rendered "$100k"/"$200k" — adjacent ticks
# collided. We compute explicit, evenly-spaced ticks and hand-format
# each label at its true value, so no two ticks can ever read the same.

_TICK_STEP_MULTIPLES = (1, 2, 2.5, 5, 10)


def _nice_step(max_value, target_ticks):
    """A human-round step (1/2/2.5/5 × 10ⁿ) giving about target_ticks
    intervals across max_value."""
    raw = max_value / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    for m in _TICK_STEP_MULTIPLES:
        if m * magnitude >= raw:
            return m * magnitude
    return 10 * magnitude


def _fmt_dollar_tick(value):
    """A dollar tick's true value, compactly: $0, $50k, $2.5k, $1.5M —
    no SI rounding, so distinct values never share a label."""
    value = float(value)
    if value == 0:
        return "$0"
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    if magnitude >= 1e6:
        body = f"{magnitude / 1e6:.1f}".rstrip("0").rstrip(".") + "M"
    elif magnitude >= 1e3:
        body = f"{magnitude / 1e3:.1f}".rstrip("0").rstrip(".") + "k"
    else:
        body = f"{magnitude:,.0f}"
    return f"{sign}${body}"


def _dollar_ticks(max_value, target_ticks=5, headroom=1.12):
    """Explicit dollar-axis ticks. Returns (tickvals, ticktext,
    axis_max). Ticks are evenly spaced on a human-round step, each
    labeled with its true value; axis_max sits a step-aligned margin
    above the largest bar so the bar and its outside label always fit."""
    if not max_value or max_value <= 0:
        return [0.0], ["$0"], 1.0
    step = _nice_step(max_value, target_ticks)
    axis_max = math.ceil((max_value * headroom) / step) * step
    count = int(round(axis_max / step))
    vals = [round(i * step, 6) for i in range(count + 1)]
    text = [_fmt_dollar_tick(v) for v in vals]
    return vals, text, axis_max


def _dollar_axis(max_value, **overrides):
    """A value axis with explicit, non-colliding dollar ticks that clear
    the largest bar."""
    vals, text, axis_max = _dollar_ticks(max_value)
    return _value_axis(
        tickmode="array", tickvals=vals, ticktext=text,
        range=[0, axis_max], **overrides,
    )


# Horizontal-bar y-axis labels are category names (product, retailer,
# region) that can be long. Plotly's automargin is supposed to reserve
# room for them, but it measures tick-label widths at first paint —
# and these panels are pre-rendered while their tab is display:none, so
# the measurement comes back short and long labels clip. We therefore
# reserve the left margin deterministically from the label lengths and
# leave automargin on as a backstop. ~7px per character at the 12px
# label font, plus room for the tick gap.
_LEFT_MARGIN_BASE = 48
_PX_PER_CHAR = 7
_LEFT_MARGIN_PAD = 28
_LEFT_MARGIN_CAP = 340


def _left_margin_for(labels) -> int:
    """A left margin wide enough to render the longest category label in
    full, floored at the base and capped so the plot never collapses."""
    longest = max((len(str(v)) for v in labels), default=0)
    needed = longest * _PX_PER_CHAR + _LEFT_MARGIN_PAD
    return int(min(max(_LEFT_MARGIN_BASE, needed), _LEFT_MARGIN_CAP))


def _base_layout(title):
    return dict(
        title=dict(
            text=title,
            font=dict(family=LL_SERIF_FAMILY, size=22, color=LL_INK),
            x=0,
            xanchor="left",
        ),
        font=dict(family=LL_SANS_FAMILY, size=12, color=LL_TEXT_SEC),
        paper_bgcolor=LL_CANVAS,
        plot_bgcolor=LL_CANVAS,
        # r: room for outside bar labels. l: a floor for the y-axis
        # category labels on horizontal-bar charts — automargin (on BOTH
        # axes below) grows it further for long names, but the floor
        # keeps short labels off the left edge before that kicks in.
        # Both axes carry automargin=True so no tick label ever clips;
        # see the tab-show resize callback in layout.py for why a relayout
        # is also forced when a hidden tab becomes visible.
        margin=dict(l=48, r=48, t=60, b=40),
        xaxis=_category_axis(),
        yaxis=_value_axis(),
        showlegend=False,
        # Legend below the plot, horizontal. A top legend sat on top of
        # the tallest bar; below the x-axis it can never overlap the
        # bars. Charts that turn the legend on must widen margin.b to
        # seat it (see split_bars_by_type).
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.18, x=0, xanchor="left",
            font=dict(family=LL_SANS_FAMILY, size=12),
            itemsizing="constant",
        ),
    )


def hbar_dollars(df, category_col, value_col, title, color_map=None):
    """Horizontal bar chart of dollars by category, labeled per bar,
    largest at top. Single-series Chicago-20 by default; color_map
    ({category: hex}) keys bars to the palette other charts use for
    the same categories, so the tabs read as one product."""
    d = df.sort_values(value_col, ascending=True)
    if color_map:
        bar_colors = [color_map.get(c, LL_CHICAGO) for c in d[category_col]]
    else:
        bar_colors = LL_CHICAGO
    fig = go.Figure(
        go.Bar(
            x=d[value_col],
            y=d[category_col],
            orientation="h",
            marker_color=bar_colors,
            text=_bold_dollars(d[value_col]),
            textposition="outside",
            textfont=dict(family=LL_SANS_FAMILY, size=12, color=LL_TEXT),
            cliponaxis=False,
        )
    )
    layout = _base_layout(title)
    # Horizontal bars: the value axis is x, so gridlines live on x here
    # (the design rule is "one axis of gridlines, following the values").
    max_value = float(d[value_col].max()) if not d.empty else 0.0
    layout["xaxis"] = _dollar_axis(max_value)
    layout["yaxis"] = _category_axis()
    layout["margin"]["l"] = _left_margin_for(d[category_col])
    fig.update_layout(**layout)
    fig.update_layout(height=max(260, 36 * len(d) + 110))
    return fig


def trend_line(df, title, max_labels=26):
    """Void count over time. Line chart (temporal x-axis), single-series
    Chicago-20. Every point is labeled up to max_labels; longer windows
    (a full year, all history) thin the text to every k-th point so the
    labels never collide, while the line and markers stay continuous."""
    counts = list(df["void_count"])
    n = len(counts)
    step = max(1, -(-n // max_labels))  # ceil(n / max_labels)
    if step == 1:
        text = [f"<b>{v:,}</b>" for v in counts]
        marker_size = 6
    else:
        text = [
            f"<b>{v:,}</b>" if (i % step == 0 or i == n - 1) else ""
            for i, v in enumerate(counts)
        ]
        marker_size = 4
    fig = go.Figure(
        go.Scatter(
            x=df["week_ending"],
            y=df["void_count"],
            mode="lines+markers+text",
            line=dict(color=LL_CHICAGO, width=2),
            marker=dict(color=LL_CHICAGO, size=marker_size),
            text=text,
            textposition="top center",
            textfont=dict(family=LL_SANS_FAMILY, size=11, color=LL_TEXT_SEC),
            cliponaxis=False,
        )
    )
    layout = _base_layout(title)
    layout["yaxis"]["rangemode"] = "tozero"
    fig.update_layout(**layout)
    fig.update_layout(height=380)
    return fig


def state_choropleth(df, title):
    """US state map of void dollars. Sequential Tokyo ramp — loss data,
    darkest = largest. Expects columns: state (2-letter), void_dollars.
    Exact values live in the hover; the takeaway line below the map
    carries the finding."""
    fig = go.Figure()
    if df is not None and not df.empty:
        # Evenly spaced stops across the Tokyo 85→5 ramp.
        n = len(LL_SEQ_TOKYO)
        colorscale = [
            (i / (n - 1), color) for i, color in enumerate(LL_SEQ_TOKYO)
        ]
        # Explicit true-value ticks — same reason as the bar axes: the
        # SI formatter collapsed adjacent ticks to the same label.
        bar_vals, bar_text, _ = _dollar_ticks(float(df["void_dollars"].max()))
        fig.add_trace(
            go.Choropleth(
                locations=df["state"],
                z=df["void_dollars"],
                locationmode="USA-states",
                colorscale=colorscale,
                marker_line_color=LL_CANVAS,
                marker_line_width=0.8,
                colorbar=dict(
                    title=dict(text="Void $", font=dict(size=12)),
                    tickmode="array",
                    tickvals=bar_vals,
                    ticktext=bar_text,
                    thickness=12,
                    outlinewidth=0,
                ),
                hovertemplate="%{location}: %{z:$,.0f}<extra></extra>",
            )
        )
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family=LL_SERIF_FAMILY, size=22, color=LL_INK),
            x=0,
            xanchor="left",
        ),
        font=dict(family=LL_SANS_FAMILY, size=12, color=LL_TEXT_SEC),
        paper_bgcolor=LL_CANVAS,
        margin=dict(l=10, r=10, t=60, b=10),
        height=420,
        geo=dict(
            scope="usa",
            bgcolor=LL_CANVAS,
            landcolor=LL_SURFACE,
            lakecolor=LL_CANVAS,
            showlakes=True,
            subunitcolor=LL_GRIDLINE,
        ),
    )
    return fig


def split_bars_by_type(df, category_col, title):
    """Grouped horizontal bars: never-scanned (Tokyo) vs went-dark
    (Hong Kong) void dollars per category."""
    pivot = (
        df.pivot_table(
            index=category_col, columns="void_type", values="void_dollars",
            aggfunc="sum", fill_value=0.0, observed=True,
        )
        .reindex(columns=["never_scanned", "went_dark"], fill_value=0.0)
        .sort_values(by=["never_scanned", "went_dark"], ascending=True)
    )
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=pivot["never_scanned"], y=pivot.index, orientation="h",
            name="Never scanned", marker_color=LL_TOKYO,
            text=_bold_dollars(pivot["never_scanned"]),
            textposition="outside",
            textfont=dict(family=LL_SANS_FAMILY, size=11, color=LL_TEXT),
            cliponaxis=False,
        )
    )
    fig.add_trace(
        go.Bar(
            x=pivot["went_dark"], y=pivot.index, orientation="h",
            name="Went dark", marker_color=LL_HK,
            text=_bold_dollars(pivot["went_dark"]),
            textposition="outside",
            textfont=dict(family=LL_SANS_FAMILY, size=11, color=LL_TEXT),
            cliponaxis=False,
        )
    )
    layout = _base_layout(title)
    max_value = float(pivot.to_numpy().max()) if pivot.size else 0.0
    layout["xaxis"] = _dollar_axis(max_value)
    layout["yaxis"] = _category_axis()
    layout["showlegend"] = True
    layout["barmode"] = "group"
    # Bottom legend needs room under the x-axis ticks so it clears the
    # plotted bars entirely; the left margin is sized to the category
    # names so they never clip.
    layout["margin"] = dict(l=_left_margin_for(pivot.index), r=48, t=60, b=96)
    fig.update_layout(**layout)
    fig.update_layout(height=max(280, 52 * len(pivot) + 130) + 40)
    return fig
