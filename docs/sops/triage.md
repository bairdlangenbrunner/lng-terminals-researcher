# LNG Terminals Triage SOP

Last revised: 2026-05 (rev 1, initial draft)

Operational rules for deciding what to work on in a given batch. Triage runs first in any quarterly cycle and feeds scope decisions into Update, Discovery, and Reconciliation batches.

Triage's output is a **memo** (markdown, not xlsx) recommending batch composition. The user makes the final scoping decision; triage informs but doesn't decide. This is intentionally the lightest of the four SOPs — most decisions live with the user.

## §1 When to run this SOP

Trigger conditions:
- Start of a quarterly cycle ("plan Q3", "what should we work on this quarter")
- User asks "what's stale", "where are the gaps", "what hasn't been touched"
- Before a long break (vacation, project pause) — to capture the state and any urgent items
- After a major industry event (FID wave, sanctions change, GIIGNL release) where the next batch should react to it
- Whenever the user is unsure what the right batch composition is

Triage is NOT a precondition for every batch. Routine user requests like "fill blank Capacity refs for the EU rows" don't need triage first — they specify scope directly. Triage is for the open-ended "what next?" cases.

## §2 What triage produces

A single markdown memo with five sections:

1. **Stale-sweep summary** — counts and notable patterns from `stale_sweep.py`
2. **Recent activity scan** — countries with notable news in the last quarter that may need attention
3. **Reconciliation backlog** — any unprocessed findings from prior reconciliation batches
4. **GIIGNL/IGU report status** — whether a fresh annual report has dropped since the last reconciliation
5. **Recommended batch composition** — 3-5 specific options the user can pick from, each scoped concretely

The memo gets saved to `../batches/triage_<YYYYMMDD>.md` and presented to the user. No xlsx is produced by triage itself.

## §3 Triage inputs

Triage pulls signals from five sources, in order:

### §3.1 Stale-sweep results

`python stale_sweep.py --output stale_sweep.json` produces a flagged-units list per `docs/reference/lifecycle_rules.md`:

- `proposed` / `construction` / `idled` / `mothballed` units with no project updates for 2 years → candidates for `inferred shelved`
- `shelved` units (confirmed or inferred 2y) with no updates for 2 more years → candidates for `inferred cancelled`
- `operating` units with `LastUpdated > 18 months` → due for routine refresh (lower priority)
- `proposed` units with `LatestPlannedStartYear < current_year - 1` → planned start date has slipped past, worth checking status

The triage memo summarizes counts by category and country, and flags concentrations (e.g. "Italy has 8 stale `proposed` units — concentrated enough to scope a single-country update batch").

### §3.2 Recent activity scan

Lightweight scan of the past quarter's LNG news. Not a full discovery sweep — just enough to identify countries/sponsors with notable activity that suggests an Update or Discovery batch should be scoped there.

Sources:
- LNG Prime, Reuters Energy, S&P Global Commodity Insights — last 90 days of headlines
- Major sponsor IR announcements (Cheniere, Venture Global, TotalEnergies, QatarEnergy, etc.) — last quarter
- Regulator activity for top-coverage countries (FERC orders, EU PCI announcements, etc.)

The scan output is a list of countries / sponsors / specific projects with notable activity, with brief notes. NOT a full source roll-up — that's Discovery's job. Triage's role is "here's where activity is happening; consider scoping a batch around it."

Per the carrier project's discovery model, this is essentially a Ring B sweep at the triage level — broad and shallow, to point Discovery at high-yield areas.

### §3.3 Reconciliation backlog

Check for `giignl_to_action` items from prior reconciliation batches that haven't been processed:
- Look for the most recent reconciliation batch xlsx in `../batches/` (or wherever the user keeps the batch archive)
- Count items in `giignl_to_action` sheet that haven't been routed to a subsequent Update or Discovery batch

If items are unprocessed, triage's recommended composition should include processing them — they're partly pre-done research.

### §3.4 Fresh annual report check

Has GIIGNL (or eventually IGU) published a new edition since the last reconciliation?

- Check project files for any new `GIIGNL*.pdf` or `IGU*.pdf` not previously processed
- Check the GIIGNL website (`giignl.org`) for current edition year
- Check the IGU website (`igu.org/world-lng-report/`) for current edition year

If yes, recommend a reconciliation batch as the first item — it's the most upstream workflow and feeds into Update/Discovery.

### §3.5 User priorities

The five most important inputs are still the user's own — what GEM team commitments are upcoming, what publications need data freshness by what dates, what specific projects or regions are getting external scrutiny.

The triage memo always closes by asking the user to flag any priorities the agent doesn't know about. The recommended batch composition is provisional until the user confirms.

## §4 The recommended batch composition

For each cycle, propose 3-5 batch options. Each option specifies:

- **Workflow** — Update, Discovery, Reconciliation, or a mix
- **Scope** — specific countries / regions / sponsor / unit list
- **Estimated effort** — light (a few hours), medium (a day), large (multi-day or multi-batch)
- **Why this option** — what triage signals justify it
- **Dependencies** — anything that needs to happen first (e.g. "do reconciliation first if processing GIIGNL backlog")

A typical recommendation set might look like:

```
Option 1 (recommended first): Reconciliation against GIIGNL 2026
  - Workflow: Reconciliation
  - Scope: full GIIGNL diff
  - Effort: medium (1-2 days)
  - Why: GIIGNL 2026 published in June, not yet processed; reconciliation feeds
    candidates into subsequent Update/Discovery batches
  - Dependencies: none

Option 2: Update — Japan terminals (FSRU activity)
  - Workflow: Update
  - Scope: all Japan operating + idled units (51 terminals, ~73 units)
  - Effort: medium (1 day)
  - Why: METI announced 3 FSRU project changes in Q1; activity scan shows
    14 trade press articles on Japanese LNG in last quarter
  - Dependencies: ideally after Option 1 (reconciliation may surface Japan findings)

Option 3: Stale-sweep processing — Italy
  - Workflow: Update (stale-driven)
  - Scope: 8 Italy proposed units flagged stale by sweep (>2 years no updates)
  - Effort: light (half day)
  - Why: concentrated stale cluster; processing as a batch is more efficient
    than individual reviews
  - Dependencies: none

Option 4: Discovery — Southeast Asia (catch-up)
  - Workflow: Discovery
  - Scope: Vietnam, Philippines, Thailand, Indonesia
  - Effort: large (multi-day)
  - Why: region last had a discovery sweep 4 quarters ago; activity scan shows
    multiple new project announcements (3 Vietnamese FSRU proposals, Philippines
    LNG round); GEM coverage likely behind
  - Dependencies: none, but consider deferring if reconciliation/update batches
    will consume the cycle's bandwidth

Option 5: Capacity [ref]-fill — global blank-fill batch
  - Workflow: Update ([ref]-fill sub-type)
  - Scope: all rows with blank Capacity [ref] AND populated Capacity (1,083 rows)
  - Effort: large (multi-batch)
  - Why: Capacity [ref] is 86% blank globally — highest-yield [ref]-fill target
    from schema analysis; batchable by region
  - Dependencies: none; can be split across multiple cycles
```

The user picks one or more options (or proposes something else). Triage doesn't pick for them.

## §5 Workflow (linear)

1. `python pull_gem_db.py` → fresh CSV. Triage needs current data to compute stale flags accurately.
2. `python stale_sweep.py --output stale_sweep.json` (§3.1)
3. Activity scan (§3.2) — typically 30-60 minutes of broad search + summarization
4. Reconciliation backlog check (§3.3) — look for prior batch outputs with unprocessed items
5. Fresh report check (§3.4) — search project files + check report publishers' sites
6. Draft the triage memo with sections per §2
7. Save to `../batches/triage_<YYYYMMDD>.md`
8. `present_files` the memo
9. **Stop and ask the user** which option(s) to pursue

Triage doesn't run any other batch's workflow. After the user picks, the chosen Update/Discovery/Reconciliation SOP takes over.

## §6 What triage does NOT do

- **No xlsx output.** Triage produces a memo. The xlsx scaffolding is only invoked by Update/Discovery/Reconciliation batches.
- **No URL verification.** The activity scan cites sources, but triage isn't staging citations for the database — verification happens when the chosen batch's SOP runs.
- **No entity lookups.** Same reason.
- **No source-tier discipline.** The activity scan is allowed to use Tier 3 sources (regional press, conference materials) because triage is about pointing the next batch, not establishing facts.
- **No decisions for the user.** Triage proposes; user decides.

## §7 Hard rules

- **Pull a fresh GEM CSV at the start of every triage run** — stale-sweep accuracy depends on current `LastUpdated` values.
- **Always include a recommendation about reconciliation when a fresh report exists** — easy to forget; reconciliation feeds everything else.
- **Always present the memo and stop** — don't auto-roll into a batch even if one option seems obviously right. The user's confirmation is the gate.
- **No batch outputs from triage** — if the user wants to combine "triage and then immediately do option 2," that's a two-batch sequence, not a single batch.

## §8 Pause-and-ask triggers

Triage is itself a pause-and-ask, so escalation triggers are narrower. But:

- If stale-sweep shows >100 units due for inferred shelved/cancelled, flag this — it's a sign the dormancy thresholds have caught up with a large backlog and the user may want to scope a dedicated stale-sweep cycle rather than mix it into regular batches.
- If the activity scan turns up something obviously urgent (major sponsor bankruptcy, sanctions change with immediate effect on multiple projects), highlight it as a "stop other work" item rather than a routine option.
- If the GEM CSV pull fails repeatedly or shows obvious schema drift, triage stops and the user is asked to address the data-source issue before any other batch is scoped.

---

## Quick-reference card

| Input | Source | Triage uses to... |
|---|---|---|
| Stale-sweep | `stale_sweep.py` | Identify concentrated dormancy candidates and routine-refresh queue |
| Activity scan | LNG Prime, Reuters, sponsor IR (last 90 days) | Identify countries/sponsors needing Discovery or Update |
| Reconciliation backlog | Prior batch xlsx `giignl_to_action` sheets | Surface partly-done research that should land in next batch |
| Fresh annual report | Project files + giignl.org/igu.org | Trigger reconciliation recommendation |
| User priorities | Direct ask | Validate or override agent's recommendations |

| Triage output | Where |
|---|---|
| Markdown memo with recommendations | `../batches/triage_<YYYYMMDD>.md` |
| (No xlsx) | Triage never produces a workbook |
