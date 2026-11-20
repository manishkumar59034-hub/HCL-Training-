"""Shared pytest fixtures: every test gets its own throw-away SQLite database."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import settings  # noqa: E402
from database import db  # noqa: E402

TEST_PASSWORD = "Test@Pass123"


@pytest.fixture(scope="session")
def seeded_template(tmp_path_factory) -> Path:
    """Build the demo database once per test session."""
    path = tmp_path_factory.mktemp("template") / "template.db"
    old = settings.DB_PATH
    settings.DB_PATH = path
    try:
        from scripts.seed_database import seed
        seed(verbose=False)
    finally:
        settings.DB_PATH = old
    return path


@pytest.fixture()
def empty_db(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "empty.db"
    monkeypatch.setattr(settings, "DB_PATH", path)
    monkeypatch.setattr(settings, "BACKUP_DIR", tmp_path / "backups")
    db.init_db()
    return path


@pytest.fixture()
def seeded_db(tmp_path, monkeypatch, seeded_template) -> Path:
    path = tmp_path / "seeded.db"
    shutil.copy(seeded_template, path)
    monkeypatch.setattr(settings, "DB_PATH", path)
    monkeypatch.setattr(settings, "BACKUP_DIR", tmp_path / "backups")
    return path
