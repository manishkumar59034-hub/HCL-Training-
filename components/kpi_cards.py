"""KPI card and insight/answer card renderers."""
from __future__ import annotations

import html

import streamlit as st

from utils.formatting import fmt_pct


def kpi_card(label: str, value: str, delta: float | None = None, delta_label: str = "",
             good_when_up: bool = True, help_text: str = "") -> str:
    delta_html = ""
    if delta is not None:
        up = delta >= 0
        cls = "up" if up == good_when_up else "down"
        arrow = "▲" if up else "▼"
        delta_html = f'<div class="kpi-delta {cls}">{arrow} {fmt_pct(abs(delta))} {html.escape(delta_label)}</div>'
    elif delta_label:
        delta_html = f'<div class="kpi-delta">{html.escape(delta_label)}</div>'
    title = f' title="{html.escape(help_text)}"' if help_text else ""
    return (f'<div class="kpi-card"{title}><div class="kpi-label">{html.escape(label)}</div>'
            f'<div class="kpi-value">{html.escape(value)}</div>{delta_html}</div>')


def kpi_row(cards: list[dict], per_row: int = 4) -> None:
    """cards: list of kwargs for kpi_card."""
    for i in range(0, len(cards), per_row):
        cols = st.columns(per_row)
        for col, card in zip(cols, cards[i:i + per_row]):
            col.markdown(kpi_card(**card), unsafe_allow_html=True)
        st.write("")


def _md_bold(text: str) -> str:
    """Escape text, then turn **x** into <b>x</b>."""
    import re
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(text))


def answer_cards(answers: list[dict]) -> None:
    cls = {"good": "good", "warn": "warn", "bad": "bad", "info": ""}
    for a in answers:
        st.markdown(f'<div class="insight {cls.get(a.get("status"), "")}"><div class="q">{html.escape(a["question"])}</div>'
                    f'<div class="a">{_md_bold(a["answer"])}</div></div>', unsafe_allow_html=True)


def insight_card(category: str, title: str, branch: str, evidence: str, action: str = "") -> None:
    cls = "good" if category == "Positive" else "warn"
    icon = "✅" if category == "Positive" else "⚠️"
    action_html = f'<div class="meta"><b>Recommended action:</b> {html.escape(action)}</div>' if action else ""
    st.markdown(f'<div class="insight {cls}"><div class="q">{icon} {html.escape(title)} '
                f'<span class="badge">{html.escape(branch)}</span></div>'
                f'<div class="a"><b>Why:</b> {html.escape(evidence)}</div>{action_html}</div>',
                unsafe_allow_html=True)


def page_header(title: str, purpose: str) -> None:
    st.title(title)
    st.markdown(f'<div class="page-sub">{html.escape(purpose)}</div>', unsafe_allow_html=True)


def chart_note(text: str) -> None:
    st.markdown(f'<div class="chart-note">{_md_bold(text)}</div>', unsafe_allow_html=True)
