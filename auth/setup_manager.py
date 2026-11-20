"""
Secure first-time manager setup and account maintenance utility.

Usage (run from the project folder, with the virtual environment active):

    python -m auth.setup_manager                    # create first manager from .env (or prompts)
    python -m auth.setup_manager --create           # create an additional manager (prompts)
    python -m auth.setup_manager --reset-password   # reset a manager's password (prompts)
    python -m auth.setup_manager --deactivate USER  # mark a manager inactive
    python -m auth.setup_manager --activate USER    # re-activate a manager
    python -m auth.setup_manager --list             # list managers (never shows hashes)

Credentials for the first manager are read from environment variables
MANAGER_USERNAME / MANAGER_PASSWORD / MANAGER_NAME (usually from `.env`).
If they are missing you are prompted; the password is typed hidden (getpass).
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import authentication as auth  # noqa: E402
from database import db  # noqa: E402

PLACEHOLDER_PASSWORDS = {"ChangeThisPassword123!", "", "changeme"}


def _prompt_password(confirm: bool = True) -> str:
    while True:
        pw = getpass.getpass("Password (hidden): ")
        problems = auth.validate_password_strength(pw)
        if problems:
            print("  Password must contain " + ", ".join(problems) + ".")
            continue
        if confirm and getpass.getpass("Confirm password: ") != pw:
            print("  Passwords do not match. Try again.")
            continue
        return pw


def create_first_manager() -> int:
    db.init_db()
    if auth.manager_count() > 0:
        print("A manager account already exists. Nothing to do.")
        print("Use --create to add another manager or --reset-password to change a password.")
        return 0

    username = os.environ.get("MANAGER_USERNAME", "").strip()
    password = os.environ.get("MANAGER_PASSWORD", "")
    name = os.environ.get("MANAGER_NAME", "").strip() or "Bank Administrator"

    if password in PLACEHOLDER_PASSWORDS:
        if password:
            print("MANAGER_PASSWORD in .env is still the example placeholder - "
                  "please choose a real password now.")
        password = ""
    if not username:
        username = input("Manager username: ").strip()
    if not password:
        password = _prompt_password()
    else:
        problems = auth.validate_password_strength(password)
        if problems:
            print("MANAGER_PASSWORD in .env is too weak (needs " + ", ".join(problems) + ").")
            password = _prompt_password()

    try:
        auth.create_manager(username, password, name, role="Administrator")
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Manager account '{username}' created (role: Administrator).")
    print("The password was hashed with PBKDF2-SHA256; it is not stored in plain text.")
    print("Tip: you can now remove MANAGER_PASSWORD from your .env file.")
    return 0


def create_additional_manager() -> int:
    db.init_db()
    username = input("New manager username: ").strip()
    name = input("Manager full name: ").strip()
    print("Roles:", ", ".join(auth.VALID_ROLES))
    role = input("Role [Branch Manager]: ").strip() or "Branch Manager"
    branch = input("Assigned branch ID (optional, e.g. BR001): ").strip() or None
    password = _prompt_password()
    try:
        auth.create_manager(username, password, name, role=role, assigned_branch_id=branch)
    except Exception as exc:  # noqa: BLE001 - show any problem to the user
        print(f"Error: {exc}")
        return 1
    print(f"Manager '{username}' created.")
    return 0


def reset_password_interactive(username: str | None = None) -> int:
    db.init_db()
    username = username or input("Username to reset: ").strip()
    password = _prompt_password()
    try:
        auth.reset_password(username, password)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Password for '{username}' reset. Failed-attempt lock cleared.")
    return 0


def list_managers() -> int:
    db.init_db()
    managers = auth.list_managers()
    if not managers:
        print("No managers found. Run: python -m auth.setup_manager")
        return 0
    print(f"{'ID':<4}{'Username':<18}{'Name':<24}{'Role':<18}{'Active':<8}Last login")
    for m in managers:
        print(f"{m.manager_id:<4}{m.username:<18}{m.manager_name:<24}{m.role:<18}"
              f"{'Yes' if m.is_active else 'No':<8}{m.last_login or '-'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manager account setup utility")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--create", action="store_true", help="create an additional manager")
    group.add_argument("--reset-password", nargs="?", const="", metavar="USERNAME",
                       help="reset a manager password")
    group.add_argument("--deactivate", metavar="USERNAME")
    group.add_argument("--activate", metavar="USERNAME")
    group.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    if args.create:
        return create_additional_manager()
    if args.reset_password is not None:
        return reset_password_interactive(args.reset_password or None)
    if args.deactivate:
        auth.set_active(args.deactivate, False)
        print(f"'{args.deactivate}' deactivated.")
        return 0
    if args.activate:
        auth.set_active(args.activate, True)
        print(f"'{args.activate}' activated.")
        return 0
    if args.list:
        return list_managers()
    return create_first_manager()


if __name__ == "__main__":
    raise SystemExit(main())
