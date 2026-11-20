"""Sidebar: brand, logged-in manager, navigation, filters, refresh info, logout."""
from __future__ import annotations

import html

import streamlit as st

from auth import authentication as auth
from components.data_loader import clear_caches, data_version
from components.filters import render_filters
from config import settings

PAGES = [
    "📊 Executive Overview",
    "🏢 Branch Performance",
    "💰 Financial Analysis",
    "👥 Customer Analysis",
    "🏦 Loan Analysis",
    "💡 Reports & Insights",
    "📤 Report Export",
    "🗄️ Data Management",
]


def do_logout() -> None:
    auth.logout_session(st.session_state)
    clear_caches()


def render_sidebar(manager):
    sb = st.sidebar
    sb.markdown(f'<div class="sb-brand"><div class="logo">{settings.APP_ICON}</div><div>'
                f'<div class="t1">{settings.APP_SHORT_TITLE}</div>'
                f'<div class="t2">{settings.APP_TITLE}</div></div></div>', unsafe_allow_html=True)
    sb.markdown(f'<div class="sb-user"><div class="n">👤 {html.escape(manager.manager_name)}</div>'
                f'<div class="r">{html.escape(manager.role)} · @{html.escape(manager.username)}</div></div>',
                unsafe_allow_html=True)
    page = sb.radio("Navigation", PAGES, key="nav_page", label_visibility="collapsed")
    sb.divider()
    filters = render_filters(manager)
    with sb.expander("Active filters", expanded=False):
        st.markdown('<div class="sb-filters">' + "<br>".join(html.escape(x) for x in filters.describe())
                    + "</div>", unsafe_allow_html=True)
    sb.markdown(f'<div class="sb-meta">Last data refresh: {html.escape(data_version())}</div>',
                unsafe_allow_html=True)
    sb.write("")
    sb.button("🚪 Logout", on_click=do_logout, key="btn_logout")
    return page, filters
