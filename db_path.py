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
# Vercel serverless: the deploy bundle is not writable; SQLite must live under /tmp.
_VERCEL_TMP_DB = "/tmp/chizhya_career_hub.db"


def _running_on_vercel() -> bool:
    return os.environ.get("VERCEL", "").strip() == "1"


def resolve_database_path() -> str:
    env = (os.environ.get("SQLITE_DATABASE") or "").strip()
    if env:
        return env if os.path.isabs(env) else os.path.join(_ROOT, env)
    if _running_on_vercel():
        return _VERCEL_TMP_DB
    if os.path.isfile(_DEFAULT_DB):
        return _DEFAULT_DB
    if os.path.isfile(_LEGACY_DB):
        return _LEGACY_DB
    return _DEFAULT_DB


DATABASE = resolve_database_path()
