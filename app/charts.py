"""Plotly figure factories following the Lailara chart rules:
horizontal gridlines only, every data point labeled, compact axis
formats, footnote handled by the surrounding layout."""

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
        # Room for outside bar labels on the right; automargin on the
        # axes grows the rest as labels demand.
        margin=dict(l=10, r=48, t=60, b=40),
        xaxis=_category_axis(),
        yaxis=_value_axis(),
        showlegend=False,
        legend=dict(
            orientation="h", y=1.06, x=0,
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
    layout["xaxis"] = _value_axis(tickformat="$,.0s")
    layout["yaxis"] = _category_axis()
    fig.update_layout(**layout)
    fig.update_layout(height=max(260, 36 * len(d) + 110))
    return fig


def trend_line(df, title):
    """Void count over time. Line chart (temporal x-axis), every point
    labeled, single-series Chicago-20."""
    fig = go.Figure(
        go.Scatter(
            x=df["week_ending"],
            y=df["void_count"],
            mode="lines+markers+text",
            line=dict(color=LL_CHICAGO, width=2),
            marker=dict(color=LL_CHICAGO, size=6),
            text=[f"<b>{v:,}</b>" for v in df["void_count"]],
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
                    tickformat="$,.0s",
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
    layout["xaxis"] = _value_axis(tickformat="$,.0s")
    layout["yaxis"] = _category_axis()
    layout["showlegend"] = True
    layout["barmode"] = "group"
    fig.update_layout(**layout)
    fig.update_layout(height=max(280, 52 * len(pivot) + 130))
    return fig
