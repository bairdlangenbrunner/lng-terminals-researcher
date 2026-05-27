#!/usr/bin/env python3
"""
gem_query.py — Query the GEM read-only Postgres database and export to CSV.

Reads the connection URL from the GEM_READONLY_DB_URL environment variable.
Never hardcodes credentials.

USAGE
-----
    # One-time setup (in your shell, NOT in this file):
    export GEM_READONLY_DB_URL='postgres://readonly:PASSWORD@HOST:5432/DBNAME'

    # Default mode: export every project-scoped table for a project type.
    # Discovers the table graph rooted at `plant` (level 0), follows FKs to
    # direct children (level 1: lng_project, powerplant_unit, plant_owner, ...),
    # and then to grandchildren (level 2: lng_unit, status_timeline, unit_fuel,
    # ...). Writes one CSV per table.
    python gem_query.py --project-type lng -o ./gem_export_lng
    python gem_query.py --project-type 8   -o ./gem_export_lng

    # Preview the plan without fetching any rows:
    python gem_query.py --discover --project-type lng

    # Include reference / lookup tables (country, status, fuel_category, etc.)
    # in their entirety, as a separate output set:
    python gem_query.py --project-type lng --include-reference \\
        -o ./gem_export_lng

    # Combustion needs a sub-filter to pick GOGPT / GBPT / GCPT. The column is
    # `trackerSearch` on `powerplant_unit` (NOT on `plant`), so this is wired
    # as a separate flag — it produces an EXISTS subquery against units.
    python gem_query.py --project-type combustion --tracker gcpt \\
        -o ./gem_export_coal

    # Single-table mode (the old behavior). Useful for one-offs and ad-hoc
    # dumps where you don't want FK traversal.
    python gem_query.py --table lng_unit -o lng_unit.csv

    # Schema introspection:
    python gem_query.py --list-tables
    python gem_query.py --describe plant
    python gem_query.py --describe lng_project

    # Custom SELECT (read-only enforced, one CSV out):
    python gem_query.py --sql "SELECT id, name FROM plant WHERE \\"projectType\\" = 8 LIMIT 10" \\
        -o sample.csv

NOTES
-----
* Defaults are tuned for the GEM schema: projects table = `plant`,
  project-type column = `projectType` (quoted camelCase). Override with
  --projects-table and --project-type-column for other schemas.
* Tables in SYSTEM_EXCLUDES (Django auth, sessions, migrations, etc.) are
  never traversed. Tables in REFERENCE_TABLES are exported only when
  --include-reference is passed, and always in full (no filtering).
* Results stream in chunks; safe on large tables. Use --limit to cap for tests.
* The role connected as should be `readonly` at the Postgres level. The script
  additionally sets the session to read-only as defense-in-depth.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
except ImportError:
    sys.stderr.write(
        "ERROR: sqlalchemy is not installed. Install with:\n"
        "    pip install 'sqlalchemy>=2.0' psycopg2-binary\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# GEM-specific constants
# ---------------------------------------------------------------------------

# Maps human-readable names to the projectType integer codes used in the DB.
# Source: GEM internal PROJECT_TYPES tuple.
PROJECT_TYPES: dict[str, int] = {
    "combustion": 1,
    "solar": 2,
    "wind": 3,
    "nuclear": 4,
    "geothermal": 5,
    "steel": 6,
    "hydro": 7,
    "lng": 8,
    "goget": 9,
}
PROJECT_TYPE_NAMES: dict[int, str] = {v: k for k, v in PROJECT_TYPES.items()}

# Sub-categorization within combustion (projectType=1). The column lives on
# `powerplant_unit`, so this is applied as an EXISTS subquery at the root.
# Source: Taylor Higgins, #data-and-research Slack thread 2026-05-08.
TRACKER_TYPES: dict[str, str] = {
    "gogpt": "GOGPT",   # oil & gas
    "gbpt":  "GBPT",    # bioenergy
    "gcpt":  "GCPT",    # coal
}
TRACKER_COLUMN = "trackerSearch"
TRACKER_TABLE = "powerplant_unit"
TRACKER_TABLE_FK = "plant_id"

ENV_VAR = "GEM_READONLY_DB_URL"
DEFAULT_PROJECTS_TABLE = "plant"
DEFAULT_PROJECT_TYPE_COL = "projectType"  # camelCase, must be quoted in SQL
DEFAULT_MAX_DEPTH = 3
DEFAULT_CHUNKSIZE = 1000
DEFAULT_STATEMENT_TIMEOUT_MS = 5 * 60 * 1000  # 5 minutes
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")

# Django framework / auth / system tables: never traverse into these.
SYSTEM_EXCLUDES: frozenset[str] = frozenset({
    "auth_user", "auth_group", "auth_permission",
    "auth_user_groups", "auth_user_user_permissions",
    "auth_group_permissions",
    "django_session", "django_migrations", "django_content_type",
    "django_admin_log", "django_site",
    "socialaccount_socialaccount", "socialaccount_socialapp",
    "socialaccount_socialapp_sites", "socialaccount_socialtoken",
    "account_emailaddress", "account_emailconfirmation",
    "user_settings",
})

# Reference / lookup tables: store enum-like option lists used by FK columns
# elsewhere. We never traverse INTO them (don't want every country joined to
# every plant export), but we optionally export them in full as a separate
# reference set with --include-reference.
REFERENCE_TABLES: frozenset[str] = frozenset({
    "capacity_rating",
    "captive_industry_type", "captive_industry_use", "captive_non_industry_use",
    "ccs", "chp",
    "country", "country_subdivision",
    "entity_status", "entity_tag", "entity_type",
    "external_id_system",
    "fuel_category", "fuel_detail",
    "hydrogen_capable", "hydrogen_generating", "hydrogen_greenwashing",
    "installation_type",
    "language", "legal_entity_type",
    "nuclear_model",
    "org_id",
    "quantity_unit",
    "relining_cost_unit",
    "research_status", "reserve_type",
    "status",
    "steel_product",
    "technology", "technology_fuel_category",
    "turbine_manufacturer",
    "ultimate_parent_rationale",
    "unit_replacement_type",
})


# ---------------------------------------------------------------------------
# Connection setup
# ---------------------------------------------------------------------------

def get_database_url() -> str:
    """Pull the DB URL from the environment, with the Heroku scheme fix applied."""
    url = os.environ.get(ENV_VAR)
    if not url:
        sys.stderr.write(
            f"ERROR: environment variable {ENV_VAR} is not set.\n\n"
            "Set it in your shell (do NOT commit it to git):\n"
            f"    export {ENV_VAR}='postgres://readonly:PASSWORD@HOST:5432/DBNAME'\n\n"
            "Or load it from a gitignored .env file before running.\n"
        )
        sys.exit(2)
    # SQLAlchemy 1.4+ requires postgresql:// rather than postgres://.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def build_engine(url: str, statement_timeout_ms: int) -> Engine:
    """Engine where every session defaults to read-only."""
    return create_engine(
        url,
        connect_args={
            "options": (
                f"-c default_transaction_read_only=on "
                f"-c statement_timeout={statement_timeout_ms}"
            )
        },
        pool_pre_ping=True,
    )


# ---------------------------------------------------------------------------
# Schema introspection
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TableRef:
    schema: str
    name: str

    @property
    def qualified(self) -> str:
        return f'"{self.schema}"."{self.name}"'

    @property
    def label(self) -> str:
        return f"{self.schema}.{self.name}"


@dataclass
class ForeignKey:
    table: TableRef         # the table the FK lives on
    column: str             # the FK column
    target_table: TableRef  # the table it points to
    target_column: str      # the PK column it points to


@dataclass
class TablePlan:
    table: TableRef
    depth: int
    # How this table is filtered:
    #   - "root"       : WHERE "projectType" = X (+ optional --where)
    #   - "fk"         : WHERE fk_col IN (SELECT pk FROM <parent_plan>)
    #   - "reference"  : SELECT * (no filter)
    #   - "single"     : --table mode, no filter unless --where given
    mode: str
    fk_column: str | None = None
    parent: "TablePlan | None" = None
    columns: list[str] = field(default_factory=list)


def list_user_tables(engine: Engine) -> list[TableRef]:
    sql = text("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
          AND table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY table_schema, table_name
    """)
    with engine.connect() as conn:
        return [TableRef(r[0], r[1]) for r in conn.execute(sql)]


def describe_table(engine: Engine, ref: TableRef) -> list[tuple[str, str, str]]:
    sql = text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = :s AND table_name = :t
        ORDER BY ordinal_position
    """)
    with engine.connect() as conn:
        return [(r[0], r[1], r[2]) for r in conn.execute(sql, {"s": ref.schema, "t": ref.name})]


def get_columns(engine: Engine, ref: TableRef) -> list[str]:
    return [c for c, _, _ in describe_table(engine, ref)]


def get_primary_key(engine: Engine, ref: TableRef) -> str | None:
    """Return the single-column PK name, or None if composite / missing."""
    sql = text("""
        SELECT a.attname
        FROM pg_index i
        JOIN pg_class c       ON c.oid = i.indrelid
        JOIN pg_namespace n   ON n.oid = c.relnamespace
        JOIN pg_attribute a   ON a.attrelid = c.oid AND a.attnum = ANY(i.indkey)
        WHERE i.indisprimary
          AND n.nspname = :s
          AND c.relname = :t
    """)
    with engine.connect() as conn:
        rows = [r[0] for r in conn.execute(sql, {"s": ref.schema, "t": ref.name})]
    return rows[0] if len(rows) == 1 else None


def list_foreign_keys(engine: Engine) -> list[ForeignKey]:
    """Every FK in non-system schemas, fully resolved."""
    sql = text("""
        SELECT
            ns.nspname  AS src_schema,
            cl.relname  AS src_table,
            att.attname AS src_column,
            tns.nspname AS tgt_schema,
            tcl.relname AS tgt_table,
            tatt.attname AS tgt_column
        FROM pg_constraint con
        JOIN pg_class cl       ON cl.oid = con.conrelid
        JOIN pg_namespace ns   ON ns.oid = cl.relnamespace
        JOIN pg_class tcl      ON tcl.oid = con.confrelid
        JOIN pg_namespace tns  ON tns.oid = tcl.relnamespace
        JOIN pg_attribute att  ON att.attrelid = con.conrelid
                              AND att.attnum = ANY(con.conkey)
        JOIN pg_attribute tatt ON tatt.attrelid = con.confrelid
                              AND tatt.attnum = ANY(con.confkey)
        WHERE con.contype = 'f'
          AND ns.nspname NOT IN ('pg_catalog','information_schema')
          AND array_length(con.conkey, 1) = 1
          AND array_length(con.confkey, 1) = 1
        ORDER BY ns.nspname, cl.relname, att.attname
    """)
    out: list[ForeignKey] = []
    with engine.connect() as conn:
        for r in conn.execute(sql):
            out.append(ForeignKey(
                table=TableRef(r[0], r[1]),
                column=r[2],
                target_table=TableRef(r[3], r[4]),
                target_column=r[5],
            ))
    return out


# ---------------------------------------------------------------------------
# Plan: BFS the FK graph rooted at the projects table.
# ---------------------------------------------------------------------------

def build_traversal_plan(
    engine: Engine,
    root: TableRef,
    project_type_col: str,
    max_depth: int,
    extra_excludes: set[str],
) -> list[TablePlan]:
    """
    BFS outward from `root` following FKs. At each step:
      - Skip tables in SYSTEM_EXCLUDES or extra_excludes.
      - Skip tables in REFERENCE_TABLES (they're handled separately).
      - Record the FK column and parent plan we used to reach the table.
    """
    fks = list_foreign_keys(engine)
    # Index FKs by their TARGET table (so we can find "what points at me?").
    fks_by_target: dict[str, list[ForeignKey]] = {}
    for fk in fks:
        fks_by_target.setdefault(fk.target_table.label, []).append(fk)

    plans: list[TablePlan] = []
    seen: set[str] = set()

    root_pk = get_primary_key(engine, root)
    if root_pk is None:
        sys.stderr.write(f"ERROR: cannot find a single-column primary key on {root.label}\n")
        sys.exit(4)

    root_plan = TablePlan(
        table=root, depth=0, mode="root", columns=get_columns(engine, root),
    )
    plans.append(root_plan)
    seen.add(root.label)

    # Track the PK we should "drive" descendants from at each plan.
    pk_for_plan: dict[str, str] = {root.label: root_pk}

    frontier: list[TablePlan] = [root_plan]
    for depth in range(1, max_depth + 1):
        next_frontier: list[TablePlan] = []
        for parent_plan in frontier:
            parent_label = parent_plan.table.label
            parent_pk = pk_for_plan.get(parent_label)
            if not parent_pk:
                continue
            # Find every table whose FK points at parent_plan's PK.
            for fk in fks_by_target.get(parent_label, []):
                if fk.target_column != parent_pk:
                    continue
                child = fk.table
                if child.label in seen:
                    continue
                if child.name in SYSTEM_EXCLUDES or child.name in extra_excludes:
                    continue
                if child.name in REFERENCE_TABLES:
                    continue
                seen.add(child.label)
                plan = TablePlan(
                    table=child,
                    depth=depth,
                    mode="fk",
                    fk_column=fk.column,
                    parent=parent_plan,
                    columns=get_columns(engine, child),
                )
                plans.append(plan)
                child_pk = get_primary_key(engine, child)
                if child_pk:
                    pk_for_plan[child.label] = child_pk
                next_frontier.append(plan)
        frontier = next_frontier
        if not frontier:
            break
    return plans


def resolve_reference_tables(engine: Engine) -> list[TableRef]:
    """Find which of the REFERENCE_TABLES actually exist in this DB."""
    out: list[TableRef] = []
    all_tables = {t.name: t for t in list_user_tables(engine)}
    for name in sorted(REFERENCE_TABLES):
        if name in all_tables:
            out.append(all_tables[name])
    return out


# ---------------------------------------------------------------------------
# SQL building
# ---------------------------------------------------------------------------

def _quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def build_select_for_plan(
    plan: TablePlan,
    project_type_code: int,
    project_type_col: str,
    extra_where: str | None,
    limit: int | None,
) -> str:
    """Compose the SELECT for one plan. Root gets project_type filter directly;
    children get an IN (...) subquery against their root ancestor."""
    cols = ", ".join(_quote_ident(c) for c in plan.columns) if plan.columns else "*"
    tbl = plan.table.qualified

    if plan.mode == "root":
        where_parts = [f'{_quote_ident(project_type_col)} = {project_type_code}']
        if extra_where:
            where_parts.append(f"({extra_where})")
        where = " AND ".join(where_parts)
        sql = f"SELECT {cols} FROM {tbl} WHERE {where}"
    elif plan.mode == "fk":
        # Walk back up to the root, composing nested IN subqueries.
        chain: list[TablePlan] = []
        cur: TablePlan | None = plan
        while cur is not None and cur.mode == "fk":
            chain.append(cur)
            cur = cur.parent
        if cur is None or cur.mode != "root":
            raise RuntimeError(f"plan for {plan.table.label} has no root ancestor")
        root = cur
        # Innermost: SELECT root_pk FROM root WHERE projectType = X
        root_pk_col = _quote_ident(
            # We stored the PK in pk_for_plan but didn't attach it; recompute.
            # The root's PK was used as fk.target_column for level-1 plans.
            # Walk the chain to find the actual target column.
            _root_pk_for_chain(chain, root),
        )
        root_where = [f'{_quote_ident(project_type_col)} = {project_type_code}']
        if extra_where:
            root_where.append(f"({extra_where})")
        inner = f"SELECT {root_pk_col} FROM {root.table.qualified} WHERE {' AND '.join(root_where)}"
        # Wrap subqueries from root outward.
        # chain is [plan, plan.parent, ..., root_child]; reverse to root-down.
        chain.reverse()
        for level in chain[:-1]:
            # level is a parent of the next deeper plan; we need level's PK
            # filtered by level's own FK to its parent.
            level_pk = _quote_ident(_pk_of(level))
            inner = (
                f"SELECT {level_pk} FROM {level.table.qualified} "
                f"WHERE {_quote_ident(level.fk_column)} IN ({inner})"
            )
        sql = (
            f"SELECT {cols} FROM {tbl} "
            f"WHERE {_quote_ident(plan.fk_column)} IN ({inner})"
        )
    elif plan.mode == "reference":
        sql = f"SELECT {cols} FROM {tbl}"
    elif plan.mode == "single":
        if extra_where:
            sql = f"SELECT {cols} FROM {tbl} WHERE {extra_where}"
        else:
            sql = f"SELECT {cols} FROM {tbl}"
    else:
        raise ValueError(f"unknown plan mode: {plan.mode}")

    if limit:
        sql += f" LIMIT {int(limit)}"
    return sql


# Two small helpers: each TablePlan in mode="fk" knows its fk_column (its own
# column pointing at its parent), so the parent's PK is just that FK's target.
# We stash it as an attribute when we build the plan.

def _pk_of(plan: TablePlan) -> str:
    pk = getattr(plan, "_pk", None)
    if pk:
        return pk
    raise RuntimeError(f"plan for {plan.table.label} is missing _pk")


def _root_pk_for_chain(chain: list[TablePlan], root: TablePlan) -> str:
    # The level-1 plan in the chain has fk_column pointing at root's PK target.
    # But that target column name is what we want. The level-1 plan's fk
    # was recorded relative to root; we can recover it from the chain ordering
    # being [deepest, ..., level-1].
    level1 = chain[-1] if chain else None
    if level1 is None:
        raise RuntimeError("empty chain")
    pk = getattr(level1, "_root_target", None) or getattr(root, "_pk", None)
    if not pk:
        raise RuntimeError("root PK not recorded")
    return pk


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

def safe_filename(label: str) -> str:
    return SAFE_NAME_RE.sub("_", label) + ".csv"


def write_query_to_csv(engine: Engine, sql: str, out_path: str, chunksize: int) -> int:
    """Stream a query result to a CSV file. Returns row count."""
    rows_written = 0
    with engine.connect().execution_options(stream_results=True) as conn:
        result = conn.execute(text(sql))
        cols = list(result.keys())
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            while True:
                batch = result.fetchmany(chunksize)
                if not batch:
                    break
                writer.writerows(batch)
                rows_written += len(batch)
    return rows_written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def resolve_tracker(value: str) -> str:
    """Map a user-supplied tracker name (any case) to the DB value."""
    v = value.strip().lower()
    if v in TRACKER_TYPES:
        return TRACKER_TYPES[v]
    # Allow the uppercase DB value too, in case someone passes it through.
    upper = value.strip().upper()
    if upper in TRACKER_TYPES.values():
        return upper
    valid = ", ".join(TRACKER_TYPES.keys())
    sys.stderr.write(f"ERROR: unknown tracker '{value}'. Valid: {valid}\n")
    sys.exit(3)


def build_tracker_exists_clause(tracker_value: str) -> str:
    """Return an EXISTS subquery filtering plant.id to plants that have at least
    one matching powerplant_unit row."""
    return (
        f'EXISTS (SELECT 1 FROM {_quote_ident(TRACKER_TABLE)} u '
        f'WHERE u.{_quote_ident(TRACKER_TABLE_FK)} = '
        f'{_quote_ident(DEFAULT_PROJECTS_TABLE)}."id" '
        f"AND u.{_quote_ident(TRACKER_COLUMN)} = '{tracker_value}')"
    )


def resolve_project_type(value: str) -> int:
    v = value.strip().lower()
    if v.isdigit():
        code = int(v)
        if code not in PROJECT_TYPE_NAMES:
            valid = ", ".join(f"{n}={k}" for k, n in PROJECT_TYPES.items())
            sys.stderr.write(
                f"WARNING: projectType={code} is not in the known list ({valid}). "
                f"Proceeding anyway.\n"
            )
        return code
    if v in PROJECT_TYPES:
        return PROJECT_TYPES[v]
    valid = ", ".join(PROJECT_TYPES.keys())
    sys.stderr.write(f"ERROR: unknown project type '{value}'. Valid: {valid}\n")
    sys.exit(3)


def parse_table_ref(s: str) -> TableRef:
    if "." in s:
        sch, _, nm = s.partition(".")
        return TableRef(sch, nm)
    return TableRef("public", s)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export GEM data to CSV via a read-only Postgres connection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Project type codes:\n  "
            + "\n  ".join(f"{code} = {name}" for name, code in PROJECT_TYPES.items())
        ),
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path. Multi-table mode: a DIRECTORY. --sql / --table mode: a FILE.",
    )
    parser.add_argument(
        "-p", "--project-type",
        help="Project type name (lng, combustion, ...) or numeric code (1-9).",
    )
    parser.add_argument(
        "-t", "--table",
        help="Dump a single specific table only (use schema.table for non-public).",
    )
    parser.add_argument(
        "--projects-table", default=DEFAULT_PROJECTS_TABLE,
        help=f"Root projects table (default: {DEFAULT_PROJECTS_TABLE}).",
    )
    parser.add_argument(
        "--project-type-column", default=DEFAULT_PROJECT_TYPE_COL,
        help=f"Column on the projects table holding the type code "
             f"(default: {DEFAULT_PROJECT_TYPE_COL}).",
    )
    parser.add_argument(
        "--max-depth", type=int, default=DEFAULT_MAX_DEPTH,
        help=f"How deep to follow FKs (default: {DEFAULT_MAX_DEPTH}).",
    )
    parser.add_argument(
        "--exclude", action="append", default=[],
        help="Extra table name to exclude from traversal. Repeatable.",
    )
    parser.add_argument(
        "--include-reference", action="store_true",
        help="Also dump every reference / lookup table in full into the output directory.",
    )
    parser.add_argument(
        "-w", "--where",
        help="Extra SQL WHERE clause applied to the projects (root) table. "
             "Filter inherits to descendants via the FK chain.",
    )
    parser.add_argument(
        "--tracker",
        help=f"Combustion sub-tracker filter. One of: "
             f"{', '.join(TRACKER_TYPES.keys())}. Only valid with "
             f"--project-type combustion. Translates to an EXISTS subquery on "
             f"{TRACKER_TABLE}.{TRACKER_COLUMN}.",
    )
    parser.add_argument(
        "--limit", type=int,
        help="Cap row count per table (handy for testing).",
    )
    parser.add_argument(
        "--sql",
        help="Run an arbitrary SELECT statement. Read-only is enforced; output is one CSV.",
    )
    parser.add_argument(
        "--chunksize", type=int, default=DEFAULT_CHUNKSIZE,
        help=f"Rows per fetch batch (default: {DEFAULT_CHUNKSIZE}).",
    )
    parser.add_argument(
        "--timeout-ms", type=int, default=DEFAULT_STATEMENT_TIMEOUT_MS,
        help=f"Postgres statement_timeout in ms (default: {DEFAULT_STATEMENT_TIMEOUT_MS}).",
    )
    parser.add_argument(
        "--list-tables", action="store_true",
        help="List all non-system tables and exit.",
    )
    parser.add_argument(
        "--describe", metavar="TABLE",
        help="Print columns + types for a table and exit.",
    )
    parser.add_argument(
        "--discover", action="store_true",
        help="Show which tables would be exported (requires --project-type). Exits.",
    )
    parser.add_argument(
        "--all-fields", choices=["lng", "gogpt"], metavar="{lng,gogpt}",
        help="Produce the website's flat 'Export all fields' CSV. "
             "`lng` = LNG terminals (one row per lng_unit, ~115 columns). "
             "`gogpt` = oil & gas power plants (combustion + trackerSearch=GOGPT). "
             "Requires -o OUTPUT_FILE.",
    )
    return parser


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------

def mode_list_tables(engine: Engine) -> int:
    for t in list_user_tables(engine):
        print(t.label)
    return 0


def mode_describe(engine: Engine, table_str: str) -> int:
    ref = parse_table_ref(table_str)
    rows = describe_table(engine, ref)
    if not rows:
        sys.stderr.write(f"ERROR: table {ref.label} not found (or no SELECT permission).\n")
        return 5
    print(f"{ref.label}")
    for name, dtype, nullable in rows:
        print(f"  {name}\t{dtype}\t{'NULL' if nullable == 'YES' else 'NOT NULL'}")
    return 0


def _attach_pks(engine: Engine, plans: list[TablePlan]) -> None:
    """Pre-fetch each plan's PK column once so we can build subqueries."""
    for p in plans:
        pk = get_primary_key(engine, p.table)
        if pk:
            setattr(p, "_pk", pk)
    # Each level-1 plan records its root_target so the chain builder can recover it.
    for p in plans:
        if p.mode == "fk" and p.parent is not None and p.parent.mode == "root":
            # the FK on p points to root's PK; that's our root_target
            setattr(p, "_root_target", getattr(p.parent, "_pk", None))


def mode_discover(
    engine: Engine, root: TableRef, project_type_col: str,
    max_depth: int, extra_excludes: set[str], include_reference: bool,
) -> int:
    plans = build_traversal_plan(
        engine, root, project_type_col, max_depth, extra_excludes,
    )
    print(f"Discovery plan (root: {root.label}, max-depth: {max_depth}):")
    print(f"{'depth':>5}  {'mode':<10}  {'table':<40}  via")
    print(f"{'-'*5}  {'-'*10}  {'-'*40}  {'-'*30}")
    for p in plans:
        via = ""
        if p.parent is not None:
            via = f"{p.parent.table.label}.{p.fk_column}"
        print(f"{p.depth:>5}  {p.mode:<10}  {p.table.label:<40}  {via}")
    if include_reference:
        print()
        print("Reference tables (would be dumped in full):")
        for r in resolve_reference_tables(engine):
            print(f"  {r.label}")
    return 0


def mode_sql(engine: Engine, sql: str, out_path: str, chunksize: int) -> int:
    stripped = sql.strip().lstrip("(").lstrip().lower()
    if not (stripped.startswith("select") or stripped.startswith("with")):
        sys.stderr.write("ERROR: --sql must be a SELECT or WITH ... SELECT statement.\n")
        return 6
    n = write_query_to_csv(engine, sql, out_path, chunksize)
    sys.stderr.write(f"Wrote {n:,} rows to {out_path}\n")
    return 0


def mode_single_table(
    engine: Engine, ref: TableRef, out_path: str,
    where: str | None, limit: int | None, chunksize: int,
) -> int:
    cols = get_columns(engine, ref)
    if not cols:
        sys.stderr.write(f"ERROR: table {ref.label} not found (or no SELECT permission).\n")
        return 7
    sql = f"SELECT * FROM {ref.qualified}"
    if where:
        sql += f" WHERE {where}"
    if limit:
        sql += f" LIMIT {int(limit)}"
    n = write_query_to_csv(engine, sql, out_path, chunksize)
    sys.stderr.write(f"Wrote {n:,} rows from {ref.label} to {out_path}\n")
    return 0


def mode_multi_table(
    engine: Engine,
    root: TableRef,
    project_type_code: int,
    project_type_col: str,
    out_dir: str,
    max_depth: int,
    extra_excludes: set[str],
    extra_where: str | None,
    limit: int | None,
    chunksize: int,
    include_reference: bool,
) -> int:
    os.makedirs(out_dir, exist_ok=True)
    plans = build_traversal_plan(
        engine, root, project_type_col, max_depth, extra_excludes,
    )
    _attach_pks(engine, plans)

    manifest_rows: list[dict[str, str]] = []
    total_rows = 0
    for p in plans:
        sql = build_select_for_plan(
            p, project_type_code, project_type_col, extra_where, limit,
        )
        fname = safe_filename(p.table.label)
        out_path = os.path.join(out_dir, fname)
        try:
            n = write_query_to_csv(engine, sql, out_path, chunksize)
        except Exception as e:
            sys.stderr.write(f"WARN: failed to export {p.table.label}: {e}\n")
            manifest_rows.append({
                "table": p.table.label, "depth": str(p.depth), "mode": p.mode,
                "rows": "ERROR", "file": "", "error": str(e),
            })
            continue
        total_rows += n
        manifest_rows.append({
            "table": p.table.label, "depth": str(p.depth), "mode": p.mode,
            "rows": str(n), "file": fname, "error": "",
        })
        sys.stderr.write(f"  [{p.depth}] {p.table.label}: {n:,} rows -> {fname}\n")

    if include_reference:
        for ref in resolve_reference_tables(engine):
            sql = f"SELECT * FROM {ref.qualified}"
            fname = safe_filename(ref.label)
            out_path = os.path.join(out_dir, fname)
            try:
                n = write_query_to_csv(engine, sql, out_path, chunksize)
            except Exception as e:
                sys.stderr.write(f"WARN: failed to export reference {ref.label}: {e}\n")
                continue
            total_rows += n
            manifest_rows.append({
                "table": ref.label, "depth": "-", "mode": "reference",
                "rows": str(n), "file": fname, "error": "",
            })
            sys.stderr.write(f"  [ref] {ref.label}: {n:,} rows -> {fname}\n")

    manifest_path = os.path.join(out_dir, "_manifest.csv")
    with open(manifest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["table", "depth", "mode", "rows", "file", "error"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    sys.stderr.write(
        f"\nDone. {total_rows:,} total rows across {len(manifest_rows)} table(s). "
        f"Manifest: {manifest_path}\n"
    )
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    args = build_arg_parser().parse_args()

    url = get_database_url()
    engine = build_engine(url, args.timeout_ms)

    # --- introspection modes (don't need --project-type) ---
    if args.list_tables:
        return mode_list_tables(engine)
    if args.describe:
        return mode_describe(engine, args.describe)

    # --- --all-fields mode (website-format flat CSV) ---
    if args.all_fields:
        if not args.output:
            sys.stderr.write("ERROR: --all-fields requires -o OUTPUT_FILE.\n")
            return 2
        if args.all_fields == "lng":
            from gem_all_fields import export_all_fields
            n = export_all_fields(engine, args.output, args.limit)
        elif args.all_fields == "gogpt":
            from gem_all_fields import export_gogpt_all_fields
            n = export_gogpt_all_fields(engine, args.output, args.limit)
        else:
            sys.stderr.write(f"ERROR: unknown --all-fields target: {args.all_fields}\n")
            return 2
        sys.stderr.write(f"Wrote {n:,} unit rows to {args.output}\n")
        return 0

    # --- --sql mode ---
    if args.sql:
        if args.project_type or args.table:
            sys.stderr.write("ERROR: --sql cannot be combined with --project-type or --table.\n")
            return 2
        if not args.output:
            sys.stderr.write("ERROR: --sql requires -o OUTPUT_FILE.\n")
            return 2
        return mode_sql(engine, args.sql, args.output, args.chunksize)

    # --- --discover mode ---
    if args.discover:
        if not args.project_type:
            sys.stderr.write("ERROR: --discover requires --project-type.\n")
            return 2
        _ = resolve_project_type(args.project_type)  # validate
        root = parse_table_ref(args.projects_table)
        return mode_discover(
            engine, root, args.project_type_column,
            args.max_depth, set(args.exclude), args.include_reference,
        )

    # --- single-table mode ---
    if args.table:
        if not args.output:
            sys.stderr.write("ERROR: --table requires -o OUTPUT_FILE.\n")
            return 2
        ref = parse_table_ref(args.table)
        return mode_single_table(
            engine, ref, args.output, args.where, args.limit, args.chunksize,
        )

    # --- multi-table mode (default) ---
    if not args.project_type:
        sys.stderr.write(
            "ERROR: must pass --project-type (multi-table mode), "
            "or --table, --sql, --list-tables, --describe, or --discover.\n"
        )
        return 2
    if not args.output:
        sys.stderr.write("ERROR: multi-table mode requires -o OUTPUT_DIR.\n")
        return 2

    code = resolve_project_type(args.project_type)
    root = parse_table_ref(args.projects_table)

    extra_where = args.where
    if args.tracker:
        if code != PROJECT_TYPES["combustion"]:
            sys.stderr.write(
                "ERROR: --tracker is only valid with --project-type combustion.\n"
            )
            return 2
        tracker_value = resolve_tracker(args.tracker)
        tracker_clause = build_tracker_exists_clause(tracker_value)
        extra_where = (
            f"({extra_where}) AND {tracker_clause}" if extra_where else tracker_clause
        )

    return mode_multi_table(
        engine, root, code, args.project_type_column, args.output,
        args.max_depth, set(args.exclude), extra_where, args.limit,
        args.chunksize, args.include_reference,
    )


if __name__ == "__main__":
    raise SystemExit(main())
