#!/usr/bin/env python3
"""One-off: assemble Thailand Update-leg staged_*.json from the 6 research JSONs."""
import csv, json, glob, os

STAGE = "../batches/staging/thailand"
CSV = "gem_export.csv"

REF_MAP = {
    'Status': 'Status [ref]', 'Substatus': 'Status [ref]', 'Capacity': 'Capacity [ref]',
    'Owner': 'Owner [ref]', 'Operator': 'Operator [ref]', 'FacilityType': 'FacilityType [ref]',
    'Location': 'Location [ref]', 'Cost': 'Cost [ref]', 'ConstructionYear': 'ConstructionDate [ref]',
    'ProposalYear': 'ProposalDate [ref]', 'FIDYear': 'FIDYear [ref]', 'FIDStatus': 'FIDYear [ref]',
    'ShelvedYear': 'ShelvedYear [ref]', 'StopYear': 'StopYear [ref]', 'CancelledYear': 'CancelledYear [ref]',
    'AssociatedTerminals': 'AssociatedTerminals [ref]',
}

# --- fresh CSV: (terminal_id, unit_id) -> {display_col: value} for old_value lookup
with open(CSV, newline='', encoding='utf-8') as f:
    r = csv.reader(f); header = next(r); rows = list(r)
ci = {c: i for i, c in enumerate(header)}
by_unit = {}
for row in rows:
    key = (row[ci['TerminalID']] if 'TerminalID' in ci else row[0],
           row[ci['GEM Unit ID']] if 'GEM Unit ID' in ci else row[1])
    by_unit[key] = row
# discover the id column names robustly
tid_col = next((c for c in header if c.replace(' ', '').lower() in ('terminalid',)), header[0])
uid_col = next((c for c in header if 'unit' in c.lower() and 'id' in c.lower()), header[1])
by_unit = {}
for row in rows:
    by_unit[(row[ci[tid_col]], row[ci[uid_col]])] = row
print(f"id cols: tid={tid_col!r} uid={uid_col!r}; {len(by_unit)} rows indexed")

def cur(tid, uid, col):
    row = by_unit.get((tid, uid))
    if row is None or col not in ci:
        return ""
    return row[ci[col]]

staged_updates, staged_timeline, staged_qa, staged_wiki = [], [], [], []

for fn in sorted(glob.glob(os.path.join(STAGE, "*.research.json"))):
    d = json.load(open(fn))
    terms = d['terminals'] if 'terminals' in d else [d]
    for t in terms:
        tid = t.get('terminal_id'); tname = t.get('terminal_name')
        for u in t.get('updates', []):
            field = u['field']
            if field.endswith(' [ref]'):
                base = field[:-len(' [ref]')]
                field_name = base
                ref_field = field
            else:
                field_name = field
                ref_field = REF_MAP.get(field, f"{field} [ref]")
            new_value = u.get('new_value', '')
            # drop no-ops (empty value + no refs)
            if (new_value is None or str(new_value) == '') and not u.get('ref_urls'):
                print(f"  drop no-op: {tid}/{u.get('unit_id')} {field}")
                continue
            rec = {
                "terminal_id": tid,
                "unit_id": u.get('unit_id'),
                "terminal_name": tname,
                "unit_name": u.get('unit_name', '--'),
                "country": "Thailand",
                "field_name": field_name,
                "old_value": cur(tid, u.get('unit_id'), field_name),
                "new_value": new_value,
                "confidence": u.get('confidence', ''),
                "source_tier": u.get('source_tier', ''),
                "ref_field": ref_field,
                "ref_urls": u.get('ref_urls', []),
                "source_notes": u.get('change_summary', ''),
                "researcher_initials": "AI-draft",
            }
            staged_updates.append(rec)
        for tl in t.get('status_timeline_additions', []):
            uid = tl.get('unit_id')
            uname = next((x.get('unit_name', '--') for x in t.get('updates', []) if x.get('unit_id') == uid), '--')
            staged_timeline.append({
                "terminal_id": tid, "unit_id": uid, "terminal_name": tname, "unit_name": uname,
                "operation": tl.get('operation', 'append'), "status": tl.get('status'),
                "sub_status": tl.get('sub_status', ''), "year": tl.get('year'),
                "part_of_year": tl.get('part_of_year', ''), "notes": tl.get('notes', ''),
                "source_url": tl.get('source_url', ''), "confidence": tl.get('confidence', ''),
                "validation_warnings": tl.get('validation_warnings', ''),
                "legal_transition_check": tl.get('legal_transition_check', ''),
                "researcher_initials": "AI-draft",
            })
        for w in t.get('wiki_updates', []):
            staged_wiki.append({
                "country": "Thailand", "terminal_id": tid, "terminal_name": tname,
                "unit_id": w.get('unit_id'), "topic": w.get('topic', ''),
                "wiki_text": w.get('wiki_text', ''),
                "verification_status": w.get('verification_status', ''),
                "source_urls": w.get('source_urls', []), "researcher_initials": "AI-draft",
            })
        for q in t.get('qa_notes', []):
            staged_qa.append({
                "category": q.get('category', ''), "terminal_id": tid, "unit_id": q.get('unit_id'),
                "terminal_name": tname, "issue": q.get('issue', ''), "severity": q.get('severity', ''),
                "suggested_action": q.get('suggested_action', ''), "gem_field": q.get('gem_field', ''),
                "paste_value": "", "researcher_initials": "AI-draft",
            })

for name, obj in [("staged_updates.json", staged_updates),
                  ("staged_status_timeline.json", staged_timeline),
                  ("staged_qa_review.json", staged_qa),
                  ("staged_wiki_updates.json", staged_wiki),
                  ("staged_entity_additions.json", [])]:
    with open(os.path.join(STAGE, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)
    print(f"wrote {name}: {len(obj)}")
