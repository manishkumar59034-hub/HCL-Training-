"""Helpers shared by every page."""
from __future__ import annotations

import streamlit as st

PLOTLY_CONFIG = {"displaylogo": False, "displayModeBar": False}


def show(fig, key: str) -> None:
    st.plotly_chart(fig, key=key, config=PLOTLY_CONFIG)


def no_data(ds) -> bool:
    """Show a friendly message and return True when the filtered data is empty."""
    if ds.is_empty:
        st.warning("No data matches the selected filters. Widen the date range or clear some filters "
                   "(sidebar → Reset filters).")
        return True
    return False
