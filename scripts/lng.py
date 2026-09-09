#!/usr/bin/env python3
"""Stable command-line entry point for the repository's batch lifecycle."""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

from batch_contract import load_json, validate_json_list, validate_meta
from paths import db_ops_repo, gem_export_csv, gogpt_repo, repo_root

ROOT = repo_root()


def _result(label: str, ok: bool, detail: str, *, required: bool = True) -> bool:
    level = "OK" if ok else ("FAIL" if required else "WARN")
    print(f"{level:4} {label:20} {detail}")
    return ok or not required


def doctor() -> int:
    """Check the local environment without opening a database connection."""
    checks: list[bool] = []
    checks.append(_result("Python", sys.version_info >= (3, 11), sys.version.split()[0]))
    checks.append(_result("openpyxl", importlib.util.find_spec("openpyxl") is not None,
                          "installed" if importlib.util.find_spec("openpyxl") else "pip install -e '.[dev]'"))
    for command in ("git", "curl", "pdftotext", "pdftoppm"):
        found = shutil.which(command)
        checks.append(_result(command, bool(found), found or "not found", required=command == "git"))
    for label, path, required in (
        ("gem-db-ops", db_ops_repo(), True),
        ("gogpt-researcher", gogpt_repo(), False),
        ("GEM export", gem_export_csv(), False),
    ):
        checks.append(_result(label, path.exists(), str(path), required=required))
    db_url = bool(os.environ.get("GEM_READONLY_DB_URL"))
    checks.append(_result("read-only DB URL", db_url, "set" if db_url else "GEM_READONLY_DB_URL is unset", required=False))
    print("\nDoctor is read-only; it does not test credentials or download data.")
    return 0 if all(checks) else 1


def validate(paths: list[str]) -> int:
    targets = [Path(p) for p in paths] if paths else sorted((ROOT / "batches" / "staging").glob("**/meta.json"))
    expanded: list[Path] = []
    for target in targets:
        resolved = target if target.is_absolute() else ROOT / target
        expanded.extend(sorted(resolved.glob("**/*.json")) if resolved.is_dir() else [resolved])
    targets = expanded
    errors: list[str] = []
    for path in targets:
        try:
            value = load_json(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if path.name == "meta.json":
            errors.extend(validate_meta(value, source=str(path)))
        elif any(token in path.name for token in ("staged_", ".updates.json", ".timeline.json", ".qa.json", ".wiki.json", ".entity.json", ".monitor.json", ".newunits.json", ".newterminals.json")):
            errors.extend(validate_json_list(path))
    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Validated {len(targets)} JSON contract file(s).")
    return 0


def run_script(script: Path, forwarded: list[str]) -> int:
    return subprocess.run([sys.executable, str(script), *forwarded]).returncode


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check dependencies, sibling repos, tools, and environment")
    val = sub.add_parser("validate", help="validate metadata or JSON paths (all metadata by default)")
    val.add_argument("paths", nargs="*")
    for command, help_text in (
        ("qc", "run the fail-closed staging QC gate"),
        ("assemble", "assemble a region and lane"),
        ("build", "build an immutable review workbook and manifest"),
        ("coverage", "render the validated coverage ledger"),
    ):
        child = sub.add_parser(command, help=help_text, add_help=False)
        child.add_argument("args", nargs=argparse.REMAINDER)
    args = ap.parse_args(argv)
    if args.command == "doctor":
        return doctor()
    if args.command == "validate":
        return validate(args.paths)
    scripts = {
        "qc": ROOT / "scripts" / "staging_qc.py",
        "assemble": ROOT / "batches" / "staging" / "_assemble.py",
        "build": ROOT / "scripts" / "build_review_package.py",
        "coverage": ROOT / "scripts" / "coverage_status.py",
    }
    return run_script(scripts[args.command], args.args)


if __name__ == "__main__":
    sys.exit(main())
