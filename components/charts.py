"""
Plotly chart builders with one consistent look.

Design rules: one y-axis per chart (never dual-axis), thin lines, recessive grid,
hover tooltips on every mark, fixed colours per entity (region / category),
Indian-number tick formatting via ₹ Lakh / Crore labels.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from config import settings

FONT = dict(family="Inter, Segoe UI, sans-serif", size=12, color=settings.CHART_TEXT)


def _crore_axis(series: pd.Series) -> tuple[float, str]:
    m = float(pd.Series(series).abs().max() or 0)
    if m >= 1e7:
        return 1e7, "₹ Crore"
    if m >= 1e5:
        return 1e5, "₹ Lakh"
    return 1, "₹"


def style(fig: go.Figure, title: str = "", height: int = 360, y_title: str | None = None,
          x_title: str | None = None, legend: bool = True) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=settings.COLOR_NAVY), x=0, xanchor="left"),
        height=height, margin=dict(l=10, r=10, t=48 if title else 16, b=10),
        paper_bgcolor="white", plot_bgcolor="white", font=FONT,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, title=None),
        showlegend=legend, hoverlabel=dict(bgcolor="white", font_size=12),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor=settings.CHART_AXIS, title=x_title)
    fig.update_yaxes(gridcolor=settings.CHART_GRID, zeroline=False, linecolor=settings.CHART_AXIS,
                     title=y_title)
    return fig


def empty_figure(message: str = "No data for the selected filters") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False, font=dict(size=13, color=settings.COLOR_GREY))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style(fig, height=260, legend=False)


def money_lines(df: pd.DataFrame, x: str, cols: dict[str, str], title: str, height: int = 340) -> go.Figure:
    """Line chart of one or more money series (same unit -> one axis)."""
    if df is None or df.empty:
        return empty_figure()
    scale, unit = _crore_axis(pd.concat([df[c] for c in cols]))
    fig = go.Figure()
    for i, (col, label) in enumerate(cols.items()):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col] / scale, name=label, mode="lines+markers",
            line=dict(width=2, color=settings.CHART_SEQUENCE[i]), marker=dict(size=8),
            hovertemplate=f"%{{x|%b %Y}}<br>{label}: %{{y:,.2f}} {unit.replace('₹ ', '')}<extra></extra>"))
    fig.update_xaxes(tickformat="%b %Y")
    return style(fig, title, height, y_title=unit, legend=len(cols) > 1)


def pct_line(df: pd.DataFrame, x: str, col: str, title: str, label: str, ref: float | None = None,
             height: int = 320) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure(go.Scatter(x=df[x], y=df[col], mode="lines+markers", name=label,
                               line=dict(width=2, color=settings.CHART_PRIMARY), marker=dict(size=8),
                               hovertemplate=f"%{{x|%b %Y}}<br>{label}: %{{y:.1f}}%<extra></extra>"))
    if ref is not None:
        fig.add_hline(y=ref, line_dash="dot", line_color=settings.COLOR_GREY,
                      annotation_text=f"{ref:.0f}%", annotation_position="top left")
    fig.update_xaxes(tickformat="%b %Y")
    return style(fig, title, height, y_title="%", legend=False)


def count_line(df: pd.DataFrame, x: str, cols: dict[str, str], title: str, y_title: str,
               height: int = 320, bars: bool = False) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    fig = go.Figure()
    for i, (col, label) in enumerate(cols.items()):
        if bars:
            fig.add_trace(go.Bar(x=df[x], y=df[col], name=label, marker_color=settings.CHART_SEQUENCE[i],
                                 hovertemplate=f"%{{x|%b %Y}}<br>{label}: %{{y:,}}<extra></extra>"))
        else:
            fig.add_trace(go.Scatter(x=df[x], y=df[col], name=label, mode="lines+markers",
                                     line=dict(width=2, color=settings.CHART_SEQUENCE[i]), marker=dict(size=8),
                                     hovertemplate=f"%{{x|%b %Y}}<br>{label}: %{{y:,}}<extra></extra>"))
    fig.update_xaxes(tickformat="%b %Y")
    if bars:
        fig.update_layout(barmode="group")
    return style(fig, title, height, y_title=y_title, legend=len(cols) > 1)


def branch_bar(df: pd.DataFrame, value: str, title: str, money: bool = True, label_col: str = "branch_name",
               color_col: str | None = None, color_map: dict | None = None, height: int | None = None,
               value_label: str = "", ref: float | None = None, suffix: str = "") -> go.Figure:
    """Horizontal bar per branch, sorted; optional fixed colour mapping (e.g. category)."""
    if df is None or df.empty:
        return empty_figure()
    d = df.dropna(subset=[value]).sort_values(value)
    scale, unit = _crore_axis(d[value]) if money else (1, value_label)
    d = d.assign(_v=d[value] / scale)
    height = height or max(300, 26 * len(d) + 90)
    hover_unit = unit.replace("₹ ", "") if money else suffix
    if color_col:
        fig = px.bar(d, x="_v", y=label_col, orientation="h", color=color_col,
                     color_discrete_map=color_map or {}, category_orders={label_col: list(d[label_col])})
        fig.update_traces(hovertemplate=f"%{{y}}<br>{value_label or value}: %{{x:,.2f}} {hover_unit}<extra></extra>")
    else:
        fig = go.Figure(go.Bar(x=d["_v"], y=d[label_col], orientation="h", marker_color=settings.CHART_PRIMARY,
                               hovertemplate=f"%{{y}}<br>{value_label or value}: %{{x:,.2f}} {hover_unit}<extra></extra>"))
    if ref is not None:
        fig.add_vline(x=ref, line_dash="dot", line_color=settings.COLOR_GREY,
                      annotation_text=f"{ref:g}{suffix}", annotation_position="top")
    return style(fig, title, height, x_title=unit if money else value_label, legend=bool(color_col))


def grouped_branch_bar(df: pd.DataFrame, cols: dict[str, str], title: str, label_col: str = "branch_name",
                       height: int = 400) -> go.Figure:
    """Vertical grouped bars, same money unit (e.g. revenue vs target)."""
    if df is None or df.empty:
        return empty_figure()
    scale, unit = _crore_axis(pd.concat([df[c] for c in cols]))
    fig = go.Figure()
    for i, (col, label) in enumerate(cols.items()):
        fig.add_trace(go.Bar(x=df[label_col], y=df[col] / scale, name=label,
                             marker_color=settings.CHART_SEQUENCE[i],
                             hovertemplate=f"%{{x}}<br>{label}: %{{y:,.2f}} {unit.replace('₹ ', '')}<extra></extra>"))
    fig.update_layout(barmode="group", bargroupgap=0.08)
    fig.update_xaxes(tickangle=-35)
    return style(fig, title, height, y_title=unit)


def category_bar(df: pd.DataFrame, cat: str, value: str, title: str, value_label: str,
                 color_map: dict | None = None, height: int = 320, money: bool = False,
                 horizontal: bool = True) -> go.Figure:
    if df is None or df.empty:
        return empty_figure()
    d = df.sort_values(value, ascending=horizontal)
    scale, unit = _crore_axis(d[value]) if money else (1, value_label)
    d = d.assign(_v=d[value] / scale)
    colors = [ (color_map or {}).get(c, settings.CHART_PRIMARY) for c in d[cat]]
    if horizontal:
        fig = go.Figure(go.Bar(x=d["_v"], y=d[cat], orientation="h", marker_color=colors,
                               hovertemplate=f"%{{y}}<br>{value_label}: %{{x:,.2f}}<extra></extra>"))
        return style(fig, title, height, x_title=unit, legend=False)
    fig = go.Figure(go.Bar(x=d[cat], y=d["_v"], marker_color=colors,
                           hovertemplate=f"%{{x}}<br>{value_label}: %{{y:,.2f}}<extra></extra>"))
    return style(fig, title, height, y_title=unit, legend=False)


def small_multiples(df: pd.DataFrame, x: str, cols: dict[str, str], title: str, height: int = 320) -> go.Figure:
    """Side-by-side panels, each with its OWN y-axis - used when two money measures
    differ greatly in scale (e.g. deposits vs loan disbursement). Not a dual-axis chart."""
    from plotly.subplots import make_subplots
    if df is None or df.empty:
        return empty_figure()
    fig = make_subplots(rows=1, cols=len(cols), subplot_titles=list(cols.values()), horizontal_spacing=0.1)
    for i, (col, label) in enumerate(cols.items(), start=1):
        scale, unit = _crore_axis(df[col])
        fig.add_trace(go.Scatter(x=df[x], y=df[col] / scale, mode="lines+markers", name=label,
                                 line=dict(width=2, color=settings.CHART_SEQUENCE[i - 1]), marker=dict(size=8),
                                 hovertemplate=f"%{{x|%b %Y}}<br>{label}: %{{y:,.2f}} {unit.replace('₹ ', '')}<extra></extra>"),
                      row=1, col=i)
        fig.update_yaxes(title_text=unit, row=1, col=i)
    fig.update_xaxes(tickformat="%b %Y")
    fig.update_annotations(font=dict(size=12, color=settings.CHART_TEXT))
    return style(fig, title, height, legend=False)
