#!/usr/bin/env python3
"""Fold the re-check pass into build_review_package inputs for one region.

  python batches/staging/devpipeline_exhaustive/_merge_recheck.py middleeast

For each country slug in the region it merges:
  <slug>.updates.json   (first pass)            <- base records
  <slug>.qa.json        (first pass)            <- base qa
  <slug>.recheck.json   (this pass, optional)   <- overrides / additions / resolutions

Merge rules:
- updates: key = (terminal_id, unit_id, field_name). A recheck `update_overrides` record REPLACES the
  first-pass record for its key (so a recovered ref, a changed value, or a delete supersedes the original);
  an override for a new key is appended. Cells the recheck never touches keep their first-pass record.
- qa: drop any first-pass qa entry matched by a `qa_resolved` selector, then append `qa_add`.
- Writes <region>/_build/staged_updates.json, staged_qa_review.json, staged_scope.json, checked_roster.json
  (same shapes _assemble.py produces). With NO recheck files present, output == a plain _assemble run.

The first-pass <slug>.updates.json / <slug>.qa.json are never modified — git is the audit trail.
"""
import json, sys, glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
REGION = sys.argv[1] if len(sys.argv) > 1 else "middleeast"
BASE = HERE / REGION
OUT = BASE / "_build"
OUT.mkdir(parents=True, exist_ok=True)


def load(fp, default):
    p = Path(fp)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  WARN: {fp}: {e}")
        return default


def ukey(r):
    return (r.get("terminal_id"), r.get("unit_id"), r.get("field_name"))


def qa_matches(entry, selector):
    """True if a qa_resolved selector matches a first-pass qa entry."""
    sub = selector.get("issue_contains")
    if sub:
        return sub in (entry.get("issue") or "")
    if selector.get("terminal_id") and selector["terminal_id"] != entry.get("terminal_id"):
        return False
    if selector.get("unit_id") and selector["unit_id"] != entry.get("unit_id"):
        return False
    fld = selector.get("field_name")
    if fld and fld not in (entry.get("issue") or ""):
        return False
    # require at least one positive criterion so an empty selector never nukes everything
    return bool(selector.get("terminal_id") or selector.get("unit_id"))


def slugs():
    return sorted({Path(p).name[:-len(".updates.json")]
                   for p in glob.glob(str(BASE / "*.updates.json"))
                   if not p.endswith(".recheck.updates.json")})


def _first(d, *keys):
    for k in keys:
        v = d.get(k)
        if v:
            return v
    return ""


def normalize_entity(e):
    """Map the per-shard entity.json record (agents use varied keys) onto the
    columns build_entity_additions_sheet expects. The remote entity_lookup
    endpoint has been degraded this effort, so the dup-check is NOT reliable —
    set lookup_was_run to a "RUN…" string so the build yellow-flags it and the
    researcher re-runs entity_lookup before creating the entity (methodology:
    no duplicate entities)."""
    return {
        "entity_name": _first(e, "entity_name", "proposed_name", "name"),
        "entity_type": _first(e, "entity_type", "type"),
        "country_of_hq": _first(e, "country_of_hq", "country_hq", "country"),
        "parent_entity": _first(e, "parent_entity", "parent", "parent_or_jv"),
        "rationale_for_new_entity": _first(e, "rationale_for_new_entity", "notes",
                                           "role", "source_notes"),
        "lookup_was_run": "RUN entity_lookup (remote endpoint degraded this batch — re-verify before creating)",
        "lookup_result_summary": _first(e, "lookup_result_summary", "lookup_result"),
        "referenced_by_terminals": _first(e, "referenced_by_terminals",
                                          "related_terminal_name", "related_terminal_id"),
        "referenced_by_units": _first(e, "referenced_by_units",
                                      "related_unit_id", "related_unit_name"),
        "researcher_initials": _first(e, "researcher_initials") or "AI-draft (devpipeline-exh)",
    }


def normalize_monitor(m, country_fallback=""):
    """Map the per-shard monitor.json record onto build_monitor_list_sheet
    columns. Agents emit either Discovery-candidate shapes (candidate_name/
    current_state/watch_for) or watch-on-existing-terminal shapes (terminal_name/
    watch_item|issue/trigger_to_act|suggested_action) — fold both. The latter
    shape carries no country, so fall back to the shard's done-marker country."""
    urls = m.get("evidence_urls") or m.get("ref_urls") or []
    return {
        "country": _first(m, "country") or country_fallback,
        "candidate_name": _first(m, "candidate_name", "terminal_name"),
        "sponsor_or_proposer": _first(m, "sponsor_or_proposer", "sponsor"),
        "first_observed_batch": _first(m, "first_observed_batch") or "2026-06 devpipeline-exhaustive",
        "last_observed_batch": _first(m, "last_observed_batch") or "2026-06 devpipeline-exhaustive",
        "current_state": _first(m, "current_state", "watch_item", "issue"),
        "missing_threshold_elements": _first(m, "missing_threshold_elements"),
        "watch_for": _first(m, "watch_for", "trigger_to_act", "suggested_action"),
        "best_lead_url": _first(m, "best_lead_url") or (urls[0] if urls else ""),
        "notes": _first(m, "notes"),
    }


def main():
    all_updates, all_qa, countries = [], [], []
    all_entities, all_monitor = [], []
    tot = {"overrides": 0, "qa_add": 0, "qa_resolved": 0, "deletes": 0}
    for slug in slugs():
        base_u = load(BASE / f"{slug}.updates.json", [])
        base_q = load(BASE / f"{slug}.qa.json", [])
        done = load(BASE / f"{slug}.done.json", {})
        slug_country = done.get("country") if isinstance(done, dict) else ""
        for e in load(BASE / f"{slug}.entity.json", []):
            all_entities.append(normalize_entity(e))
        for m in load(BASE / f"{slug}.monitor.json", []):
            all_monitor.append(normalize_monitor(m, slug_country))
        rc = load(BASE / f"{slug}.recheck.json", {})
        overrides = rc.get("update_overrides", []) if isinstance(rc, dict) else []
        qa_add = rc.get("qa_add", []) if isinstance(rc, dict) else []
        qa_resolved = rc.get("qa_resolved", []) if isinstance(rc, dict) else []

        # merge updates (override by key, preserving first-pass order; new keys appended)
        merged = {ukey(r): r for r in base_u}
        order = [ukey(r) for r in base_u]
        for ov in overrides:
            k = ukey(ov)
            if k not in merged:
                order.append(k)
            merged[k] = ov
            if ov.get("delete"):
                tot["deletes"] += 1
        all_updates.extend(merged[k] for k in order)

        # merge qa (drop resolved, append new)
        kept = [e for e in base_q if not any(qa_matches(e, s) for s in qa_resolved)]
        all_qa.extend(kept + qa_add)

        tot["overrides"] += len(overrides)
        tot["qa_add"] += len(qa_add)
        tot["qa_resolved"] += len(base_q) - len(kept)
        # roster: prefer the recheck done-marker's country, else first-pass done-marker
        countries.append((rc.get("country") if isinstance(rc, dict) else None)
                         or (done.get("country") if isinstance(done, dict) else None) or slug)

    # clear stale staged_* then write fresh
    for old in OUT.glob("staged_*.json"):
        old.unlink()
    (OUT / "staged_updates.json").write_text(
        json.dumps(all_updates, ensure_ascii=False, indent=2), encoding="utf-8")
    if all_qa:
        (OUT / "staged_qa_review.json").write_text(
            json.dumps(all_qa, ensure_ascii=False, indent=2), encoding="utf-8")
    tids = sorted({u.get("terminal_id") for u in all_updates if u.get("terminal_id")})
    (OUT / "staged_scope.json").write_text(
        json.dumps({"_comment": f"{REGION} dev-pipeline exhaustive + re-check", "terminal_ids": tids},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "checked_roster.json").write_text(
        json.dumps(sorted(set(countries)), ensure_ascii=False, indent=2), encoding="utf-8")

    # entity additions: dedupe by (entity_name lower, entity_type), merging the
    # referenced_by_* fields so one entity seen by two shards lists both terminals
    ent_by = {}
    for e in all_entities:
        if not e.get("entity_name"):
            continue
        k = (e["entity_name"].strip().lower(), (e.get("entity_type") or "").strip().lower())
        if k in ent_by:
            cur = ent_by[k]
            for fld in ("referenced_by_terminals", "referenced_by_units"):
                a, b = cur.get(fld, ""), e.get(fld, "")
                if b and b not in a:
                    cur[fld] = "; ".join([p for p in [a, b] if p])
        else:
            ent_by[k] = e
    entities = list(ent_by.values())
    if entities:
        (OUT / "staged_entity_additions.json").write_text(
            json.dumps(entities, ensure_ascii=False, indent=2), encoding="utf-8")

    # monitor list: dedupe by (country lower, candidate_name lower)
    mon_by = {}
    for m in all_monitor:
        if not (m.get("country") or m.get("candidate_name")):
            continue
        k = ((m.get("country") or "").strip().lower(),
             (m.get("candidate_name") or "").strip().lower())
        mon_by.setdefault(k, m)
    monitor = list(mon_by.values())
    if monitor:
        (OUT / "staged_monitor_list.json").write_text(
            json.dumps(monitor, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"region={REGION}  build_dir={OUT}")
    print(f"  updates(merged): {len(all_updates)}   qa(merged): {len(all_qa)}   scope_terminals: {len(tids)}")
    print(f"  entities: {len(entities)}   monitor: {len(monitor)}")
    print(f"  recheck: overrides={tot['overrides']} (deletes={tot['deletes']})  "
          f"qa_add={tot['qa_add']}  qa_resolved={tot['qa_resolved']}")


if __name__ == "__main__":
    main()
