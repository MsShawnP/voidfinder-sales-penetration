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
    LL_TEXT_SEC,
    LL_TOKYO,
)


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
        margin=dict(l=10, r=10, t=60, b=40),
        xaxis=dict(showgrid=False, zeroline=False, color=LL_TEXT_SEC),
        yaxis=dict(
            showgrid=True,
            gridcolor=LL_GRIDLINE,
            zeroline=False,
            color=LL_TEXT_SEC,
        ),
        showlegend=False,
    )


def hbar_dollars(df, category_col, value_col, title):
    """Horizontal bar chart of dollars by category, labeled per bar,
    largest at top, single-series Chicago-20."""
    d = df.sort_values(value_col, ascending=True)
    fig = go.Figure(
        go.Bar(
            x=d[value_col],
            y=d[category_col],
            orientation="h",
            marker_color=LL_CHICAGO,
            text=[f"${v:,.0f}" for v in d[value_col]],
            textposition="outside",
            textfont=dict(family=LL_SANS_FAMILY, size=12),
            cliponaxis=False,
        )
    )
    layout = _base_layout(title)
    # Horizontal bars: the value axis is x, so gridlines live on x here
    # (the design rule is "one axis of gridlines, following the values").
    layout["xaxis"] = dict(
        showgrid=True, gridcolor=LL_GRIDLINE, zeroline=False,
        color=LL_TEXT_SEC, tickformat="$,.0s",
    )
    layout["yaxis"] = dict(showgrid=False, zeroline=False, color=LL_TEXT_SEC)
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
            text=[f"{v:,}" for v in df["void_count"]],
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
            text=[f"${v:,.0f}" for v in pivot["never_scanned"]],
            textposition="outside",
            textfont=dict(family=LL_SANS_FAMILY, size=11),
            cliponaxis=False,
        )
    )
    fig.add_trace(
        go.Bar(
            x=pivot["went_dark"], y=pivot.index, orientation="h",
            name="Went dark", marker_color=LL_HK,
            text=[f"${v:,.0f}" for v in pivot["went_dark"]],
            textposition="outside",
            textfont=dict(family=LL_SANS_FAMILY, size=11),
            cliponaxis=False,
        )
    )
    layout = _base_layout(title)
    layout["xaxis"] = dict(
        showgrid=True, gridcolor=LL_GRIDLINE, zeroline=False,
        color=LL_TEXT_SEC, tickformat="$,.0s",
    )
    layout["yaxis"] = dict(showgrid=False, zeroline=False, color=LL_TEXT_SEC)
    layout["showlegend"] = True
    layout["legend"] = dict(orientation="h", y=1.06, x=0, font=dict(size=12))
    layout["barmode"] = "group"
    fig.update_layout(**layout)
    fig.update_layout(height=max(280, 52 * len(pivot) + 130))
    return fig
