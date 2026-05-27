# Source Roster (LNG Terminals)

Quick reference for picking sources at query time. Tiers are operational: a "Tier 1" source carries more weight in confidence labeling per the Update SOP §6. Per the methodology FAQ, no industry report (including GIIGNL) is automatically authoritative — sponsor IR and primary regulatory filings take priority.

When a new useful source is found during a batch, add it here AND note it in `docs/country_notes/` for the relevant country.

## Tier 1 — Primary (stand-alone for green confidence)

Sources that establish facts on their own. A single Tier 1 source supporting a value is usually sufficient for green confidence.

### Tier 1a — Sponsor / operator / yard direct (always primary when they name the project)

| Source | URL pattern | Strongest at |
|---|---|---|
| US sponsors | IR pages (cheniere.com, venturegloballng.com, sempra.com, nextdecade.com, freeport-lng.com, energytransfer.com, tellurianinc.com) | New PR, FID announcements, capacity, ownership |
| Integrated majors | corporate.totalenergies.com, shell.com, bp.com, exxonmobil.com, chevron.com, conocophillips.com, eni.com | Multi-country project portfolio updates |
| State-linked sponsors | qatarenergy.qa, adnoc.ae, petronas.com, pertamina.com, cnpc.com.cn, sinopec.com, cnooc.com.cn, kogas.or.kr, jera.co.jp | National LNG strategies, project status |
| FSRU operators | excelerateenergy.com, hoeghevi.com, bwlng.com, energosinfra.com, newfortressenergy.com, karpowership.com | FSRU deployments, vessel reassignments |
| Import sponsors | engie.com, naturgy.com, snam.it, fluxys.com, enagas.es, rwe.com, uniper.energy | European import terminal status, regas capacity |

### Tier 1b — Regulators (primary when they name the project)

| Country / region | Source | URL pattern |
|---|---|---|
| United States | FERC eLibrary | `elibrary.ferc.gov` |
| United States | DOE FECM export authorizations | `energy.gov/fecm/listings/lng-reports` |
| European Union | PCI list portal | `energy.ec.europa.eu/topics/infrastructure/projects-common-interest_en` |
| United Kingdom | Ofgem decisions | `ofgem.gov.uk/decisions` |
| United Kingdom | Planning Inspectorate (NSIP) | `infrastructure.planninginspectorate.gov.uk` |
| Canada | CER (Canada Energy Regulator) | `cer-rec.gc.ca` |
| Australia | NOPSEMA (offshore) | `nopsema.gov.au` |
| Australia | AEMO Gas Statement | `aemo.com.au` |
| Japan | METI announcements | `meti.go.jp/english/press/` |
| South Korea | MOTIE | `motie.go.kr/eng/` |
| South Korea | KOGAS IR | `kogas.or.kr/eng/main.do` |
| South Korea | DART (filings) | `dart.fss.or.kr` |
| China | NDRC | `en.ndrc.gov.cn` |
| India | MOPNG | `mopng.gov.in` |
| India | PNGRB | `pngrb.gov.in` |
| Brazil | ANP | `gov.br/anp/pt-br` |
| Mexico | CRE | `gob.mx/cre` |
| Philippines | DOE | `doe.gov.ph` |
| Vietnam | MOIT | `moit.gov.vn` |
| Indonesia | ESDM | `esdm.go.id` |
| Bangladesh | Petrobangla | `petrobangla.org.bd` |
| Pakistan | OGRA | `ogra.org.pk` |
| Argentina | ENARGAS | `enargas.gob.ar` |
| Türkiye | EPDK | `epdk.gov.tr` |
| Singapore | EMA | `ema.gov.sg` |
| Thailand | ERC | `erc.or.th` |

For countries not listed, search pattern: `"<country name>" "energy regulator" OR "petroleum regulator" OR "gas regulator"`. Add findings to this table and to `docs/country_notes/`.

### Tier 1c — Class societies (for FSRU/FLNG vessel identification)

Same as carrier project — useful when the terminal involves a named vessel:

- DNV Vessel Register: `vesselregister.dnv.com`
- Lloyd's Register: `lr.org/en/class-direct/`
- ABS Record: `eagle.org/.../abs-record-public-search.html`
- Korean Register: `krs.co.kr/eng/srch/srch_main.aspx`
- ClassNK: `classnk.or.jp/register/regships/regships_e.aspx`
- Equasis: `equasis.org`

## Tier 1 (with caveats) — Industry reports

| Source | Notes |
|---|---|
| GIIGNL Annual Report | Tier 1 for the annual operating snapshot it covers; **not authoritative** per methodology FAQ. A value supported by GIIGNL alone is yellow; GIIGNL + sponsor IR is green. Known gaps in coverage (small-scale, non-member, sanctioned). |
| IGU World LNG Report | Same caveats as GIIGNL; methodology FAQ notes IGU often disagrees with GIIGNL on capacity and owners. |
| BloombergNEF (BNEF) | Methodology FAQ explicitly cautions: a 2020/2021 BNEF data import is the source of many unreliable values in the legacy data. **Avoid citing standalone**; replace with primary source when possible. |

## Tier 2 — Trade press (good for cluster-level coverage; need primary source for green)

| Source | URL pattern | Notes |
|---|---|---|
| LNG Prime | `lngprime.com` | Most comprehensive LNG-specific coverage. Daily newsletter. Paywalled (GEM has subscription per methodology FAQ — login in O&G 1Password vault). Headlines/leads usually public. |
| Reuters Energy | `reuters.com/business/energy/` | General energy coverage, strong on US/Europe. Some content paywalled. |
| S&P Global Commodity Insights | `spglobal.com/commodityinsights/` | Premium analytical content; mostly paywalled. |
| Argus Media | `argusmedia.com` | Same. |
| Upstream Online | `upstreamonline.com` | Strong on upstream-to-LNG project linkages. |
| Energy Intelligence | `energyintel.com` | Mostly paywalled. |
| Bloomberg Energy | `bloomberg.com/energy` | Some paywalling. |
| Splash247 | `splash247.com` | Shipping/FSRU angle; useful for vessel-related developments. |
| Riviera Maritime Media | `rivieramm.com` | Technical detail. **Watch for soft-error 429 pages** — URL verifier catches these. |
| Hellenic Shipping News | `hellenicshippingnews.com` | Europe/Mediterranean shipping focus. |
| Hydrocarbons Africa | `africa-energy.com` | Africa-focused. |
| Energy Voice | `energyvoice.com` | UK/North Sea focus. |
| Offshore Energy | `offshore-energy.biz` | Offshore project coverage including FLNG. |
| Maritime Executive | `maritime-executive.com` | Shipping; FSRU coverage. |
| Reuters Africa | `africa.reuters.com` | Africa LNG; general energy. |
| en.sedaily.com | `en.sedaily.com` | Korean reg-filing English proxy (faster than parsing DART). |
| iMarine | `imarinenews.com` | Asia-focused. |
| Asia Business Daily | `asiabiz.com` | Asia regulatory press. |
| Petroleum Economist | `petroleum-economist.com` | Analytical; some paywalled. |

## Tier 3 — Regional / specialized press

Use as corroborators or leads, not standalone primary citations.

- Country-specific business press (e.g. La Nación for Argentina, El Universal for Mexico)
- Industry conferences press releases (LNG2026, Gastech, World Gas Conference)
- Financial press for project finance angle (Project Finance International, IJGlobal)
- NGO research (IEEFA, Reclaim Finance, Oil Change International) — useful for leads, especially on opposition / ESJ data; not authoritative on technical facts
- Wikipedia — never cite directly; can be a lead to original sources

## Tier 4 — Vessel databases (for FSRU/FLNG vessel data)

- VesselFinder: `vesselfinder.com`
- MarineTraffic: `marinetraffic.com`
- marinetraffic.org (the §6a.8 IMO tracker fallback from carriers): `marinetraffic.org` — see `imo_tracker.py`
- marinevesseltraffic.com
- BalticShipping: `balticshipping.com`

## Forbidden / cautioned

| Source | Why |
|---|---|
| **SFOC** | Project's legacy data origin; not a citable URL |
| **GEM.wiki** | Don't self-cite. Wiki pages link back to original sources; use those. |
| **BNEF (legacy 2020/2021 imports)** | Per methodology FAQ. Replace with primary source where possible; if absolutely necessary as a citation, mark in qa_review. |
| **GTT standalone** | The containment supplier appears as a generic source for many projects; pair with non-GTT source. |
| **Auto-generated wiki citations from October 2025 batch** | Per methodology FAQ, these are the "orange error" references; replace if possible. |

## English-language proxies for non-English regulator filings

Useful when the primary regulator publishes in non-English and you need faster access:

- **DART (Korean filings)**: `en.sedaily.com` and `kind.krx.co.kr` (KRX English mirror)
- **Bursa Malaysia**: filings published in English natively
- **JFSA / TSE (Japan)**: TSE has English summaries; deep filings often Japanese-only
- **TWSE (Taiwan)**: English summaries
- **CNINFO (China)**: limited English; use sponsor IR or trade press instead

## Most productive search query patterns

For finding new projects:
- `LNG terminal "<country>" announced <year>`
- `"<sponsor>" LNG <country> proposed`
- `regasification terminal "<country>" "<year>"`
- `liquefaction "<country>" FID`
- `FSRU "<country>" deployment`

For finding existing project updates:
- `"<TerminalName>" "<year>" status`
- `"<TerminalName>" capacity expansion`
- `"<sponsor>" "<TerminalName>" update`
- `site:<sponsor-domain> "<TerminalName>"`

For finding regulatory filings:
- `site:<regulator-domain> "<project name>"`
- `"<project name>" FERC filing`
- `"<project name>" "PCI" "European Commission"`

For FSRU vessel tracking:
- `"<vessel name>" deployed "<country>"`
- `"<vessel name>" IMO`
- IMO-tracker fallback (see `imo_tracker.py`)
