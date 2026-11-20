"""Password hashing, login, inactive accounts, lockout, logout."""
from auth import authentication as auth
from config import settings
from database import db
from tests.conftest import TEST_PASSWORD


def test_hash_is_not_plaintext_and_verifies():
    h = auth.hash_password(TEST_PASSWORD)
    assert TEST_PASSWORD not in h and h.startswith("pbkdf2_sha256$")
    assert auth.verify_password(TEST_PASSWORD, h)
    assert not auth.verify_password("wrong", h)
    assert auth.hash_password(TEST_PASSWORD) != h  # random salt


def test_verify_handles_garbage():
    assert not auth.verify_password("x", "not-a-hash")
    assert not auth.verify_password("x", "")


def test_password_strength_rules():
    assert auth.validate_password_strength("short") != []
    assert auth.validate_password_strength("alllowercase1") != []
    assert auth.validate_password_strength(TEST_PASSWORD) == []


def test_stored_password_is_hashed(empty_db):
    auth.create_manager("admin", TEST_PASSWORD, "Admin")
    stored = db.fetch_one("SELECT password_hash FROM managers WHERE username='admin'")[0]
    assert stored != TEST_PASSWORD and TEST_PASSWORD not in stored


def test_correct_login(empty_db):
    auth.create_manager("admin", TEST_PASSWORD, "Admin")
    r = auth.authenticate("admin", TEST_PASSWORD)
    assert r.success and r.manager.username == "admin"
    assert not hasattr(r.manager, "password_hash")


def test_incorrect_login(empty_db):
    auth.create_manager("admin", TEST_PASSWORD, "Admin")
    r = auth.authenticate("admin", "Wrong@Pass1")
    assert not r.success and r.message == auth.GENERIC_FAIL
    assert not auth.authenticate("nobody", TEST_PASSWORD).success
    assert not auth.authenticate("", "").success


def test_inactive_manager_cannot_login(empty_db):
    auth.create_manager("admin", TEST_PASSWORD, "Admin", is_active=False)
    r = auth.authenticate("admin", TEST_PASSWORD)
    assert not r.success and "inactive" in r.message.lower()


def test_lockout_after_repeated_failures(empty_db):
    auth.create_manager("admin", TEST_PASSWORD, "Admin")
    for _ in range(settings.MAX_FAILED_ATTEMPTS):
        auth.authenticate("admin", "Wrong@Pass1")
    r = auth.authenticate("admin", TEST_PASSWORD)
    assert not r.success and "locked" in r.message.lower()
    auth.reset_password("admin", "New@Pass1234")
    assert auth.authenticate("admin", "New@Pass1234").success


def test_duplicate_username_rejected(empty_db):
    auth.create_manager("admin", TEST_PASSWORD, "Admin")
    try:
        auth.create_manager("ADMIN", TEST_PASSWORD, "Other")
        assert False, "duplicate allowed"
    except ValueError:
        pass


def test_session_login_and_logout():
    state = {"unrelated": 1}
    m = auth.Manager(1, "admin", "Admin", "Administrator", None, True)
    auth.login_session(state, m)
    assert auth.is_authenticated(state)
    auth.logout_session(state)
    assert not auth.is_authenticated(state) and state == {}


def test_deactivated_session_detected(empty_db):
    auth.create_manager("admin", TEST_PASSWORD, "Admin")
    r = auth.authenticate("admin", TEST_PASSWORD)
    state = {}
    auth.login_session(state, r.manager)
    assert auth.is_still_active(state)
    auth.set_active("admin", False)
    assert not auth.is_still_active(state)
