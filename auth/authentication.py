"""
Manager authentication.

Passwords are hashed with PBKDF2-HMAC-SHA256 (Python standard library,
`hashlib.pbkdf2_hmac`) using a random 16-byte salt per password and
260,000 iterations. The stored format is:

    pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>

Verification uses `hmac.compare_digest` (constant-time comparison).
Plain-text passwords are never stored, logged or returned.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from config import settings
from database import db

ALGORITHM = "pbkdf2_sha256"
TIME_FMT = "%Y-%m-%d %H:%M:%S"
VALID_ROLES = ("Administrator", "Regional Manager", "Branch Manager", "Analyst")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str, iterations: int | None = None) -> str:
    if not isinstance(password, str) or password == "":
        raise ValueError("Password must be a non-empty string.")
    iterations = iterations or settings.PBKDF2_ITERATIONS
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, hash_hex = stored_hash.split("$")
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), hash_hex)
    except (ValueError, AttributeError, TypeError):
        return False


def validate_password_strength(password: str) -> list[str]:
    """Return a list of problems (empty list = acceptable password)."""
    problems = []
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        problems.append(f"at least {settings.MIN_PASSWORD_LENGTH} characters")
    if not any(c.isupper() for c in password):
        problems.append("an uppercase letter")
    if not any(c.islower() for c in password):
        problems.append("a lowercase letter")
    if not any(c.isdigit() for c in password):
        problems.append("a digit")
    return problems


# ---------------------------------------------------------------------------
# Manager accounts
# ---------------------------------------------------------------------------
@dataclass
class Manager:
    """Safe view of a manager - deliberately has NO password_hash field."""
    manager_id: int
    username: str
    manager_name: str
    role: str
    assigned_branch_id: str | None
    is_active: bool
    last_login: str | None = None


@dataclass
class LoginResult:
    success: bool
    message: str
    manager: Manager | None = None


def manager_count(db_path=None) -> int:
    row = db.fetch_one("SELECT COUNT(*) FROM managers", db_path=db_path)
    return int(row[0]) if row else 0


def create_manager(username: str, password: str, manager_name: str,
                   role: str = "Administrator", assigned_branch_id: str | None = None,
                   is_active: bool = True, db_path=None, enforce_strength: bool = True) -> int:
    username = (username or "").strip()
    manager_name = (manager_name or "").strip() or username
    if not username:
        raise ValueError("Username is required.")
    if role not in VALID_ROLES:
        raise ValueError(f"Role must be one of: {', '.join(VALID_ROLES)}")
    if enforce_strength:
        problems = validate_password_strength(password)
        if problems:
            raise ValueError("Password must contain " + ", ".join(problems) + ".")
    if db.fetch_one("SELECT 1 FROM managers WHERE username = ?", [username], db_path):
        raise ValueError(f"Username '{username}' already exists.")
    with db.transaction(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO managers (username, password_hash, manager_name, role, "
            "assigned_branch_id, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [username, hash_password(password), manager_name, role,
             assigned_branch_id, 1 if is_active else 0, datetime.now().strftime(TIME_FMT)],
        )
        return int(cur.lastrowid)


def reset_password(username: str, new_password: str, db_path=None,
                   enforce_strength: bool = True) -> None:
    if enforce_strength:
        problems = validate_password_strength(new_password)
        if problems:
            raise ValueError("Password must contain " + ", ".join(problems) + ".")
    changed = db.execute(
        "UPDATE managers SET password_hash = ?, failed_attempts = 0, locked_until = NULL "
        "WHERE username = ?",
        [hash_password(new_password), username.strip()], db_path,
    )
    if changed == 0:
        raise ValueError(f"No manager found with username '{username}'.")


def set_active(username: str, active: bool, db_path=None) -> None:
    changed = db.execute("UPDATE managers SET is_active = ? WHERE username = ?",
                         [1 if active else 0, username.strip()], db_path)
    if changed == 0:
        raise ValueError(f"No manager found with username '{username}'.")


def list_managers(db_path=None) -> list[Manager]:
    rows = db.fetch_all(
        "SELECT manager_id, username, manager_name, role, assigned_branch_id, is_active, last_login "
        "FROM managers ORDER BY manager_id", db_path=db_path)
    return [_row_to_manager(r) for r in rows]


def _row_to_manager(row) -> Manager:
    return Manager(
        manager_id=row["manager_id"], username=row["username"],
        manager_name=row["manager_name"], role=row["role"],
        assigned_branch_id=row["assigned_branch_id"], is_active=bool(row["is_active"]),
        last_login=row["last_login"],
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
GENERIC_FAIL = "Invalid username or password."


def authenticate(username: str, password: str, db_path=None) -> LoginResult:
    """Verify credentials, enforcing active status and failed-attempt lockout."""
    username = (username or "").strip()
    if not username or not password:
        return LoginResult(False, "Please enter both username and password.")

    row = db.fetch_one("SELECT * FROM managers WHERE username = ?", [username], db_path)
    if row is None:
        # Still run a hash to keep timing similar for unknown users.
        verify_password(password, hash_password("dummy-password", iterations=1000))
        return LoginResult(False, GENERIC_FAIL)

    now = datetime.now()
    if row["locked_until"]:
        locked_until = datetime.strptime(row["locked_until"], TIME_FMT)
        if locked_until > now:
            minutes = max(1, int((locked_until - now).total_seconds() // 60) + 1)
            return LoginResult(False, f"Account temporarily locked after repeated failed "
                                      f"attempts. Try again in about {minutes} minute(s).")

    if not verify_password(password, row["password_hash"]):
        attempts = int(row["failed_attempts"]) + 1
        locked = None
        msg = GENERIC_FAIL
        if attempts >= settings.MAX_FAILED_ATTEMPTS:
            locked = (now + timedelta(minutes=settings.LOCKOUT_MINUTES)).strftime(TIME_FMT)
            attempts = 0
            msg = (f"Too many failed attempts. Account locked for "
                   f"{settings.LOCKOUT_MINUTES} minutes.")
        db.execute("UPDATE managers SET failed_attempts = ?, locked_until = ? WHERE manager_id = ?",
                   [attempts, locked, row["manager_id"]], db_path)
        return LoginResult(False, msg)

    if not row["is_active"]:
        return LoginResult(False, "This manager account is inactive. Contact the administrator.")

    stamp = now.strftime(TIME_FMT)
    db.execute("UPDATE managers SET failed_attempts = 0, locked_until = NULL, last_login = ? "
               "WHERE manager_id = ?", [stamp, row["manager_id"]], db_path)
    manager = _row_to_manager(row)
    manager.last_login = stamp
    return LoginResult(True, "Login successful.", manager)


# ---------------------------------------------------------------------------
# Streamlit session helpers (imported lazily so the module works without UI)
# ---------------------------------------------------------------------------
SESSION_KEYS = ("authenticated", "manager", "login_time", "last_activity")


def login_session(state, manager: Manager) -> None:
    now = datetime.now()
    state["authenticated"] = True
    state["manager"] = manager
    state["login_time"] = now
    state["last_activity"] = now


def logout_session(state) -> None:
    """Remove every key from the session (auth + cached filters/uploads)."""
    for key in list(state.keys()):
        del state[key]


def is_authenticated(state) -> bool:
    if not state.get("authenticated") or state.get("manager") is None:
        return False
    last = state.get("last_activity")
    if last and datetime.now() - last > timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES):
        logout_session(state)
        return False
    state["last_activity"] = datetime.now()
    return True


def is_still_active(state, db_path=None) -> bool:
    """Re-check the DB so a deactivated manager is signed out on the next rerun."""
    manager = state.get("manager")
    if manager is None:
        return False
    row = db.fetch_one("SELECT is_active FROM managers WHERE manager_id = ?",
                       [manager.manager_id], db_path)
    return bool(row and row["is_active"])
