"""Login screen and safe first-time setup screen. Nothing else is rendered before login."""
from __future__ import annotations

import streamlit as st

from auth import authentication as auth
from config import settings


def _header(subtitle: str) -> None:
    st.markdown(f'<div class="login-logo">{settings.APP_ICON}</div>'
                f'<div class="login-title">{settings.APP_TITLE}</div>'
                f'<div class="login-sub">{subtitle}</div>', unsafe_allow_html=True)


def render_login() -> None:
    _, mid, _ = st.columns([1, 1.25, 1])
    with mid:
        st.write("")
        st.write("")
        with st.container(border=True):
            _header("Manager sign-in")
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", key="login_username", autocomplete="username")
                password = st.text_input("Password", type="password", key="login_password",
                                         autocomplete="current-password")
                submitted = st.form_submit_button("Login", type="primary", use_container_width=True)
            if submitted:
                result = auth.authenticate(username, password)
                if result.success:
                    st.session_state.pop("login_password", None)
                    auth.login_session(st.session_state, result.manager)
                    st.rerun()
                else:
                    st.error(result.message)
            st.markdown('<div class="login-auth">🔒 Authorized Managers Only</div>', unsafe_allow_html=True)
        st.caption("Academic demo application with synthetic data. Access attempts are rate-limited.")


def render_first_time_setup() -> None:
    """Shown ONLY when the managers table is empty: create the first Administrator."""
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        with st.container(border=True):
            _header("First-time setup — create the administrator account")
            st.info("No manager account exists yet. Create the first **Administrator** account. "
                    "This screen disappears permanently once an account exists. "
                    "(Alternatively run `python -m auth.setup_manager` in a terminal.)")
            with st.form("setup_form"):
                name = st.text_input("Full name")
                username = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                pw2 = st.text_input("Confirm password", type="password")
                st.caption(f"Password needs at least {settings.MIN_PASSWORD_LENGTH} characters, "
                           "an uppercase letter, a lowercase letter and a digit.")
                ok = st.form_submit_button("Create administrator", type="primary", use_container_width=True)
            if ok:
                if auth.manager_count() > 0:
                    st.error("An account already exists. Please log in.")
                elif pw != pw2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        auth.create_manager(username, pw, name, role="Administrator")
                        st.success("Administrator created. Please log in.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))