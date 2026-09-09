"""Canonical batch metadata, validation, and reproducibility manifests."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from atomic_io import atomic_write_json

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = {
    "update", "discovery", "update+discovery", "reconciliation", "captive_power",
    "refsweep", "record_repair", "qc", "coverage_audit",
}
STATUSES = {"in_progress", "built", "applied", "abandoned", "superseded"}
RETIRED_STATUSES = {"abandoned", "superseded"}


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def repository_identity(repo: str | Path) -> dict[str, Any]:
    repo = Path(repo).resolve()
    head = _git(repo, "rev-parse", "HEAD")
    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=normal")
    return {
        "path": str(repo),
        "commit": head,
        "dirty": bool(status) if status is not None else None,
    }


def validate_meta(meta: Any, *, source: str = "meta.json") -> list[str]:
    """Return actionable contract violations; never mutate legacy metadata."""
    if not isinstance(meta, dict):
        return [f"{source}: root must be a JSON object"]
    errors: list[str] = []
    required = ("scope_slug", "workflow", "countries", "status")
    for key in required:
        if meta.get(key) in (None, "", []):
            errors.append(f"{source}: {key!r} is required")
    workflow = meta.get("workflow")
    if workflow and workflow not in WORKFLOWS:
        errors.append(f"{source}: unsupported workflow {workflow!r}")
    status = meta.get("status")
    if status == "complete":
        errors.append(f"{source}: status 'complete' is legacy; use 'built' or 'applied'")
    elif status and status not in STATUSES:
        errors.append(f"{source}: unsupported status {status!r}")
    countries = meta.get("countries")
    if countries is not None and (
        not isinstance(countries, list)
        or any(not isinstance(v, str) or not v.strip() for v in countries)
    ):
        errors.append(f"{source}: countries must be a non-empty-string list")
    for field in ("started", "built", "applied"):
        value = meta.get(field)
        if value:
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError):
                errors.append(f"{source}: {field} must be YYYY-MM-DD, got {value!r}")
    if status == "applied" and not meta.get("applied"):
        errors.append(f"{source}: applied status requires an applied date")
    if status == "built" and not meta.get("built"):
        errors.append(f"{source}: built status requires a built date")
    return errors


def load_json(path: str | Path) -> Any:
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc


def validate_json_list(path: str | Path) -> list[str]:
    path = Path(path)
    try:
        value = load_json(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    if not isinstance(value, list):
        return [f"{path}: expected a JSON list, got {type(value).__name__}"]
    return []


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    try:
        display = str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        display = str(path.resolve())
    return {"path": display, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _csv_contract(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            header = next(csv.reader(handle))
    except (OSError, StopIteration):
        header = []
    encoded = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode()
    return {"columns": header, "column_count": len(header), "header_sha256": hashlib.sha256(encoded).hexdigest()}


def build_manifest(
    *, output: str | Path, mode: str, inputs: Iterable[str | Path],
    command: Iterable[str] | None = None, extra_repositories: Iterable[str | Path] = (),
) -> dict[str, Any]:
    files = [Path(p).resolve() for p in inputs if Path(p).is_file()]
    repo = repository_identity(REPO_ROOT)
    manifest: dict[str, Any] = {
        "manifest_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "output": str(Path(output).resolve()),
        "command": list(command or []),
        "repository": repo,
        "inputs": [_file_record(p, REPO_ROOT) for p in sorted(set(files))],
        "related_repositories": [repository_identity(p) for p in extra_repositories if Path(p).is_dir()],
    }
    csv_inputs = [p for p in files if p.suffix.lower() == ".csv"]
    if csv_inputs:
        manifest["csv_contracts"] = {
            rec["path"]: _csv_contract(path)
            for path, rec in ((p, _file_record(p, REPO_ROOT)) for p in csv_inputs)
        }
    return manifest


def write_manifest(path: str | Path, manifest: dict[str, Any]) -> None:
    atomic_write_json(path, manifest)
