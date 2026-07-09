"""
Reference universe of countries that could plausibly host an LNG terminal.

This is the comparison set for the coverage-gap check in completeness_sweep.py.
The whole research workflow (dedup_index.py, the discovery sweep, the regional
fan-out) is keyed off countries that ALREADY appear in the GEM export — so a
country with ZERO GEM LNG terminals but a real new proposal (a first-time
importer signing an FSRU charter, say) is invisible to every other tool. Diffing
this universe against the GEM-covered set surfaces those blind spots.

WHY COASTAL: every LNG terminal form (onshore liquefaction/regas, FSRU/FSU/FLNG,
deepwater port) needs marine or navigable-waterway access. Landlocked countries
effectively cannot host one, so including them would only add noise to the
worklist. Landlocked states are therefore omitted here by construction (a few
river-served edge cases — e.g. inland terminals on a major navigable river — are
the kind of thing to add by hand if one ever appears).

THIS LIST IS THE TUNABLE KNOB. It is intentionally broad (it includes micro- and
island states that will realistically never build LNG) so the check errs toward
"don't miss anything" — the discovery agent triages the worklist, the list does
not pre-judge. If completeness_sweep reports a GEM-covered country that is NOT in
this set (`gem_countries_outside_reference`), that's a signal to ADD it here (or a
name-normalization mismatch to fix) — not to ignore.

Names are stored in plain English; completeness_sweep runs both these and the GEM
`Country/Area` values through normalize.normalize_country() before comparing, so
canonical/alias differences (USA↔United States, etc.) fold out.
"""

# Coastal sovereign states + LNG-relevant territories, grouped by region for
# review. Order is irrelevant (consumed as a set).
COASTAL_COUNTRIES = {
    # --- Africa ---
    "Algeria", "Angola", "Benin", "Cameroon", "Cape Verde", "Comoros",
    "Republic of the Congo", "Democratic Republic of the Congo", "Cote d'Ivoire",
    "Djibouti", "Egypt", "Equatorial Guinea", "Eritrea", "Gabon", "Gambia",
    "Ghana", "Guinea", "Guinea-Bissau", "Kenya", "Liberia", "Libya",
    "Madagascar", "Mauritania", "Mauritius", "Morocco", "Mozambique", "Namibia",
    "Nigeria", "Sao Tome and Principe", "Senegal", "Seychelles", "Sierra Leone",
    "Somalia", "South Africa", "Sudan", "Tanzania", "Togo", "Tunisia",
    "Western Sahara",

    # --- Americas ---
    "Antigua and Barbuda", "Argentina", "Bahamas", "Barbados", "Belize",
    "Brazil", "Canada", "Chile", "Colombia", "Costa Rica", "Cuba", "Dominica",
    "Dominican Republic", "Ecuador", "El Salvador", "Grenada", "Guatemala",
    "Guyana", "Haiti", "Honduras", "Jamaica", "Mexico", "Nicaragua", "Panama",
    "Peru", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Vincent and the Grenadines", "Suriname", "Trinidad and Tobago",
    "United States", "Uruguay", "Venezuela",
    # territories / dependencies
    "Puerto Rico", "Aruba", "Curacao", "Bermuda", "Greenland",
    "Falkland Islands",

    # --- Asia / Middle East ---
    "Bahrain", "Bangladesh", "Brunei", "Cambodia", "China", "Hong Kong",
    "India", "Indonesia", "Iran", "Iraq", "Israel", "Japan", "Jordan",
    "Kuwait", "Lebanon", "Malaysia", "Maldives", "Myanmar", "North Korea",
    "Oman", "Pakistan", "Philippines", "Qatar", "Saudi Arabia", "Singapore",
    "South Korea", "Sri Lanka", "Syria", "Taiwan", "Thailand", "Timor-Leste",
    "Turkey", "United Arab Emirates", "Vietnam", "Yemen", "Georgia", "Russia",

    # --- Europe ---
    "Albania", "Belgium", "Bosnia and Herzegovina", "Bulgaria", "Croatia",
    "Cyprus", "Denmark", "Estonia", "Finland", "France", "Germany", "Greece",
    "Iceland", "Ireland", "Italy", "Latvia", "Lithuania", "Malta", "Monaco",
    "Montenegro", "Netherlands", "Norway", "Poland", "Portugal", "Romania",
    "Slovenia", "Spain", "Sweden", "Ukraine", "United Kingdom", "Gibraltar",

    # --- Oceania ---
    "Australia", "Fiji", "Kiribati", "Marshall Islands",
    "Federated States of Micronesia", "Nauru", "New Zealand", "Palau",
    "Papua New Guinea", "Samoa", "Solomon Islands", "Tonga", "Tuvalu",
    "Vanuatu", "New Caledonia", "French Polynesia", "Guam",

    # --- Hand-added edge cases (GEM-covered despite no open-ocean coast; see
    # docstring — a gem_countries_outside_reference hit means ADD, not ignore) ---
    "Botswana",      # landlocked; GEM tracks a domestic-linked LNG project (Serowe)
    "Turkmenistan",  # Caspian-coastal only; GEM-covered
}
