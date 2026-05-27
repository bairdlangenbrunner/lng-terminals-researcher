# Entity canonical names and variants (LNG Terminals)

Authoritative version: the `_ENTITY_MAP` dict in `scripts/normalize.py`. This file is the human-readable reference for what canonical tags exist and which variants resolve to each.

When you encounter a new entity in a batch, add it to `normalize.py` AND to this table. The GEM entity system is shared across all trackers, so before creating any new entity, run `entity_lookup.py` to check for existing matches.

## Why this matters

Per the methodology, the GEM entity system is shared across all GEM trackers. Creating duplicate entities is real cleanup work for the Ownership Team. Canonical naming serves two purposes:

1. **Dedup index matching** — `dedup_index.py` uses canonical names to match candidate terminals against existing GEM coverage. "TotalEnergies" and "Total Energies" must resolve to the same tag.
2. **Trade press attribution** — sources use many name variants. Mapping to canonical lets cluster-coherence checks (Update SOP §5) work consistently.

## Canonical tags (key) → known variants (value)

### US-focused exporters

| Canonical | Variants seen |
|---|---|
| `cheniere` | Cheniere Energy, Cheniere, Cheniere Inc, Cheniere Energy Partners |
| `venture-global` | Venture Global LNG, Venture Global, VG LNG |
| `nextdecade` | NextDecade, NextDecade Corp |
| `sempra` | Sempra, Sempra Infrastructure, Sempra Energy, Sempra LNG |
| `freeport-lng` | Freeport LNG, Freeport LNG Development |
| `tellurian` | Tellurian, Tellurian Inc, Driftwood LNG |
| `energy-transfer` | Energy Transfer, Energy Transfer LNG, Lake Charles LNG |
| `new-fortress` | New Fortress Energy, NFE, NewFortress |
| `glenfarne` | Glenfarne Group, Glenfarne, Glenfarne Energy Transition |
| `commonwealth` | Commonwealth LNG, Commonwealth |

### Integrated majors

| Canonical | Variants seen |
|---|---|
| `totalenergies` | TotalEnergies, Total, Total Energies, Total SA, TOTAL |
| `shell` | Shell, Royal Dutch Shell, Shell plc |
| `bp` | BP, British Petroleum, BP plc |
| `exxonmobil` | ExxonMobil, Exxon Mobil, Exxon, XOM |
| `chevron` | Chevron, Chevron Corp |
| `conocophillips` | ConocoPhillips, Conoco Phillips, COP |
| `eni` | Eni, ENI, Eni SpA |
| `equinor` | Equinor, Statoil (legacy) |
| `repsol` | Repsol, Repsol SA |
| `galp` | Galp, Galp Energia |

### State-linked sponsors / NOCs

| Canonical | Variants seen |
|---|---|
| `qatarenergy` | QatarEnergy, Qatar Petroleum (legacy), QP |
| `adnoc` | ADNOC, Abu Dhabi National Oil Company, ADNOC Gas, ADNOC LNG |
| `aramco` | Saudi Aramco, Aramco |
| `petronas` | Petronas, Petroliam Nasional Berhad |
| `pertamina` | Pertamina, PT Pertamina, Pertamina Hulu |
| `cnpc` | CNPC, China National Petroleum Corp, PetroChina |
| `sinopec` | Sinopec, China Petroleum & Chemical Corp |
| `cnooc` | CNOOC, China National Offshore Oil Corp |
| `kogas` | KOGAS, Korea Gas Corporation |
| `jera` | JERA, JERA Co |
| `inpex` | INPEX, INPEX Corp |
| `gazprom` | Gazprom, Gazprom Export |
| `novatek` | Novatek, NOVATEK |
| `ngc-trinidad` | NGC, National Gas Company of Trinidad and Tobago |
| `nlng` | NLNG, Nigeria LNG, Nigeria LNG Limited |
| `bgt` | BGT, Bonny Gas Transport (Nigeria LNG affiliate) |
| `sonangol` | Sonangol, Sonangol EP |
| `sonatrach` | Sonatrach |
| `egas` | EGAS, Egyptian Natural Gas Holding |
| `egpc` | EGPC, Egyptian General Petroleum Corp |
| `staatsolie` | Staatsolie (Suriname) |
| `pdvsa` | PDVSA, Petróleos de Venezuela |
| `ypf` | YPF |
| `enarsa` | Enarsa, IEASA, Integración Energética Argentina |
| `petrobras` | Petrobras, Petróleo Brasileiro |
| `ecopetrol` | Ecopetrol |
| `bapco` | Bapco, Bapco Energies |
| `nnpc` | NNPC, Nigerian National Petroleum Corporation |
| `gnpc` | GNPC, Ghana National Petroleum Corp |
| `socar` | SOCAR, State Oil Company of Azerbaijan Republic |
| `tpao` | TPAO, Türkiye Petrolleri Anonim Ortaklığı |
| `botas` | BOTAŞ, Boru Hatları ile Petrol Taşıma A.Ş. |

### FSRU operators

| Canonical | Variants seen |
|---|---|
| `excelerate` | Excelerate Energy, Excelerate |
| `hoegh-evi` | Höegh Evi, Höegh LNG, Hoegh LNG, Hoegh Evi, Höegh |
| `bw-lng` | BW LNG, BW Group, BW |
| `energos` | Energos Infrastructure, Energos |
| `new-fortress` | (same canonical as US-focused exporters; New Fortress operates FSRUs too) |
| `karmol` | KARMOL, Karpowership+MOL JV |
| `karpowership` | Karpowership, Karadeniz Holding |
| `golar` | Golar LNG, Golar |
| `flex-lng` | Flex LNG (note: primarily a carrier owner; some FSRU exposure) |
| `mol` | MOL, Mitsui OSK Lines, Mitsui O.S.K. Lines |
| `gaslog` | GasLog (now part of BlackRock GEPIF) |

### European import sponsors

| Canonical | Variants seen |
|---|---|
| `engie` | ENGIE, Engie, GDF Suez (legacy) |
| `naturgy` | Naturgy, Naturgy Energy Group, Gas Natural Fenosa (legacy) |
| `snam` | Snam, Snam SpA |
| `fluxys` | Fluxys, Fluxys Belgium |
| `enagas` | Enagas, Enagás, Enagas SA |
| `rwe` | RWE, RWE AG |
| `uniper` | Uniper, Uniper SE |
| `national-grid` | National Grid (UK) |
| `gas-natural-acu` | Gas Natural Açu (Brazil — Prumo/BP/Siemens JV) |
| `gnl-quintero` | GNL Quintero (Chile, Enagas/Oman Oil JV legacy) |
| `gnl-mejillones` | GNL Mejillones (Chile, ENGIE/Ameris JV) |

### Asian state utilities / IPPs

| Canonical | Variants seen |
|---|---|
| `tepco` | TEPCO, Tokyo Electric Power Company |
| `chubu` | Chubu Electric Power |
| `osaka-gas` | Osaka Gas, Daigas |
| `tokyo-gas` | Tokyo Gas, TG |
| `cpc-taiwan` | CPC, CPC Corporation Taiwan |
| `pgn-indonesia` | PGN, Perusahaan Gas Negara |
| `ptt` | PTT, PTT Public Company |
| `gail-india` | GAIL, GAIL India |
| `petronet` | Petronet LNG, Petronet |
| `dahej-lng` | (typically resolves to petronet for ownership) |

### African

| Canonical | Variants seen |
|---|---|
| `mozambique-lng` | Mozambique LNG (TotalEnergies-led consortium) |
| `coral-fl` | Coral South FLNG (Eni-led) |
| `marathon` | Marathon, Marathon Oil |
| `kosmos` | Kosmos Energy |
| `smhpm` | SMHPM, Société Mauritanienne des Hydrocarbures |
| `petrosen` | Petrosen (Senegal) |
| `enh` | ENH, Empresa Nacional de Hidrocarbonetos (Mozambique) |

### Lender / financier / EPC (use sparingly — these don't usually own projects but appear in financing/EPC contexts)

| Canonical | Variants seen |
|---|---|
| `jbic` | JBIC, Japan Bank for International Cooperation |
| `kexim` | KEXIM, Export-Import Bank of Korea |
| `nexi` | NEXI, Nippon Export and Investment Insurance |
| `ifc` | IFC, International Finance Corporation |
| `bechtel` | Bechtel |
| `mcdermott` | McDermott, McDermott International |
| `jgc` | JGC Holdings, JGC Corp |
| `kbr` | KBR |
| `saipem` | Saipem |
| `technip` | TechnipFMC, Technip Energies |
| `worley` | Worley |
| `gtt` | GTT, Gaztransport & Technigaz — note: containment-only supplier; never cite GTT standalone per source roster |
| `air-products` | Air Products, Air Products and Chemicals |
| `chart` | Chart Industries |

### SPVs (project-specific entities — common in LNG)

SPVs are project-specific shell companies. The canonical tag follows the project name convention.

| Canonical | Variants seen | Underlying parents |
|---|---|---|
| `corpus-christi-lng` | Corpus Christi Liquefaction LLC | cheniere |
| `sabine-pass-lng` | Sabine Pass Liquefaction LLC | cheniere |
| `plaquemines-lng` | Plaquemines LNG LLC | venture-global |
| `calcasieu-pass-lng` | Calcasieu Pass LLC | venture-global |
| `rio-grande-lng` | Rio Grande LNG LLC | nextdecade |
| `lng-canada` | LNG Canada Development Inc | shell / petronas / kogas / mitsubishi / petrochina JV |
| `cedar-flng` | Cedar LNG Partners | pembina / haisla-nation |
| `egyptian-lng` | Egyptian LNG | shell / petronas / egpc / egas / totalenergies |
| `damietta-lng` | Damietta LNG | eni / egas / egpc |
| `angola-lng` | Angola LNG | chevron / sonangol / bp / eni / totalenergies |
| `eg-lng` | EG LNG | marathon / sonagas / mitsui / marubeni |

## DART regional euphemism decoder

DART filings sometimes disclose counterparties by region rather than name (carrier project encountered this; terminals may too via DART-filing Korean sponsors like KOGAS, POSCO, Daewoo):

| DART phrasing | Often actually... |
|---|---|
| "Oceania-region utility" | Tokyo Gas, Osaka Gas, or Australian utility |
| "Americas-region utility" | Cheniere, Venture Global, or Sempra |
| "Asia-region utility" | JERA, CPC Taiwan, or PGN Indonesia |
| "Europe-region utility" | RWE, Uniper, or ENGIE |

Cross-check with trade press attribution. Pattern is consistent enough to seed a hypothesis but not authoritative on its own.

## Note on JV-style ownership

Per Discovery SOP §9, the methodology preference is to list each JV partner as a separate Owner with percentage rather than create a JV entity. Exception: when the JV operates as a real legal entity with its own staff and publications (NLNG, Angola LNG, Egyptian LNG, etc.), treat as a single entity.

When a GIIGNL row shows ownership as "ENI 50%, EGAS 40%, EGPC 10%", that maps to three Owner entries (eni, egas, egpc) plus a Parent entry if applicable, NOT a single "Damietta LNG JV" entity.
