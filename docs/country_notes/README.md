# Country research notes

One file per country. Use `_template.md` as the starting point for new countries.

## How to use

For each country in scope of a batch:

1. **Before searching**, check `<country>.md` for:
   - Known regulator URLs
   - Trade press patterns that have worked
   - Source-tier exceptions
   - Recurring gotchas
   - Notes from prior batches

2. **During the batch**, take notes on new resources, search patterns, and findings.

3. **At batch end**, stage them in the `country_notes_contributions` sheet of
   the batch xlsx. After review, the user transfers them into the country file.

## Currently seeded

The countries below have starter content from the original scaffolding.
Countries not listed should be created from `_template.md` when first researched.

- algeria, australia, bangladesh, brazil, canada
- china, croatia, egypt, germany, hong-kong
- india, indonesia, japan, mexico, new-zealand
- nigeria, pakistan, papua-new-guinea, philippines
- qatar, russia, south-korea, taiwan, united-states, vietnam

## Coverage status (GEM Q2 2026 export)

The countries with the largest GEM terminal coverage are also the highest-leverage
research targets:

| Country | Terminal count |
|---|---|
| United States | 208 |
| China | 158 |
| Japan | 51 |
| Canada | 48 |
| Australia, Russia | 46 each |
| Indonesia | 42 |
| India | 39 |
| Vietnam | 33 |
| Brazil | 26 |
| Mexico, Nigeria | 25 each |
| Papua New Guinea | 24 |
| Italy | 19 |

## Recurring multi-country patterns

Patterns that appear in many countries — note here once rather than in each
country file.

- **FSRU vessel reassignments**: Brazil, Germany, Bangladesh, Pakistan, and
  others frequently see vessel swaps. Always trigger the FSRU sync rule
  (see `CLAUDE.md`).
- **JV ownership complexity**: Mozambique, Angola, Equatorial Guinea, Nigeria,
  Egypt — large LNG export projects almost always have multi-sponsor JVs.
  List each partner with percentage; don't create a JV entity unless it's a
  real legal entity (per Discovery SOP §9).
- **Dead-and-revived proposals**: Common in countries that went through
  2014-2016 oil price collapse + 2020 COVID slowdown + 2022 European energy
  crisis — many proposals shelved and revived. Per `docs/reference/lifecycle_rules.md`,
  same-fundamentals revivals stay on same unit; different fundamentals = new unit.
- **Government procurement → sponsor selection**: Common in emerging-import
  countries (Sri Lanka, Cambodia, Senegal). Pre-sponsor-selection phase
  often fails the methodology's "sufficient information to add" threshold;
  track in `monitor_list` instead.
