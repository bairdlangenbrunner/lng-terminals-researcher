"""
Report-vs-GEM reconciliation diff.

Parameterized on report type so the same logic handles GIIGNL today and IGU
(or any future industry report) tomorrow.

Produces a four-way classification per Reconciliation SOP:
  - Match: report row and GEM row exist for the same project (capacity/owner
           may agree or disagree — flagged separately)
  - GIIGNL-only: report shows a project GEM doesn't have (discovery candidate)
  - GEM-only: GEM shows a project the report doesn't list (usually expected —
              GEM tracks more than the report does; see Reconciliation SOP §4)
  - Ambiguous: name/country triggers multiple GEM matches; needs disambiguation

Matching is PROJECT-LEVEL not unit-level — multi-unit GEM projects collapse
to one row for the diff. Per Reconciliation SOP §3.5, this means unit-level
capacity disagreements get reported at the project total level. The decision
to match project-level not unit-level is documented in the SOP; this script
implements that.

Two-pass matching:
  Pass 1: exact (normalized country, normalized site name)
  Pass 2: fuzzy within same country (for surviving GIIGNL-only rows) —
          a candidate is "fuzzy match" if normalized site name is a substring
          match in either direction, OR shares a common token of length ≥4
          AND owner overlap.

Usage:
    python report_diff.py --report giignl \\
        --extracted ./giignl_extracted.csv \\
        --output ./giignl_diff.json
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import (
    normalize_country, normalize_entity, normalize_terminal_name,
    parse_entity_list, transliterate_to_english,
)


DEFAULT_GEM_CSV = "./gem_export.csv"

# Matches a trailing " Expansion" / " Extension" qualifier on a report site name.
# GIIGNL splits a phased terminal across "<Site>" and "<Site> Expansion" rows;
# this captures the "<Site>" base so the rows can be folded together (see
# _classify). Requires a non-empty base before the qualifier, so a bare
# "expansion" extraction artifact does NOT match.
_EXPANSION_RE = re.compile(r"^(.*\S)\s+(?:expansion|extension)\s*$", re.IGNORECASE)


def _strip_expansion_suffix(raw):
    """Return the base site name if `raw` ends in 'Expansion'/'Extension', else None."""
    if not raw:
        return None
    m = _EXPANSION_RE.match(str(raw).strip())
    return m.group(1).strip() if m else None


# Matches a trailing unit/complex code on a report site name, e.g. the Algerian
# Sonatrach complexes "Arzew GL1Z" / "Arzew GL2Z" / "Skikda GL1K". The code must
# contain BOTH letters and digits (regex: 1-4 letters, digits, optional trailing
# letter) so plain named stages WITHOUT a digit are never stripped — protects
# "Senboku II", "Bontang Train E", "Corpus Christi Stage III". Used to fold the
# per-complex rows to a shared base site so they (a) match one GEM project and
# (b) align 1:1 to GEM unit names (the code "GL1Z" == GEM unit "GL1Z").
_UNIT_CODE_RE = re.compile(r"^(.*\S)\s+([A-Za-z]{1,4}\d+[A-Za-z]?)$")


def _strip_unit_code_suffix(raw):
    """Return the base site name if `raw` ends in a unit/complex code, else None.

    "Arzew GL1Z" -> "Arzew"   "Skikda GL1K" -> "Skikda"   "Senboku II" -> None
    """
    if not raw:
        return None
    m = _UNIT_CODE_RE.match(str(raw).strip())
    if not m:
        return None
    code = m.group(2)
    # Regex guarantees a digit; require a letter too (a code, not a bare number).
    if not any(c.isalpha() for c in code):
        return None
    return m.group(1).strip()


# Matches a trailing explicit "Train <code>" designator — GIIGNL writes some
# complexes' per-train rows with the literal word "Train"/"Trains" plus a short
# code (Indonesia "Bontang Train E/F/G/H") instead of the compact "T<n>" form
# (which giignl_extract already peels into the `trains` column). The unit-code
# fold above deliberately ignores single-letter codes to protect named stages
# ("Senboku II", "Corpus Christi Stage III"); the literal word "Train" marks a
# genuine per-train row, so those fold to the shared base. Code is a 1-2 letter
# token, a 1-2 digit number, or a roman numeral.
_TRAIN_WORD_RE = re.compile(
    r"^(.*\S)\s+trains?\s+(?:[a-z]{1,2}|\d{1,2}|[ivxlc]{1,4})\s*$", re.IGNORECASE)


def _strip_train_word_suffix(raw):
    """Return the base site name if `raw` ends in an explicit 'Train <code>'
    designator, else None.  'Bontang Train E' -> 'Bontang'."""
    if not raw:
        return None
    m = _TRAIN_WORD_RE.match(str(raw).strip())
    return m.group(1).strip() if m else None


# Per-status anchor-year column to surface on the non-operating sheet. Pre-operating
# and dormancy statuses each have their own anchor; post-operating statuses fall back
# to the stop year then the actual start.
_STATUS_ANCHOR_COL = {
    "proposed": ["proposal_year"],
    "construction": ["construction_year", "proposal_year"],
    "shelved": ["shelved_year"],
    "cancelled": ["cancelled_year", "shelved_year"],
    "idled": ["stop_year", "actual_start_year"],
    "mothballed": ["stop_year", "actual_start_year"],
    "retired": ["stop_year", "actual_start_year"],
}


def _unit_anchor_year(row, ci, status):
    """Return a representative year string for a unit given its current status."""
    for col in _STATUS_ANCHOR_COL.get(status, []):
        idx = ci.get(col)
        if idx is not None and idx < len(row):
            val = (row[idx] or "").strip()
            if val:
                return val
    return ""


import string as _string

# GEM-side statuses that are NOT currently operating. GIIGNL's liq/regas tables
# are operating-only, so these never appear there — they populate the
# non-operating sheet (defaulting to "GEM has, GIIGNL doesn't").
_NONOP_STATUSES = {
    "proposed", "construction", "shelved", "cancelled",
    "idled", "mothballed", "retired",
}


def _simple_tokens(s):
    """Lowercased tokens split on whitespace / hyphen / slash, punctuation-stripped.

    Splitting on '-' and '/' lets 'arzew-bethioua' yield {'arzew','bethioua'} so a
    GIIGNL 'Arzew ...' row shares the 'arzew' token with GEM's hyphenated name.
    """
    out = set()
    for raw in re.split(r"[\s\-/]+", s or ""):
        clean = raw.strip(_string.punctuation + "()[]{}")
        if clean:
            out.add(clean)
    return out


def _tokens_4plus(s):
    """Distinctive (4+ char) tokens, for fuzzy name overlap."""
    return {t for t in _simple_tokens(s) if len(t) >= 4}


def _split_trailing_paren(name_norm):
    """Split a trailing '(...)' group off a normalized name.

    GEM disambiguates same-base-name terminals with a trailing first-owner
    parenthetical: 'tianjin lng terminal (sinopec)' → ('tianjin lng terminal',
    'sinopec'). Returns (base, paren_text); paren_text is '' when there is none.
    """
    m = re.match(r"^(.*)\(([^()]*)\)\s*$", name_norm)
    if m and m.group(1).strip():
        return m.group(1).strip(), m.group(2).strip()
    return name_norm, ""


# A sub-terminal designator like "S(2)" / "N(1)": a short letter group + a
# parenthesized digit. GIIGNL names a Qatar sub-terminal "QatarEnergy LNG S(2)";
# GEM names the corresponding unit "S(2) T3-5". The designator ("s2") is the stable
# bridge between them — it survives BOTH GIIGNL's per-train rows folding into one
# sub-terminal row AND GEM's train-range unit naming, where a plain token-subset
# check fails (GEM unit tokens {s(2, t3, 5} are not a subset of the report site
# {qatarenergy, lng, s(2}). It also disambiguates GEM's same-base-name siblings on
# its own: an "n*" designator can only belong to "QatarEnergy LNG (N)", an "s*" to
# "(S)" — no reliance on the parenthetical-owner heuristic.
_DESIGNATOR_RE = re.compile(r"([A-Za-z]{1,4})\s*\(\s*(\d+)\s*\)")


def _unit_designators(name):
    """Return the sub-terminal designator codes in a name.

    "QatarEnergy LNG S(2)" -> {"s2"}   "N(3) T6" -> {"n3"}   "Sabine Pass" -> set()
    Empty for the common case of a name without a parenthesized-digit code.
    """
    if not name:
        return set()
    return {(m.group(1) + m.group(2)).lower()
            for m in _DESIGNATOR_RE.finditer(str(name))}


def _align_units(rp, gp):
    """Align report member rows to GEM units within an already-matched project.

    The bridge is that a GEM unit name often appears as a token inside the GIIGNL
    site name (GIIGNL 'Arzew GL1Z' ⊃ GEM unit 'GL1Z'). A GEM unit is accepted for a
    report row when its normalized name is a token-subset of the report site name
    AND (the unit name is code-like [contains a digit] OR capacities are within 25%).

    Returns (unit_matches, matched_gem_unit_names).
    """
    unit_matches = []
    used = set()
    for r in rp["rows"]:
        site_tokens = _simple_tokens(normalize_terminal_name(r.get("site_name", "")))
        try:
            rcap = float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
        except ValueError:
            rcap = 0.0
        proj_total = gp.get("total_capacity_mtpa", 0.0)
        chosen = None
        for u in gp.get("units", []):
            un = u["unit_name_norm"]
            if not un or u["unit_name"] in used:
                continue
            un_tokens = _simple_tokens(un)
            if not un_tokens or not un_tokens <= site_tokens:
                continue
            has_digit = any(c.isdigit() for c in un)
            gcap = u["capacity_mtpa"]
            cap_close = bool(gcap and rcap and abs(rcap - gcap) / gcap <= 0.25)
            # Guard against pinning a whole-project report row onto a single unit
            # via a coincidental code token: GIIGNL "Portovaya LNG T1 (+ FSU)" is
            # 1.5 MTPA (the whole terminal) and tokenizes to GEM unit "T1" (0.75),
            # which would emit a spurious unit-level 100% conflict beside the
            # correct project-level 1.5-vs-1.5 match. Only accept the unit when the
            # report capacity is at least as close to this unit as to the project
            # total (otherwise the row clearly spans multiple units → leave it to
            # the project-level comparison).
            closer_to_unit = (not proj_total) or (
                bool(gcap) and abs(rcap - gcap) <= abs(rcap - proj_total))
            if (has_digit or cap_close) and closer_to_unit:
                chosen = u
                break
        if chosen:
            used.add(chosen["unit_name"])
            gcap = chosen["capacity_mtpa"]
            dpct = (abs(rcap - gcap) / gcap * 100) if gcap else None
            unit_matches.append({
                "report_site": r.get("site_name", ""),
                "report_capacity_mtpa": round(rcap, 2),
                "gem_unit_name": chosen["unit_name"],
                "gem_unit_status": chosen["status"],
                "gem_unit_capacity_mtpa": round(gcap, 2),
                "capacity_delta_pct": round(dpct, 1) if dpct is not None else None,
                # Agree only when capacities are identical at 2-decimal precision;
                # any non-zero difference is a conflict (red).
                "agree": bool(round(rcap - gcap, 2) == 0),
            })
    return unit_matches, {um["gem_unit_name"] for um in unit_matches}


def _corroborate_nonop(nonop_report_rows, gp):
    """Map a GEM non-operating unit_name -> a corroboration note, for each GIIGNL
    non-op report row that aligns to it.

    GIIGNL's tables are operating-only, so a GEM non-op unit normally defaults to
    "GEM has, GIIGNL doesn't". But when GIIGNL annotates a row "(Mothballed)" /
    "(stopped)" (Bontang Train E, Balhaf T1/T2), GIIGNL DOES list that unit — just
    as not-operating. We align such a row to the GEM non-op unit whose name is a
    token of the row's site_name + trains (so "Bontang Train E" -> unit "E", and
    "Balhaf" + trains "T1" -> unit "T1"), and return a note so the non-operating
    sheet shows the corroboration instead of a spurious gem-only flag. Scoped to a
    single matched terminal's units and conservative (first unique hit, marked
    used) — tiny blast radius (only fires when a report row carries a status)."""
    notes = {}
    used = set()
    nonop_units = [u for u in gp.get("units", []) if u["status"] in _NONOP_STATUSES]
    for r in nonop_report_rows:
        # Lowercase: _simple_tokens doesn't case-fold, and the `trains` field
        # ("T1") isn't normalized like site_name is, so compare case-insensitively
        # against GEM's already-lowercased unit_name_norm.
        toks = {t.lower() for t in
                (_simple_tokens(normalize_terminal_name(r.get("site_name", "")))
                 | _simple_tokens(r.get("trains", "")))}
        rstatus = (r.get("status") or "").strip().lower()
        for u in nonop_units:
            if u["unit_name"] in used:
                continue
            un_tokens = {t.lower() for t in _simple_tokens(u["unit_name_norm"])}
            if not un_tokens or not un_tokens <= toks:
                continue
            used.add(u["unit_name"])
            label = (r.get("site_name", "")
                     + (" " + r.get("trains", "") if r.get("trains") else "")).strip()
            if r.get("_prose_source"):
                notes[u["unit_name"]] = (
                    f"GIIGNL narrative: '{label}' not operating "
                    f"({r['_prose_source']})")
            else:
                notes[u["unit_name"]] = (
                    f"GIIGNL table lists '{label}' as {rstatus or 'non-operating'}")
            break
    return notes


def _fmt_nonop_report_rows(rp):
    """Human-readable list of the NON-operating GIIGNL rows excluded from a report
    project's operating total (surfaced as `report_nonoperating` on a match).
    A row excluded by the §3.2.1 narrative pass (not by a table tag) is marked
    so the reviewer sees the prose justification + citation."""
    out = []
    for r in rp.get("nonop_rows", []):
        label = (r.get("site_name", "")
                 + (" " + r.get("trains", "") if r.get("trains") else "")).strip()
        cap = r.get("capacity_mtpa", "")
        entry = f"{label} ({r.get('status', 'non-operating')}, {cap})"
        if r.get("_prose_source"):
            entry += f" [GIIGNL narrative: {r['_prose_source']}]"
        out.append(entry)
    return out


def _load_prose_corrections(path):
    """Load agent-authored §3.2.1 narrative findings. Returns
        {"op": op_map, "nonop": nonop_map}
    where:
      op_map[(country_norm, site_norm, section)]  = [{unit, status, source}]
        — operating-status corrections: the prose says a row listed (untagged) in
          GIIGNL's operating-only TABLE isn't actually operating (Bontang: "only
          Trains G and H currently in operation" ⇒ Train F idled). report_diff
          moves the named report row out of the operating total into nonop_rows.
          `site_norm` is matched against the REPORT project key.
      nonop_map[(country_norm, gem_terminal_norm, section)] = [{unit, source}]
        — narrative corroborations of a GEM NON-operating unit that has NO GIIGNL
          table row (NWS Train 2: ceased, so absent from the operating table, but
          the prose names it). Clears that unit's "GEM has, GIIGNL doesn't" flag.
          `gem_terminal_norm` is matched against the GEM project key.
    {} maps if the file is absent/empty. Capacity NUMBERS are never touched here
    (§5.6 prefers the tabular value); nothing is auto-applied to GEM (§3.8) — this
    only makes the GIIGNL side of the diff consistent with GIIGNL's own narrative."""
    empty = {"op": {}, "nonop": {}}
    if not path or not Path(path).exists():
        return empty
    data = json.loads(Path(path).read_text())
    op = defaultdict(list)
    for c in data.get("operating_status_corrections", []):
        key = (normalize_country(c.get("country", "")),
               normalize_terminal_name(c.get("site", "")),
               c.get("section_type", ""))
        src = c.get("source", "")
        for nu in c.get("nonoperating_units", []):
            op[key].append({
                "unit": str(nu.get("unit", "")),
                "status": (nu.get("status", "") or "idled").strip().lower(),
                "source": src,
            })
    nonop = defaultdict(list)
    for c in data.get("nonop_corroborations", []):
        key = (normalize_country(c.get("country", "")),
               normalize_terminal_name(c.get("gem_terminal", c.get("site", ""))),
               c.get("section_type", ""))
        src = c.get("source", "")
        for u in c.get("units", []):
            nonop[key].append({"unit": str(u).strip().lower(), "source": src})
    return {"op": dict(op), "nonop": dict(nonop)}


def _apply_prose_corrections(report_projects, corr_map):
    """Reclassify report rows the narrative pass marks non-operating. For each
    correction, find the report row whose site_name+trains carries the named unit
    token, move it from `rows` to `nonop_rows` with the prose status + source, and
    recompute the operating total/train count. Conservative: matches one row per
    named unit (first unused token hit), no-op if the unit isn't found."""
    if not corr_map:
        return
    for key, corrections in corr_map.items():
        rp = report_projects.get(key)
        if not rp:
            continue
        used = set()
        for corr in corrections:
            unit_tok = corr["unit"].strip().lower()
            if not unit_tok:
                continue
            moved = None
            for r in rp["rows"]:
                if id(r) in used:
                    continue
                toks = {t.lower() for t in
                        (_simple_tokens(normalize_terminal_name(r.get("site_name", "")))
                         | _simple_tokens(r.get("trains", "")))}
                if unit_tok in toks:
                    moved = r
                    break
            if moved is None:
                continue
            used.add(id(moved))
            moved["status"] = corr["status"]
            moved["_prose_source"] = corr["source"]
            rp["rows"].remove(moved)
            rp["nonop_rows"].append(moved)
        # Recompute operating aggregates from the surviving rows.
        total = 0.0
        for r in rp["rows"]:
            try:
                total += float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
            except ValueError:
                pass
        rp["total_capacity_mtpa"] = total
        rp["trains_count"] = len(rp["rows"])


# Tokens to drop when matching a GIIGNL vessel name against a GEM unit name —
# GEM unit names are the bare vessel ("Energos Power"); GIIGNL/site labels may
# carry facility tags.
_FSRU_VESSEL_STOPWORDS = {"fsru", "fsu", "fru", "flng", "lng", "terminal", "vessel"}


def _report_vessels(rp):
    """Comma-joined distinct vessel names across a report project's rows
    (operating + non-operating). GIIGNL identifies FSRU/FLNG terminals by their
    deployed vessel (e.g. Damietta / "Energos Winter (FSRU)"); the vessel is kept
    out of the matching key (it would break name normalization) but preserved here
    so the diff/workbook can show it in the displayed name. Important for the FSRU
    sync rule (vessel reassignments)."""
    seen, out = set(), []
    for r in list(rp.get("rows", [])) + list(rp.get("nonop_rows", [])):
        v = (r.get("vessel_name") or "").strip()
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return ", ".join(out)


def _merge_subname_report_projects(report_projects, gem_projects, alias_map):
    """Merge GIIGNL report projects whose names are each a distinct token-subset
    of ONE GEM multi-train terminal's name into a single project, force-matched to
    that terminal.

    GIIGNL splits some complexes that GEM models as a single terminal under names
    with NO shared base token — Oman's "Oman LNG" (T1/T2 = 7.8) + "Qalhat"
    (T3 = 3.7) vs GEM "Oman Qalhat LNG Terminal" (T1/T2/T3 = 11.4). The
    expansion / unit-code / train-word folds all key off a shared base, so they
    can't group two differently-named rows; but the GEM terminal name literally
    contains both ("oman" + "qalhat"). Grouping them compares the SUM against the
    GEM total (11.5 vs 11.4) instead of matching one row and orphaning the other
    (the §5.3 "complex split differently" case, generalized).

    Conservative guards:
      - GEM terminal must be multi-unit and its normalized name must have >=2
        distinctive (>=4-char) tokens;
      - each report name must be a >=4-char token-SUBSET of that GEM name and not
        already have its own exact/alias home;
      - >=2 report projects must map to the SAME terminal; and
      - merging must IMPROVE the capacity fit (summed capacity closer to the GEM
        total than any single member) — so two genuinely separate terminals that
        merely share a token are left alone.
    """
    def toks(name):
        return {t for t in _simple_tokens(normalize_terminal_name(name)) if len(t) >= 4}

    gem_multi = []  # (gem_key, gp, name_tokens)
    for gk, gp in gem_projects.items():
        if gp.get("total_units", 0) < 2 and gp.get("operating_units", 0) < 2:
            continue
        gtoks = toks(gp.get("terminal_name", ""))
        if len(gtoks) >= 2:
            gem_multi.append((gk, gp, gtoks))
    if not gem_multi:
        return report_projects

    groups = defaultdict(list)  # gem_key -> [report_key, ...]
    for rk, rp in report_projects.items():
        if rp.get("_forced_gem_key") or rk in gem_projects or rk in alias_map:
            continue  # already routed / has its own exact/alias home
        rtoks = toks(rp.get("site_name", ""))
        if not rtoks:
            continue
        for gk, gp, gtoks in gem_multi:
            if gk[0] != rk[0] or gp.get("section_type") != rp.get("section_type"):
                continue
            if rtoks <= gtoks:
                groups[gk].append(rk)
                break

    for gk, rks in groups.items():
        if len(rks) < 2:
            continue
        gp = gem_projects[gk]
        gem_total = gp.get("total_capacity_mtpa", 0.0)
        members = [report_projects[rk] for rk in rks]
        total = round(sum(m["total_capacity_mtpa"] for m in members), 2)
        best_single = min(abs(m["total_capacity_mtpa"] - gem_total) for m in members)
        if abs(total - gem_total) >= best_single:
            continue  # merging doesn't improve the fit → leave them separate
        # Survivor = largest-capacity member (deterministic; ties broken by key).
        rks_sorted = sorted(
            rks, key=lambda rk: (-report_projects[rk]["total_capacity_mtpa"], rk))
        keep = report_projects[rks_sorted[0]]
        for rk in rks_sorted[1:]:
            mp = report_projects[rk]
            keep["total_capacity_mtpa"] = round(
                keep["total_capacity_mtpa"] + mp["total_capacity_mtpa"], 2)
            keep["trains_count"] += mp["trains_count"]
            keep["rows"].extend(mp["rows"])
            keep["nonop_rows"].extend(mp.get("nonop_rows", []))
            keep["owners_set"] |= mp["owners_set"]
            keep["site_names"] |= mp["site_names"]
            del report_projects[rk]
        keep["_forced_gem_key"] = gk
    return report_projects


def _vessel_tokens(name):
    return {t for t in _simple_tokens(name) if t not in _FSRU_VESSEL_STOPWORDS}


def _vessel_key_tokens(name):
    """Lowercased vessel-identity tokens (drops facility tags). Used to match a
    GIIGNL vessel name against a GEM FloatingVesselName robustly across case and
    operator prefixes (GIIGNL 'Excelerate Excelsior' ⊇ GEM 'Excelsior')."""
    return frozenset(t.lower() for t in _simple_tokens(name)) - _FSRU_VESSEL_STOPWORDS


def _parse_vessel_name_sets(raw):
    """Parse a GEM FloatingVesselName cell into a list of vessel token-sets.
    The cell holds one vessel, or several comma-separated (sequential-berth)."""
    sets = []
    for part in (raw or "").split(","):
        toks = _vessel_key_tokens(part)
        if toks and toks not in sets:
            sets.append(toks)
    return sets


def _fsru_operating_report_capacity(rp, gp):
    """Recompute an FSRU terminal's report-side capacity as OPERATING-only.

    GIIGNL's regas table lists every recently-deployed FSRU as a separate
    'operating' row, so a single berth that cycled through several vessels shows
    several rows. GEM models such a berth as sequential — one operating unit, the
    superseded vessels kept as `retired`/`idled` units. Summing all GIIGNL rows
    would then compare GIIGNL's lifetime-of-vessels against GEM's currently-
    operating vessel, a spurious "disagreement".

    (NB: when the GIIGNL rows actually belong to DIFFERENT GEM terminals — same
    port, distinct terminals each with its own FloatingVesselName — they are split
    upstream by `_split_multiterminal_fsru_sites` before reaching here, so this
    function only sees genuinely single-terminal berths.)

    GEM's `unit_name` is the vessel identity, so we align each GIIGNL FSRU row to a
    GEM unit by vessel name and sum only the rows that map to a GEM OPERATING unit.
    Rows mapping to a retired/idled GEM unit, or to no GEM unit, are surfaced as
    per-vessel notes (a status/discovery signal, not a capacity delta).

    Returns (report_operating_capacity, notes, applied). `applied` is False when
    this isn't a resolvable multi-vessel FSRU case (GEM not flagged FSRU, fewer
    than two vessel-bearing GIIGNL rows, or no GIIGNL vessel tied to a GEM
    operating unit) — the caller then keeps the normal project-total comparison.
    """
    if not gp.get("fsru"):
        return 0.0, [], False
    vrows = [r for r in rp["rows"] if (r.get("vessel_name") or "").strip()]
    if len(vrows) < 2:
        # 0 or 1 vessel row → nothing to disaggregate; the plain sum is correct.
        return 0.0, [], False

    gem_operating = []   # (tokens, unit_name)
    gem_nonop = []       # (tokens, unit_name, status)
    for u in gp.get("units", []):
        toks = _vessel_tokens(u.get("unit_name", ""))
        if not toks:
            continue
        if u.get("status") == "operating":
            gem_operating.append((toks, u["unit_name"]))
        else:
            gem_nonop.append((toks, u["unit_name"], u.get("status", "")))

    def _rcap(r):
        try:
            return float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
        except ValueError:
            return 0.0

    op_cap = 0.0
    op_matched = 0
    excluded_cap = 0.0
    notes = []
    for r in vrows:
        vtoks = _vessel_tokens(r.get("vessel_name", ""))
        rcap = _rcap(r)
        if any(toks == vtoks for toks, _ in gem_operating):
            op_cap += rcap
            op_matched += 1
            continue
        excluded_cap += rcap
        nonop = next((st for toks, _, st in gem_nonop if toks == vtoks), None)
        if nonop:
            notes.append(f"GIIGNL FSRU '{r.get('vessel_name')}' ({rcap:.1f}) listed operating; GEM marks it {nonop}")
        else:
            notes.append(f"GIIGNL FSRU '{r.get('vessel_name')}' ({rcap:.1f}) listed operating; not in GEM")

    if op_matched == 0:
        notes.append("FSRU vessels could not be aligned to a GEM operating unit; verify vessel identities (compared at project total)")
        return 0.0, notes, False

    # Any report rows without a vessel name aren't sequential FSRUs — keep them.
    op_cap += sum(_rcap(r) for r in rp["rows"] if not (r.get("vessel_name") or "").strip())
    if excluded_cap > 0:
        notes.insert(0, f"FSRU operating-only: compared {op_cap:.1f} MTPA from {op_matched} operating vessel(s); excluded {excluded_cap:.1f} MTPA of GIIGNL FSRU rows not operating in GEM")
    return op_cap, notes, True


def _split_multiterminal_fsru_sites(report_projects, gem_projects):
    """Split a GIIGNL FSRU site that GEM models as MULTIPLE distinct terminals.

    GIIGNL labels several physically distinct FSRU terminals at one port with the
    same site name, disambiguating only by vessel — e.g. Germany 'Wilhelmshaven'
    appears twice, once for 'Höegh Esperanza' and once for 'Excelerate Excelsior',
    which GEM tracks as two separate terminals ('Wilhelmshaven FSRU' and
    'Wilhelmshaven TES FSRU'). Grouped by site name alone, the two rows collapse
    into one summed project (9.8 MTPA, 2 "trains"), producing a bogus project total.

    This routes each GIIGNL vessel row to the GEM terminal whose FloatingVesselName
    carries that vessel, then emits one report sub-project per GEM terminal
    (force-matched via `_forced_gem_key`). Each sub-project's site name carries the
    vessel so the diff shows them separately.

    Distinguished from the SEQUENTIAL-berth case (Ain-Sokhna: ONE GEM terminal that
    cycled through several FSRUs, kept as units) by requiring the site's distinct
    vessels to resolve to >=2 DISTINCT GEM project keys. Ain-Sokhna's vessels all
    map to its single GEM terminal, so it is left grouped for
    `_fsru_operating_report_capacity` to handle.

    Conservative: only splits when EVERY row in the project is a vessel row that
    maps to a GEM terminal, and >=2 distinct GEM terminals are hit. Any partial /
    mixed case is left untouched.
    """
    # GEM FSRU terminals with at least one vessel name, indexed by (country, section).
    gem_fsru_by_cs = defaultdict(list)  # (country_norm, section) -> [(gem_key, [vessel_sets])]
    for gk, gp in gem_projects.items():
        if gp.get("fsru") and gp.get("vessel_name_sets"):
            gem_fsru_by_cs[(gk[0], gk[2])].append((gk, gp["vessel_name_sets"]))

    result = {}
    for rp_key, rp in report_projects.items():
        rows = rp["rows"]
        candidates = gem_fsru_by_cs.get((rp_key[0], rp_key[2]), [])
        # Every row must carry a vessel for this to be a clean multi-FSRU site.
        if len(rows) < 2 or not candidates \
                or not all((r.get("vessel_name") or "").strip() for r in rows):
            result[rp_key] = rp
            continue

        # Route each row to the GEM terminal whose FloatingVesselName it carries.
        row_gem_key = []
        for r in rows:
            rt = _vessel_key_tokens(r.get("vessel_name", ""))
            gk = next((gk for gk, vsets in candidates
                       if rt and any(vs <= rt for vs in vsets)), None)
            row_gem_key.append(gk)

        distinct_keys = {gk for gk in row_gem_key if gk is not None}
        if len(distinct_keys) < 2 or any(gk is None for gk in row_gem_key):
            # Single GEM terminal (sequential berth) or unresolved vessels → leave grouped.
            result[rp_key] = rp
            continue

        # Emit one sub-project per GEM terminal.
        rows_by_key = defaultdict(list)
        for r, gk in zip(rows, row_gem_key):
            rows_by_key[gk].append(r)
        for gk, sub_rows in rows_by_key.items():
            sub = _make_fsru_subproject(rp, sub_rows, gk)
            sub_key = (rp_key[0], f"{rp_key[1]} ## {gk[1]}", rp_key[2])
            result[sub_key] = sub
    return result


def _make_fsru_subproject(rp, sub_rows, forced_gem_key):
    """Build a report sub-project (same shape as a grouped report project) holding
    only `sub_rows`, force-matched to `forced_gem_key`. Display name carries the
    vessel so the reviewer sees the two terminals separately."""
    cap = 0.0
    owners = set()
    for r in sub_rows:
        try:
            cap += float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
        except ValueError:
            pass
        for ent in parse_entity_list(r.get("owner", "")):
            if ent["entity"]:
                owners.add(ent["entity"])
    vessels = []
    for r in sub_rows:
        v = (r.get("vessel_name") or "").strip()
        if v and v not in vessels:
            vessels.append(v)
    vessel = ", ".join(vessels)
    base_site = rp["site_name"]
    return {
        "country": rp["country"],
        "country_norm": rp["country_norm"],
        "site_name": f"{base_site} ({vessel})" if vessel else base_site,
        "name_norm": rp["name_norm"],
        "section_type": rp["section_type"],
        "total_capacity_mtpa": cap,
        "owners_set": owners,
        "trains_count": len(sub_rows),
        "rows": sub_rows,
        "nonop_rows": [],
        "site_names": {r.get("site_name", "") for r in sub_rows},
        "_forced_gem_key": forced_gem_key,
    }


# Key-name suffix that separates the FLOATING (FSRU) member of a same-named
# regas port from its onshore sibling. GEM tracks them as two terminals but
# `normalize_terminal_name` strips both " FSRU" and " LNG Terminal" to the same
# token, so they'd collide on one key (and one merged project) — Ravenna FSRU vs
# Ravenna LNG Terminal, Stade FSRU vs Stade LNG Terminal, etc. (~12 ports). The
# floating member's key/name gets this suffix on BOTH the GEM side and the report
# side (a vessel-bearing GIIGNL row at a collision port), so onshore↔onshore and
# FSRU↔FSRU match instead of merging. Not a trailing parenthetical, so it doesn't
# trip the same-name-by-owner family logic.
_FLOAT_VARIANT_SUFFIX = " fsru"


def _report_row_is_floating(r):
    """Whether a report (regas) row describes a floating terminal — it carries a
    vessel name, or its type is an FSRU/FSU/FRU (a bare 'offshore'/deepwater port
    is NOT floating). Used only to pick the floating variant at a collision port."""
    if (r.get("vessel_name") or "").strip():
        return True
    return (r.get("type") or "").strip().lower() in ("fsru", "fsu", "fru")


def _load_colmap(csv_path):
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(f"colmap.json not found at {map_path}. Run pull_gem_db.py first.")
    return json.loads(map_path.read_text())


def _build_gem_project_table(gem_csv):
    """Collapse the unit-level GEM CSV into project-level entries.

    Returns (projects, alias_map):
      projects = {(country_norm, terminal_name_norm, section_type): project_dict}
      alias_map = {(country_norm, alias_norm, section_type): canonical_key}

    Key includes section_type so a single GEM terminal with BOTH liquefaction
    and regasification facilities (e.g. Sabine Pass, which has 6 export trains
    and 1 import terminal under the same TerminalName) becomes TWO project
    entries — one per section_type. Otherwise their capacities would sum
    incorrectly when matched against GIIGNL's section-specific tables.

    alias_map lets the matcher find a GEM project when GIIGNL uses a name
    that lives in GEM's OtherNames column rather than TerminalName. Example:
    Kribi FLNG is in GEM under TerminalName "Cameroon FLNG Terminal" with
    "Kribi FLNG Terminal" listed under OtherNames; the alias map makes the
    GIIGNL "Kribi" row match.

    project_dict fields:
      - terminal_id, terminal_name, country, section_type
      - aliases_norm: set of normalized OtherNames (used by fuzzy match too)
      - status_set, total_capacity_mtpa, operating_units, total_units
      - owners_set, fsru
    """
    colmap = _load_colmap(gem_csv)
    ci = {k: colmap.get(k) for k in [
        "terminal_id", "terminal_name", "unit_name", "country", "facility_type",
        "status", "fuel", "owner", "capacity_mtpa", "floating", "floating_vessel_name",
        "import_export_only", "other_names", "local_names", "language",
        "proposal_year", "construction_year", "shelved_year", "cancelled_year",
        "stop_year", "actual_start_year",
    ]}
    if None in (ci["terminal_id"], ci["terminal_name"], ci["country"]):
        sys.exit("ERROR: GEM CSV missing required columns")

    def _row_section(ftype, ie_only):
        combined = (ftype + " " + ie_only).lower()
        if "export" in combined or "liquefaction" in ftype.lower():
            return "liquefaction"
        if "import" in combined or "regasification" in ftype.lower():
            return "regasification"
        return "unknown"

    def _row_is_floating(row):
        v = (row[ci["floating"]] if ci["floating"] is not None else "")
        return str(v).strip().lower() in ("true", "yes", "1")

    # Pre-scan: find regasification ports where GEM has BOTH a floating (FSRU) and
    # a non-floating (onshore) terminal under the same normalized name. They'd
    # otherwise collide on one key and silently MERGE into a single project,
    # because normalize_terminal_name strips both " FSRU" and " LNG Terminal" (e.g.
    # Ravenna FSRU + Ravenna LNG Terminal → "ravenna"; ~12 such ports). The
    # floating member is keyed under the `_FLOAT_VARIANT_SUFFIX` variant to stay
    # distinct. Restricted to regasification — a report row's floating-ness is
    # determinable there (vessel/type), but GIIGNL liquefaction rows carry no such
    # signal, so liq FLNG/onshore pairs (Cameroon, Rovuma) are left as-is.
    site_floats: dict[tuple, dict] = defaultdict(lambda: {True: set(), False: set()})
    with open(gem_csv, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            if (row[ci["fuel"]] if ci["fuel"] is not None else "LNG") != "LNG":
                continue
            cn = normalize_country(row[ci["country"]])
            tn = normalize_terminal_name(row[ci["terminal_name"]])
            ft = row[ci["facility_type"]] if ci["facility_type"] is not None else ""
            ie = row[ci["import_export_only"]] if ci["import_export_only"] is not None else ""
            if not cn or not tn or _row_section(ft, ie) != "regasification":
                continue
            site_floats[(cn, tn, "regasification")][_row_is_floating(row)].add(row[ci["terminal_id"]])
    collision_regas = {k for k, fm in site_floats.items() if fm[True] and fm[False]}

    projects = {}
    alias_map: dict[tuple, tuple] = {}
    with open(gem_csv, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            fuel = row[ci["fuel"]] if ci["fuel"] is not None else "LNG"
            if fuel != "LNG":
                continue
            country = row[ci["country"]]
            tname = row[ci["terminal_name"]]
            uname = row[ci["unit_name"]] if ci["unit_name"] is not None else ""
            ftype = row[ci["facility_type"]] if ci["facility_type"] is not None else ""
            country_norm = normalize_country(country)
            tname_norm = normalize_terminal_name(tname)
            if not country_norm or not tname_norm:
                continue

            ie_only = row[ci["import_export_only"]] if ci["import_export_only"] is not None else ""
            section_type = _row_section(ftype, ie_only)
            if section_type == "unknown":
                continue

            # At a collision port, the floating (FSRU) terminal keys under the
            # variant so it stays separate from its onshore sibling; the report
            # side mirrors this for a vessel-bearing row.
            keyed_name = tname_norm
            if (country_norm, tname_norm, section_type) in collision_regas and _row_is_floating(row):
                keyed_name = tname_norm + _FLOAT_VARIANT_SUFFIX
            key = (country_norm, keyed_name, section_type)

            status = row[ci["status"]] if ci["status"] is not None else ""
            owner = row[ci["owner"]] if ci["owner"] is not None else ""
            cap_mtpa = row[ci["capacity_mtpa"]] if ci["capacity_mtpa"] is not None else ""
            floating = row[ci["floating"]] if ci["floating"] is not None else ""
            other_names_raw = row[ci["other_names"]] if ci["other_names"] is not None else ""

            try:
                cap = float(cap_mtpa) if cap_mtpa else 0.0
            except ValueError:
                cap = 0.0

            # Parse the GEM owner cell with the same parser the report side uses.
            # GEM cells are ";"-separated with "[NN%]" brackets ("QatarEnergy
            # [70%]; Exxon Mobil Corp [30%]"); the previous comma-only split
            # collapsed a multi-owner cell to a single (often wrong) tag, which
            # manufactured false owner conflicts on nearly every multi-owner match.
            owner_tags = set()
            for ent in parse_entity_list(owner):
                if ent["entity"]:
                    owner_tags.add(ent["entity"])

            if key not in projects:
                projects[key] = {
                    "terminal_id": row[ci["terminal_id"]],
                    "terminal_name": tname,
                    "country": country,
                    "country_norm": country_norm,
                    "name_norm": keyed_name,
                    "section_type": section_type,
                    "unit_names": [],
                    "operating_unit_names": [],
                    "units": [],
                    "aliases_norm": set(),
                    "aliases_raw": set(),
                    "status_set": set(),
                    "total_capacity_mtpa": 0.0,
                    "operating_units": 0,
                    "total_units": 0,
                    "owners_set": set(),
                    "fsru": False,
                    "vessel_name_sets": [],
                }
            p = projects[key]
            p["status_set"].add(status)
            # Terminal-level FSRU vessel name(s). One single-berth terminal carries
            # one vessel ("Höegh Esperanza"); a sequential-berth terminal lists all
            # deployed vessels comma-separated ("Energos Power FSRU, BW Singapore
            # FSRU, ..."). Captured as token-sets so the multi-terminal FSRU site
            # split (_split_multiterminal_fsru_sites) can route a GIIGNL vessel row
            # to the GEM terminal that actually carries that vessel.
            if ci["floating_vessel_name"] is not None:
                for vs in _parse_vessel_name_sets(row[ci["floating_vessel_name"]]):
                    if vs not in p["vessel_name_sets"]:
                        p["vessel_name_sets"].append(vs)
            if uname and uname != "--" and uname not in p["unit_names"]:
                p["unit_names"].append(uname)
            if status == "operating" and uname and uname != "--" \
                    and uname not in p["operating_unit_names"]:
                p["operating_unit_names"].append(uname)
            p["total_units"] += 1
            if status == "operating":
                p["operating_units"] += 1
                p["total_capacity_mtpa"] += cap
            p["owners_set"].update(owner_tags)
            if floating and floating.lower() in ("true", "yes", "1"):
                p["fsru"] = True

            # Per-unit detail (used by the unit-level alignment pass in _classify
            # and by the non-operating sheet). unit_name_norm is a plain lowercased
            # token form — NOT normalize_terminal_name (which strips suffixes that
            # are meaningful in unit names like "GL1Z").
            uname_norm = (uname or "").lower().strip()
            if uname_norm == "--":
                uname_norm = ""
            p["units"].append({
                "unit_name": uname if (uname and uname != "--") else "",
                "unit_name_norm": uname_norm,
                "status": status,
                "capacity_mtpa": cap,
                "start_year": _unit_anchor_year(row, ci, status),
                "owners_set": owner_tags,
            })

            local_names_raw = row[ci["local_names"]] if ci["local_names"] is not None else ""
            languages_raw = row[ci["language"]] if ci["language"] is not None else ""

            def _register_alias(alias_raw_input: str) -> None:
                """Normalize + register an alias on this project."""
                if not alias_raw_input or not alias_raw_input.strip():
                    return
                alias_norm = normalize_terminal_name(alias_raw_input)
                if not alias_norm or alias_norm == tname_norm:
                    return
                if alias_norm in p["aliases_norm"]:
                    return
                p["aliases_norm"].add(alias_norm)
                p["aliases_raw"].add(alias_raw_input.strip())
                alias_key = (country_norm, alias_norm, section_type)
                # Don't let an alias overwrite a canonical entry: if alias_key
                # is already a canonical key, leave alias_map alone (canonical wins).
                if alias_key not in projects and alias_key not in alias_map:
                    alias_map[alias_key] = key

            # OtherNames: simple comma-split, register each as alias.
            for alias_raw in (other_names_raw or "").split(","):
                _register_alias(alias_raw)

            # LocalNames: comma-split paired with Language column (1:1). Each
            # local name gets registered raw AND with English transliterations
            # (e.g. "中石油唐山曹妃甸LNG接收站" → also adds the pinyin form so
            # GIIGNL's "Caofeidian (Tangshan)" can match via shared tokens).
            # See normalize.transliterate_to_english for supported scripts.
            local_list = [n.strip() for n in (local_names_raw or "").split(",") if n.strip()]
            lang_list = [l.strip() for l in (languages_raw or "").split(",") if l.strip()]
            for i, local_name in enumerate(local_list):
                language = lang_list[i] if i < len(lang_list) else ""
                for variant in transliterate_to_english(local_name, language):
                    _register_alias(variant)

    # Parenthetical-owner disambiguation. GEM distinguishes multiple terminals
    # that share a base name by appending the first owner in parentheses —
    # "Tianjin LNG Terminal (PipeChina)" / "(Sinopec)" / "(Beijing Gas Group)"
    # (common for Chinese terminals; may occur elsewhere). When ≥2 terminals in
    # the same country+section share a base name (paren stripped) with distinct
    # parentheticals, treat each parenthetical as an OWNER tag rather than a name
    # token: (a) add it to owners_set so a GIIGNL row's first owner can pick the
    # right sibling, and (b) build the fuzzy name-match tokens from the base name
    # only — otherwise the owner word ("sinopec") matches as a name token and
    # drags in other same-owner terminals (Liuheng/Longkou (Sinopec)).
    families = defaultdict(list)
    for k, p in projects.items():
        base, paren = _split_trailing_paren(p["name_norm"])
        p["_base_norm"] = base
        p["_paren_text"] = paren
        families[(k[0], base, k[2])].append(k)
    for fam_key, members in families.items():
        distinct_parens = {projects[m]["_paren_text"] for m in members if projects[m]["_paren_text"]}
        is_family = len(members) >= 2 and len(distinct_parens) >= 2
        for m in members:
            p = projects[m]
            if is_family and p["_paren_text"]:
                po = normalize_entity(p["_paren_text"])
                p["paren_owner"] = po
                if po:
                    p["owners_set"].add(po)
                name_for_tokens = p["_base_norm"]
            else:
                p["paren_owner"] = ""
                name_for_tokens = p["name_norm"]
            toks = _tokens_4plus(name_for_tokens)
            for a in p["aliases_norm"]:
                toks |= _tokens_4plus(a)
            p["match_tokens"] = toks

    return projects, alias_map, collision_regas


def _classify(report_rows, gem_projects, alias_map=None, collision_regas=None,
              prose_corrections=None):
    """Apply matching with canonical + alias + fuzzy passes, then classify.

    Returns dict with: matches, fuzzy_matches, report_only, gem_only_operating,
                       ambiguous, stats
    """
    alias_map = alias_map or {}
    collision_regas = collision_regas or set()
    prose_corrections = prose_corrections or {}
    prose_op = prose_corrections.get("op", {})
    prose_nonop = prose_corrections.get("nonop", {})

    def _row_keyparts(r):
        """(country_norm, full_name_norm, section_type) for a report row, or None
        if the row is a subtotal or missing a required field.

        At a collision port (GEM has both an FSRU and an onshore terminal of this
        name), a floating row's name gets the `_FLOAT_VARIANT_SUFFIX` so it keys to
        the FSRU GEM project and an onshore row keys to the onshore one — instead of
        both collapsing onto one project (which had wrongly merged GIIGNL's onshore
        Ravenna + Ravenna FSRU into a single 4.4 MTPA entry)."""
        if (r.get("notes") or "").lower().startswith("country subtotal"):
            return None
        country_norm = normalize_country(r.get("country", ""))
        name_norm = normalize_terminal_name(r.get("site_name", ""))
        section_type = r.get("section_type", "")
        if not country_norm or not name_norm or not section_type:
            return None
        if (country_norm, name_norm, section_type) in collision_regas \
                and _report_row_is_floating(r):
            name_norm = name_norm + _FLOAT_VARIANT_SUFFIX
        return country_norm, name_norm, section_type

    # First scan: the set of (country, full-name, section) keys present in the
    # report. Used below to decide whether an "<X> Expansion" row has a base
    # "<X>" partner to fold into.
    rep_name_keys = set()
    for r in report_rows:
        kp = _row_keyparts(r)
        if kp:
            rep_name_keys.add(kp)

    # Second scan: count how many report rows share each unit-code-stripped base
    # (country, base_norm, section). ≥2 distinct rows sharing a base (e.g. Algeria
    # 'Arzew GL1Z'/'GL2Z'/'GL3Z' → 'arzew') is itself evidence the base is a real
    # multi-complex site, so the unit-code fold can fire even when GEM names the
    # project differently ('Arzew-Bethioua LNG Terminal').
    unit_code_base_counts = defaultdict(int)
    train_word_base_counts = defaultdict(int)
    for r in report_rows:
        kp = _row_keyparts(r)
        if not kp:
            continue
        country_norm, _full, section_type = kp
        base_raw = _strip_unit_code_suffix(r.get("site_name", ""))
        if base_raw:
            base_norm = normalize_terminal_name(base_raw)
            if base_norm:
                unit_code_base_counts[(country_norm, base_norm, section_type)] += 1
        tw_raw = _strip_train_word_suffix(r.get("site_name", ""))
        if tw_raw:
            tw_norm = normalize_terminal_name(tw_raw)
            if tw_norm:
                train_word_base_counts[(country_norm, tw_norm, section_type)] += 1

    def _grouping_name(country_norm, raw_site, section_type, full_norm):
        """Resolve the grouping name for a report row, returning
        (group_name_norm, folded, base_display_raw).

        Two conservative folds, each firing only when the stripped base resolves:

        1. Expansion/extension fold. GIIGNL splits a phased terminal across
           '<Site>' + '<Site> Expansion' rows (e.g. Taiwan 'Taichung' 6.1 +
           'Taichung Expansion' 1.9 = one 8.0 MTPA CPC terminal). Fold when the
           base resolves to another report row, a GEM canonical key, or alias.

        2. Unit-code fold. GIIGNL splits a multi-complex site across per-complex
           rows carrying a code suffix ('Arzew GL1Z'/'GL2Z'/'GL3Z'). Fold when the
           base resolves to a GEM key/alias OR ≥2 report rows share the base.

        3. Train-word fold. GIIGNL splits a complex into explicit per-train rows
           ('Bontang Train E'/'F'/'G'/'H'). Fold when the base resolves the same
           way as the unit-code fold. The literal word 'Train' is what makes the
           single-letter code safe to strip here (unit-code fold can't, lest it
           eat 'Senboku II').

        All three avoid merging extraction artifacts and genuinely distinct named
        stages that lack a suffix/code/train-word ('Senboku II', 'Corpus Christi
        Stage III')."""
        base_raw = _strip_expansion_suffix(raw_site)
        if base_raw:
            base_norm = normalize_terminal_name(base_raw)
            if base_norm:
                base_key = (country_norm, base_norm, section_type)
                if base_key in rep_name_keys or base_key in gem_projects or base_key in alias_map:
                    return base_norm, True, base_raw

        code_base_raw = _strip_unit_code_suffix(raw_site)
        if code_base_raw:
            cb_norm = normalize_terminal_name(code_base_raw)
            if cb_norm and cb_norm != full_norm:
                cb_key = (country_norm, cb_norm, section_type)
                if (cb_key in gem_projects or cb_key in alias_map
                        or cb_key in rep_name_keys
                        or unit_code_base_counts.get(cb_key, 0) >= 2):
                    return cb_norm, True, code_base_raw

        tw_base_raw = _strip_train_word_suffix(raw_site)
        if tw_base_raw:
            tw_norm = normalize_terminal_name(tw_base_raw)
            if tw_norm and tw_norm != full_norm:
                tw_key = (country_norm, tw_norm, section_type)
                if (tw_key in gem_projects or tw_key in alias_map
                        or tw_key in rep_name_keys
                        or train_word_base_counts.get(tw_key, 0) >= 2):
                    return tw_norm, True, tw_base_raw

        return full_norm, False, None

    # Group report rows by (country, name, section_type) — collapse subtotal rows.
    # section_type is part of the key so a site with both liquefaction and
    # regasification rows in GIIGNL maps to two separate report-side projects,
    # mirroring the GEM-side keying.
    report_projects = {}
    for r in report_rows:
        kp = _row_keyparts(r)
        if kp is None:
            continue
        country_norm, full_norm, section_type = kp
        name_norm, folded, base_display = _grouping_name(
            country_norm, r.get("site_name", ""), section_type, full_norm)
        key = (country_norm, name_norm, section_type)

        try:
            cap = float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
        except ValueError:
            cap = 0.0

        owner_tags = set()
        for ent in parse_entity_list(r.get("owner", "")):
            if ent["entity"]:
                owner_tags.add(ent["entity"])

        if key not in report_projects:
            report_projects[key] = {
                "country": r.get("country", ""),
                "country_norm": country_norm,
                "site_name": r.get("site_name", ""),
                "name_norm": name_norm,
                "section_type": section_type,
                "total_capacity_mtpa": 0.0,
                "owners_set": set(),
                "trains_count": 0,
                "rows": [],
                "nonop_rows": [],
                "site_names": set(),
            }
        rp = report_projects[key]
        # Prefer the base name as the display name (so a folded group shows
        # "Taichung" / "Arzew", not "Taichung Expansion" / "Arzew GL1Z").
        if folded and base_display:
            rp["site_name"] = base_display
        elif full_norm == name_norm and not rp.get("_display_locked"):
            rp["site_name"] = r.get("site_name", "")
        if folded and base_display:
            rp["_display_locked"] = True
        rp["site_names"].add(r.get("site_name", ""))
        rp["owners_set"].update(owner_tags)
        # A GIIGNL row annotated non-operating ("(Mothballed)"/"(stopped)") is
        # excluded from the OPERATING total and capacity comparison — GIIGNL's
        # tables are operating-only, so such a row is a status note, not operating
        # capacity (e.g. Bontang Train E mothballed; Balhaf T1/T2 stopped). It is
        # kept in `nonop_rows` to surface on the match and to corroborate the GEM
        # non-op unit it lines up with (see _corroborate_nonop).
        if (r.get("status") or "").strip().lower() in _NONOP_STATUSES:
            rp["nonop_rows"].append(r)
        else:
            rp["total_capacity_mtpa"] += cap
            rp["trains_count"] += 1
            rp["rows"].append(r)

    # Split GIIGNL FSRU sites that GEM models as multiple distinct terminals
    # (e.g. Wilhelmshaven → 'Wilhelmshaven FSRU' + 'Wilhelmshaven TES FSRU'),
    # routing each vessel row to its GEM terminal. See the function docstring.
    report_projects = _split_multiterminal_fsru_sites(report_projects, gem_projects)

    # Merge GIIGNL rows that GEM models as ONE multi-train terminal under a name
    # with no shared base token (Oman "Oman LNG" + "Qalhat" → GEM "Oman Qalhat
    # LNG Terminal"); compare the summed capacity vs the GEM total instead of
    # matching one row and orphaning the other. See _merge_subname_report_projects.
    report_projects = _merge_subname_report_projects(report_projects, gem_projects, alias_map)

    # Apply §3.2.1 narrative-prose corrections to operating status: GIIGNL's prose
    # can mark a train listed in its operating-only TABLE as not actually operating
    # (Bontang: "only Trains G and H currently in operation" → Train F is idled,
    # though the table lists it untagged). Move such rows out of the operating total.
    _apply_prose_corrections(report_projects, prose_op)

    # Pass 1: exact match — first try canonical TerminalName, then OtherNames alias.
    matches = []
    matched_gp_keys: list[tuple] = []  # every GEM project key that got matched
    aligned_unit_names_by_gp: dict[tuple, set] = defaultdict(set)
    # Report projects matched to each GEM key — used after matching to corroborate
    # GEM non-op units against the GIIGNL non-op rows that mapped to that terminal.
    matched_rps_by_gp: dict[tuple, list] = defaultdict(list)
    matched_report_keys: set[tuple] = set()
    matched_gem_keys: set[tuple] = set()
    # Map each report key to the GEM canonical key it matched (if any) and
    # which side of the GEM record matched it.
    canonical_via_alias: dict[tuple, tuple] = {}  # report_key -> (canonical_key, alias_norm)
    # Report sub-projects force-matched to a specific GEM terminal by the
    # multi-terminal FSRU split (report_key -> gem_key).
    forced_gem: dict[tuple, tuple] = {
        rk: rp["_forced_gem_key"] for rk, rp in report_projects.items()
        if rp.get("_forced_gem_key") and rp["_forced_gem_key"] in gem_projects
    }

    for rp_key in list(report_projects.keys()):
        if rp_key in forced_gem:
            matched_report_keys.add(rp_key)
            matched_gem_keys.add(forced_gem[rp_key])
        elif rp_key in gem_projects:
            matched_report_keys.add(rp_key)
            matched_gem_keys.add(rp_key)
        elif rp_key in alias_map:
            canonical_key = alias_map[rp_key]
            matched_report_keys.add(rp_key)
            matched_gem_keys.add(canonical_key)
            canonical_via_alias[rp_key] = (canonical_key, rp_key[1])

    giignl_only_keys = set(report_projects.keys()) - matched_report_keys
    gem_only_keys = set(gem_projects.keys()) - matched_gem_keys

    for rp_key in sorted(matched_report_keys):
        rp = report_projects[rp_key]
        if rp_key in forced_gem:
            gp_key = forced_gem[rp_key]
            gp = gem_projects[gp_key]
            matched_alias_norm = ""
            via_alias = False
        elif rp_key in canonical_via_alias:
            gp_key, matched_alias_norm = canonical_via_alias[rp_key]
            gp = gem_projects[gp_key]
            via_alias = True
        else:
            gp_key = rp_key
            gp = gem_projects[gp_key]
            matched_alias_norm = ""
            via_alias = False
        key = rp_key  # variable name kept for code below that uses `key`

        # Compare capacity. For FSRU terminals, compare OPERATING-vessel capacity
        # only (GIIGNL lists every deployed FSRU as an operating row; GEM keeps
        # superseded vessels as retired units — see _fsru_operating_report_capacity).
        report_cap = rp["total_capacity_mtpa"]
        fsru_op_cap, fsru_notes, fsru_applied = _fsru_operating_report_capacity(rp, gp)
        if fsru_applied:
            report_cap = fsru_op_cap
        cap_delta = report_cap - gp["total_capacity_mtpa"]
        cap_pct = abs(cap_delta) / gp["total_capacity_mtpa"] * 100 if gp["total_capacity_mtpa"] else None

        # Compare owners
        owner_overlap = rp["owners_set"] & gp["owners_set"]
        owner_only_report = rp["owners_set"] - gp["owners_set"]
        owner_only_gem = gp["owners_set"] - rp["owners_set"]

        # Confidence on the match — "high" for canonical name hit, "high"
        # also for alias hit (still deterministic, just via OtherNames).
        confidence = "high"
        disagreements = []
        # Any non-zero capacity difference is a conflict (compared at the
        # 2-decimal precision the diff reports). GIIGNL is one source in a
        # conflict, not authoritative — every disagreement routes to Update.
        if round(cap_delta, 2) != 0:
            pct_str = f"{cap_pct:.1f}%" if cap_pct is not None else "n/a"
            disagreements.append(f"capacity differs by {pct_str} (report={report_cap:.2f}, gem={gp['total_capacity_mtpa']:.2f})")
        if owner_only_report:
            disagreements.append(f"owners in report not in GEM: {sorted(owner_only_report)}")
        if owner_only_gem:
            disagreements.append(f"owners in GEM not in report: {sorted(owner_only_gem)}")
        disagreements.extend(fsru_notes)

        unit_matches, aligned_names = _align_units(rp, gp)
        matched_gp_keys.append(gp_key)
        aligned_unit_names_by_gp[gp_key] |= aligned_names
        matched_rps_by_gp[gp_key].append(rp)

        matches.append({
            "match_type": "exact_via_alias" if via_alias else "exact",
            "confidence": confidence,
            "match_granularity": "unit" if unit_matches else "project",
            "country": rp["country"],
            "site_name": rp["site_name"],
            "report_vessel": _report_vessels(rp),
            "gem_terminal_id": gp["terminal_id"],
            "gem_terminal_name": gp["terminal_name"],
            "gem_unit_name": gp["operating_unit_names"],
            "matched_alias": matched_alias_norm if via_alias else "",
            "section_type_report": rp["section_type"],
            "section_type_gem": gp["section_type"],
            "report_capacity_mtpa": round(report_cap, 2),
            "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
            "capacity_delta_mtpa": round(cap_delta, 2),
            "capacity_delta_pct": round(cap_pct, 1) if cap_pct is not None else None,
            "owners_overlap": sorted(owner_overlap),
            "owners_report_only": sorted(owner_only_report),
            "owners_gem_only": sorted(owner_only_gem),
            "report_train_count": rp["trains_count"],
            "report_sites_merged": sorted(rp["site_names"]) if len(rp["site_names"]) > 1 else [],
            "gem_operating_units": gp["operating_units"],
            "gem_total_units": gp["total_units"],
            "unit_matches": unit_matches,
            "report_nonoperating": _fmt_nonop_report_rows(rp),
            "disagreements": disagreements,
        })

    # Pass 1.5: sub-terminal designator → GEM unit match.
    #
    # GIIGNL splits a complex into sub-terminals (Qatar "QatarEnergy LNG S(1)" /
    # "S(2)" / "S(3)"), each its own report project; GEM splits the SAME complex
    # into a terminal-with-units ("QatarEnergy LNG (S)" → units "S(1) T1-2",
    # "S(2) T3-5", "S(3) T6-7"). So several report projects map to ONE GEM terminal,
    # each to a DIFFERENT unit — a shape neither the project-level matcher (it would
    # compare each sub-terminal's capacity against the whole terminal's, e.g. the
    # bogus S(2)=14.1 vs (S)=36.3 "61% conflict") nor _align_units (GEM unit tokens
    # {s(2,t3,5} ⊄ report site {qatarenergy,lng,s(2}) handles. The designator code
    # (S(2)→"s2") bridges them: a report project carrying a designator that
    # identifies exactly one GEM unit (within a single GEM terminal in the same
    # country+section) is matched to that UNIT, comparing capacities at unit level.
    #
    # Build a GEM designator index: (country, section) -> code -> [(gem_key, unit)].
    gem_desig_index = defaultdict(lambda: defaultdict(list))
    for gk, gp in gem_projects.items():
        for u in gp["units"]:
            for code in _unit_designators(u["unit_name"]):
                gem_desig_index[(gk[0], gk[2])][code].append((gk, u))

    for rp_key in sorted(giignl_only_keys):
        rp = report_projects[rp_key]
        codes = _unit_designators(rp["name_norm"])
        if not codes:
            continue
        idx = gem_desig_index.get((rp_key[0], rp_key[2]), {})
        cand = [(gk, u) for code in codes for gk, u in idx.get(code, [])]
        gks = {gk for gk, _ in cand}
        if len(gks) != 1:
            continue  # designator unknown, or spans 2 GEM terminals → leave to fuzzy
        gk = next(iter(gks))
        gp = gem_projects[gk]
        # One distinct GEM unit only — be conservative (a report sub-terminal maps
        # to a single GEM unit; bail to fuzzy if the codes hit several units).
        uniq_units, seen_u = [], set()
        for _gk, u in cand:
            if u["unit_name"] and u["unit_name"] not in seen_u:
                seen_u.add(u["unit_name"])
                uniq_units.append(u)
        if len(uniq_units) != 1:
            continue
        unit = uniq_units[0]
        # Corroboration (mirrors fuzzy): a 4+ char name token shared with the GEM
        # terminal, OR an owner overlap. Guards against a coincidental designator.
        name_ok = bool(_tokens_4plus(rp["name_norm"]) & gp.get("match_tokens", set()))
        owner_ok = bool(rp["owners_set"] & gp["owners_set"])
        if not (name_ok or owner_ok):
            continue

        report_cap = rp["total_capacity_mtpa"]
        unit_cap = unit["capacity_mtpa"]
        cap_delta = report_cap - unit_cap
        cap_pct = abs(cap_delta) / unit_cap * 100 if unit_cap else None
        unit_owners = unit.get("owners_set", set())
        owner_only_report = rp["owners_set"] - unit_owners
        owner_only_gem = unit_owners - rp["owners_set"]
        disagreements = []
        if round(cap_delta, 2) != 0:
            pct_str = f"{cap_pct:.1f}%" if cap_pct is not None else "n/a"
            disagreements.append(
                f"capacity differs by {pct_str} (report={report_cap:.2f}, gem_unit={unit_cap:.2f})")
        if owner_only_report:
            disagreements.append(f"owners in report not in GEM: {sorted(owner_only_report)}")
        if owner_only_gem:
            disagreements.append(f"owners in GEM not in report: {sorted(owner_only_gem)}")

        unit_match = {
            "report_site": rp["site_name"],
            "report_capacity_mtpa": round(report_cap, 2),
            "gem_unit_name": unit["unit_name"],
            "gem_unit_status": unit["status"],
            "gem_unit_capacity_mtpa": round(unit_cap, 2),
            "capacity_delta_pct": round(cap_pct, 1) if cap_pct is not None else None,
            "agree": bool(round(cap_delta, 2) == 0),
        }
        matches.append({
            "match_type": "unit_designator",
            "confidence": "high",
            "match_granularity": "unit",
            "country": rp["country"],
            "site_name": rp["site_name"],
            "report_vessel": _report_vessels(rp),
            "gem_terminal_id": gp["terminal_id"],
            "gem_terminal_name": gp["terminal_name"],
            "gem_unit_name": [unit["unit_name"]],
            "matched_alias": "",
            "section_type_report": rp["section_type"],
            "section_type_gem": gp["section_type"],
            "report_capacity_mtpa": round(report_cap, 2),
            "gem_capacity_mtpa": round(unit_cap, 2),
            "capacity_delta_mtpa": round(cap_delta, 2),
            "capacity_delta_pct": round(cap_pct, 1) if cap_pct is not None else None,
            "owners_overlap": sorted(rp["owners_set"] & unit_owners),
            "owners_report_only": sorted(owner_only_report),
            "owners_gem_only": sorted(owner_only_gem),
            "report_train_count": rp["trains_count"],
            "report_sites_merged": sorted(rp["site_names"]) if len(rp["site_names"]) > 1 else [],
            "gem_operating_units": gp["operating_units"],
            "gem_total_units": gp["total_units"],
            "unit_matches": [unit_match],
            "match_criteria": {"designator": sorted(codes), "matched_unit": unit["unit_name"]},
            "report_nonoperating": _fmt_nonop_report_rows(rp),
            "disagreements": disagreements,
        })
        matched_gem_keys.add(gk)
        matched_gp_keys.append(gk)
        aligned_unit_names_by_gp[gk].add(unit["unit_name"])
        matched_rps_by_gp[gk].append(rp)
        giignl_only_keys.discard(rp_key)
        gem_only_keys.discard(gk)

    # Pass 2: fuzzy on remaining report-only rows
    ambiguous = []
    fuzzy_matches = []
    still_only = []
    # Sort for determinism: this loop discards from gem_only_keys as it assigns
    # fuzzy matches, so when several report rows contend for the same GEM
    # candidate (e.g. Qatar's QatarEnergy LNG train rows vs the (N)/(S) GEM
    # records) the outcome depends on iteration order. Iterating a set is not
    # stable run-to-run, which made the diff non-reproducible.
    for key in sorted(giignl_only_keys):
        rp = report_projects[key]
        country_norm = key[0]
        name_norm = key[1]
        section_type = key[2]
        # Candidates in same country AND same section_type (a GIIGNL
        # liquefaction row shouldn't fuzzy-match a GEM regasification entry).
        candidates = [
            (gk, gp) for gk, gp in gem_projects.items()
            if gk[0] == country_norm and gk[2] == section_type and gk in gem_only_keys
        ]
        # Fuzzy criteria (any of):
        #   (a) substring match — name is contained in the other (strong signal)
        #   (b) any 4+ char token shared AND owner overlap — distinct word + confirmation
        #   (c) 2+ distinctive 4+ char tokens shared — owner-free strong signal
        # Compare across BOTH canonical TerminalName AND all OtherNames + LocalNames
        # aliases (the latter includes transliterations of CJK names per normalize.py).
        # (c) catches cases where the GIIGNL owner cell is truncated or mis-parsed
        # (e.g. Caofeidian/Tangshan PetroChina where the owner line wraps onto the
        # previous row's partition); 2 distinctive shared tokens make a strong
        # enough match to surface as a candidate (even if just for ambiguous).
        fuzzy_hits = []
        # Strip a trailing owner/tag parenthetical from the report name before
        # tokenizing (mirrors the GEM-side family handling) so the owner word
        # ("sinopec") isn't treated as a name token. Substring still uses the FULL
        # names — a short base like "tianjin" would substring-match every sibling.
        rp_base, rp_paren = _split_trailing_paren(name_norm)
        rp_tokens = _tokens_4plus(rp_base)
        rp_owners = set(rp["owners_set"])
        if rp_paren:
            rp_owners.add(normalize_entity(rp_paren))
        rp_first_owner = ""
        if rp["rows"]:
            ents = parse_entity_list(rp["rows"][0].get("owner", ""))
            if ents and ents[0].get("entity"):
                rp_first_owner = ents[0]["entity"]
        for gk, gp in candidates:
            all_names = {gk[1]} | gp.get("aliases_norm", set())
            substring = any((name_norm in n) or (n in name_norm) for n in all_names)
            gp_tokens = gp.get("match_tokens")
            if gp_tokens is None:
                gp_tokens = set()
                for n in all_names:
                    gp_tokens |= _tokens_4plus(n)
            shared_tokens = rp_tokens & gp_tokens
            token_overlap = bool(shared_tokens)
            owner_overlap = bool(rp_owners & gp["owners_set"])
            if substring or (token_overlap and owner_overlap) or len(shared_tokens) >= 2:
                fuzzy_hits.append((gk, gp, {
                    "substring": substring,
                    "token_overlap": token_overlap,
                    "owner_overlap": owner_overlap,
                    "shared_token_count": len(shared_tokens),
                    "shared_tokens": sorted(shared_tokens),
                    "matched_against_names": sorted(all_names),
                }))

        # Same-base-name family disambiguation: if several candidates remain,
        # prefer the one whose GEM parenthetical owner equals the GIIGNL row's
        # first owner (Tianjin (PipeChina) vs (Sinopec) vs (Beijing Gas Group)).
        if len(fuzzy_hits) > 1 and rp_first_owner:
            owner_hits = [h for h in fuzzy_hits if h[1].get("paren_owner") == rp_first_owner]
            if len(owner_hits) == 1:
                fuzzy_hits = owner_hits

        if len(fuzzy_hits) == 1:
            gk, gp, criteria = fuzzy_hits[0]
            unit_matches, aligned_names = _align_units(rp, gp)
            matched_gp_keys.append(gk)
            aligned_unit_names_by_gp[gk] |= aligned_names
            matched_rps_by_gp[gk].append(rp)
            # FSRU operating-only capacity (see Pass 1 / _fsru_operating_report_capacity).
            report_cap = rp["total_capacity_mtpa"]
            fsru_op_cap, fsru_notes, fsru_applied = _fsru_operating_report_capacity(rp, gp)
            if fsru_applied:
                report_cap = fsru_op_cap
            cap_delta = report_cap - gp["total_capacity_mtpa"]
            cap_pct = abs(cap_delta) / gp["total_capacity_mtpa"] * 100 if gp["total_capacity_mtpa"] else None
            owner_only_report = rp["owners_set"] - gp["owners_set"]
            owner_only_gem = gp["owners_set"] - rp["owners_set"]
            disagreements = []
            # Any non-zero capacity difference is a conflict (see Pass 1).
            if round(cap_delta, 2) != 0:
                pct_str = f"{cap_pct:.1f}%" if cap_pct is not None else "n/a"
                disagreements.append(f"capacity differs by {pct_str} (report={report_cap:.2f}, gem={gp['total_capacity_mtpa']:.2f})")
            if owner_only_report:
                disagreements.append(f"owners in report not in GEM: {sorted(owner_only_report)}")
            if owner_only_gem:
                disagreements.append(f"owners in GEM not in report: {sorted(owner_only_gem)}")
            disagreements.extend(fsru_notes)
            fuzzy_matches.append({
                "match_type": "fuzzy",
                "confidence": "medium",
                "match_granularity": "unit" if unit_matches else "project",
                "country": rp["country"],
                "site_name": rp["site_name"],
                "report_vessel": _report_vessels(rp),
                "gem_terminal_id": gp["terminal_id"],
                "gem_terminal_name": gp["terminal_name"],
                "gem_unit_name": gp["operating_unit_names"],
                "matched_alias": "",
                "section_type_report": rp["section_type"],
                "section_type_gem": gp["section_type"],
                "report_capacity_mtpa": round(report_cap, 2),
                "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
                "capacity_delta_mtpa": round(cap_delta, 2),
                "capacity_delta_pct": round(cap_pct, 1) if cap_pct is not None else None,
                "owners_overlap": sorted(rp["owners_set"] & gp["owners_set"]),
                "owners_report_only": sorted(owner_only_report),
                "owners_gem_only": sorted(owner_only_gem),
                "report_train_count": rp["trains_count"],
                "report_sites_merged": sorted(rp["site_names"]) if len(rp["site_names"]) > 1 else [],
                "gem_operating_units": gp["operating_units"],
                "gem_total_units": gp["total_units"],
                "unit_matches": unit_matches,
                "match_criteria": criteria,
                "report_nonoperating": _fmt_nonop_report_rows(rp),
                "disagreements": disagreements,
                "needs_review": True,
            })
            gem_only_keys.discard(gk)
        elif len(fuzzy_hits) > 1:
            ambiguous.append({
                "country": rp["country"],
                "site_name": rp["site_name"],
                "report_capacity_mtpa": round(rp["total_capacity_mtpa"], 2),
                "candidate_count": len(fuzzy_hits),
                "candidates": [
                    {
                        "gem_terminal_id": gp["terminal_id"],
                        "gem_terminal_name": gp["terminal_name"],
                        "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
                        "criteria": criteria,
                    }
                    for gk, gp, criteria in fuzzy_hits
                ],
            })
        else:
            still_only.append({
                "type": "report_only",
                "country": rp["country"],
                "site_name": rp["site_name"],
                "report_vessel": _report_vessels(rp),
                "section_type": rp["section_type"],
                "report_capacity_mtpa": round(rp["total_capacity_mtpa"], 2),
                "owners_in_report": sorted(rp["owners_set"]),
                "trains_count": rp["trains_count"],
                "report_sites_merged": sorted(rp["site_names"]) if len(rp["site_names"]) > 1 else [],
                "report_nonoperating": _fmt_nonop_report_rows(rp),
            })

    gem_only = []
    for key in sorted(gem_only_keys):
        gp = gem_projects[key]
        # Only flag if operating — if shelved/cancelled/proposed, "GEM-only" is
        # expected (GEM tracks pre-operating, GIIGNL doesn't)
        if "operating" not in gp["status_set"]:
            continue
        gem_only.append({
            "type": "gem_only",
            "country": gp["country"],
            "terminal_id": gp["terminal_id"],
            "terminal_name": gp["terminal_name"],
            "section_type": gp["section_type"],
            "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
            "status_set": sorted(gp["status_set"]),
            "operating_units": gp["operating_units"],
            "total_units": gp["total_units"],
            "fsru": gp["fsru"],
            "owners": sorted(gp["owners_set"]),
            "note": "GEM has this as operating but the report doesn't list it; investigate whether "
                    "report missed it (small/non-member/sanctioned) OR GEM has it wrong",
        })

    # Non-operating units of MATCHED projects. GIIGNL's tables are operating-only,
    # so each defaults to is_gem_only=True ("GEM has, GIIGNL doesn't") UNLESS the
    # unit was aligned to a report row, OR the §3.2.1 narrative-prose pass annotates
    # giignl_narrative_mention downstream (a confirmed forward phase, no conflict —
    # Reconciliation SOP §5.7). Scoped to matched projects only (gem-only projects
    # live wholly in giignl_to_action).
    nonoperating_units = []
    for gk in sorted(set(matched_gp_keys)):
        gp = gem_projects[gk]
        aligned = aligned_unit_names_by_gp.get(gk, set())
        # Corroborate GEM non-op units against any GIIGNL non-op rows ("(Mothballed)"
        # / "(stopped)") that mapped to this terminal — those units are NOT
        # "GEM has, GIIGNL doesn't"; GIIGNL lists them too, just as not-operating.
        nonop_report_rows = [
            r for sub in matched_rps_by_gp.get(gk, []) for r in sub.get("nonop_rows", [])]
        corro = _corroborate_nonop(nonop_report_rows, gp) if nonop_report_rows else {}
        # Merge in §3.2.1 narrative corroborations of GEM non-op units that have NO
        # GIIGNL table row (NWS Train 2: ceased → absent from the operating table,
        # but the prose names it). Keyed by GEM unit name (case-insensitive).
        for pc in prose_nonop.get(gk, []):
            for u in gp["units"]:
                if u["unit_name"].strip().lower() == pc["unit"] and not corro.get(u["unit_name"]):
                    corro[u["unit_name"]] = f"GIIGNL narrative: {pc['source']}"
        for u in gp["units"]:
            if u["status"] not in _NONOP_STATUSES:
                continue
            mention = corro.get(u["unit_name"], "")
            nonoperating_units.append({
                "country": gp["country"],
                "gem_terminal_id": gp["terminal_id"],
                "gem_terminal_name": gp["terminal_name"],
                "gem_unit_name": u["unit_name"],
                "status": u["status"],
                "capacity_mtpa": round(u["capacity_mtpa"], 2),
                "start_year": u["start_year"],
                "section_type": gp["section_type"],
                "owners": sorted(u["owners_set"]),
                "giignl_narrative_mention": mention,
                "is_gem_only": (u["unit_name"] not in aligned) and not mention,
            })

    return {
        "matches": matches,
        "fuzzy_matches": fuzzy_matches,
        "report_only": still_only,
        "gem_only_operating": gem_only,
        "nonoperating_units": nonoperating_units,
        "ambiguous": ambiguous,
        "stats": {
            "report_project_count": len(report_projects),
            "gem_project_count": len(gem_projects),
            "exact_matches": len(matches),
            "fuzzy_matches": len(fuzzy_matches),
            "unit_level_matches": sum(1 for m in matches + fuzzy_matches
                                      if m.get("match_granularity") == "unit"),
            "report_only_unmatched": len(still_only),
            "gem_only_operating": len(gem_only),
            "nonoperating_units": len(nonoperating_units),
            "ambiguous": len(ambiguous),
            "matches_with_disagreement": sum(1 for m in matches if m["disagreements"]),
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", choices=["giignl", "igu"], default="giignl",
                   help="Report type (only affects metadata labels)")
    p.add_argument("--extracted", required=True,
                   help="Path to extracted report CSV (from giignl_extract.py)")
    p.add_argument("--gem-csv", default=DEFAULT_GEM_CSV)
    p.add_argument("--prose-corrections", default=None,
                   help="Path to agent-authored §3.2.1 narrative operating-status "
                        "corrections JSON. Defaults to giignl_prose_corrections.json "
                        "next to the extracted CSV, if present.")
    p.add_argument("--output", default="./report_diff.json")
    args = p.parse_args()

    with open(args.extracted, encoding="utf-8") as f:
        report_rows = list(csv.DictReader(f))

    # Default the prose-corrections path to a file beside the extracted CSV.
    prose_path = args.prose_corrections
    if prose_path is None:
        guess = Path(args.extracted).with_name("giignl_prose_corrections.json")
        prose_path = str(guess) if guess.exists() else None
    prose_corrections = _load_prose_corrections(prose_path)
    n_op = sum(len(v) for v in prose_corrections["op"].values())
    n_nonop = sum(len(v) for v in prose_corrections["nonop"].values())
    if n_op or n_nonop:
        print(f"  Loaded {n_op} operating-status correction(s) + {n_nonop} non-op "
              f"corroboration(s) from narrative pass ({prose_path})")

    gem_projects, alias_map, collision_regas = _build_gem_project_table(args.gem_csv)
    diff = _classify(report_rows, gem_projects, alias_map=alias_map,
                     collision_regas=collision_regas,
                     prose_corrections=prose_corrections)
    diff["report_type"] = args.report
    diff["extracted_csv"] = args.extracted
    diff["gem_csv"] = args.gem_csv
    diff["prose_corrections_path"] = prose_path or ""

    Path(args.output).write_text(json.dumps(diff, indent=2, default=str))

    print(f"\n  Report: {args.report.upper()}")
    print(f"  Stats:")
    for k, v in diff["stats"].items():
        print(f"    {k:35} {v}")
    print(f"\n  Saved diff to {args.output}")


if __name__ == "__main__":
    main()
