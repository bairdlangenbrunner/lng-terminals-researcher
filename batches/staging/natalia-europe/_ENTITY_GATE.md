# Orchestrator entity gate — `natalia-europe`

Per the §5 step-3a merge gate. `entity_lookup.py --remote` is **unavailable this session**
(`GEM_PROJECT_DB_BASE_URL` unset), so every subagent's `no_remote_match` is a *skipped check*,
not a negative result. All staged new entities are therefore re-checked here directly against the
read-only Postgres `company` table (`GEM_READONLY_DB_URL`), matching on `name` / `name_local` /
`name_search`, including soft-deleted rows.

Checked 2026-07-29.

## Confirmed genuinely new — safe to stage as entity additions

| Entity | Staged by | Postgres result |
|---|---|---|
| Smart Gas S.p.A. | italy.disc.entity | 0 hits |
| Vescovini Group S.p.A. | italy.disc.entity | 0 hits |
| Molino Casillo S.p.A. | italy.disc.entity | 0 hits |

All three are Monfalcone LNG Logistics Terminal sponsors. Local lookup and Postgres agree.

## Already exist — REUSE the ID, never stage as new

Checked pre-emptively because they appear in in-flight research and are exactly the
cross-country false-negative class that `--country` filtering causes.

| Entity | GEM entity ID | Where it came up |
|---|---|---|
| Aktor LNG USA | `100002025152` | Port of Vlora FSRU 2 owner (already on the live record) |
| DEPA Commercial | `100001014516` | Atlantic-SEE LNG Trade JV partner (Vlora) |
| JERA | `100000001533` | Montenegro / Bar LNG Terminal MOU |
| Endesa | `100000000968` | Melilla + Granadilla (Spain discovery) |
| Enagás | `100001014505` | Melilla + Gran Canaria / Tenerife (Spain discovery) |

Both Spanish entities also have `[TO BE DELETED]` soft-deleted duplicates (`100000188589` Endesa,
`100000189152` Enagás) plus live subsidiaries (Endesa Generación, Enagas Internacional, Enagás
Renovable, …). Attach to the plain parent unless the source names a subsidiary specifically.

## Tooling note — why the local lookup "missed" Endesa

The Spain discovery agent reported `entity_lookup.py` false-negativing on Endesa. It is not a bug
and not a false negative: **the local lookup scans this tracker's LNG export CSV only**, and Endesa
does not currently own any LNG terminal row in it (its Canary Islands projects are precisely the
ones missing from GEM). The entity nonetheless exists in the shared GEM entity system because it
holds power plants on other trackers — which is the exact cross-tracker case the bare-lookup rule
exists for.

So with `--remote` down, "local not found" carries **no** information about whether an entity
exists. Postgres `company` is the authoritative check, and it is what this gate uses.

`JERA` also has 8 live subsidiaries in GEM (JERA Americas, JERA Asia, JERA Australia, JERA Co,
JERA Energy America, JERA Power Management Asia, JERA Power Management Mid East). Pick the entity
the source actually names rather than defaulting to the parent. Note `JERA Co` (`100002025198`)
is a live near-duplicate of `JERA` — flag to the reviewer if a Montenegro edit needs one of them.

`Ellaktor` / `Ellaktor Group` exist and are the Aktor group's listed parent lineage, with several
`[TO BE DELETED]` soft-deleted duplicates. Do not attach a Vlora edit to a deleted row.

## Not found, but not staged either

`Atlantic-SEE LNG Trade` — 0 hits. It is the Aktor 60% / DEPA Commercial 40% JV vehicle for the
Vlora project. Not currently staged by anyone; if an Update agent decides the JV (rather than
Aktor LNG USA) is the owner of record, it would be a legitimate new entity.
