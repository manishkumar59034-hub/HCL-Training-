"""
Secure first-time manager setup and account maintenance utility (multi-bank).

Usage (run from the project folder, with the virtual environment active):

    python -m auth.setup_manager                       # har bank ka first manager (.env se)
    python -m auth.setup_manager --create              # additional manager (prompts)
    python -m auth.setup_manager --reset-password USER --bank INDB
    python -m auth.setup_manager --deactivate USER --bank INDB
    python -m auth.setup_manager --activate USER --bank INDB
    python -m auth.setup_manager --list                # saare managers (hash kabhi nahi dikhta)

.env me har bank ke liye credentials:
    MANAGER_USERNAME_INDB=indian_manager
    MANAGER_PASSWORD_INDB=StrongPass@123
    MANAGER_NAME_INDB=Indian Bank Administrator      (optional)
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth import authentication as auth  # noqa: E402
from config import settings  # noqa: E402
from database import db  # noqa: E402

PLACEHOLDER_PASSWORDS = {"ChangeThisPassword123!", "ChangeMe@12345", "", "changeme"}


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


def _choose_bank(bank_code: str | None = None):
    """Bank ka row return karta hai (code se, ya user se puchkar)."""
    banks = db.get_banks()
    if not banks:
        print("No banks found. Check BANKS in config/settings.py")
        return None
    if bank_code:
        for b in banks:
            if b["bank_code"].upper() == bank_code.upper():
                return b
        print(f"Unknown bank code '{bank_code}'.")
        return None
    print("Banks:")
    for b in banks:
        print(f"  {b['bank_code']:<6} {b['bank_name']}")
    code = input("Bank code: ").strip().upper()
    for b in banks:
        if b["bank_code"].upper() == code:
            return b
    print("Unknown bank code.")
    return None


def _env_credentials(bank_code: str) -> tuple[str, str, str]:
    """Bank-wise .env credentials. Default bank ke liye purane MANAGER_* ka fallback."""
    username, password = settings.get_bank_manager_credentials(bank_code)
    name = os.environ.get(f"MANAGER_NAME_{bank_code}", "").strip()
    if bank_code == settings.DEFAULT_BANK_CODE:
        username = username or os.environ.get("MANAGER_USERNAME", "").strip()
        password = password or os.environ.get("MANAGER_PASSWORD", "")
        name = name or os.environ.get("MANAGER_NAME", "").strip()
    return username.strip(), password, name


def create_first_managers() -> int:
    """Jis bank me abhi koi manager nahi hai, uska pehla Administrator banata hai."""
    db.init_db()
    created = skipped = 0
    for bank in db.get_banks():
        code, bank_id, bank_name = bank["bank_code"], bank["bank_id"], bank["bank_name"]
        if auth.manager_count(bank_id=bank_id) > 0:
            print(f"[{code}] manager already exists - skipped.")
            continue

        username, password, name = _env_credentials(code)
        if not username or password in PLACEHOLDER_PASSWORDS:
            print(f"[{code}] .env me MANAGER_USERNAME_{code} / MANAGER_PASSWORD_{code} "
                  f"set nahi hai (ya placeholder hai) - skipped. "
                  f"Baad me: python -m auth.setup_manager --create")
            skipped += 1
            continue
        problems = auth.validate_password_strength(password)
        if problems:
            print(f"[{code}] .env password weak hai (needs {', '.join(problems)}) - skipped.")
            skipped += 1
            continue
        try:
            auth.create_manager(username, password, name or f"{bank_name} Administrator",
                                role="Administrator", bank_id=bank_id)
        except ValueError as exc:
            print(f"[{code}] Error: {exc}")
            skipped += 1
            continue
        print(f"[{code}] manager '{username}' created (Administrator).")
        created += 1

    print(f"\nDone. Created: {created}, skipped: {skipped}.")
    if created:
        print("Passwords PBKDF2-SHA256 se hash hue hain. Ab .env se passwords hata sakte ho.")
    return 0


def create_additional_manager(bank_code: str | None = None) -> int:
    db.init_db()
    bank = _choose_bank(bank_code)
    if not bank:
        return 1
    username = input("New manager username: ").strip()
    name = input("Manager full name: ").strip()
    print("Roles:", ", ".join(auth.VALID_ROLES))
    role = input("Role [Branch Manager]: ").strip() or "Branch Manager"
    branch = input("Assigned branch ID (optional, e.g. INDB-BR001): ").strip() or None
    password = _prompt_password()
    try:
        auth.create_manager(username, password, name, role=role,
                            assigned_branch_id=branch, bank_id=bank["bank_id"])
    except Exception as exc:  # noqa: BLE001 - show any problem to the user
        print(f"Error: {exc}")
        return 1
    print(f"Manager '{username}' created in {bank['bank_name']}.")
    return 0


def reset_password_interactive(username: str | None = None,
                               bank_code: str | None = None) -> int:
    db.init_db()
    bank = _choose_bank(bank_code)
    if not bank:
        return 1
    username = username or input("Username to reset: ").strip()
    password = _prompt_password()
    try:
        auth.reset_password(username, password, bank_id=bank["bank_id"])
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Password for '{username}' ({bank['bank_name']}) reset. Failed-attempt lock cleared.")
    return 0


def list_managers() -> int:
    db.init_db()
    managers = auth.list_managers()
    if not managers:
        print("No managers found. Run: python -m auth.setup_manager")
        return 0
    print(f"{'ID':<4}{'Bank':<7}{'Username':<18}{'Name':<26}{'Role':<18}{'Active':<8}Last login")
    for m in managers:
        print(f"{m.manager_id:<4}{m.bank_code:<7}{m.username:<18}{m.manager_name:<26}"
              f"{m.role:<18}{'Yes' if m.is_active else 'No':<8}{m.last_login or '-'}")
    return 0


def _toggle_active(username: str, active: bool, bank_code: str | None) -> int:
    db.init_db()
    bank = _choose_bank(bank_code)
    if not bank:
        return 1
    try:
        auth.set_active(username, active, bank_id=bank["bank_id"])
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1
    print(f"'{username}' ({bank['bank_name']}) {'activated' if active else 'deactivated'}.")
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
    parser.add_argument("--bank", metavar="CODE", help="bank code, e.g. INDB")
    args = parser.parse_args(argv)

    if args.create:
        return create_additional_manager(args.bank)
    if args.reset_password is not None:
        return reset_password_interactive(args.reset_password or None, args.bank)
    if args.deactivate:
        return _toggle_active(args.deactivate, False, args.bank)
    if args.activate:
        return _toggle_active(args.activate, True, args.bank)
    if args.list:
        return list_managers()
    return create_first_managers()


if __name__ == "__main__":
    raise SystemExit(main())