export const meta = {
  name: 'lng-devpipeline-exhaustive',
  description: 'Exhaustive re-verify of dev-pipeline (proposed/construction/shelved) LNG units, one subagent per country',
  phases: [{ title: 'Reverify' }],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
const ROOT = '/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher'
const R = A.region
const BASE = `${ROOT}/batches/staging/devpipeline_exhaustive`

function prompt(g) {
  return `Exhaustive dev-pipeline re-verify — GEM LNG terminals, ONE country. A human reviews the staged xlsx; never touch the live DB.

REPO = ${ROOT}

FIRST read and follow EXACTLY this brief (defines your task, the rules, the output record schema, and the done-marker):
  ${BASE}/_devpipeline_exhaustive_brief.md

Your assignment:
- REGION: ${R}
- COUNTRY: ${g.country}
- SLUG: ${g.slug}
- WORKLIST (your units + per-cell cells_to_reverify + blank_refs_with_data):
    ${BASE}/${R}/${g.slug}.worklist.json
- Write each non-empty finding list to ${BASE}/${R}/${g.slug}.<type>.json  (types: updates,qa,wiki,entity,monitor)
- Write ${BASE}/${R}/${g.slug}.done.json LAST (the resume marker).
- GEM export (context only; worklist already has current values): ${ROOT}/scripts/gem_export.csv

Execution notes:
- Load WebSearch / WebFetch via ToolSearch before researching.
- EXHAUSTIVE: re-verify EVERY cell in cells_to_reverify for EVERY unit; fill blank_refs_with_data where a
  real (non-"unknown"/"--") data value can be corroborated.
- Verify EVERY url (existing GEM refs in ref_current AND new ones) with:
    python ${ROOT}/scripts/url_verifier.py "<url>" "<the actual cell value>"
  Only PASSing URLs go in records. Pile ALL PASSing URLs for a value into ref_urls — the more the merrier.
- Unchanged-and-reconfirmed cell -> confidence "blue", new_value = old_value, ref_urls = existing-still-PASS + new.
- A verified DIFFERENT value -> green (primary/regulatory or >=2 independent) / yellow (single non-primary).
- Cannot corroborate off-GEM -> do NOT stage a value; add a qa entry (category unsourced_after_reverify).
- Status CHANGE -> qa note (category status_timeline); do NOT stage a Status field edit (fetch_timeline is DOWN).
- NEVER cite gem.wiki / globalenergymonitor.org or a GEM-derivative; chase the primary source.
- Copy ref_field from each worklist cell verbatim (handles irregular pairings). Use absolute paths everywhere.

RETURN ONLY the terse <=12-line summary the brief specifies. Do NOT paste records.`
}

const tasks = A.groups.map(g => ({ label: `dpx:${g.slug}`, prompt: prompt(g) }))
phase('Reverify')
log(`${R}: exhaustive dev-pipeline re-verify across ${tasks.length} countries`)
const results = await parallel(tasks.map(t => () =>
  agent(t.prompt, { label: t.label, phase: 'Reverify' }).then(s => ({ label: t.label, summary: s }))
))
const ok = results.filter(Boolean)
const missing = tasks.filter((t, i) => !results[i]).map(t => t.label)
log(`${R}: ${ok.length}/${tasks.length} returned${missing.length ? '; MISSING: ' + missing.join(', ') : ''}`)
return { region: R, dispatched: tasks.length, returned: ok.length, missing, summaries: ok }
