"""Central path resolution + GEM database access — so nothing hard-codes
/Users/baird/... and no script reinvents the connection.

Repo layout is fixed relative to this file (scripts/paths.py). Sibling repos
default to siblings of this repo and can be overridden by env vars:

    GEM_DB_OPS_REPO   -> gem-db-ops       (the pull/query engine)
    GEM_GOGPT_REPO    -> gogpt-researcher (cross-tracker captive-power inputs)

`get_engine()` is the ONLY way DB-backed scripts here should reach Postgres.
It borrows gem-db-ops' `build_engine`, which sets
`default_transaction_read_only=on` plus a statement timeout on every session —
so a stray write can't happen, rather than merely being unlikely. Before
2026-08-11 six scripts here each had their own `create_engine` /
`psycopg2.connect` and only one of them set the read-only guard; if you need
something new, add it here.

Mirrors gogpt-researcher/scripts/paths.py — keep the two in step.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Same env var name the pull engine reads, so one export covers everything.
DB_ENV_VAR = "GEM_READONLY_DB_URL"


def repo_root() -> Path:
    return REPO_ROOT


def _sibling(name: str, env: str) -> Path:
    override = os.environ.get(env)
    if override:
        return Path(override).expanduser().resolve()
    return (REPO_ROOT.parent / name).resolve()


def db_ops_repo() -> Path:
    """Local gem-db-ops repo — the pull engine (single source of truth)."""
    return _sibling("gem-db-ops", "GEM_DB_OPS_REPO")


def gogpt_repo() -> Path:
    """Local gogpt-researcher repo — cross-tracker captive-power inputs."""
    return _sibling("gogpt-researcher", "GEM_GOGPT_REPO")


def gem_export_csv() -> Path:
    """Default location of the fresh all-fields LNG export (never committed)."""
    return REPO_ROOT / "scripts" / "gem_export.csv"


def _import_db_ops():
    """Put gem-db-ops on sys.path and return its gem_query module."""
    path = db_ops_repo()
    if not (path / "gem_query.py").is_file():
        sys.exit(
            f"error: gem-db-ops not found at {path}\n"
            "  Clone it beside this repo, or set GEM_DB_OPS_REPO=/path/to/gem-db-ops.\n"
            "  It owns the GEM database connection and every tracker pull."
        )
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    try:
        import gem_query  # noqa: PLC0415
    except ImportError as exc:  # sqlalchemy/psycopg2 missing
        sys.exit(f"error: {exc}\n  pip install 'sqlalchemy>=2.0' psycopg2-binary")
    return gem_query


def get_engine(statement_timeout_ms: int | None = None):
    """Read-only SQLAlchemy Engine for the GEM project DB, from gem-db-ops.

    Exits with gem-db-ops' own instructions if GEM_READONLY_DB_URL is unset.
    """
    gem_query = _import_db_ops()
    timeout = (statement_timeout_ms if statement_timeout_ms is not None
               else gem_query.DEFAULT_STATEMENT_TIMEOUT_MS)
    return gem_query.build_engine(gem_query.get_database_url(), timeout)


def database_url() -> str:
    """The raw connection URL, normalized to the postgresql:// scheme.

    For the rare caller that needs a driver other than SQLAlchemy (psycopg2
    directly, psql, ...). Prefer get_engine() — it carries the read-only guard.
    """
    return _import_db_ops().get_database_url()


def colmap_expected_columns() -> dict:
    """gem-db-ops' canonical LNG short-name -> header-text map."""
    path = db_ops_repo()
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
    import gem_colmap  # noqa: PLC0415

    return gem_colmap.LNG_EXPECTED_COLUMNS


def work_dir() -> Path:
    d = REPO_ROOT / "work"
    d.mkdir(exist_ok=True)
    return d
