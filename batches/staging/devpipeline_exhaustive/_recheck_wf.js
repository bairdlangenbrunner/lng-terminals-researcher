export const meta = {
  name: 'lng-devpipeline-recheck',
  description: 'Re-check pass: recover bot-blocked refs via Wayback, resolve unsourced values (change or green-empty delete), one subagent per country',
  phases: [{ title: 'Recheck' }],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
const ROOT = '/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher'
const R = A.region
const BASE = `${ROOT}/batches/staging/devpipeline_exhaustive`

function prompt(g) {
  return `Dev-pipeline RE-CHECK pass — GEM LNG terminals, ONE country. A human reviews the staged xlsx; never touch the live DB.

REPO = ${ROOT}

FIRST read and follow EXACTLY this brief (defines the task, rules, output schema, and done-marker):
  ${BASE}/_recheck_brief.md

Your assignment:
- REGION: ${R}
- COUNTRY: ${g.country}
- SLUG: ${g.slug}
- WORKLIST (units + per-cell ref_current/old_value/ref_field): ${BASE}/${R}/${g.slug}.worklist.json
- FIRST-PASS UPDATES (read existing ref_urls to MERGE, don't drop): ${BASE}/${R}/${g.slug}.updates.json
- FIRST-PASS QA (find unsourced_after_reverify + dead/bot-block notes): ${BASE}/${R}/${g.slug}.qa.json
- Write ${BASE}/${R}/${g.slug}.recheck.json  (object: update_overrides, qa_add, qa_resolved, summary)
- Write ${BASE}/${R}/${g.slug}.recheck.done.json LAST (the resume marker).
- GEM export (context): ${ROOT}/scripts/gem_export.csv

Execution notes:
- Load WebSearch / WebFetch via ToolSearch before researching.
- TASK 1 — for EVERY dropped/dead 401/403/000/202 ref: re-try url_verifier; if still bot-blocked, check Wayback
  ( curl -s "http://archive.org/wayback/available?url=<URL>" -> archived_snapshots.closest.url ) and
  url_verifier the cell's value against the SNAPSHOT. Snapshot PASS => recover (the LIVE url is the [ref];
  note "bot-blocked; confirmed via Wayback" in source_notes). An override that adds a recovered ref MUST carry
  the cell's FULL ref_urls = its already-staged URLs (from <slug>.updates.json) PLUS the recovered one.
- TASK 2 — for each genuinely unsourced FACTUAL value: search elsewhere. Different corroborated value => CHANGE
  (green/yellow). Nothing anywhere AND existing value unsupportable => DELETE: {delete:true, new_value:"",
  confidence:"green", ref_urls:[]} (clears the cell + its [ref]). Delete a multi-field value as a SET.
  DO NOT delete Lat/Long/Accuracy, GEM-inferred shelved-status metadata, or "unknown"/"--"/"TBD" placeholders.
- url_verifier substring-matches: put '$' in dollar tokens; eyeball the sentence before trusting a numeric PASS.
- NEVER cite gem.wiki / globalenergymonitor.org or a GEM-derivative. >=2 independent URLs per staged value.
- Copy ref_field verbatim. Use absolute paths everywhere.

RETURN ONLY the terse <=10-line summary the brief specifies. Do NOT paste records.`
}

const tasks = A.groups.map(g => ({ label: `rc:${g.slug}`, prompt: prompt(g) }))
phase('Recheck')
log(`${R}: re-check (Wayback recovery + unsourced resolution) across ${tasks.length} countries`)
const results = await parallel(tasks.map(t => () =>
  agent(t.prompt, { label: t.label, phase: 'Recheck' }).then(s => ({ label: t.label, summary: s }))
))
const ok = results.filter(Boolean)
const missing = tasks.filter((t, i) => !results[i]).map(t => t.label)
log(`${R}: ${ok.length}/${tasks.length} returned${missing.length ? '; MISSING: ' + missing.join(', ') : ''}`)
return { region: R, dispatched: tasks.length, returned: ok.length, missing, summaries: ok }
