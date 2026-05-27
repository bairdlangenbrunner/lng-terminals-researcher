# Lifecycle Rules — Status Timeline State Machine

The rules for how a GEM LNG terminal unit moves between lifecycle states, how the timeline is constructed and read, and how current status is derived from a timeline. This file is operational scaffolding; the methodology doc is the authoritative source. Where this file and the methodology disagree, the methodology wins and this file gets updated.

## The eight statuses

Per the methodology, every LNG unit has exactly one current status drawn from this set:

| Status | Meaning | Substatus options |
|---|---|---|
| `proposed` | Announced or in pre-construction development | (blank), `actual` (rare) |
| `construction` | Site prep or active building underway | `actual` |
| `operating` | Commissioned or in commercial operation | `actual` |
| `idled` | Operated once, now sitting unused (typically short-term) | `actual` |
| `mothballed` | Formally taken offline, not yet retired | `actual` |
| `retired` | Permanently taken out of operation | `actual` |
| `shelved` | Sponsor publicly paused, OR no updates for 2-4 years | `confirmed`, `inferred 2 y` |
| `cancelled` | Sponsor publicly cancelled, OR no updates for 4+ years | `confirmed`, `inferred 4 y`, `actual` (rare) |

**`FID` is not a status.** It's a milestone that lives in the timeline as a separate entry type with its own substatus (`actual` or `planned`).

### Substatus semantics

Substatus has two distinct meanings depending on Status:

1. **Active statuses** (`construction`, `operating`, `idled`, `mothballed`, `retired`) plus `FID`: `actual` vs `planned`. The export only ever emits `actual` because it shows current status; `planned` entries live in the timeline.
2. **Dormancy statuses** (`shelved`, `cancelled`): `confirmed` vs `inferred 2 y` / `inferred 4 y`. Confirmed = the sponsor announced the pause/cancellation. Inferred = no updates for the threshold period.

`proposed` has no substatus (blank); the rare `proposed` + `actual` cases are likely data-entry artifacts and should be flagged in `qa_review`.

## The timeline model

A unit's status timeline is an **ordered list of entries**, each with:

- `status` — one of the eight statuses, or `FID`
- `sub_status` — `actual` / `planned` / `confirmed` / `inferred 2 y` / `inferred 4 y` / blank
- `year` — 4-digit year
- `part_of_year` — month, quarter, half, or blank
- `notes` — free text, optional
- (hidden) `data_entry_timestamp` — when the entry was added

**The timeline is append-only.** New developments add new entries; they do NOT modify or delete prior entries. The only exception per the methodology FAQ is correcting genuine errors in past entries.

**Ordering is by stage of development**, not by `data_entry_timestamp`. Researchers can drag-and-drop to re-order. New planned entries usually go after their corresponding actual milestone; new actuals appended to the bottom.

### Why ordering matters

The current status of a unit is derived as: **the status closest to the bottom of the timeline, excluding entries with substatus `planned` and excluding `FID` entries.**

A worked example from the methodology:

```
Proposed (2023)
Construction (planned, 2025)
Operating (planned, 2026)
Construction (actual, 2025)
FID (actual, 2025)
Operating (planned, 2027)
```

Current status = `construction` (the only non-planned non-FID entry below the proposal). Future revisions (e.g. operation actually starts in 2027) append a new `Operating (actual, 2027)` entry at the bottom, which then becomes the current status.

## Anchor years vs timeline (the export gap)

**The CSV export does NOT contain the timeline.** It contains:

- The current status and substatus (one each, current value)
- Eleven "anchor year" columns that flatten the most important year values:
  - `ProposalYear`, `ProposalMonth` — earliest proposed entry's year
  - `ConstructionYear`, `ConstructionMonth` — first construction (actual) entry's year
  - `OriginalPlannedStartYear` — first operating (planned) entry's year
  - `LatestPlannedStartYear` — most recent operating (planned) entry's year
  - `ActualStartYear`, `ActualStartMonth` — first operating (actual) entry's year
  - `ActualStartYear2`, `ActualStartYear3` — used for restarts after idling (rare)
  - `ShelvedYear` — shelved entry's year
  - `CancelledYear` — cancelled entry's year
  - `StopYear` — when operation stopped (any of idled, mothballed, retired); `PlannedStopYear` for planned
  - `FIDYear` — FID entry's year (`actual` or `planned`, see ambiguity note below)

**Implication for all SOPs:** any status timeline change requires pulling the existing timeline first with `fetch_timeline.py <UnitID>`. The export alone cannot tell you:
- Whether a status transition was previously recorded as planned
- The order of entries
- Per-entry notes
- The data-entry timestamps

Working blind from the export risks duplicate entries, incorrect ordering, and lost methodology-required context.

## Legal state transitions

The methodology doesn't explicitly enumerate legal transitions, but reading the status definitions in order yields the following graph. The build script and `status_timeline.py` use this for validation.

```
proposed ─┬─→ construction ─→ operating ─┬─→ idled ─┬─→ operating  (restart)
          │                               │          ├─→ mothballed
          │                               │          └─→ retired
          ├─→ shelved ─→ cancelled        ├─→ mothballed ─→ retired
          └─→ cancelled                   └─→ retired
                                          │
                                          (very rarely: → shelved or cancelled
                                           if a project is abandoned mid-operation;
                                           see "Edge cases" below)

proposed ←─ (no transition from any other state to proposed under normal rules;
             see "Dead-and-revived" edge case below)
```

### Strict transitions

- `proposed` can transition to: `construction`, `shelved`, `cancelled`
- `construction` can transition to: `operating`, `shelved` (rare — methodology: "shelved if entered construction but never went operating")
- `operating` can transition to: `idled`, `mothballed`, `retired`
- `idled` can transition to: `operating`, `mothballed`, `retired`
- `mothballed` can transition to: `operating` (rare), `retired`
- `retired` is terminal (no outbound transitions)
- `shelved` can transition to: `cancelled` (either confirmed or inferred), `construction` (rare revival), `operating` (very rare)
- `cancelled` is normally terminal, but see "Dead-and-revived" below

### Forbidden transitions (flag in `qa_review`)

- Any transition INTO `proposed` from another active state — proposed projects that revive are usually a new unit (see "Dead-and-revived")
- `retired` → anything (retirement is permanent per the methodology)
- Any direct `construction` → `retired` skipping `operating`
- Any direct `operating` → `cancelled` (operating projects that stop get `idled`/`mothballed`/`retired`, not `cancelled`)

## Anchor year invariants

Year values must be consistent with each other and with the current status. The build script enforces these on write; `stale_sweep.py` flags violations on read.

For any unit:

- `ProposalYear ≤ ConstructionYear ≤ ActualStartYear` when all three are populated
- `ConstructionYear ≤ LatestPlannedStartYear` when both are populated
- `ActualStartYear ≤ StopYear` when both are populated
- `OriginalPlannedStartYear ≤ LatestPlannedStartYear` (the latest planned should not be earlier than the original)
- `ShelvedYear ≤ CancelledYear` when both are populated (a project shelved before cancellation)

By current status:

- **`proposed`**: `ProposalYear` should be populated. `ConstructionYear`, `ActualStartYear`, `ShelvedYear`, `CancelledYear`, `StopYear` should be blank.
- **`construction`**: `ProposalYear` and `ConstructionYear` should be populated. `ActualStartYear`, `ShelvedYear`, `CancelledYear`, `StopYear` should be blank.
- **`operating`**: `ActualStartYear` should be populated. `ShelvedYear`, `CancelledYear`, `StopYear` should be blank.
- **`idled` / `mothballed` / `retired`**: `ActualStartYear` and `StopYear` should be populated. `ShelvedYear`, `CancelledYear` should be blank.
- **`shelved`**: `ShelvedYear` should be populated. `CancelledYear`, `StopYear` should be blank (unless the project was operating before being shelved, which is rare).
- **`cancelled`**: `CancelledYear` should be populated.

### Reality check: invariants are violated in the existing data

The May 2026 export reveals that "should be populated" is aspirational, not enforced:

- 28 `operating` units have no `ActualStartYear`
- 48 `proposed` units have no `ProposalYear`
- 29 `cancelled` units have no `CancelledYear`
- 10 `shelved` units have no `ShelvedYear`
- 3 `construction` units have no `ConstructionYear`

These are not bugs in the database — they're historical records where the anchor year wasn't captured during data entry. **Treat invariant violations as `qa_review` flags, not as hard errors that block a batch.** Backfilling a missing anchor year is a legitimate update.

### FIDStatus / FIDYear ambiguity

`FIDStatus=Pre-FID` with `FIDYear` populated appears 87 times in the export. The methodology says FIDYear should be set only with explicit reporting of an actual FID, so `Pre-FID` + populated `FIDYear` is ambiguous. Most likely meaning: "year of expected/planned FID." When updating these units:

- If the sponsor has since taken FID, update to `FIDStatus=FID` with the actual year
- If the planned FID year has passed without FID, leave the FIDStatus alone but flag in `qa_review` — a project that missed its planned FID is a candidate for stale-sweep
- Never *set* a `Pre-FID` + `FIDYear` combination on a new entry; it's only acceptable as a legacy state

## Dormancy thresholds (the stale-sweep rules)

Per the methodology:

- A `proposed`, `construction`, `idled`, or `mothballed` unit with no project updates for **2 years** → candidate for `inferred shelved`
- A `shelved` (`confirmed` or `inferred 2 y`) unit with no project updates for **2 more years** (4 years total since last activity) → candidate for `inferred cancelled`

The "no updates" clock starts from the most recent of: the last status timeline entry's year, or the LastUpdated field on the unit (whichever is more recent and trustworthy). `stale_sweep.py` uses `LastUpdated` as the primary signal because it's mechanically tractable.

### Adding an inferred entry

When `stale_sweep.py` flags a unit:

1. Pull the existing timeline with `fetch_timeline.py`
2. Confirm via research that there really are no recent updates (sometimes a unit is stale because of researcher capacity, not because the project is dormant — a quick news search resolves this)
3. If genuinely dormant, append a new timeline entry:
   - Status: `shelved` or `cancelled`
   - Substatus: `inferred 2 y` or `inferred 4 y`
   - Year: the current year (the year the inference is being made)
   - Notes: a brief explanation including the "last known activity" date
   - Datasource: per the methodology FAQ, the datasource for `inferred shelved` and the subsequent `inferred cancelled` can be the same source — the one originally cited for the latest active-status entry

### Shelved → Cancelled escalation

The methodology FAQ specifically permits: a unit confirmed `shelved` with no updates for 2+ more years can be labeled `confirmed cancelled` (not `inferred`) using the same source. This is a deliberate departure from the literal "inferred from time" rule — the project is treated as confirmed cancelled because the prior confirmed-shelved status carries forward the sponsor intent.

## Edge cases

### Dead-and-revived proposal

A previously cancelled or shelved proposal re-emerges. Per the methodology FAQ:

- **Same fundamental proposal** (same sponsor, same site, same approximate design): re-use the existing unit. Add a new `proposed` entry to the timeline. Do NOT delete the prior cancelled/shelved entries.
- **Significantly different proposal** (different sponsor, different design, even if same site): create a new unit. The old unit stays cancelled.

This is one of the few cases where `proposed` is a valid transition destination in the timeline (though only as a new entry appended to a timeline that may already contain a later `cancelled`).

### Project shelved during construction

The methodology explicitly notes: "A project is also shelved if it has entered construction but never formally goes into operation." So `construction` → `shelved` is legal even though it's unusual. Example given: Nord Stream 2 (a pipeline, not LNG, but illustrative).

### Project with multiple operating start dates

Some units restart after a period of idling — captured in `ActualStartYear2` and `ActualStartYear3`. Only 3 units use `ActualStartYear2` and 0 use `ActualStartYear3` in the current export, so this is rare but real. The timeline gets a new `operating (actual, YYYY)` entry; the `ActualStartYear2` field gets updated; `StopYear` should remain populated from the prior stop.

### FID without project status change

Taking FID does not change the unit's Status — a unit can be `construction` and have `FIDStatus=FID` with `FIDYear` set, but Status stays `construction` (or whatever it was). FID is recorded as a separate timeline entry but doesn't affect status derivation.

### Multi-unit project with units at different statuses

Each unit has its own status timeline. A project may have:
- Train 1: `operating`
- Train 2: `construction`
- Train 3: `proposed`
- Train 4: `cancelled`

This is normal. The project-level rollups (`TotImportLNGTerminalCapacityinMtpa` etc.) summarize operating capacity differently from total proposed-or-greater capacity — the build script doesn't compute these (they're read-only DB-side), but staging xlsx outputs should make per-unit status differences visible in the `updates` sheet.

### Operating unit that's part of a permanent-replacement scheme

Per the methodology, the `TempFacility` field marks units as `interim` or `permanent replacement`. Lifecycle handling:
- The interim FSRU usually goes through `operating` → `idled` → `retired` as the permanent terminal commissions
- The permanent terminal follows the normal `proposed` → `construction` → `operating` arc
- Both units share an `AssociatedTerminals` link; the FSRU sync rule may apply if the interim is an FSRU vessel

## How the build script uses these rules

Every status change staged to the xlsx goes through `status_timeline.py`, which validates:

1. The proposed new entry is a legal transition from the prior current status
2. Anchor year invariants will not be violated after the entry is applied
3. If substatus is `inferred 2 y` or `inferred 4 y`, the timeline genuinely supports the inference (no recent active entries)
4. If status is `cancelled` and substatus is `confirmed` via the shelved→cancelled escalation, the prior `shelved` entry exists in the timeline

Failures → the entry is staged with a warning in `qa_review`, but not blocked. Human review at xlsx-application time makes the final call. The script is a guardrail, not a gate.

## Quick-reference card

For day-of-batch consultation without re-reading this whole file:

| If you're doing... | Read this section |
|---|---|
| Adding a new proposed unit | "The eight statuses" + "Anchor year invariants" → proposed row |
| Confirming a status change (e.g. proposed → construction) | "Legal state transitions" |
| Adding an inferred shelved/cancelled | "Dormancy thresholds" |
| Resolving a dead-and-revived case | "Edge cases" → first bullet |
| FID milestone update | "Substatus semantics" + "FIDStatus/FIDYear ambiguity" |
| FSRU vessel swap-out on a terminal | "Edge cases" → permanent-replacement scheme + the FSRU sync rule in CLAUDE.md |
| Multi-unit project with mixed statuses | "Edge cases" → multi-unit |
