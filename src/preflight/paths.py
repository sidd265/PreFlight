"""Local storage paths. Everything stays under a local `.preflight/` dir (S2)."""

from __future__ import annotations

from pathlib import Path

DEFAULT_DIR = ".preflight"
DB_NAME = "preflight.db"


def default_db_path(base: str | Path = ".") -> Path:
    return Path(base) / DEFAULT_DIR / DB_NAME
