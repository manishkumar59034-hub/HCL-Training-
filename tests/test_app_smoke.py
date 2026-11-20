"""End-to-end UI checks with Streamlit's AppTest: login gate, every page, empty filters, logout."""
from pathlib import Path

import pytest

from auth import authentication as auth
from tests.conftest import TEST_PASSWORD

APP = str(Path(__file__).resolve().parent.parent / "app.py")
AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def _login(at, password=TEST_PASSWORD):
    at.text_input(key="login_username").input("admin")
    at.text_input(key="login_password").input(password)
    at.button[0].click().run()


@pytest.fixture()
def app(seeded_db):
    auth.create_manager("admin", TEST_PASSWORD, "Test Admin", role="Administrator")
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    return at


def test_dashboard_hidden_before_login(app):
    assert not app.exception
    assert [t.value for t in app.title] == []           # no page rendered
    assert {t.label for t in app.text_input} == {"Username", "Password"}


def test_wrong_password_shows_error(app):
    _login(app, "Wrong@Pass1")
    assert any("Invalid username or password" in e.value for e in app.error)
    assert [t.value for t in app.title] == []


def test_all_pages_render_after_login(app):
    _login(app)
    assert [t.value for t in app.title] == ["Executive Overview"]
    for page in app.radio(key="nav_page").options:
        app.radio(key="nav_page").set_value(page).run()
        assert not app.exception, page
        assert not app.error, (page, [e.value for e in app.error])


def test_pages_handle_empty_filter_result(app):
    _login(app)
    app.selectbox(key="f_year").set_value("2025").run()
    app.selectbox(key="f_month").set_value("January").run()   # demo data starts May 2025
    for page in app.radio(key="nav_page").options:
        app.radio(key="nav_page").set_value(page).run()
        assert not app.exception, page


def test_region_filter_changes_kpis(app):
    _login(app)
    before = [m.value for m in app.markdown if "kpi-value" in m.value][:2]
    app.multiselect(key="f_region").set_value(["South"]).run()
    after = [m.value for m in app.markdown if "kpi-value" in m.value][:2]
    assert before != after


def test_logout_clears_session(app):
    _login(app)
    app.button(key="btn_logout").click().run()
    assert [t.value for t in app.title] == []
    assert "manager" not in app.session_state


def test_first_time_setup_when_no_manager(seeded_db):
    at = AppTest.from_file(APP, default_timeout=120)
    at.run()
    assert any("First-time setup" in m.value for m in at.markdown)
