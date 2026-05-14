"""
SQLite database file location for this app.

Uses Python's built-in sqlite3 only — no MySQL, PostgreSQL drivers, or ORM required.
Override with env SQLITE_DATABASE (absolute path or path relative to this project folder).
"""
from __future__ import annotations

import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB = os.path.join(_ROOT, "chizhya_career_hub.db")
_LEGACY_DB = os.path.join(_ROOT, "smarthire.db")


def resolve_database_path() -> str:
    env = (os.environ.get("SQLITE_DATABASE") or "").strip()
    if env:
        return env if os.path.isabs(env) else os.path.join(_ROOT, env)
    if os.path.isfile(_DEFAULT_DB):
        return _DEFAULT_DB
    if os.path.isfile(_LEGACY_DB):
        return _LEGACY_DB
    return _DEFAULT_DB


DATABASE = resolve_database_path()
