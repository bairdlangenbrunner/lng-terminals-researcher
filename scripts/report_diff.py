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
    effective_status, normalize_country, normalize_entity,
    normalize_terminal_name, parse_entity_list, same_owner_entity,
    transliterate_to_english,
)


DEFAULT_GEM_CSV = "./gem_export.csv"


# ---------------------------------------------------------------------------
# GIIGNL Owner-column parser
# ---------------------------------------------------------------------------
#
# GIIGNL's Owner column is NOT a flat comma-separated entity list — it has a
# small grammar that the generic `parse_entity_list` (built for GEM's
# ";"-separated "Entity [NN%]" cells) mis-handles, producing garbage tokens
# like "50% YPF)" and polluting the owner set with vessel owners. Observed
# grammar (GIIGNL 2026 Annual Report, Owner column):
#
#   * Role labels, "<Role>:" — these map onto GEM's separate fields:
#       - "Owner:" / "FSRU:"  -> the VESSEL owner of a floating terminal
#         (GEM tracks this in `vessel_owner`, NOT the terminal `owner`).
#       - "Charterer:" / "Sub-charterer:" / "Terminal:" / "GNLQ:" / bare text
#         -> the TERMINAL owner/operator (GEM's `owner`).
#     e.g. Bahia: "Owner: Excelerate Energy  Charterer: Petrobras" — GEM models
#     Excelerate as vessel_owner and Petrobras as owner. Comparing GIIGNL's
#     terminal owners against GEM's owner set is the like-for-like comparison;
#     including the vessel owner would manufacture a false delta on every FSRU.
#
#   * A percentage may LEAD ("50% YPF") or TRAIL ("ENGIE (63%)", "ENGIE 63%").
#
#   * A parenthetical containing entity NAMES (not just a "%") lists the
#     preceding entity's SHAREHOLDERS:
#       "Charterer: UTE Escobar (50% Enarsa, 50% YPF)"
#         -> terminal owner: UTE Escobar; shareholders: Enarsa, YPF
#     A purely-numeric parenthetical ("ENGIE (63%)") is just the head's stake.
#     Nested parens ("Electrogas Malta (GEM Holdings (33%), Siemens (33%))")
#     are handled by balanced-paren matching.
#
# The owner SET used for the diff is (terminal_owners + shareholders) — the
# GEM-comparable entities — with vessel owners kept separate. Shareholders are
# folded in so the set matches whichever representation GEM uses (the JV vehicle
# OR its shareholders); the build-side benign-owner detector then classifies the
# JV-vs-shareholders granularity difference.

_OWNER_VESSEL_LABELS = ("owner", "fsru")
_OWNER_LABEL_RE = re.compile(
    r"\b(owner|sub-?charterer|charterer|fsru|terminal|gnlq)\s*:", re.IGNORECASE)
_PCT_ONLY_RE = re.compile(r"^\s*\d+(?:\.\d+)?\s*%?\s*$")
_PCT_PREFIX_RE = re.compile(r"^\s*\d+(?:\.\d+)?\s*%\s+(.*\S)\s*$")
_PCT_SUFFIX_RE = re.compile(r"^(.*?\S)\s*[\(\[]?\s*\d+(?:\.\d+)?\s*%\s*[\)\]]?\s*$")


def _find_matching_paren(s, open_idx):
    """Index of the ')' matching the '(' at `open_idx`, or -1 if unbalanced."""
    depth = 0
    for i in range(open_idx, len(s)):
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _split_top_level(s, seps=",;"):
    """Split on `seps` — and on the connector word 'and' — that are NOT inside
    (...) — so a shareholder list like '(50% Enarsa, 50% YPF)' stays one segment
    instead of breaking at its comma (the bug that produced the stray '50% YPF)'
    token).

    GIIGNL writes an owner list with the final item joined by 'and' rather than a
    comma: 'Petronas Gas (65%), Dialog Group (25%) and Johor State (10%)'. The
    'and' is a list connector, not part of a name, so it splits like a comma and
    is dropped — yielding three owners, not a merged 'Dialog Group and Johor
    State'. The split is gated on word boundaries (so 'Finland', 'Iceland',
    'Netherlands' are untouched) and only fires at depth 0. '&' is intentionally
    NOT a separator — it identifies names like 'Black & Veatch'. (No GEM owner
    entity contains a standalone 'and'; the only 'and' canonical is the COUNTRY
    'Trinidad and Tobago', which never appears in an owner cell.)"""
    out, buf, depth = [], [], 0
    i, n = 0, len(s)
    while i < n:
        ch = s[i]
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch in seps and depth == 0:
            out.append("".join(buf))
            buf = []
        elif (depth == 0 and ch in "aA" and s[i:i + 3].lower() == "and"
                and (i == 0 or not s[i - 1].isalnum())
                and (i + 3 >= n or not s[i + 3].isalnum())):
            out.append("".join(buf))
            buf = []
            i += 3
            continue
        else:
            buf.append(ch)
        i += 1
    if buf:
        out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


def _clean_owner_token(seg):
    """Strip a leading/trailing percentage and stray brackets from one entity
    segment (already paren-group-free). Returns '' if it's pct-only/empty."""
    seg = (seg or "").strip().strip(",;").strip()
    if not seg or _PCT_ONLY_RE.match(seg):
        return ""
    m = _PCT_PREFIX_RE.match(seg)        # "50% YPF" -> "YPF"
    if m:
        seg = m.group(1).strip()
    m = _PCT_SUFFIX_RE.match(seg)        # "ENGIE (63%)" / "ENGIE 63%" -> "ENGIE"
    if m:
        seg = m.group(1).strip()
    return seg.strip(" ,;()[]").strip()


def _parse_owner_inner(seg):
    """Parse a shareholder sub-segment that may carry its own '(NN%)'
    ('Siemens (33.33%)' -> 'Siemens'). Returns the bare entity or ''."""
    seg = (seg or "").strip()
    op = seg.find("(")
    if op != -1:
        cl = _find_matching_paren(seg, op)
        inside = seg[op + 1:cl] if cl != -1 else seg[op + 1:]
        if _PCT_ONLY_RE.match(inside.strip()):
            tail = seg[cl + 1:] if cl != -1 else ""
            seg = (seg[:op] + " " + tail).strip()
        else:
            seg = seg[:op].strip()  # rare nested non-pct paren: keep the head
    return _clean_owner_token(seg)


def _parse_owner_segment(seg, named, shareholders):
    """Parse one top-level segment (label already stripped). Appends the head
    entity to `named` and any parenthetical shareholder NAMES to `shareholders`.
    A purely-numeric paren is the head's stake, not a shareholder list."""
    seg = (seg or "").strip()
    if not seg:
        return
    op = seg.find("(")
    if op == -1:
        ent = _clean_owner_token(seg)
        if ent:
            named.append(ent)
        return
    cl = _find_matching_paren(seg, op)
    if cl == -1:                          # unbalanced (wrapping artifact)
        inside, head = seg[op + 1:], seg[:op]
    else:
        inside, head = seg[op + 1:cl], (seg[:op] + " " + seg[cl + 1:])
    head_ent = _clean_owner_token(head)
    if _PCT_ONLY_RE.match(inside.strip()):   # "(63%)" — just the head's stake
        if head_ent:
            named.append(head_ent)
        return
    if head_ent:                              # holding co / charterer is a named owner
        named.append(head_ent)
    for sub in _split_top_level(inside):      # the inner names are shareholders
        sub_ent = _parse_owner_inner(sub)
        if sub_ent:
            shareholders.append(sub_ent)


def parse_report_owner(s):
    """Parse a GIIGNL Owner-column cell into
    (terminal_owners, vessel_owners, shareholders) — each an ordered,
    de-duplicated list of CANONICAL entity names. See the section comment above
    for the grammar. Empty cell -> ([], [], [])."""
    if not s or not str(s).strip():
        return [], [], []
    s = str(s).strip()
    clauses, last, cur_role = [], 0, "terminal"  # pre-label text is bare/terminal
    for m in _OWNER_LABEL_RE.finditer(s):
        if m.start() > last:
            clauses.append((cur_role, s[last:m.start()]))
        lab = m.group(1).lower()
        cur_role = "vessel" if lab in _OWNER_VESSEL_LABELS else "terminal"
        last = m.end()
    clauses.append((cur_role, s[last:]))

    term_named, term_share, vess_named = [], [], []
    for role, text in clauses:
        if role == "vessel":
            for seg in _split_top_level(text):
                _parse_owner_segment(seg, vess_named, vess_named)
        else:
            for seg in _split_top_level(text):
                _parse_owner_segment(seg, term_named, term_share)

    def _canon_dedup(names):
        out = []
        for n in names:
            c = normalize_entity(n)
            if c and c not in out:
                out.append(c)
        return out

    return _canon_dedup(term_named), _canon_dedup(vess_named), _canon_dedup(term_share)


def _report_owner_sets(owner_cell):
    """Convenience wrapper: returns (owners_set, vessel_owners_set) for a GIIGNL
    owner cell, where owners_set = terminal owners + their shareholders (the
    GEM-`owner`-comparable entities) and vessel owners are kept separate so they
    don't manufacture false owner deltas against GEM (GEM tracks vessel owners in
    its own `vessel_owner` field)."""
    term, vess, share = parse_report_owner(owner_cell)
    return set(term) | set(share), set(vess)


def _owner_alignment(rp_owners, gem_owners, gem_parents):
    """Align a report row's owners against GEM's `owner` ∪ `parent` sets.

    GEM records the lower-level (JV / operating-company) owners in `owner` and
    the ULTIMATE PARENT companies in `parent`; GIIGNL may name an entity at
    EITHER level (Escobar: GEM owner "UTE Escobar", parent "ENARSA; YPF"; GIIGNL
    lists Enarsa + YPF). Checking only `owner` flags the parent-level GIIGNL
    entities as false report-only deltas — so the alignment uses owner ∪ parent.

    Returns (overlap, report_only, gem_only, via_parent):
      overlap     — report owners aligned with a GEM owner OR parent
      report_only — report owners in NEITHER GEM owner nor parent (a real delta)
      gem_only    — GEM OWNERS absent from the report (parents are supplementary,
                    not expected to appear in GIIGNL, so they're not gem-only)
      via_parent  — report owners matched only at the GEM PARENT level (surfaced
                    so a reviewer sees the alignment is parent-, not owner-level)

    Alignment is EQUIVALENCE-aware (normalize.same_owner_entity), not exact set
    intersection: a name that differs only by a legal suffix or descriptive
    qualifier ("Gasum" vs "Gasum Oy", "Chugoku Electric" vs "Chugoku Electric
    Power") aligns rather than surfacing as a spurious report_only/gem_only delta.
    This affects DELTA reporting only — the match gating stays owner-level exact
    elsewhere (a shared ultimate parent is too broad to identify a terminal).
    """
    rp_owners, gem_owners, gem_parents = set(rp_owners), set(gem_owners), set(gem_parents)
    gem_all = gem_owners | gem_parents

    def _aligned(o, others):
        return any(same_owner_entity(o, x) for x in others)

    overlap = {o for o in rp_owners if _aligned(o, gem_all)}
    report_only = {o for o in rp_owners if not _aligned(o, gem_all)}
    gem_only = {o for o in gem_owners if not _aligned(o, rp_owners)}
    via_parent = {o for o in rp_owners
                  if _aligned(o, gem_parents) and not _aligned(o, gem_owners)}
    return overlap, report_only, gem_only, via_parent


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
# letter) so plain named stages WITHOUT a digit are never stripped here — leaves
# "Senboku II", "Bontang Train E", "Corpus Christi Stage III" to the dedicated
# train-word / stage-word folds (or, for Senboku, to nothing). Used to fold the
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
# ("Senboku II"); the literal word "Train" marks a genuine per-train row, so those
# fold to the shared base. ("Corpus Christi Stage III" folds via the separate
# Stage/Phase-word fold below, not here.) Code is a 1-2 letter token, a 1-2 digit
# number, or a roman numeral.
_TRAIN_WORD_RE = re.compile(
    r"^(.*\S)\s+trains?\s+(?:[a-z]{1,2}|\d{1,2}|[ivxlc]{1,4})\s*$", re.IGNORECASE)


def _strip_train_word_suffix(raw):
    """Return the base site name if `raw` ends in an explicit 'Train <code>'
    designator, else None.  'Bontang Train E' -> 'Bontang'."""
    if not raw:
        return None
    m = _TRAIN_WORD_RE.match(str(raw).strip())
    return m.group(1).strip() if m else None


# Matches a trailing explicit "Stage <numeral>" / "Phase <numeral>" designator —
# GIIGNL splits a phased terminal whose LATER stage GEM still models as UNITS of
# the SAME terminal: "Corpus Christi" (Stage 1/2 trains) + "Corpus Christi Stage
# III" (the Phase-3 trains that came online) both belong to GEM's one "Corpus
# Christi LNG Terminal". The literal word "Stage"/"Phase" plus a numeral marks a
# phase row of an existing site (NOT a distinct terminal), so — like the explicit
# "Train" word — it's safe to fold even though the numeral alone would not be
# (the bare unit-code fold ignores numeral-only suffixes to protect "Senboku II",
# which carries no "Stage"/"Phase" word and is therefore untouched here).
_STAGE_WORD_RE = re.compile(
    r"^(.*\S)\s+(?:stage|phase)\s+(?:\d{1,2}|[ivxlc]{1,4})\s*$", re.IGNORECASE)


def _strip_stage_suffix(raw):
    """Return the base site name if `raw` ends in an explicit 'Stage/Phase <num>'
    designator, else None.  'Corpus Christi Stage III' -> 'Corpus Christi'."""
    if not raw:
        return None
    m = _STAGE_WORD_RE.match(str(raw).strip())
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


def _trailing_numeral(s):
    """The trailing standalone numeral token of a normalized name, or '' .

    'map ta phut terminal 1' -> '1'; 'map ta phut' -> ''. Numerals are
    canonicalized to Arabic by normalize_terminal_name (roman II -> 2), so this
    compares like with like. Used to disambiguate numbered siblings (Map Ta Phut
    1/2/3) whose only distinguishing token is the trailing number — too short for
    `_tokens_4plus`, so the generic ≥2-shared-token rule otherwise pulls in every
    sibling and the row falls to `ambiguous`."""
    toks = _ordered_tokens(s)
    if toks and re.fullmatch(r"\d{1,2}", toks[-1]):
        return toks[-1]
    return ""


def _ordered_tokens(s):
    """Ordered list of lowercased tokens (whitespace/hyphen/slash split,
    punctuation-stripped). Like _simple_tokens but preserves order & duplicates
    so a whole-token-subsequence containment test is possible."""
    out = []
    for raw in re.split(r"[\s\-/]+", s or ""):
        clean = raw.strip(_string.punctuation + "()[]{}")
        if clean:
            out.append(clean)
    return out


def _word_boundary_substring(a, b):
    """True if one name's token sequence is a contiguous run of the other's —
    i.e. a whole-WORD substring, not a raw character substring. 'nansha' matches
    'guangzhou nansha' but NOT 'longkou nanshan' ('nansha' is a char-substring of
    'nanshan' but not a whole token). Hyphen/slash count as boundaries, so 'arzew'
    still matches 'arzew-bethioua' (the old char-substring behaviour for that
    case, but without the cross-word false positives a bare substring invites)."""
    ta, tb = _ordered_tokens(a), _ordered_tokens(b)
    if not ta or not tb:
        return False
    short, long = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    for i in range(len(long) - len(short) + 1):
        if long[i:i + len(short)] == short:
            return True
    return False


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


# Train tokens inside a name / `trains` string. GEM frequently models a SPAN of
# trains as one unit whose name encodes the range it covers ("Phase 1 (T1-T2)",
# "(T1-T6)"); GIIGNL splits the same span across per-train rows ("LNG Canada T1",
# "LNG Canada T2"). _train_numbers expands a name's "T<n>" / "T<a>-T<b>" tokens to
# the set of train numbers, so several GIIGNL per-train rows can be SUMMED against
# the single GEM unit that covers them (see _align_units) — instead of one row
# matching the unit at half-capacity and the rest orphaning into report_only.
_TRAIN_RANGE_RE = re.compile(r"t(\d+)\s*[-–]\s*t?(\d+)", re.IGNORECASE)
_TRAIN_NUM_RE = re.compile(r"t(\d+)", re.IGNORECASE)


def _train_numbers(text):
    """Set of train numbers a name / `trains` string encodes via 'T<n>' tokens.

    'Phase 1 (T1-T2)' -> {1, 2}   'T1-6' -> {1,2,3,4,5,6}   'T2' -> {2}
    'Phase 2' -> set()   'GL1Z' -> set()  (no 'T' immediately before the digit)
    """
    if not text:
        return set()
    s = str(text)
    nums, consumed = set(), []
    for m in _TRAIN_RANGE_RE.finditer(s):
        a, b = int(m.group(1)), int(m.group(2))
        if a <= b and b - a < 50:  # sane bound; ignore "T1-T9999" garbage
            nums.update(range(a, b + 1))
            consumed.append((m.start(), m.end()))
    for m in _TRAIN_NUM_RE.finditer(s):
        if any(lo <= m.start() < hi for lo, hi in consumed):
            continue  # already counted inside a range
        nums.add(int(m.group(1)))
    return nums


def _row_capacity_mtpa(r):
    """Float operating capacity of a report row, 0.0 if blank/unparseable."""
    try:
        return float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_capacity_source(refs):
    """Classify a GEM `capacity_ref` cell (one or more comma/space-separated URLs)
    into the provenance the verdict logic needs: which GIIGNL edition year(s) it
    cites (parsed from giignl.org URLs like `GIIGNL2022_Annual_Report` or
    `giignl_-_2020_annual_report`) and whether it ALSO cites any non-GIIGNL source.

    The 'GIIGNL 2026 supersedes' verdict fires only when GIIGNL is the SOLE capacity
    source (giignl_years non-empty AND not has_non_giignl); a mixed cell routes to
    research because the non-GIIGNL source may be the authoritative one.

    Returns {"giignl_years": sorted[int], "has_non_giignl": bool, "refs": str}.
    """
    refs = (refs or "").strip()
    if not refs:
        return {"giignl_years": [], "has_non_giignl": False, "refs": ""}
    years, has_non = set(), False
    for url in re.split(r"[\s,]+", refs):
        if not url:
            continue
        if "giignl.org" in url.lower():
            yrs = [int(y) for y in re.findall(r"(?:19|20)\d{2}", url)]
            if yrs:
                years.add(max(yrs))  # path + filename usually agree; max = edition
        else:
            has_non = True
    return {"giignl_years": sorted(years), "has_non_giignl": has_non, "refs": refs}


def _gem_capacity_source_for_project(gp):
    """Provenance of the capacity that fed `gem_capacity_mtpa` — i.e. the union of
    the OPERATING units' capacity_ref cells (the operating-only total GIIGNL is
    compared against). Returns the _parse_capacity_source shape."""
    if not gp:
        return {"giignl_years": [], "has_non_giignl": False, "refs": ""}
    op_refs = [u.get("capacity_ref", "") for u in gp.get("units", [])
               if u.get("status") == "operating" and u.get("capacity_ref")]
    return _parse_capacity_source(", ".join(op_refs))


# GEM statuses that are PRE-operating capacity GIIGNL might already be counting as
# operating (it counts a train as operating once it is producing LNG, before GEM
# moves it off construction). A retired/mothballed unit's capacity is NOT a forward
# phase that would inflate a current GIIGNL operating total, so it's excluded here.
_PREOP_STATUSES = {"construction", "proposed", "pre-construction"}


def _gem_nonop_capacity_explanation(gp):
    """Summarize the GEM NON-OPERATING units whose capacity could plausibly explain a
    GIIGNL-operating-capacity-EXCEEDS-GEM gap — the Corpus Christi shape: GIIGNL counts
    mid-scale "Stage III" trains as operating that GEM deliberately holds as
    construction. GIIGNL's operating total can then sit ABOVE GEM's operating total
    not because GEM's capacity figure is stale, but because the two sources disagree
    on which trains are operating (a STATUS divergence) and how the stage is split
    into trains (a train-ORGANIZATION divergence).

    Returns a dict the verdict layer (build_review_package._classify_disagreement)
    uses to STOP the GIIGNL-edition-supersede rule from blindly bumping GEM's
    capacity, plus the researcher notes the human reviewer needs to see:
      {
        "preop_capacity_mtpa": float,   # sum of construction/proposed unit capacities
        "preop_units": [{name,status,capacity_mtpa,researcher_notes}, ...],
        "researcher_notes": [{unit,status,note}, ...],   # ALL non-op units w/ a note
        "has_researcher_note": bool,
      }
    `preop_*` is scoped to forward (construction/proposed) phases — the gap-explainers;
    `researcher_notes` spans every non-op unit carrying a note (the explanatory note
    often lives on the construction unit, but capture all so none is lost).
    """
    if not gp:
        return {"preop_capacity_mtpa": 0.0, "preop_units": [],
                "researcher_notes": [], "has_researcher_note": False}
    preop_units, preop_cap = [], 0.0
    notes = []
    for u in gp.get("units", []):
        st = (u.get("status") or "").strip().lower()
        if st == "operating":
            continue
        note = (u.get("researcher_notes") or "").strip()
        if note:
            notes.append({"unit": u.get("unit_name", ""), "status": st, "note": note})
        if st in _PREOP_STATUSES:
            cap = u.get("capacity_mtpa") or 0.0
            preop_cap += cap
            preop_units.append({
                "unit_name": u.get("unit_name", ""),
                "status": st,
                "capacity_mtpa": round(cap, 2),
                "researcher_notes": note,
            })
    return {
        "preop_capacity_mtpa": round(preop_cap, 2),
        "preop_units": preop_units,
        "researcher_notes": notes,
        "has_researcher_note": bool(notes),
    }


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
    rows = list(rp["rows"])
    consumed = set()  # indices into `rows` claimed by the train-range pre-pass

    # --- Train-range pre-pass --------------------------------------------------
    # A GEM unit whose name encodes a multi-train range ("Phase 1 (T1-T2)") absorbs
    # the GIIGNL per-train rows whose train number falls inside that range; their
    # capacities are SUMMED before comparison, so the unit isn't pitted against a
    # single train's half-capacity (which produced the bogus LNG Canada "T1: 7 vs
    # 14, 50% conflict" + "T2 orphaned to report_only" before this pass existed).
    # Restricted to OPERATING units — GIIGNL's tables are operating-only, matching
    # the operating-only project total this aligns within. Fires only for units
    # naming >=2 trains, so single-train units fall through to the token pass below.
    range_units = []
    for u in gp.get("units", []):
        if u.get("status") != "operating" or not u.get("unit_name"):
            continue
        tnums = _train_numbers(u.get("unit_name", ""))
        if len(tnums) >= 2:
            range_units.append((u, tnums))
    # Widest range first, so a broad unit claims its rows before a narrower overlap.
    range_units.sort(key=lambda ut: -len(ut[1]))
    for u, tnums in range_units:
        if u["unit_name"] in used:
            continue
        members = []
        for idx, r in enumerate(rows):
            if idx in consumed:
                continue
            row_trains = (_train_numbers(r.get("trains", ""))
                          | _train_numbers(r.get("site_name", "")))
            if row_trains and row_trains <= tnums:
                members.append((idx, r))
        if not members:
            continue
        rsum = round(sum(_row_capacity_mtpa(r) for _i, r in members), 2)
        gcap = u["capacity_mtpa"]
        dpct = (abs(rsum - gcap) / gcap * 100) if gcap else None
        used.add(u["unit_name"])
        consumed.update(idx for idx, _r in members)
        label = "; ".join(
            (r.get("site_name", "") + (" " + r.get("trains", "") if r.get("trains") else "")).strip()
            for _i, r in members)
        unit_matches.append({
            "report_site": label,
            "report_capacity_mtpa": rsum,
            "gem_unit_name": u["unit_name"],
            "gem_unit_status": u["status"],
            "gem_unit_capacity_mtpa": round(gcap, 2),
            "gem_unit_capacity_ref": u.get("capacity_ref", ""),
            "capacity_delta_pct": round(dpct, 1) if dpct is not None else None,
            "agree": bool(round(rsum - gcap, 2) == 0),
        })

    # --- Token-subset pass (rows not claimed above) ----------------------------
    for idx, r in enumerate(rows):
        if idx in consumed:
            continue
        site_tokens = _simple_tokens(normalize_terminal_name(r.get("site_name", "")))
        rcap = _row_capacity_mtpa(r)
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
                "gem_unit_capacity_ref": chosen.get("capacity_ref", ""),
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


def _load_match_overrides(path):
    """Load agent-authored match overrides. Returns
        {(country_norm, report_site_norm, section): {gem_terminal_id, gem_terminal_name, basis}}
    Each entry PINS a GIIGNL report project to a specific GEM terminal by ID,
    overriding the deterministic canonical/alias/fuzzy match.

    This is the escape hatch for the one shape the matcher can't settle safely:
    an EXACT name-token collision where GIIGNL's name matches one GEM terminal
    verbatim but actually denotes a DIFFERENT same-token terminal. Canonical
    case — GIIGNL "Putian, Fujian" (6.3 MTPA operating, owner CNOOC 60% / Fujian
    Inv & Dev 40%) exact-matches GEM "Putian LNG Terminal" (the Hanas
    construction site at the same Meizhou Bay port, 0 operating) on the bare
    "putian" token, while the real operating terminal is GEM "Fujian LNG
    Terminal" (CNOOC, 6.3, same owner split). The operating-capacity / owner
    tie-breaks only fire on the FUZZY same-name-family path, never on an exact
    canonical hit, so the matcher takes the wrong terminal at face value and
    orphans the real one into gem_only_operating ("why is GIIGNL missing it?").
    The override re-pins the report row to its true GEM terminal; the displaced
    same-token terminal falls to gem_only and, being non-operating, drops out of
    gem_only_operating (correct — GIIGNL's operating tables never list it).

    `report_site_name` is matched against the REPORT project key (same
    normalization, so the author can write the verbatim GIIGNL site name).
    Nothing is auto-applied to GEM (§3.8) — this only corrects which GEM terminal
    the GIIGNL row is compared against. {} if the file is absent/empty."""
    if not path or not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text())
    out = {}
    for o in data.get("match_overrides", []):
        key = (normalize_country(o.get("country", "")),
               normalize_terminal_name(o.get("report_site_name", "")),
               o.get("section_type", ""))
        tid = (o.get("gem_terminal_id") or "").strip()
        if not all(key) or not tid:
            continue
        out[key] = {
            "gem_terminal_id": tid,
            "gem_terminal_name": o.get("gem_terminal_name", ""),
            "basis": o.get("basis", ""),
        }
    return out


def _apply_match_overrides(report_projects, gem_projects, override_map):
    """Pin each overridden report project to its target GEM terminal by setting
    `_forced_gem_key` (the same mechanism the multi-terminal FSRU split uses).
    The target is resolved by (terminal_id, section) — a liq+regas terminal is
    two GEM projects sharing one id, so section disambiguates. No-op (with a
    warning) if the report project or the target GEM terminal isn't present, or
    if the report project is already force-matched (FSRU split wins; they don't
    overlap in practice). Returns the count applied. Must run after the FSRU
    split / subname merge / prose pass (final report-project keys) and before
    `forced_gem` is read in the matching loop."""
    if not override_map:
        return 0
    by_tid_section = {(gp["terminal_id"], gp["section_type"]): gk
                      for gk, gp in gem_projects.items()}
    applied = 0
    for rkey, ov in override_map.items():
        section = rkey[2]
        rp = report_projects.get(rkey)
        if rp is None:
            print(f"  WARNING: match override {rkey} skipped — no such GIIGNL "
                  f"report project (name may have changed this edition)")
            continue
        gkey = by_tid_section.get((ov["gem_terminal_id"], section))
        if gkey is None:
            print(f"  WARNING: match override {rkey} skipped — GEM terminal "
                  f"{ov['gem_terminal_id']} ({section}) not in export")
            continue
        if rp.get("_forced_gem_key"):
            print(f"  WARNING: match override {rkey} skipped — already "
                  f"force-matched to {rp['_forced_gem_key']}")
            continue
        rp["_forced_gem_key"] = gkey
        rp["_match_override_basis"] = (
            ov.get("basis", "") or f"agent-pinned to {ov['gem_terminal_id']}")
        applied += 1
    return applied


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


def _report_vessel_token_sets(rp):
    """Vessel-identity token-sets carried by a report project's rows (operating +
    non-operating). One set per distinct GIIGNL vessel — e.g. Sepetiba's single
    row 'LNGt Powership Asia' → [{'lngt','powership','asia'}]."""
    sets = []
    for r in rp.get("rows", []) + rp.get("nonop_rows", []):
        toks = _vessel_key_tokens(r.get("vessel_name", "") or "")
        if toks and toks not in sets:
            sets.append(toks)
    return sets


def _fsru_vessel_match(rp, gp):
    """True if a GIIGNL FSRU/FSU row's vessel name matches this GEM terminal's
    FloatingVesselName. The vessel identity is a strong, near-unique corroborator:
    GIIGNL identifies a floating terminal by its deployed vessel, and GEM tracks
    the same vessel in FloatingVesselName, so an exact/containment vessel match
    binds the two records even when the SITE names diverge (GIIGNL 'Sepetiba LNG'
    vs GEM 'Sepetiba Bay FSRU') and owners/capacity disagree (Sepetiba: GIIGNL's
    Karpowership/MOL JV partners vs GEM's 'KARMOL' tag; 0.5 vs 2.7 MTPA). Match is
    by token containment in either direction so an operator-prefixed GIIGNL name
    ('Excelerate Excelsior') still matches a bare GEM vessel ('Excelsior').

    Only fires for FSRU GEM terminals that carry a vessel name — onshore terminals
    have none, so this never manufactures a floating-vs-onshore false match."""
    if not gp.get("fsru"):
        return False
    gem_sets = gp.get("vessel_name_sets") or []
    if not gem_sets:
        return False
    for rt in _report_vessel_token_sets(rp):
        for gt in gem_sets:
            if rt and gt and (rt <= gt or gt <= rt):
                return True
    return False


def _build_fsru_fleet_index(fleet_path):
    """Index the GIIGNL FSRU-fleet table by country so the gem_only pass can tell
    when a GEM FSRU the country regasification tables OMIT is in fact listed in the
    report's FSRU fleet table. GIIGNL routinely carries a floating terminal only in
    the fleet table, not in the per-country regas tables (e.g. GEM 'Tema FSRU' /
    Ghana ↔ fleet 'Tema LNG', vessel 'Torman') — without this cross-check the diff
    wrongly reports 'the report doesn't list it'. Returns {country_norm: [entry]}
    with each entry carrying precomputed site tokens (>=4-char, suffix-stripped)
    and vessel-identity tokens. Empty dict if the file is absent/unreadable."""
    if not fleet_path:
        return {}
    try:
        data = json.loads(Path(fleet_path).read_text())
    except (OSError, ValueError):
        return {}
    index = defaultdict(list)
    for v in data.get("vessels", []):
        country = normalize_country(v.get("location_country", "") or "")
        site = (v.get("location_site", "") or "").strip()
        if not country or not site:
            continue
        site_toks = {t for t in _simple_tokens(normalize_terminal_name(site))
                     if len(t) >= 4}
        index[country].append({
            "location_site": site,
            "vessel_name": (v.get("vessel_name", "") or "").strip(),
            "site_tokens": site_toks,
            "vessel_tokens": _vessel_key_tokens(v.get("vessel_name", "") or ""),
        })
    return dict(index)


def _fleet_match_for_gem_only(gp, fleet_index):
    """Return the FSRU-fleet entry that corroborates a gem_only FSRU project, or
    None. Same-country match on either a vessel-name token containment (strongest —
    the deployed vessel is a near-unique key) or a significant site-token subset
    (GEM 'Tema' ⊆ fleet 'Tema'). Only fires for FSRU GEM terminals, so it never
    manufactures a floating-vs-onshore false match."""
    if not gp.get("fsru") or not fleet_index:
        return None
    entries = fleet_index.get(normalize_country(gp.get("country", "") or ""))
    if not entries:
        return None
    gem_site_toks = {t for t in _simple_tokens(
        normalize_terminal_name(gp.get("terminal_name", ""))) if len(t) >= 4}
    gem_vessel_sets = gp.get("vessel_name_sets") or []
    for e in entries:
        for gt in gem_vessel_sets:
            if gt and e["vessel_tokens"] and (
                    gt <= e["vessel_tokens"] or e["vessel_tokens"] <= gt):
                return e
        st = e["site_tokens"]
        if gem_site_toks and st and (gem_site_toks <= st or st <= gem_site_toks):
            return e
    return None


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
    vessel_owners = set()
    for r in sub_rows:
        try:
            cap += float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
        except ValueError:
            pass
        o_set, v_set = _report_owner_sets(r.get("owner", ""))
        owners |= o_set
        vessel_owners |= v_set
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
        "vessel_owners_set": vessel_owners,
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
        "status", "substatus", "fuel", "owner", "parent", "capacity_mtpa", "capacity_ref",
        "floating", "floating_vessel_name",
        "import_export_only", "other_names", "local_names", "language",
        "proposal_year", "construction_year", "shelved_year", "cancelled_year",
        "stop_year", "actual_start_year", "researcher_notes_unit",
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

            raw_status = row[ci["status"]] if ci["status"] is not None else ""
            substatus = row[ci["substatus"]] if ci["substatus"] is not None else ""
            # Honor the planned/actual substatus rule: an operating/construction
            # unit whose substatus is 'planned' has not actually reached that
            # milestone, so it counts as `proposed` and must NOT inflate the
            # operating capacity total (Tilbury Phase 1b / LNG Canada T3-T4).
            status = effective_status(raw_status, substatus)
            owner = row[ci["owner"]] if ci["owner"] is not None else ""
            parent = row[ci["parent"]] if ci["parent"] is not None else ""
            cap_mtpa = row[ci["capacity_mtpa"]] if ci["capacity_mtpa"] is not None else ""
            cap_ref = row[ci["capacity_ref"]] if ci["capacity_ref"] is not None else ""
            floating = row[ci["floating"]] if ci["floating"] is not None else ""
            other_names_raw = row[ci["other_names"]] if ci["other_names"] is not None else ""
            researcher_notes_unit = (
                row[ci["researcher_notes_unit"]]
                if ci["researcher_notes_unit"] is not None else "")

            # Distinguish a genuine 0 capacity from a MISSING/unknown one. A blank or
            # unparseable cell leaves capacity UNKNOWN (cap_known=False) and must not
            # render as "0" downstream — a cancelled unit with no DB capacity is
            # unknown, not zero (Pluto LNG Terminal T3). `cap` stays a float (0.0
            # sentinel) so the hardened capacity arithmetic below is unaffected;
            # cap_known only gates DISPLAY (the non-operating sheet).
            cap_known = bool(cap_mtpa)
            try:
                cap = float(cap_mtpa) if cap_mtpa else 0.0
            except ValueError:
                cap = 0.0
                cap_known = False

            # Parse the GEM owner cell with the same parser the report side uses.
            # GEM cells are ";"-separated with "[NN%]" brackets ("QatarEnergy
            # [70%]; Exxon Mobil Corp [30%]"); the previous comma-only split
            # collapsed a multi-owner cell to a single (often wrong) tag, which
            # manufactured false owner conflicts on nearly every multi-owner match.
            owner_tags = set()
            for ent in parse_entity_list(owner):
                if ent["entity"]:
                    owner_tags.add(ent["entity"])
            # GEM also records the ULTIMATE PARENT companies in a separate `parent`
            # field, while `owner` holds the lower-level (often JV/operating-co)
            # owners. GIIGNL may name an entity at EITHER level — e.g. Escobar:
            # GEM owner "UTE Escobar", parent "ENARSA; YPF"; GIIGNL lists Enarsa +
            # YPF. So an owner-alignment check must consider owner ∪ parent, else
            # the parent-level GIIGNL entities show as false "report-only" deltas.
            parent_tags = set()
            for ent in parse_entity_list(parent):
                if ent["entity"]:
                    parent_tags.add(ent["entity"])

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
                    "parents_set": set(),
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
            p["parents_set"].update(parent_tags)
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
                # raw GEM status before the planned/actual substatus rule, kept for
                # audit: status != raw_status means a planned milestone was demoted
                # to proposed (e.g. operating/planned -> proposed).
                "raw_status": raw_status,
                "substatus": substatus,
                "capacity_mtpa": cap,
                "capacity_known": cap_known,
                "capacity_ref": (cap_ref or "").strip(),
                "start_year": _unit_anchor_year(row, ci, status),
                "owners_set": owner_tags,
                "parents_set": parent_tags,
                # A GEM researcher note on this unit can encode a DELIBERATE position
                # the reconciliation must defer to — e.g. Corpus Christi Stage 3
                # (T04-T10): "trains producing LNG but commercial operations not
                # declared, so I'm holding it as construction." Surfaced on the match
                # so the verdict logic won't blindly bump GEM's operating capacity to a
                # GIIGNL total that counts those not-yet-commercial trains.
                "researcher_notes": (researcher_notes_unit or "").strip(),
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
              prose_corrections=None, fsru_fleet_index=None, match_overrides=None):
    """Apply matching with canonical + alias + fuzzy passes, then classify.

    Returns dict with: matches, fuzzy_matches, report_only, gem_only_operating,
                       ambiguous, stats
    """
    alias_map = alias_map or {}
    collision_regas = collision_regas or set()
    fsru_fleet_index = fsru_fleet_index or {}
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

        4. Stage/Phase fold. GIIGNL splits a later phase that GEM keeps as UNITS of
           the existing terminal ('Corpus Christi' + 'Corpus Christi Stage III' →
           one GEM 'Corpus Christi LNG Terminal'); the 6.0 MTPA Stage-III rows then
           surface as a capacity/status conflict on the matched terminal (GIIGNL
           counts the Phase-3 trains as operating; GEM still has them as
           construction) instead of a misleading report_only "GIIGNL has, GEM
           doesn't". The literal word 'Stage'/'Phase' makes the numeral safe to
           fold (the numeral-only unit-code fold can't, lest it eat 'Senboku II').

        All four avoid merging extraction artifacts and genuinely distinct named
        terminals that lack a recognized suffix/code/train-/stage-word
        ('Senboku II' has no Stage/Phase word, so it is never folded)."""
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

        # 4. Stage/Phase fold. GIIGNL splits a later phase that GEM models as units
        #    of the same terminal ('Corpus Christi' + 'Corpus Christi Stage III' →
        #    one GEM 'Corpus Christi LNG Terminal'). Requires the base to resolve to
        #    a GEM key/alias OR another report row carrying the base name — so a
        #    stand-alone 'X Stage N' with no base partner is left as its own row.
        sg_base_raw = _strip_stage_suffix(raw_site)
        if sg_base_raw:
            sg_norm = normalize_terminal_name(sg_base_raw)
            if sg_norm and sg_norm != full_norm:
                sg_key = (country_norm, sg_norm, section_type)
                if (sg_key in gem_projects or sg_key in alias_map
                        or sg_key in rep_name_keys):
                    return sg_norm, True, sg_base_raw

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

        owner_tags, vessel_owner_tags = _report_owner_sets(r.get("owner", ""))

        if key not in report_projects:
            report_projects[key] = {
                "country": r.get("country", ""),
                "country_norm": country_norm,
                "site_name": r.get("site_name", ""),
                "name_norm": name_norm,
                "section_type": section_type,
                "total_capacity_mtpa": 0.0,
                "owners_set": set(),
                "vessel_owners_set": set(),
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
        rp.setdefault("vessel_owners_set", set()).update(vessel_owner_tags)
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

    # Agent-authored match overrides: re-pin a GIIGNL report row that exact-matched
    # the WRONG same-token GEM terminal to its true GEM terminal (e.g. "Putian,
    # Fujian" → GEM "Fujian LNG Terminal", not the same-named Hanas construction
    # site). Runs after the FSRU split / subname merge / prose pass so it sees the
    # final report-project keys, and before `forced_gem` is read below.
    _apply_match_overrides(report_projects, gem_projects, match_overrides or {})

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

        # Compare owners against GEM owner ∪ parent (see _owner_alignment).
        owner_overlap, owner_only_report, owner_only_gem, owner_via_parent = _owner_alignment(
            rp["owners_set"], gp["owners_set"], gp["parents_set"])

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
            "match_type": ("exact_via_alias" if via_alias
                           else "override" if rp.get("_match_override_basis")
                           else "exact"),
            "match_override": rp.get("_match_override_basis", ""),
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
            "owners_matched_via_gem_parent": sorted(owner_via_parent),
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
        owner_ok = bool(rp["owners_set"] & gp["owners_set"])  # gate owner-level (see fuzzy gate)
        if not (name_ok or owner_ok):
            continue

        report_cap = rp["total_capacity_mtpa"]
        unit_cap = unit["capacity_mtpa"]
        cap_delta = report_cap - unit_cap
        cap_pct = abs(cap_delta) / unit_cap * 100 if unit_cap else None
        unit_owners = unit.get("owners_set", set())
        owner_overlap_u, owner_only_report, owner_only_gem, _ = _owner_alignment(
            rp["owners_set"], unit_owners, unit.get("parents_set", set()))
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
            "owners_overlap": sorted(owner_overlap_u),
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
        # Also exclude a GEM project whose every unit is CANCELLED: a GIIGNL
        # liq/regas row is operating-only, so a fully-cancelled terminal can never
        # be its match. Without this, GIIGNL "Caofeidian (Tangshan)" (operating,
        # PetroChina, 10.0) substring-matched the cancelled "Caofeidian FSRU"
        # (0 operating MTPA) — a confident-but-wrong fuzzy match — because the
        # other (operating) Tangshan/PetroChina candidate lost its corroboration
        # to a bled owner cell. Dropping the cancelled shell lets that row fall to
        # report_only (a GIIGNL coverage note) instead of a false positive. Scoped
        # to status_set ⊆ {cancelled} so a terminal with any non-cancelled phase
        # (e.g. Saint John's operating import facility) is untouched.
        candidates = [
            (gk, gp) for gk, gp in gem_projects.items()
            if gk[0] == country_norm and gk[2] == section_type and gk in gem_only_keys
            and not (gp["status_set"] and gp["status_set"] <= {"cancelled"})
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
            term_owners, _, _ = parse_report_owner(rp["rows"][0].get("owner", ""))
            if term_owners:
                rp_first_owner = term_owners[0]
        for gk, gp in candidates:
            all_names = {gk[1]} | gp.get("aliases_norm", set())
            # Word-boundary (whole-token) containment, NOT raw character substring:
            # 'nansha' matches 'guangzhou nansha' but not the unrelated 'longkou
            # nanshan'. A short stripped GIIGNL name like 'nansha' (region tag
            # removed) would otherwise char-substring every longer name sharing
            # those letters and force a spurious ambiguous/match.
            substring = any(_word_boundary_substring(name_norm, n) for n in all_names)
            gp_tokens = gp.get("match_tokens")
            if gp_tokens is None:
                gp_tokens = set()
                for n in all_names:
                    gp_tokens |= _tokens_4plus(n)
            shared_tokens = rp_tokens & gp_tokens
            token_overlap = bool(shared_tokens)
            # Match GATING uses owner-level only — a shared ULTIMATE PARENT (a
            # national oil co, etc.) is too broad to IDENTIFY a terminal and would
            # spawn spurious candidates / ambiguity. Parents are folded in only for
            # the owner-DELTA reporting on a confirmed match (see _owner_alignment).
            owner_overlap = bool(rp_owners & gp["owners_set"])
            # An exact FSRU vessel-name match is a strong, near-unique corroborator
            # (GIIGNL identifies a floating terminal by its deployed vessel; GEM
            # tracks the same vessel in FloatingVesselName). It generates a
            # candidate ON ITS OWN — even when the site names don't substring and
            # owners/capacity diverge — so e.g. Sepetiba LNG ('LNGt Powership
            # Asia') binds to GEM 'Sepetiba Bay FSRU' (same vessel) and the
            # 0.5-vs-2.7 capacity gap surfaces as a real value-disagreement instead
            # of splitting into report_only + gem_only.
            vessel_match = _fsru_vessel_match(rp, gp)
            if (substring or (token_overlap and owner_overlap)
                    or len(shared_tokens) >= 2 or vessel_match):
                fuzzy_hits.append((gk, gp, {
                    "substring": substring,
                    "token_overlap": token_overlap,
                    "owner_overlap": owner_overlap,
                    "vessel_match": vessel_match,
                    "shared_token_count": len(shared_tokens),
                    "shared_tokens": sorted(shared_tokens),
                    "matched_against_names": sorted(all_names),
                }))

        # Vessel-match preference: an exact FSRU vessel-name match is far stronger
        # than a coincidental token/owner overlap, so if exactly one candidate
        # carries the GIIGNL row's vessel, it wins outright over non-vessel hits.
        # EXCEPTION — a vessel that RELOCATED: GEM keeps a superseded vessel on its
        # OLD (now non-operating) terminal, so a vessel match can point at the wrong
        # site. Deutsche Ostsee/Mukran: the "Neptune" FSRU moved from Lubmin (now
        # proposed/retired, 0 operating MTPA, still lists "Neptune") to Mukran (now
        # operating as "Energos Power", 9.92 MTPA, OtherNames "Mukran/Deutsche
        # Ostsee"). The GIIGNL row is OPERATING, so when the lone vessel hit has ZERO
        # operating capacity but another candidate operates, the vessel preference is
        # suppressed and the operating-capacity tie-break below picks the live site.
        if len(fuzzy_hits) > 1:
            vessel_hits = [h for h in fuzzy_hits if h[2].get("vessel_match")]
            if len(vessel_hits) == 1:
                v_op = vessel_hits[0][1].get("total_capacity_mtpa", 0.0) > 0
                others_op = any(
                    h[1].get("total_capacity_mtpa", 0.0) > 0
                    for h in fuzzy_hits if h is not vessel_hits[0]
                )
                if not (rp["total_capacity_mtpa"] > 0 and not v_op and others_op):
                    fuzzy_hits = vessel_hits

        # Numbered-sibling disambiguation: when the GIIGNL name ends in a numeral
        # (Map Ta Phut "Terminal 1"/"2") and the candidates are numbered siblings,
        # restrict to the candidate whose canonical name carries the SAME trailing
        # numeral. The number is the only distinguishing token but is too short for
        # _tokens_4plus, so substring (via a short OtherName like "Map Ta Phut")
        # and the ≥2-shared-token rule both fire for every sibling — this isolates
        # the right one. Fires only when exactly one candidate's name matches the
        # report numeral, so a non-numbered candidate set is untouched.
        if len(fuzzy_hits) > 1:
            rp_num = _trailing_numeral(name_norm)
            if rp_num:
                num_hits = [h for h in fuzzy_hits if _trailing_numeral(h[0][1]) == rp_num]
                if len(num_hits) == 1:
                    fuzzy_hits = num_hits

        # Same-base-name family disambiguation: if several candidates remain,
        # prefer the one whose GEM parenthetical owner identifies the GIIGNL row.
        # Two signals, in order: (1) the GEM paren-owner equals the GIIGNL row's
        # FIRST owner (Tianjin (PipeChina) vs (Sinopec) vs (Beijing Gas Group));
        # (2) failing that, the GEM paren-owner token APPEARS in the GIIGNL owner
        # text (any position). GIIGNL's owner cell is often noisy — Chaozhou's
        # "Sinopec 50%, Huaying 50% PipeChina (75%), Dalian" parses with Sinopec
        # first and fuses "Huaying" into "huaying 50% pipechina" — so exact
        # first-owner equality misses, but the operator token "huaying" still
        # uniquely picks GEM's "(Huaying)" sibling over "(Huafeng)".
        if len(fuzzy_hits) > 1 and rp_first_owner:
            owner_hits = [h for h in fuzzy_hits if h[1].get("paren_owner") == rp_first_owner]
            if len(owner_hits) == 1:
                fuzzy_hits = owner_hits
        if len(fuzzy_hits) > 1:
            # Tokens of every GIIGNL owner entity string ("huaying 50% pipechina"
            # → {huaying, pipechina}), used to spot a paren-owner anywhere in the
            # cell. Only fires when it isolates exactly one candidate.
            rp_owner_tokens = set()
            for ent in rp_owners:
                rp_owner_tokens |= _simple_tokens(ent)
            paren_hits = [
                h for h in fuzzy_hits
                if h[1].get("paren_owner") and h[1]["paren_owner"] in rp_owner_tokens]
            if len(paren_hits) == 1:
                fuzzy_hits = paren_hits

        # Operating-capacity disambiguation: a GIIGNL row is operating-only, so
        # among tied same-name candidates prefer the ONE that actually has
        # operating capacity. Rudong has four same-base siblings — three are
        # construction/proposed (0 operating MTPA) and only (PetroChina) operates
        # (10.0, matching GIIGNL's 10.0). Fires only when the GIIGNL row carries
        # capacity AND exactly one candidate has any operating capacity — the
        # other zero-operating siblings can't be what GIIGNL lists as operating.
        if len(fuzzy_hits) > 1 and rp["total_capacity_mtpa"] > 0:
            op_hits = [h for h in fuzzy_hits if h[1].get("total_capacity_mtpa", 0.0) > 0]
            if len(op_hits) == 1:
                fuzzy_hits = op_hits

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
            owner_overlap_f, owner_only_report, owner_only_gem, owner_via_parent = _owner_alignment(
                rp["owners_set"], gp["owners_set"], gp["parents_set"])
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
                "owners_overlap": sorted(owner_overlap_f),
                "owners_report_only": sorted(owner_only_report),
                "owners_gem_only": sorted(owner_only_gem),
                "owners_matched_via_gem_parent": sorted(owner_via_parent),
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
        rec = {
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
        }
        # An FSRU absent from GIIGNL's country regas tables may still be in the
        # separate FSRU fleet table — GIIGNL often lists floating terminals only
        # there. Cross-check it before declaring "the report doesn't list it".
        fleet_hit = _fleet_match_for_gem_only(gp, fsru_fleet_index)
        if fleet_hit:
            rec["report_fleet_match"] = {
                "location_site": fleet_hit["location_site"],
                "vessel_name": fleet_hit["vessel_name"],
            }
            rec["note"] = (
                f"NOT a country-table omission to investigate — GIIGNL's FSRU "
                f"fleet table DOES list this (vessel '{fleet_hit['vessel_name']}' "
                f"at '{fleet_hit['location_site']}'); only the per-country regas "
                f"tables skip it, as GIIGNL routinely does for floating terminals. "
                f"Confirm GEM capacity/status against the giignl_fsru_fleet sheet.")
        else:
            rec["note"] = (
                "GEM has this as operating but the report doesn't list it; "
                "investigate whether report missed it "
                "(small/non-member/sanctioned) OR GEM has it wrong")
        gem_only.append(rec)

    # Attach the GEM capacity provenance to every match, so the build-script verdict
    # logic can fire the "GIIGNL <year> edition superseded by 2026" rule (and route
    # non-GIIGNL-sourced conflicts to research). Keyed (terminal_id, section_type),
    # unique per GEM project (a liq+regas terminal is two projects sharing one id).
    gp_by_tid_section = {
        (gp["terminal_id"], gp["section_type"]): gp for gp in gem_projects.values()}
    for m in matches + fuzzy_matches:
        gp = gp_by_tid_section.get((m["gem_terminal_id"], m["section_type_gem"]))
        m["gem_capacity_source"] = _gem_capacity_source_for_project(gp)
        # Non-operating phases + researcher notes of the SAME GEM project, so the
        # verdict layer can recognize the "GIIGNL counts capacity GEM deliberately
        # holds as non-operating" pattern (Corpus Christi) and not blind-bump GEM's
        # operating capacity, AND can quote the researcher's deliberate-divergence
        # note inline. Attached to project-level matches only (gp is the whole
        # project); a unit_designator match has no whole-project non-op context to
        # mislead it, but attaching the explanation is harmless there too.
        m["gem_nonop_explanation"] = _gem_nonop_capacity_explanation(gp)

    # Non-operating units of MATCHED projects. GIIGNL's tables are operating-only,
    # so each defaults to is_gem_only=True ("GEM has, GIIGNL doesn't") UNLESS the
    # unit was aligned to a report row, OR the §3.2.1 narrative-prose pass annotates
    # giignl_narrative_mention downstream (a confirmed forward phase, no conflict —
    # Reconciliation SOP §5.7). Scoped to matched projects only (gem-only projects
    # live wholly in the routing sheet).
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
                # None (blank cell) when GEM has NO capacity value for this unit —
                # never conflate unknown with a genuine 0.
                "capacity_mtpa": (round(u["capacity_mtpa"], 2)
                                  if u.get("capacity_known", True) else None),
                "start_year": u["start_year"],
                "section_type": gp["section_type"],
                "owners": sorted(u["owners_set"]),
                "researcher_notes": u.get("researcher_notes", ""),
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
    p.add_argument("--fsru-fleet", default=None,
                   help="Path to the parsed GIIGNL FSRU-fleet JSON (from "
                        "giignl_fsru_fleet.py). Defaults to giignl_fsru_fleet.json "
                        "next to the extracted CSV, if present. Lets the gem_only "
                        "pass recognize FSRUs GIIGNL lists only in the fleet table.")
    p.add_argument("--match-overrides", default=None,
                   help="Path to agent-authored match-override JSON (pins a "
                        "GIIGNL row to a specific GEM terminal by id, overriding "
                        "a wrong same-token exact match). Defaults to "
                        "staged_match_overrides.json next to the extracted CSV.")
    # Default matches the filename every SOP/CLAUDE.md command passes and that
    # build_review_package.py looks for (it keeps a report_diff.json fallback too).
    p.add_argument("--output", default="./giignl_diff.json")
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

    # Default the FSRU-fleet path to a file beside the extracted CSV.
    fleet_path = args.fsru_fleet
    if fleet_path is None:
        guess = Path(args.extracted).with_name("giignl_fsru_fleet.json")
        fleet_path = str(guess) if guess.exists() else None
    fsru_fleet_index = _build_fsru_fleet_index(fleet_path)
    if fsru_fleet_index:
        n_vessels = sum(len(v) for v in fsru_fleet_index.values())
        print(f"  Loaded {n_vessels} FSRU-fleet deployment(s) for gem_only "
              f"cross-check ({fleet_path})")

    # Default the match-overrides path to a file beside the extracted CSV.
    override_path = args.match_overrides
    if override_path is None:
        guess = Path(args.extracted).with_name("staged_match_overrides.json")
        override_path = str(guess) if guess.exists() else None
    match_overrides = _load_match_overrides(override_path)
    if match_overrides:
        print(f"  Loaded {len(match_overrides)} match override(s) ({override_path})")

    gem_projects, alias_map, collision_regas = _build_gem_project_table(args.gem_csv)
    diff = _classify(report_rows, gem_projects, alias_map=alias_map,
                     collision_regas=collision_regas,
                     prose_corrections=prose_corrections,
                     fsru_fleet_index=fsru_fleet_index,
                     match_overrides=match_overrides)
    diff["report_type"] = args.report
    diff["extracted_csv"] = args.extracted
    diff["gem_csv"] = args.gem_csv
    diff["prose_corrections_path"] = prose_path or ""
    diff["fsru_fleet_path"] = fleet_path or ""
    diff["match_overrides_path"] = override_path or ""

    Path(args.output).write_text(json.dumps(diff, indent=2, default=str))

    print(f"\n  Report: {args.report.upper()}")
    print(f"  Stats:")
    for k, v in diff["stats"].items():
        print(f"    {k:35} {v}")
    print(f"\n  Saved diff to {args.output}")


if __name__ == "__main__":
    main()
