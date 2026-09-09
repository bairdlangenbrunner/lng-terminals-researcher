# LNG coverage audit — researcher assignment vs actual updates

Generated 2026-08-26 09:15 local. Export `gem_export.csv` (1257 unit rows, 836 terminals, 114 countries).
Roster source: live Sheet via gws-gem (read-only).
Staleness definition: **no `added`/`updated`/`no changes` tick on or after 2026-01-01** ("never touched in 2026").
Trailing-window comparison also shown: nothing since 2026-04-28.

Scope: `Fuel = LNG` only. Excluded as out of scope (LH2 2 rows/2 terminals, NH3 6 rows/5 terminals, Oil 15 rows/14 terminals, eLNG 1 rows/1 terminals) — the Oil rows are legacy US crude/NGL deepwater-port records, and the NH3/LH2/eLNG rows are alt-fuel units on European LNG terminals whose fields the methodology marks read-only from 2026. Neither is work a researcher was assigned this cycle.

Three sources, deliberately cross-checked: the assignment sheet (who was responsible), `unit_update` (every tick, with person and research status), and `plant_history` (whether any researched field actually changed). The export's `Researcher`/`LastUpdated` columns answer neither question on their own.

## Headline

- **16** unit rows on a **live status** (operating, construction, proposed, idle) never ticked in 2026 and with no field edit either — **this is the actionable gap.**
- **64** more never ticked, but on a dead status (cancelled/shelved/retired/mothballed) — deprioritized by design, not a coverage failure. Listed separately so the two never get summed.
- **57** edited in 2026 but never ticked — work done, tracking sheet blind to it.
- **0** ticked `added`/`updated` in 2026 with no researched field change — verify the tick reflects real work.
- **1120** clean.
- For comparison, **289** rows have no tick in the trailing 120-day window — this number is inflated by finished passes that simply ended earlier in the year.

## By researcher (assignment sheet)

Reading the columns: **live gap** is the number that matters. **dead-status gap** is cancelled/shelved/retired rows nobody was expected to revisit. **edited, not ticked** means the fields moved in 2026 but the box was never checked — work done, invisible to the tracking sheet. The three are disjoint and together make up every row with no 2026 tick.

| Researcher | Countries | Terminals | Unit rows | **live gap** | dead-status gap | edited, not ticked | Tick range |
|---|---|---|---|---|---|---|---|
| Maggie | 3 | 98 | 175 | **16** | 0 | 29 | 2024-02-01 → 2026-08-06 |
| Rob | 2 | 95 | 169 | **0** | 54 | 6 | 2025-07-24 → 2026-08-05 |
| Gregor | 21 | 91 | 110 | **0** | 5 | 7 | 2025-06-18 → 2026-08-20 |
| Isabel | 8 | 86 | 139 | **0** | 1 | 10 | 2025-06-04 → 2026-07-02 |
| Natalia | 13 | 67 | 87 | **0** | 4 | 4 | 2025-06-18 → 2026-07-30 |
| Aiganym | 13 | 111 | 163 | **0** | 0 | 1 | 2025-07-23 → 2026-07-02 |
| Amalia | 26 | 167 | 247 | **0** | 0 | 0 | 2026-04-09 → 2026-07-27 |
| Andrew | 22 | 55 | 86 | **0** | 0 | 0 | 2026-05-19 → 2026-08-13 |
| Baird | 1 | 3 | 3 | **0** | 0 | 0 | 2026-07-29 → 2026-07-29 |
| Warda | 5 | 63 | 78 | **0** | 0 | 0 | 2026-05-19 → 2026-08-06 |

## By country — countries with any flagged row

| Country | Assigned | Sheet says complete | Terminals | Unit rows | **live gap** | dead-status gap | edited, not ticked | Tick range |
|---|---|---|---|---|---|---|---|---|
| China | Maggie | TRUE | 90 | 158 | **16** | 0 | 27 | 2024-02-01 → 2026-08-06 |
| United States | Rob | TRUE | 94 | 168 | **0** | 54 | 6 | 2025-07-24 → 2026-08-05 |
| Canada | Isabel | TRUE | 36 | 52 | **0** | 1 | 6 | 2025-06-18 → 2026-06-16 |
| Italy | Natalia | TRUE | 18 | 22 | **0** | 2 | 3 | 2025-07-16 → 2026-07-30 |
| Venezuela | Gregor | TRUE | 5 | 6 | **0** | 4 | 0 | 2025-07-25 → 2026-08-05 |
| Chile | Gregor | TRUE | 6 | 7 | **0** | 1 | 2 | 2025-08-05 → 2026-08-04 |
| Spain | Natalia | TRUE | 10 | 11 | **0** | 2 | 1 | 2025-06-18 → 2026-07-20 |
| Australia | Isabel | TRUE | 28 | 46 | **0** | 0 | 2 | 2025-07-18 → 2026-07-02 |
| Mexico | Gregor | TRUE | 19 | 28 | **0** | 0 | 2 | 2025-09-03 → 2026-08-18 |
| Papua New Guinea | Isabel | TRUE | 7 | 24 | **0** | 0 | 2 | 2025-06-04 → 2026-07-01 |
| Taiwan | Maggie | TRUE | 7 | 16 | **0** | 0 | 2 | 2025-06-17 → 2026-03-12 |
| Bahamas | Gregor | TRUE | 3 | 3 | **0** | 0 | 1 | 2025-06-18 → 2026-08-06 |
| Dominican Republic | Gregor | TRUE | 4 | 4 | **0** | 0 | 1 | 2025-07-17 → 2026-08-06 |
| Panama | Gregor | TRUE | 3 | 3 | **0** | 0 | 1 | 2025-07-16 → 2026-08-06 |
| Romania | Aiganym | TRUE | 2 | 3 | **0** | 0 | 1 | 2025-07-23 → 2026-06-16 |

99 countries are fully current: Albania, Algeria, Angola, Antigua and Barbuda, Argentina, Aruba, Bahrain, Bangladesh, Belgium, Benin, Botswana, Brazil, Brunei, Cambodia, Cameroon, Colombia, Croatia, Cyprus, Côte d'Ivoire, Djibouti, Ecuador, Egypt, El Salvador, Equatorial Guinea, Estonia, Finland, France, Gabon, Georgia, Germany, Ghana, Gibraltar, Greece, Guinea, Guyana, Haiti, Honduras, Hong Kong, India, Indonesia, Iran, Iraq, Ireland, Israel, Jamaica, Japan, Jordan, Kenya, Kuwait, Latvia, Lebanon, Libya, Lithuania, Malaysia, Malta, Mauritania, Mauritius, Montenegro, Morocco, Mozambique, Myanmar, Namibia, Netherlands, New Zealand, Nicaragua, Nigeria, Norway, Oman, Pakistan, Peru, Philippines, Poland, Portugal, Puerto Rico, Qatar, Republic of the Congo, Russia, Senegal, Sierra Leone, Singapore, South Africa, South Korea, Sri Lanka, Sudan, Suriname, Sweden, Tanzania, Thailand, Timor-Leste, Trinidad and Tobago, Turkmenistan, Türkiye, Ukraine, United Arab Emirates, United Kingdom, Uruguay, Vietnam, Western Sahara, Yemen

## Roster/export reconciliation

- Export countries with no row on the assignment sheet (0): none
- Assignment-sheet countries with no terminal in the export (0): none
- The sheet's **Region** column is corrupted (Nigeria→Europe, Colombia→Africa, Republic of the Congo→Americas). Subregion and Country are reliable and are what this audit joins on.

## The live-status gap, row by row

Every unit row on a live status with no 2026 tick and no 2026 field edit. This is the list to clear before handoff.

| Country | Assigned | Terminal | Unit | Status | Last tick | By | Last field edit | By |
|---|---|---|---|---|---|---|---|---|
| China | Maggie | Dalian LNG Terminal | Phase 1 | operating | 2025-06-02 | Aiqun Yu | 2025-06-02 | Aiqun Yu |
| China | Maggie | Dalian LNG Terminal | Phase 2 | operating | 2025-06-02 | Aiqun Yu | 2025-06-02 | Aiqun Yu |
| China | Maggie | Fujian LNG Terminal | Phase I | operating | 2025-06-04 | Aiqun Yu | 2025-10-06 | Robert Rozansky |
| China | Maggie | Fujian LNG Terminal | Phase II (Expansion) | operating | 2025-06-04 | Aiqun Yu | 2025-10-06 | Robert Rozansky |
| China | Maggie | Hainan Shennan LNG Storage Facility | Phase 1 | operating | 2025-06-11 | Aiqun Yu | 2025-06-11 | Aiqun Yu |
| China | Maggie | Pinghu LNG Terminal | -- | operating | 2025-05-21 | Aiqun Yu | 2025-05-21 | Aiqun Yu |
| China | Maggie | Qidong LNG Terminal | Phase 1 | operating | 2025-05-15 | Aiqun Yu | 2025-10-09 | Robert Rozansky |
| China | Maggie | Qidong LNG Terminal | Phase 2 | operating | 2025-05-20 | Aiqun Yu | 2025-10-09 | Robert Rozansky |
| China | Maggie | Qidong LNG Terminal | Phase 3 | operating | 2025-05-15 | Aiqun Yu | 2025-10-09 | Robert Rozansky |
| China | Maggie | Qidong LNG Terminal | Phase 4 | operating | 2024-02-01 | Aiqun Yu | 2025-10-09 | Robert Rozansky |
| China | Maggie | Qidong LNG Terminal | Phase 5 | operating | 2025-05-15 | Aiqun Yu | 2025-10-09 | Robert Rozansky |
| China | Maggie | Shenzhen Diefu CNOOC LNG Terminal | Phase 1 | operating | 2025-05-08 | Aiqun Yu | 2025-05-08 | Aiqun Yu |
| China | Maggie | Wenzhou LNG Terminal | -- | operating | 2025-05-26 | Aiqun Yu | 2025-05-26 | Aiqun Yu |
| China | Maggie | Wuhaogou LNG Storage Facility | Phase 1 | operating | 2025-06-12 | Aiqun Yu | 2025-06-12 | Aiqun Yu |
| China | Maggie | Wuhaogou LNG Storage Facility | Phase 2 | operating | 2025-06-12 | Aiqun Yu | 2025-06-12 | Aiqun Yu |
| China | Maggie | Zhangzhou LNG Terminal | Phase 1 | operating | 2025-05-07 | Aiqun Yu | 2025-05-07 | Aiqun Yu |

## Every flagged unit row

| Country | Assigned | Terminal | Unit | Status | Last tick | By | Last field edit | By | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Romania | Aiganym | Black Sea LNG Terminal | Export Facility | shelved | 2025-07-23 | Robert Rozansky | 2026-06-16 | Aiganym Valikhanova | edited_not_ticked |
| Bahamas | Gregor | Ocean Cay LNG Terminal | -- | cancelled | 2025-06-18 | Amalia Llano | 2026-08-11 | Gregor Clark | edited_not_ticked |
| Chile | Gregor | Colbun FLNG Terminal | -- | cancelled | 2025-08-05 | Amalia Llano | 2026-08-04 | Gregor Clark | edited_not_ticked |
| Chile | Gregor | Gas Atacama FLNG Terminal | -- | cancelled | 2025-08-05 | Amalia Llano | 2025-08-05 | Amalia Llano | stale |
| Chile | Gregor | Quintero LNG Terminal | Expansion | cancelled | 2025-08-05 | Amalia Llano | 2026-08-21 | Gregor Clark | edited_not_ticked |
| Dominican Republic | Gregor | San Pedro de Macoris LNG Terminal | -- | cancelled | 2025-07-17 | Amalia Llano | 2026-08-19 | Alejandra Rodriguez | edited_not_ticked |
| Mexico | Gregor | Costa Azul LNG Terminal | Export Terminal Phase 1 | construction | 2025-09-03 | Gregor Clark | 2026-08-21 | Gregor Clark | edited_not_ticked |
| Mexico | Gregor | Karpowership Yucatán FSRU | -- | proposed | never | — | 2026-08-21 | Gregor Clark | edited_not_ticked |
| Panama | Gregor | Telfers FSRU | -- | cancelled | 2025-07-16 | Amalia Llano | 2026-07-06 | Isabel Mahon | edited_not_ticked |
| Venezuela | Gregor | Delta Caribe Oriental Terminal | T1 | cancelled | 2025-07-25 | Amalia Llano | 2025-07-25 | Amalia Llano | stale |
| Venezuela | Gregor | Delta Caribe Oriental Terminal | T2 | cancelled | 2025-07-25 | Amalia Llano | 2025-07-25 | Amalia Llano | stale |
| Venezuela | Gregor | Project Venezuela LNG Terminal | -- | cancelled | 2025-07-25 | Amalia Llano | 2025-07-25 | Amalia Llano | stale |
| Venezuela | Gregor | Venezuela Offshore LNG Terminal | -- | cancelled | 2025-07-25 | Amalia Llano | 2025-07-25 | Amalia Llano | stale |
| Australia | Isabel | Darwin LNG Terminal | T1 | idled | 2025-07-18 | Hanna Fralikhina | 2026-06-04 | Isabel Mahon | edited_not_ticked |
| Australia | Isabel | Gorgon LNG Terminal | T4 | cancelled | 2025-09-24 | Robert Rozansky | 2026-05-27 | Isabel Mahon | edited_not_ticked |
| Canada | Isabel | Kitimat LNG Terminal | T1-T3 | cancelled | 2025-06-24 | Robert Rozansky | 2026-06-11 | Isabel Mahon | edited_not_ticked |
| Canada | Isabel | Kwispaa LNG Terminal | T1-T4 | cancelled | 2025-06-25 | Robert Rozansky | 2026-06-16 | Isabel Mahon | edited_not_ticked |
| Canada | Isabel | Malahat LNG Terminal | -- | cancelled | 2025-06-24 | Robert Rozansky | 2026-06-16 | Isabel Mahon | edited_not_ticked |
| Canada | Isabel | Nisga'a LNG Terminal | -- | cancelled | 2025-06-18 | Robert Rozansky | 2026-06-16 | Isabel Mahon | edited_not_ticked |
| Canada | Isabel | Port Edward LNG Terminal | -- | cancelled | 2025-06-18 | Robert Rozansky | 2026-06-16 | Isabel Mahon | edited_not_ticked |
| Canada | Isabel | Texada LNG Terminal | -- | cancelled | 2025-06-25 | Robert Rozansky | 2025-06-25 | Robert Rozansky | stale |
| Canada | Isabel | WCC LNG Terminal | T1-T6 | cancelled | 2025-06-18 | Robert Rozansky | 2026-06-11 | Isabel Mahon | edited_not_ticked |
| Papua New Guinea | Isabel | Pandora FLNG Terminal | -- | cancelled | 2025-06-05 | Natalia Fretz | 2026-06-26 | Isabel Mahon | edited_not_ticked |
| Papua New Guinea | Isabel | Papua New Guinea LNG Terminal | T3 | cancelled | 2025-06-04 | Natalia Fretz | 2026-06-29 | Isabel Mahon | edited_not_ticked |
| China | Maggie | Dalian LNG Terminal | Phase 1 | operating | 2025-06-02 | Aiqun Yu | 2025-06-02 | Aiqun Yu | stale |
| China | Maggie | Dalian LNG Terminal | Phase 2 | operating | 2025-06-02 | Aiqun Yu | 2025-06-02 | Aiqun Yu | stale |
| China | Maggie | Fujian LNG Terminal | Phase I | operating | 2025-06-04 | Aiqun Yu | 2025-10-06 | Robert Rozansky | stale |
| China | Maggie | Fujian LNG Terminal | Phase II (Expansion) | operating | 2025-06-04 | Aiqun Yu | 2025-10-06 | Robert Rozansky | stale |
| China | Maggie | Guangdong Dapeng LNG Terminal | Phase 1 | operating | 2025-05-12 | Aiqun Yu | 2026-06-06 | Baird Langenbrunner | edited_not_ticked |
| China | Maggie | Hainan LNG Terminal | Phase I | operating | 2025-06-11 | Aiqun Yu | 2026-04-06 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Hainan Shennan LNG Storage Facility | Phase 1 | operating | 2025-06-11 | Aiqun Yu | 2025-06-11 | Aiqun Yu | stale |
| China | Maggie | Pinghu LNG Terminal | -- | operating | 2025-05-21 | Aiqun Yu | 2025-05-21 | Aiqun Yu | stale |
| China | Maggie | Qidong LNG Terminal | Phase 1 | operating | 2025-05-15 | Aiqun Yu | 2025-10-09 | Robert Rozansky | stale |
| China | Maggie | Qidong LNG Terminal | Phase 2 | operating | 2025-05-20 | Aiqun Yu | 2025-10-09 | Robert Rozansky | stale |
| China | Maggie | Qidong LNG Terminal | Phase 3 | operating | 2025-05-15 | Aiqun Yu | 2025-10-09 | Robert Rozansky | stale |
| China | Maggie | Qidong LNG Terminal | Phase 4 | operating | 2024-02-01 | Aiqun Yu | 2025-10-09 | Robert Rozansky | stale |
| China | Maggie | Qidong LNG Terminal | Phase 5 | operating | 2025-05-15 | Aiqun Yu | 2025-10-09 | Robert Rozansky | stale |
| China | Maggie | Rudong LNG Terminal (PetroChina) | Phase 1 | operating | 2025-05-14 | Aiqun Yu | 2026-04-04 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Rudong LNG Terminal (PetroChina) | Phase 3 | operating | 2025-05-14 | Aiqun Yu | 2026-04-04 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Shandong LNG Terminal | Phase 1 | operating | 2025-05-29 | Aiqun Yu | 2026-04-09 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Shandong LNG Terminal | Phase 2 | operating | 2025-05-29 | Aiqun Yu | 2026-04-09 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Shandong LNG Terminal | Phase 3 | operating | 2025-05-29 | Aiqun Yu | 2026-04-09 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Shenzhen Diefu CNOOC LNG Terminal | Phase 1 | operating | 2025-05-08 | Aiqun Yu | 2025-05-08 | Aiqun Yu | stale |
| China | Maggie | Tangshan LNG Terminal (PetroChina) | Phase 1 | operating | 2025-06-05 | Aiqun Yu | 2026-04-13 | Robert Rozansky | edited_not_ticked |
| China | Maggie | Tangshan LNG Terminal (PetroChina) | Phase 2 | operating | 2025-06-05 | Aiqun Yu | 2026-04-13 | Robert Rozansky | edited_not_ticked |
| China | Maggie | Tangshan LNG Terminal (PetroChina) | Phase 3  (Expansion） | operating | 2025-06-05 | Aiqun Yu | 2026-04-13 | Robert Rozansky | edited_not_ticked |
| China | Maggie | Tangshan LNG Terminal (Xintian) | Phase 1 | operating | 2025-06-05 | Aiqun Yu | 2026-06-06 | Baird Langenbrunner | edited_not_ticked |
| China | Maggie | Tianjin LNG Terminal (Beijing Gas Group) | Phase 1 | operating | 2025-06-11 | Aiqun Yu | 2026-05-28 | Baird Langenbrunner | edited_not_ticked |
| China | Maggie | Tianjin LNG Terminal (Beijing Gas Group) | Phase 2 | operating | 2025-06-11 | Aiqun Yu | 2026-05-28 | Baird Langenbrunner | edited_not_ticked |
| China | Maggie | Tianjin LNG Terminal (Beijing Gas Group) | Phase 3 | operating | 2025-06-11 | Aiqun Yu | 2026-05-28 | Baird Langenbrunner | edited_not_ticked |
| China | Maggie | Tianjin LNG Terminal (PipeChina) | Phase 1 replacement | operating | 2025-06-11 | Aiqun Yu | 2026-08-03 | Natalia Fretz | edited_not_ticked |
| China | Maggie | Tianjin LNG Terminal (PipeChina) | Phase 2 | operating | 2025-06-11 | Aiqun Yu | 2026-08-03 | Natalia Fretz | edited_not_ticked |
| China | Maggie | Tianjin LNG Terminal (Sinopec) | Phase 1 | operating | 2025-06-11 | Aiqun Yu | 2026-04-05 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Tianjin LNG Terminal (Sinopec) | Phase 2 | operating | 2025-06-11 | Aiqun Yu | 2026-04-05 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Wenzhou Huagang LNG Terminal | -- | operating | 2025-05-26 | Aiqun Yu | 2026-06-06 | Baird Langenbrunner | edited_not_ticked |
| China | Maggie | Wenzhou LNG Terminal | -- | operating | 2025-05-26 | Aiqun Yu | 2025-05-26 | Aiqun Yu | stale |
| China | Maggie | Wuhaogou LNG Storage Facility | Phase 1 | operating | 2025-06-12 | Aiqun Yu | 2025-06-12 | Aiqun Yu | stale |
| China | Maggie | Wuhaogou LNG Storage Facility | Phase 2 | operating | 2025-06-12 | Aiqun Yu | 2025-06-12 | Aiqun Yu | stale |
| China | Maggie | Yancheng LNG Terminal | Phase 1 | operating | 2025-05-20 | Aiqun Yu | 2026-04-05 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Yancheng LNG Terminal | Phase 1 Expansion | operating | 2025-05-20 | Aiqun Yu | 2026-04-05 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Zhangzhou LNG Terminal | Phase 1 | operating | 2025-05-07 | Aiqun Yu | 2025-05-07 | Aiqun Yu | stale |
| China | Maggie | Zhejiang Ningbo LNG Terminal | Phase 1 | operating | 2025-05-26 | Aiqun Yu | 2026-04-01 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Zhejiang Ningbo LNG Terminal | Phase 2 | operating | 2025-05-26 | Aiqun Yu | 2026-04-01 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Zhoushan LNG Terminal | Phase 1 | operating | 2025-05-26 | Aiqun Yu | 2026-04-08 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Zhoushan LNG Terminal | Phase 2 | operating | 2025-05-26 | Aiqun Yu | 2026-04-08 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Zhoushan LNG Terminal | Phase 3 | operating | 2025-05-26 | Aiqun Yu | 2026-04-08 | Maggie Zheng | edited_not_ticked |
| China | Maggie | Zhuhai LNG Terminal | Phase 1 | operating | 2024-02-14 | Aiqun Yu | 2026-03-26 | Maggie Zheng | edited_not_ticked |
| Taiwan | Maggie | Taichung LNG Terminal | Phase 2 | operating | 2025-06-17 | Aiqun Yu | 2026-03-12 | Maggie Zheng | edited_not_ticked |
| Taiwan | Maggie | Taoyuan LNG Terminal | Phase 1 | operating | 2025-06-23 | Aiqun Yu | 2026-03-13 | Maggie Zheng | edited_not_ticked |
| Italy | Natalia | Brindisi LNG Terminal | -- | cancelled | 2025-07-16 | Robert Rozansky | 2025-07-16 | Robert Rozansky | stale |
| Italy | Natalia | Panigaglia LNG Terminal | Expansion I | cancelled | 2025-07-16 | Robert Rozansky | 2026-07-14 | Natalia Fretz | edited_not_ticked |
| Italy | Natalia | Priolo Augusta LNG Terminal | -- | cancelled | 2025-07-16 | Robert Rozansky | 2026-07-15 | Natalia Fretz | edited_not_ticked |
| Italy | Natalia | Trieste Monfalcone LNG Terminal | -- | cancelled | 2025-07-17 | Robert Rozansky | 2026-07-15 | Natalia Fretz | edited_not_ticked |
| Italy | Natalia | Zaule LNG Terminal | -- | cancelled | 2025-07-17 | Robert Rozansky | 2025-07-17 | Robert Rozansky | stale |
| Spain | Natalia | Gran Canaria LNG Terminal | -- | cancelled | 2025-06-18 | Isabel Mahon | 2025-06-18 | Isabel Mahon | stale |
| Spain | Natalia | Mugardos LNG Terminal | Expansion | cancelled | 2025-07-17 | Robert Rozansky | 2026-07-20 | Natalia Fretz | edited_not_ticked |
| Spain | Natalia | Tenerife LNG Terminal | -- | cancelled | 2025-06-18 | Isabel Mahon | 2025-06-18 | Isabel Mahon | stale |
| United States | Rob | Alaska Japan LNG Terminal | -- | cancelled | 2025-07-24 | Robert Rozansky | 2025-07-24 | Robert Rozansky | stale |
| United States | Rob | Alturas LNG Terminal | -- | cancelled | 2025-07-24 | Robert Rozansky | 2025-07-24 | Robert Rozansky | stale |
| United States | Rob | American Coast LNG Terminal | Phase 1 | cancelled | 2025-07-24 | Robert Rozansky | 2025-10-09 | Robert Rozansky | stale |
| United States | Rob | American Coast LNG Terminal | Phase 2 | cancelled | 2025-07-24 | Robert Rozansky | 2025-10-09 | Robert Rozansky | stale |
| United States | Rob | American LNG Titusville Terminal | -- | cancelled | 2025-07-24 | Robert Rozansky | never | — | stale |
| United States | Rob | Annova LNG Terminal | T1-T6 | cancelled | 2025-07-24 | Robert Rozansky | 2025-07-24 | Robert Rozansky | stale |
| United States | Rob | Avocet FLNG Terminal | -- | cancelled | 2025-07-24 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Barca LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Battery Rock LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2026-07-01 | Isabel Mahon | edited_not_ticked |
| United States | Rob | Bay Crossing LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Beacon Port LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Bienville FSRU | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Bradwood Landing LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Broadwater FSRU | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | CE FLNG Terminal | T1-T2 | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Calais LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Calhoun LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Calypso LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Casotte Landing LNG Terminal | -- | cancelled | 2025-07-25 | Robert Rozansky | 2025-07-25 | Robert Rozansky | stale |
| United States | Rob | Compass Port LNG Terminal | -- | cancelled | 2025-07-28 | Robert Rozansky | 2025-07-28 | Robert Rozansky | stale |
| United States | Rob | Creole Trail LNG Terminal | -- | cancelled | 2025-07-28 | Robert Rozansky | 2025-07-28 | Robert Rozansky | stale |
| United States | Rob | Crown Landing LNG Terminal | -- | cancelled | 2025-07-31 | Robert Rozansky | 2025-07-31 | Robert Rozansky | stale |
| United States | Rob | Delta LNG Terminal | Phase 1 (T1–T18) | cancelled | 2025-07-28 | Robert Rozansky | 2025-07-29 | Robert Rozansky | stale |
| United States | Rob | Delta LNG Terminal | Phase 2 (T19–T36) | cancelled | 2025-07-28 | Robert Rozansky | 2025-07-29 | Robert Rozansky | stale |
| United States | Rob | Downeast LNG Terminal | Export | cancelled | 2025-07-29 | Robert Rozansky | 2026-04-07 | Maisie Bird | edited_not_ticked |
| United States | Rob | Downeast LNG Terminal | Import | cancelled | 2025-07-29 | Robert Rozansky | 2026-04-07 | Maisie Bird | edited_not_ticked |
| United States | Rob | Eos FLNG Terminal | -- | cancelled | 2025-07-30 | Robert Rozansky | 2025-07-30 | Robert Rozansky | stale |
| United States | Rob | Floridian LNG Terminal | -- | cancelled | 2025-07-30 | Robert Rozansky | 2025-07-30 | Robert Rozansky | stale |
| United States | Rob | Fourchon LNG Terminal | Phase 1 | cancelled | 2025-07-30 | Robert Rozansky | 2025-07-30 | Robert Rozansky | stale |
| United States | Rob | Fourchon LNG Terminal | Phase 2 | cancelled | 2025-07-30 | Robert Rozansky | 2025-07-30 | Robert Rozansky | stale |
| United States | Rob | G2 LNG Terminal | T1-T10 | cancelled | 2025-07-30 | Robert Rozansky | 2026-07-10 | Baird Langenbrunner | edited_not_ticked |
| United States | Rob | Galveston Bay LNG Terminal | T1-T3 | cancelled | 2025-07-30 | Robert Rozansky | 2025-07-30 | Robert Rozansky | stale |
| United States | Rob | Gulf Gateway Deepwater Port LNG Terminal | -- | retired | 2025-07-31 | Robert Rozansky | 2025-10-14 | admin | stale |
| United States | Rob | Ingleside Energy LNG Terminal | -- | cancelled | 2025-07-31 | Robert Rozansky | 2025-07-31 | Robert Rozansky | stale |
| United States | Rob | Jordan Cove LNG Terminal | T1-T5 | cancelled | 2025-07-31 | Robert Rozansky | 2025-07-31 | Robert Rozansky | stale |
| United States | Rob | Keyspan LNG Terminal | -- | cancelled | 2025-07-31 | Robert Rozansky | 2025-07-31 | Robert Rozansky | stale |
| United States | Rob | Liberty FSRU | -- | cancelled | 2025-09-25 | Robert Rozansky | never | — | stale |
| United States | Rob | Long Beach LNG Terminal | -- | cancelled | 2025-09-25 | Robert Rozansky | never | — | stale |
| United States | Rob | Louisiana LNG Terminal | T1-T2 | cancelled | 2025-09-25 | Robert Rozansky | 2026-07-06 | Isabel Mahon | edited_not_ticked |
| United States | Rob | Main Pass Energy Hub FLNG Terminal | T1-T6 | cancelled | 2025-09-25 | Robert Rozansky | 2025-09-25 | Robert Rozansky | stale |
| United States | Rob | New Fortress Grand Isle FLNG Terminal | -- | cancelled | 2025-09-25 | Robert Rozansky | 2025-09-25 | Robert Rozansky | stale |
| United States | Rob | New Fortress Wyalusing LNG Terminal | T1-T2 | cancelled | 2025-09-26 | Robert Rozansky | 2025-09-26 | Robert Rozansky | stale |
| United States | Rob | Nopetro LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | 2025-09-26 | Robert Rozansky | stale |
| United States | Rob | OceanWay LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Oregon LNG Terminal | Export Terminal (T1-T2) | cancelled | 2025-09-26 | Robert Rozansky | 2025-09-26 | Robert Rozansky | stale |
| United States | Rob | Oregon LNG Terminal | Import Terminal | cancelled | 2025-09-26 | Robert Rozansky | 2025-09-26 | Robert Rozansky | stale |
| United States | Rob | Oxnard LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Point Comfort LNG Terminal | T1-T2 | cancelled | 2025-09-26 | Robert Rozansky | 2025-09-26 | Robert Rozansky | stale |
| United States | Rob | Pointe LNG Terminal | T1-T3 | cancelled | 2025-09-26 | Robert Rozansky | 2025-09-26 | Robert Rozansky | stale |
| United States | Rob | Port Dolphin LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Port Esperanza FSRU | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Port Lavaca FLNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Port Pelican LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Quoddy Bay LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Safe Harbor Energy LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | 2025-09-26 | Robert Rozansky | stale |
| United States | Rob | South Texas LNG Terminal | T1-T2 | cancelled | 2025-09-26 | Robert Rozansky | 2026-07-06 | Isabel Mahon | edited_not_ticked |
| United States | Rob | Sparrows Point LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Strom LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Vista Del Sol LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |
| United States | Rob | Weaver's Cove LNG Terminal | -- | cancelled | 2025-09-26 | Robert Rozansky | never | — | stale |

