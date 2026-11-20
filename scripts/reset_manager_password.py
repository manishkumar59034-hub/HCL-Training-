"""
Manager password reset utility.

    python scripts/reset_manager_password.py              # prompts for username
    python scripts/reset_manager_password.py bankadmin    # reset a specific user

The new password is typed hidden and stored only as a PBKDF2 hash.
Resetting also clears any failed-login lockout on the account.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth.setup_manager import reset_password_interactive  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(reset_password_interactive(sys.argv[1] if len(sys.argv) > 1 else None))
