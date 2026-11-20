"""
Financial analysis: trend direction and answers to the Financial Analysis
page's business questions, generated from the filtered data.
"""
from __future__ import annotations

import pandas as pd

from analytics import kpi_calculations as kpi
from config import settings
from utils.formatting import fmt_inr, fmt_pct


def trend_direction(series: pd.Series, flat_band: float = 1.0) -> tuple[str, float | None]:
    """Classify a monthly series as increasing / decreasing / stable."""
    change = kpi.period_change(series)
    if change is None:
        return "not enough data", None
    if change > flat_band:
        return "increasing", change
    if change < -flat_band:
        return "decreasing", change
    return "stable", change


def financial_answers(fin: pd.DataFrame, summary: pd.DataFrame) -> list[dict]:
    """Return a list of {question, answer, status} dicts (status: good/warn/info)."""
    answers: list[dict] = []
    if fin is None or fin.empty or summary is None or summary.empty:
        return [{"question": "Financial analysis", "answer": "No financial data for the selected filters.",
                 "status": "info"}]
    m = kpi.monthly_financials(fin)

    direction, change = trend_direction(m["revenue"])
    answers.append({
        "question": "Is revenue increasing or decreasing?",
        "answer": (f"Revenue is **{direction}** across the period ({fmt_pct(change, signed=True)}, "
                   f"comparing the average of the last 3 months with the first 3)."
                   if change is not None else "Not enough months selected to judge a trend."),
        "status": "good" if direction == "increasing" else ("warn" if direction == "decreasing" else "info"),
    })

    rev_c, exp_c = kpi.period_change(m["revenue"]), kpi.period_change(m["expenses"])
    if rev_c is not None and exp_c is not None:
        faster = exp_c > rev_c
        answers.append({
            "question": "Are expenses increasing faster than revenue?",
            "answer": (f"{'**Yes**' if faster else '**No**'} — expenses changed {fmt_pct(exp_c, signed=True)} "
                       f"vs revenue {fmt_pct(rev_c, signed=True)}."),
            "status": "warn" if faster else "good",
        })

    top = summary.sort_values("profit", ascending=False).head(3)
    answers.append({
        "question": "Which branches generate the highest profit?",
        "answer": ", ".join(f"**{r.branch_name}** ({fmt_inr(r.profit, short=True)})" for r in top.itertuples()),
        "status": "good",
    })

    low = summary.dropna(subset=["profit_margin"]).sort_values("profit_margin").head(3)
    answers.append({
        "question": "Which branches have the lowest profit margin?",
        "answer": ", ".join(f"**{r.branch_name}** ({fmt_pct(r.profit_margin)})" for r in low.itertuples()),
        "status": "warn",
    })

    d_dir, d_change = trend_direction(m["deposits"])
    answers.append({
        "question": "Are deposits growing?",
        "answer": (f"Monthly deposit mobilisation is **{d_dir}** ({fmt_pct(d_change, signed=True)})."
                   if d_change is not None else "Not enough months selected to judge a trend."),
        "status": "good" if d_dir == "increasing" else ("warn" if d_dir == "decreasing" else "info"),
    })

    below = summary[summary["target_achievement"] < settings.HIGH_PERFORMER_THRESHOLD] \
        .sort_values("target_achievement")
    answers.append({
        "question": "Which branches are not meeting their targets?",
        "answer": (f"{len(below)} of {len(summary)} branches are below 100% of target: "
                   + ", ".join(f"**{r.branch_name}** ({fmt_pct(r.target_achievement)})"
                               for r in below.head(6).itertuples())
                   + (" …" if len(below) > 6 else "")) if len(below) else "All selected branches met their targets.",
        "status": "warn" if len(below) else "good",
    })

    high = high_expense_branches(summary)
    answers.append({
        "question": "Which branches have unusually high expenses?",
        "answer": (", ".join(f"**{r.branch_name}** (expenses = {fmt_pct(r.expense_ratio)} of revenue)"
                             for r in high.itertuples())
                   if len(high) else
                   f"No branch spends more than {settings.HIGH_EXPENSE_RATIO_THRESHOLD:.0f}% of its revenue."),
        "status": "warn" if len(high) else "good",
    })
    return answers


def high_expense_branches(summary: pd.DataFrame) -> pd.DataFrame:
    """Branches whose expense ratio exceeds the threshold OR is > 1.5 std above the mean."""
    if summary is None or summary.empty:
        return pd.DataFrame()
    s = summary.dropna(subset=["expense_ratio"])
    if s.empty:
        return s
    cutoff = settings.HIGH_EXPENSE_RATIO_THRESHOLD
    if len(s) >= 4:
        cutoff = min(cutoff, s["expense_ratio"].mean() + 1.5 * s["expense_ratio"].std())
    return s[s["expense_ratio"] > cutoff].sort_values("expense_ratio", ascending=False)
