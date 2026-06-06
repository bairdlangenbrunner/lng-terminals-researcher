"""
Maintain the durable cross-batch monitor list — the loop the Discovery SOP
assumes but nothing previously closed.

Discovery SOP §5/§10.10: below-threshold candidates (sponsor TBD, vague
location, verbal intent only) are parked in `monitor_list` so we don't
re-discover the same vague-rumor project every batch, and they drop out once a
later batch promotes them to `new_terminals`. The durable store for that
cross-batch state is `monitor_list/current.json` (committed; see
`batches/staging/README.md`: "Cross-batch monitor state lives in monitor_list/").

The store is a JSON list of monitor entries — the same schema
`build_review_package.py`'s monitor_list sheet writes:
    country, candidate_name, sponsor_or_proposer,
    first_observed_batch, last_observed_batch,
    current_state, missing_threshold_elements, watch_for, best_lead_url, notes

`build_review_package.py` already merges a `prior_monitor_list.json` (found in
its --inputs-dir) with the current batch's candidates into the sheet, but
nothing fed that prior file from the durable store, and nothing folded a
batch's results back. This script is the two missing halves of the loop:

  seed <inputs-dir>
      Copy the durable store -> <inputs-dir>/prior_monitor_list.json so the
      NEXT discovery build's roll-forward merge starts from accumulated state.
      Run BEFORE `build_review_package.py --mode discovery`.

  update <inputs-dir> [--batch <label>]
      Fold THIS batch's discovery outputs back into the durable store. Run
      AFTER the discovery build (and ideally after the user has reviewed it).
      Merges the durable store with <inputs-dir>/staged_monitor_list.json by
      (country, candidate_name) — preserving first_observed_batch, bumping
      last_observed_batch — then DROPS any entry promoted to new_terminals this
      batch (matched against <inputs-dir>/staged_new_terminals.json by
      normalized country + name). Writes monitor_list/current.json.

Usage:
    python scripts/monitor_store.py seed   batches/staging/<region>/_build
    python scripts/monitor_store.py update batches/staging/<region>/_build --batch 20260605_1400_ET
    python scripts/monitor_store.py show          # print the durable store summary
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize_country, normalize_terminal_name

REPO_ROOT = Path(__file__).resolve().parent.parent
STORE_PATH = REPO_ROOT / "monitor_list" / "current.json"

# Entry fields preserved across batches (mirrors build_review_package.py's
# monitor_list sheet headers).
MONITOR_FIELDS = (
    "country", "candidate_name", "sponsor_or_proposer",
    "first_observed_batch", "last_observed_batch",
    "current_state", "missing_threshold_elements",
    "watch_for", "best_lead_url", "notes",
)


def _entry_key(entry):
    """Dedup key: normalized (country, candidate_name).

    Normalizing (vs. the raw-string key build_review_package.py historically
    used) keeps 'Vietnam ' / 'vietnam' and diacritic variants from splitting
    into duplicate monitor rows across batches.
    """
    country = normalize_country(entry.get("country") or "") or (entry.get("country") or "").strip().lower()
    name = normalize_terminal_name(entry.get("candidate_name") or "") or (entry.get("candidate_name") or "").strip().lower()
    return (country, name)


def _new_terminal_key(term):
    """Promotion-match key for a staged new_terminals row."""
    country = normalize_country(term.get("Country/Area") or "") or (term.get("Country/Area") or "").strip().lower()
    name = normalize_terminal_name(term.get("TerminalName") or "") or (term.get("TerminalName") or "").strip().lower()
    return (country, name)


def load_store():
    """Read the durable store as a list. Tolerates the legacy empty `{}`."""
    if not STORE_PATH.exists():
        return []
    raw = STORE_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    if isinstance(data, dict):
        # Legacy/empty placeholder ({}). Treat as empty unless it wraps a list.
        if not data:
            return []
        if isinstance(data.get("monitor_list"), list):
            return data["monitor_list"]
        return []
    return data if isinstance(data, list) else []


def save_store(entries):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _load_list(path):
    if not path.exists():
        return []
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    data = json.loads(raw)
    return data if isinstance(data, list) else []


def cmd_seed(inputs_dir):
    inputs_dir = Path(inputs_dir)
    if not inputs_dir.exists():
        sys.exit(f"ERROR: inputs dir not found: {inputs_dir}")
    store = load_store()
    out = inputs_dir / "prior_monitor_list.json"
    out.write_text(json.dumps(store, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  seeded {len(store)} durable monitor entr{'y' if len(store)==1 else 'ies'} -> {out}")
    print("  (build_review_package.py --mode discovery will roll these forward into the sheet)")


def _merge(prior, current, batch_label):
    """Merge durable (prior) + this batch's monitor candidates by entry key.

    Preserves first_observed_batch; bumps last_observed_batch; non-empty
    current values overwrite prior. Same semantics as the build sheet's merge,
    keyed on the normalized entry key.
    """
    combined = {}
    for e in prior:
        combined[_entry_key(e)] = dict(e)
    for e in current:
        key = _entry_key(e)
        entry = dict(e)
        if batch_label:
            entry.setdefault("first_observed_batch", batch_label)
            entry["last_observed_batch"] = batch_label
        if key in combined:
            existing = combined[key]
            # preserve the original first_observed_batch
            entry["first_observed_batch"] = existing.get("first_observed_batch") or entry.get("first_observed_batch")
            merged = dict(existing)
            for k, v in entry.items():
                if k == "first_observed_batch":
                    merged[k] = entry["first_observed_batch"]
                elif v:
                    merged[k] = v
            combined[key] = merged
        else:
            combined[key] = entry
    return combined


def cmd_update(inputs_dir, batch_label):
    inputs_dir = Path(inputs_dir)
    if not inputs_dir.exists():
        sys.exit(f"ERROR: inputs dir not found: {inputs_dir}")

    prior = load_store()
    current = _load_list(inputs_dir / "staged_monitor_list.json")
    promotions = _load_list(inputs_dir / "staged_new_terminals.json")

    combined = _merge(prior, current, batch_label)

    # Drop anything promoted to new_terminals this batch (Discovery SOP §5:
    # "dropping items that have since moved to the real new_terminals sheet").
    promoted_keys = {_new_terminal_key(t) for t in promotions}
    dropped = [v for k, v in combined.items() if k in promoted_keys]
    kept = {k: v for k, v in combined.items() if k not in promoted_keys}

    entries = list(kept.values())
    save_store(entries)

    added = len(kept) - sum(1 for e in prior if _entry_key(e) in kept)
    print(f"  durable store updated -> {STORE_PATH}")
    print(f"    prior:        {len(prior)}")
    print(f"    this batch:   {len(current)} monitor candidate(s)")
    print(f"    promoted out: {len(dropped)} (now in new_terminals)")
    if dropped:
        for d in dropped:
            print(f"      - {d.get('country')}: {d.get('candidate_name')}")
    print(f"    total now:    {len(entries)}")


def cmd_show():
    store = load_store()
    print(f"  durable monitor store: {STORE_PATH}")
    print(f"  entries: {len(store)}")
    by_country = {}
    for e in store:
        by_country.setdefault(e.get("country") or "?", 0)
        by_country[e.get("country") or "?"] += 1
    for c in sorted(by_country):
        print(f"    {c}: {by_country[c]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser("seed", help="copy durable store -> <inputs-dir>/prior_monitor_list.json (before a discovery build)")
    p_seed.add_argument("inputs_dir")

    p_upd = sub.add_parser("update", help="fold this batch's monitor candidates back into the durable store (after a discovery build)")
    p_upd.add_argument("inputs_dir")
    p_upd.add_argument("--batch", default=None, help="batch label to stamp on first/last_observed_batch (e.g. 20260605_1400_ET)")

    sub.add_parser("show", help="print the durable store summary")

    args = ap.parse_args()
    if args.cmd == "seed":
        cmd_seed(args.inputs_dir)
    elif args.cmd == "update":
        cmd_update(args.inputs_dir, args.batch)
    elif args.cmd == "show":
        cmd_show()


if __name__ == "__main__":
    main()
