"""Shared pytest fixtures: isolate DB and uploads dir per test."""

import shutil
from pathlib import Path

import pytest

from app.config import settings


@pytest.fixture
def isolated_env(tmp_path: Path):
    """Point the app's DATABASE_PATH and UPLOADS_DIR at a temp directory for this test."""
    original_db = settings.DATABASE_PATH
    original_uploads = settings.UPLOADS_DIR
    settings.DATABASE_PATH = tmp_path / "app.db"
    settings.UPLOADS_DIR = tmp_path / "uploads"
    settings.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        yield settings
    finally:
        settings.DATABASE_PATH = original_db
        settings.UPLOADS_DIR = original_uploads
        shutil.rmtree(tmp_path, ignore_errors=True)
