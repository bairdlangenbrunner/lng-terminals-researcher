export const meta = {
  name: 'lng-resweep-reverify',
  description: 'Re-source already-staged sweep records: strip gem.wiki, require >=2 independent verified URLs per value',
  phases: [{ title: 'Reverify' }],
}

const A = typeof args === 'string' ? JSON.parse(args) : args
const ROOT = '/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher'
const R = A.region

function prompt(g) {
  return `Re-verification subagent — GEM LNG sweep sourcing fix.

REPO = ${ROOT}

FIRST read and follow EXACTLY this brief (defines your task, the two rules, output schema, done-marker):
  ${ROOT}/batches/staging/_resweep_reverify_brief.md

Your assignment:
- SLUG: ${g.slug}   (write ${ROOT}/batches/staging/${R}/${g.slug}.reverify.done.json LAST)
- REGION: ${R}
- FILES YOU OWN (rewrite each in place, same schema):
${g.files.map(f => '    ' + f).join('\n')}
- Fresh GEM export (for cross-checking old_value only; do NOT re-pick research): ${ROOT}/scripts/gem_export.csv

The job is a SOURCING FIX, not a new sweep: for every value already staged in these files, find >=2
INDEPENDENT non-GEM URLs that each explicitly contain the value (verify with url_verifier.py using the
value as the token), replace any gem.wiki/globalenergymonitor.org citation, and blank+qa any value you
cannot corroborate off-GEM. Do not invent new edits or new terminals.

Use absolute paths in every command and file write.
RETURN: only the terse <=12-line summary the brief specifies. Do not paste records.`
}

const tasks = A.groups.map(g => ({ label: `rv:${g.slug}`, prompt: prompt(g) }))

phase('Reverify')
log(`${R}: re-verifying ${tasks.length} slug-groups`)
const results = await parallel(tasks.map(t => () =>
  agent(t.prompt, { label: t.label, phase: 'Reverify' }).then(s => ({ label: t.label, summary: s }))
))
const ok = results.filter(Boolean)
const missing = tasks.filter((t, i) => !results[i]).map(t => t.label)
log(`${R}: ${ok.length}/${tasks.length} returned${missing.length ? '; MISSING: ' + missing.join(', ') : ''}`)
return { region: R, dispatched: tasks.length, returned: ok.length, missing, summaries: ok }
