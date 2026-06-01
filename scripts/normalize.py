"""
Canonical name normalization for countries, entities (owners/operators/parents),
and capacity units. Used by dedup_index.py, report_diff.py, and build_review_package.py
to make matching consistent across batches.

Without this, "TotalEnergies" vs "Total Energies" vs "Total" would be treated as
three different entities, and cluster-coherence checks would over- or under-merge.

The mappings are conservative — only canonicalize where there's no ambiguity.
When a new entity/country appears in a batch and isn't in the map, add it here
AND to the corresponding reference markdown file rather than papering over it.

Returns canonical short tags (e.g. 'totalenergies', 'qatarenergy', 'cheniere').
If the input doesn't match any known variant, returns the input lowercased
and stripped — so unknown entities still cluster against themselves.
"""
import re
import unicodedata


# --- Diacritic folding (Latin-script matching only) ---
#
# GIIGNL writes terminal/country names WITHOUT diacritics ("Pecem", "Swinoujscie",
# "Turkiye"), while GEM stores them WITH ("Pecém", "Świnoujście", "Türkiye"). The
# matcher compares normalized token forms, so accent-variant names must fold to the
# same ASCII spelling or the same terminal lands in two buckets (a false
# "GIIGNL has, GEM doesn't" discovery candidate).
#
# NFKD decomposes most accented Latin letters into base + combining mark, which we
# then drop. A handful of letters carry the diacritic in the codepoint itself and
# do NOT decompose under NFKD (ø, đ, ł, ı, ß, ...) — those need an explicit map.
# Applied ONLY in the Latin-script normalization paths; non-Latin scripts go
# through transliterate_to_english instead (pinyin output is already ASCII, so
# folding it is a harmless no-op and never corrupts CJK segmentation).
_DIACRITIC_FALLBACKS = {
    "ø": "o", "Ø": "O",
    "đ": "d", "Đ": "D",
    "ð": "d", "Ð": "D",
    "ł": "l", "Ł": "L",
    "ı": "i", "İ": "I",
    "ß": "ss",
    "æ": "ae", "Æ": "AE",
    "œ": "oe", "Œ": "OE",
    "þ": "th", "Þ": "TH",
}


def _strip_diacritics(s):
    """Fold Latin diacritics to their ASCII base letters.

    NFKD-decompose, drop combining marks (Unicode category 'Mn'), and apply an
    explicit fallback map for letters NFKD leaves intact (ø→o, đ→d, ł→l, ı→i,
    ß→ss, ...). CJK and other non-Latin codepoints are untouched: NFKD does not
    introduce combining marks for them and they aren't in the fallback map, so
    they pass through unchanged.
    """
    if s is None:
        return ""
    s = str(s)
    # Explicit fallbacks first (these don't decompose under NFKD).
    if any(c in _DIACRITIC_FALLBACKS for c in s):
        s = "".join(_DIACRITIC_FALLBACKS.get(c, c) for c in s)
    decomposed = unicodedata.normalize("NFKD", s)
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


# --- Country normalization ---

# Canonical country names (left side) and their variants
_COUNTRY_MAP = {
    "united states": "united states",
    "usa": "united states",
    "us": "united states",
    "u.s.": "united states",
    "u.s": "united states",
    "u.s.a.": "united states",
    "u.s.a": "united states",
    "america": "united states",
    "united kingdom": "united kingdom",
    "uk": "united kingdom",
    "great britain": "united kingdom",
    "russia": "russia",
    "russian federation": "russia",
    "south korea": "south korea",
    "korea, south": "south korea",
    "republic of korea": "south korea",
    "korea": "south korea",  # GIIGNL labels South Korea simply "Korea"
    "north korea": "north korea",
    "democratic people's republic of korea": "north korea",
    "dprk": "north korea",
    "china": "china",
    "people's republic of china": "china",
    "prc": "china",
    "taiwan": "taiwan",
    "republic of china": "taiwan",
    "japan": "japan",
    "uae": "united arab emirates",
    "u.a.e.": "united arab emirates",
    "united arab emirates": "united arab emirates",
    "ivory coast": "côte d'ivoire",
    "cote d'ivoire": "côte d'ivoire",
    "côte d'ivoire": "côte d'ivoire",
    "burma": "myanmar",
    "myanmar": "myanmar",
    "cape verde": "cape verde",
    "cabo verde": "cape verde",
    "swaziland": "eswatini",
    "eswatini": "eswatini",
    "trinidad": "trinidad and tobago",
    "trinidad and tobago": "trinidad and tobago",
    # GIIGNL abbreviates a few full country names GEM keeps in long form.
    # "Congo" in GIIGNL = the Republic of the Congo (Eni's Tango/Nguya FLNG sit at
    # Pointe-Noire, RoC) — kept distinct from the DRC, which has no LNG terminal.
    "congo": "republic of the congo",
    "republic of the congo": "republic of the congo",
    "congo-brazzaville": "republic of the congo",
    "dr congo": "democratic republic of the congo",
    "drc": "democratic republic of the congo",
    "democratic republic of the congo": "democratic republic of the congo",
    # GIIGNL labels the Dominican Republic simply "Dominican".
    "dominican": "dominican republic",
    "dominican republic": "dominican republic",
    "papua new guinea": "papua new guinea",
    "png": "papua new guinea",
    "north macedonia": "north macedonia",
    "macedonia": "north macedonia",
    "czech republic": "czech republic",
    "czechia": "czech republic",
    "turkey": "türkiye",
    "türkiye": "türkiye",
    "turkiye": "türkiye",
    "viet nam": "vietnam",
    "vietnam": "vietnam",
    # Region/area names that GEM uses
    "puerto rico": "puerto rico",
    "hong kong": "hong kong",
    "macao": "macao",
    "macau": "macao",
}


# --- Entity normalization ---
# See entity_canonical_map.md for the human-readable version.
_ENTITY_MAP = {
    # US-focused exporters
    "cheniere energy": "cheniere",
    "cheniere": "cheniere",
    "cheniere energy partners": "cheniere",
    "venture global lng": "venture-global",
    "venture global": "venture-global",
    "vg lng": "venture-global",
    "nextdecade": "nextdecade",
    "nextdecade corp": "nextdecade",
    "sempra": "sempra",
    "sempra infrastructure": "sempra",
    "sempra energy": "sempra",
    "sempra lng": "sempra",
    "freeport lng": "freeport-lng",
    "freeport lng development": "freeport-lng",
    "tellurian": "tellurian",
    "tellurian inc": "tellurian",
    "driftwood lng": "tellurian",
    "energy transfer": "energy-transfer",
    "energy transfer lng": "energy-transfer",
    "lake charles lng": "energy-transfer",
    "new fortress energy": "new-fortress",
    "nfe": "new-fortress",
    "newfortress": "new-fortress",
    "glenfarne": "glenfarne",
    "glenfarne group": "glenfarne",
    "glenfarne energy transition": "glenfarne",
    "commonwealth lng": "commonwealth",
    "commonwealth": "commonwealth",

    # Integrated majors
    "totalenergies": "totalenergies",
    "total": "totalenergies",
    "total energies": "totalenergies",
    "total sa": "totalenergies",
    "shell": "shell",
    "royal dutch shell": "shell",
    "shell plc": "shell",
    "bp": "bp",
    "british petroleum": "bp",
    "bp plc": "bp",
    "exxonmobil": "exxonmobil",
    "exxon mobil": "exxonmobil",
    "exxon": "exxonmobil",
    "chevron": "chevron",
    "chevron corp": "chevron",
    "conocophillips": "conocophillips",
    "conoco phillips": "conocophillips",
    "eni": "eni",
    "eni spa": "eni",
    "equinor": "equinor",
    "statoil": "equinor",
    "repsol": "repsol",
    "repsol sa": "repsol",
    "galp": "galp",
    "galp energia": "galp",

    # State-linked / NOCs
    "qatarenergy": "qatarenergy",
    "qatar energy": "qatarenergy",
    "qatar petroleum": "qatarenergy",
    "qp": "qatarenergy",
    "adnoc": "adnoc",
    "abu dhabi national oil company": "adnoc",
    "adnoc gas": "adnoc",
    "adnoc lng": "adnoc",
    "saudi aramco": "aramco",
    "aramco": "aramco",
    "petronas": "petronas",
    "petroliam nasional berhad": "petronas",
    "pertamina": "pertamina",
    "pt pertamina": "pertamina",
    "pertamina hulu": "pertamina",
    "cnpc": "cnpc",
    "china national petroleum corp": "cnpc",
    "petrochina": "cnpc",
    "sinopec": "sinopec",
    "cnooc": "cnooc",
    "china national offshore oil corp": "cnooc",
    "kogas": "kogas",
    "korea gas corporation": "kogas",
    "jera": "jera",
    "jera co": "jera",
    "inpex": "inpex",
    "inpex corp": "inpex",
    "gazprom": "gazprom",
    "gazprom export": "gazprom",
    "novatek": "novatek",
    "ngc": "ngc-trinidad",
    "national gas company of trinidad": "ngc-trinidad",
    "nlng": "nlng",
    "nigeria lng": "nlng",
    "bgt": "bgt",
    "bonny gas transport": "bgt",
    "sonangol": "sonangol",
    "sonangol ep": "sonangol",
    "sonatrach": "sonatrach",
    "egas": "egas",
    "egyptian natural gas holding": "egas",
    "egpc": "egpc",
    "egyptian general petroleum corp": "egpc",
    "pdvsa": "pdvsa",
    "petroleos de venezuela": "pdvsa",
    "ypf": "ypf",
    "enarsa": "enarsa",
    "ieasa": "enarsa",
    "petrobras": "petrobras",
    "petroleo brasileiro": "petrobras",
    "ecopetrol": "ecopetrol",
    "bapco": "bapco",
    "bapco energies": "bapco",
    "nnpc": "nnpc",
    "nigerian national petroleum corporation": "nnpc",
    "gnpc": "gnpc",
    "socar": "socar",
    "tpao": "tpao",
    "botas": "botas",

    # FSRU operators
    "excelerate energy": "excelerate",
    "excelerate": "excelerate",
    "höegh evi": "hoegh-evi",
    "hoegh evi": "hoegh-evi",
    "höegh lng": "hoegh-evi",
    "hoegh lng": "hoegh-evi",
    "höegh": "hoegh-evi",
    "bw lng": "bw-lng",
    "bw group": "bw-lng",
    "energos infrastructure": "energos",
    "energos": "energos",
    # KARMOL is the Karpowership (Karadeniz) + Mitsui O.S.K. Lines (MOL) FSRU joint
    # venture. GEM tags KARMOL terminals with the brand "KARMOL"; GIIGNL often
    # lists the two JV parents instead ("MOL ..., Karadeniz Holding ..." at
    # Sepetiba). These canonicalize to DISTINCT tokens on purpose — Karpowership
    # and MOL each operate non-KARMOL assets, so collapsing them into "karmol"
    # would over-merge. The owner delta (GEM "karmol" vs report "karpowership"/"mol")
    # is therefore a real, reviewer-visible naming note; the terminal match itself
    # is carried by the FSRU vessel-name corroboration (see report_diff
    # _fsru_vessel_match), not owner overlap.
    "karmol": "karmol",
    "karmol ltd": "karmol",
    "karpowership": "karpowership",
    "karadeniz holding": "karpowership",
    "golar lng": "golar",
    "golar": "golar",
    "flex lng": "flex-lng",
    "mol": "mol",
    "mitsui osk lines": "mol",
    "mitsui o.s.k. lines": "mol",

    # European import sponsors
    "engie": "engie",
    "gdf suez": "engie",
    "naturgy": "naturgy",
    "naturgy energy group": "naturgy",
    "gas natural fenosa": "naturgy",
    "snam": "snam",
    "snam spa": "snam",
    "fluxys": "fluxys",
    "fluxys belgium": "fluxys",
    "enagas": "enagas",
    "enagás": "enagas",
    "enagas sa": "enagas",
    "rwe": "rwe",
    "rwe ag": "rwe",
    "uniper": "uniper",
    "uniper se": "uniper",
    "national grid": "national-grid",

    # Asian state utilities / IPPs
    "tepco": "tepco",
    "tokyo electric power": "tepco",
    "chubu electric power": "chubu",
    "kansai electric": "kansai-electric",
    "kansai electric power": "kansai-electric",
    "osaka gas": "osaka-gas",
    "daigas": "osaka-gas",
    "tokyo gas": "tokyo-gas",
    "cpc corporation taiwan": "cpc-taiwan",
    "cpc": "cpc-taiwan",
    "pgn": "pgn-indonesia",
    "perusahaan gas negara": "pgn-indonesia",
    "ptt": "ptt",
    "gail": "gail-india",
    "petronet lng": "petronet",
    "petronet": "petronet",

    # North American import/export sponsors
    "fortisbc": "fortisbc",
    "fortisbc energy": "fortisbc",
    "fortisbc energy inc": "fortisbc",

    # African
    "kosmos energy": "kosmos",
    "kosmos": "kosmos",
    "marathon": "marathon",
    "marathon oil": "marathon",
    "smhpm": "smhpm",
    "société mauritanienne des hydrocarbures": "smhpm",
    "petrosen": "petrosen",
    "enh": "enh",
    "empresa nacional de hidrocarbonetos": "enh",
}


# --- Capacity unit normalization ---

# Canonical conversion factors to mtpa (for LNG)
# 1 mtpa LNG ~ 1.36 bcm/y natural gas (industry standard)
# 1 mtpa LNG ~ 130 bcf/y (1 bcf/d * 365 / ~2.74)
_CAPACITY_TO_MTPA = {
    "mtpa": 1.0,
    "mt/y": 1.0,
    "million tonnes per annum": 1.0,
    "million tons per annum": 1.0,
    "tpa": 1.0e-6,
    "bcm/y": 1.0 / 1.36,  # 1 bcm/y = ~0.735 mtpa
    "bcm/year": 1.0 / 1.36,
    "billion cubic meters per year": 1.0 / 1.36,
    "mmtpa": 1.0,  # synonym for mtpa
    "bcf/d": 365 / 130,  # 1 bcf/d ~ 2.81 mtpa
    "bcf/day": 365 / 130,
    "mmcf/d": 365 / 130_000,  # 1 MMcf/d ~ 0.00281 mtpa
    "mmcf/day": 365 / 130_000,
}


def _normalize_input(s):
    """Lowercase, fold diacritics, strip, collapse whitespace, remove parens."""
    if s is None:
        return ""
    # Fold diacritics so accent-variant inputs ("Türkiye"/"Turkiye",
    # "Enagás"/"Enagas") collapse to one form before map lookup / clustering.
    s = _strip_diacritics(str(s)).lower().strip()
    # Remove parenthetical content
    s = re.sub(r"\([^)]*\)", "", s).strip()
    # Strip trailing periods
    s = s.rstrip(".")
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s


# _normalize_input folds diacritics, so a map key carrying one (e.g. "türkiye",
# "côte d'ivoire", "enagás") would never be hit by a lookup. Pre-fold the keys so
# both the accented and unaccented spellings resolve. Canonical VALUES keep their
# preferred display form (with diacritics) — they're only compared for equality,
# and both accent-variants now route to the same value.
_COUNTRY_MAP_FOLDED = {_strip_diacritics(k): v for k, v in _COUNTRY_MAP.items()}
_ENTITY_MAP_FOLDED = {_strip_diacritics(k): v for k, v in _ENTITY_MAP.items()}


def normalize_country(s):
    """Return canonical country name. Unknown inputs returned lowercased/stripped."""
    norm = _normalize_input(s)
    if not norm:
        return ""
    if norm in _COUNTRY_MAP_FOLDED:
        return _COUNTRY_MAP_FOLDED[norm]
    return norm


def normalize_entity(s):
    """Return canonical entity tag. Unknown inputs returned lowercased/stripped."""
    norm = _normalize_input(s)
    if not norm:
        return ""
    # Exact match first (keys pre-folded so "höegh"/"hoegh" both resolve).
    if norm in _ENTITY_MAP_FOLDED:
        return _ENTITY_MAP_FOLDED[norm]
    # Substring match (longer keys first to avoid false positives)
    for key in sorted(_ENTITY_MAP_FOLDED.keys(), key=len, reverse=True):
        if norm.startswith(key + " ") or norm == key or " " + key + " " in " " + norm + " ":
            return _ENTITY_MAP_FOLDED[key]
    return norm


def parse_entity_list(s):
    """Parse a comma- or semicolon-separated entity list with optional percentages.
    Returns list of {entity, pct} dicts; pct is None if not present.
    
    Examples:
        "ENI 50%, EGAS 40%, EGPC 10%" -> [{eni,50},{egas,40},{egpc,10}]
        "Cheniere"                     -> [{cheniere,None}]
        "Shell, Total, BP"             -> [{shell,None},{totalenergies,None},{bp,None}]
    """
    if not s:
        return []
    s = str(s).strip()
    parts = re.split(r"[,;]", s)
    out = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Try to extract a trailing percentage in (...) OR [...] brackets, or bare.
        # GEM owner cells use square brackets ("Exxon Mobil Corp [24.15%]"); GIIGNL
        # uses round parens or none ("ExxonMobil 30%") — accept all so the entity
        # name is recovered cleanly either way.
        m = re.search(r"(.+?)\s*[\(\[]?(\d+(?:\.\d+)?)\s*%[\)\]]?\s*$", part)
        if m:
            entity = m.group(1).strip().rstrip("([").strip()
            pct = float(m.group(2))
        else:
            entity = part
            pct = None
        canonical = normalize_entity(entity)
        out.append({"entity": canonical, "raw": entity, "pct": pct})
    return out


def normalize_capacity_unit(s):
    """Return canonical capacity unit. Returns lowercased input if unknown."""
    if s is None:
        return ""
    return str(s).lower().strip()


def to_mtpa(value, unit):
    """Convert a capacity value to MTPA. Returns None if unit unknown."""
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    u = normalize_capacity_unit(unit)
    factor = _CAPACITY_TO_MTPA.get(u)
    if factor is None:
        return None
    return v * factor


def to_bcm_per_y(value, unit):
    """Convert a capacity value to bcm/y. Returns None if unit unknown."""
    mtpa = to_mtpa(value, unit)
    if mtpa is None:
        return None
    return mtpa * 1.36


# --- Transliteration of non-Latin LocalNames into English-matchable variants ---
#
# GEM's LocalNames column holds the locally-used name (e.g. "中石油唐山曹妃甸
# LNG接收站" for Tangshan/PetroChina). To match against industry reports like
# GIIGNL — which use English / Latin-script transliterations like "Caofeidian
# (Tangshan)" — we need to convert the local-script name into something the
# match algorithm can tokenize against the report side.
#
# Supported today: Chinese (via jieba word segmentation + pypinyin per word).
# Future: Japanese (pykakasi), Korean (hangul-romanize), Arabic, etc.
#
# Returns a LIST of candidate transliterations (zero or more), each suitable
# to feed through normalize_terminal_name and use as an alias key.

_HAS_CHINESE_RE = re.compile(r"[一-鿿]")  # CJK Unified Ideographs

# Lazy-imported so the module loads even when jieba/pypinyin are absent.
_jieba = None
_pypinyin = None


def _load_chinese_tools():
    global _jieba, _pypinyin
    if _jieba is None:
        try:
            import jieba as _j
            from pypinyin import lazy_pinyin as _lp
            _jieba = _j
            _pypinyin = _lp
        except ImportError:
            _jieba = False  # sentinel meaning "tried and failed"
    return _jieba and _pypinyin


def _transliterate_chinese(text):
    """Segment Chinese text with jieba, return pinyin per word joined by spaces.

    Per-WORD pinyin (not per-character) so that "曹妃甸" emits "caofeidian"
    as a single 10-char token rather than three 3-char tokens ("cao", "fei",
    "dian") that would fall below the fuzzy-matcher's 4-char token threshold.
    """
    if not _load_chinese_tools():
        return ""
    words = list(_jieba.cut(text))
    parts = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        if _HAS_CHINESE_RE.search(w):
            parts.append("".join(_pypinyin(w)))
        else:
            parts.append(w)
    return " ".join(parts).lower()


def transliterate_to_english(text, language=None):
    """Return a list of English-script candidate forms of `text`.

    Always includes the original (lowercased+stripped). When non-Latin script
    is detected, also includes a transliterated variant suitable for token-
    overlap matching against industry-report extractions.

    `language` is GEM's per-name language label (e.g. "Chinese"), used as a
    hint but the script detection on `text` itself is the authoritative path.
    """
    if not text:
        return []
    # Fold diacritics on the Latin candidate so an accented OtherNames/LocalNames
    # alias matches GIIGNL's accent-stripped spelling. Script detection and the
    # CJK transliteration both run on the ORIGINAL `text` — folding never touches
    # CJK codepoints (no combining marks, not in the fallback map), and pinyin
    # output is already ASCII, so segmentation is unaffected.
    out = [_strip_diacritics(text).lower().strip()]
    if _HAS_CHINESE_RE.search(text) or (language or "").lower().startswith("chinese"):
        tx = _transliterate_chinese(text)
        if tx and tx not in out:
            out.append(tx)
    # Hooks for future scripts (Japanese, Korean, Arabic, Russian, etc.)
    # would add their detect-and-transliterate branches here.
    return out


# Trailing ", <Region>" tag on a GIIGNL site name (province/state/emirate).
# Alpha-only segment (letters, space, dot, apostrophe), comma-gated, end-anchored,
# and NOT consuming a final "expansion"/"extension" word (left for the fold).
_TRAILING_REGION_RE = re.compile(
    r",\s*(?!(?:[A-Za-z .']+\s+)?(?:expansion|extension)\s*$)"
    r"[A-Za-z][A-Za-z .']*$",
    re.IGNORECASE,
)


# Roman → Arabic for standalone trailing numeral tokens, so GIIGNL's Arabic
# spelling matches GEM's Roman spelling: GIIGNL "Sakhalin-2" vs GEM "Sakhalin II
# LNG Terminal". Conversion is whole-TOKEN only (a token must BE a pure roman
# numeral), and only canonicalizes the spelling of a number — it never merges two
# DIFFERENT numbers (so "Map Ta Phut 1"/"2", "Senboku 1"/"2" stay distinct: 1≠2).
# Scanned against the GEM universe, only Coatzacoalcos II, Eni Congo FLNG II, and
# Sakhalin II carry a standalone roman numeral, none of which collide with an
# Arabic-numbered sibling once folded.
_ROMAN_TO_ARABIC = {
    "i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5",
    "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10",
}


def _canon_numerals(s):
    """Canonicalize trailing/standalone roman-numeral tokens to Arabic.

    'sakhalin ii'   -> 'sakhalin 2'
    'sakhalin-2'    -> 'sakhalin 2'  (hyphen-joined numeral split to a token)
    'corpus christi stage iii' -> 'corpus christi stage 3'
    'senboku 1'     -> unchanged (already Arabic; never collides with 'ii'=2)

    Only a token that is ENTIRELY a roman numeral is converted — a name like
    "Ixtoc" or "Diablo" (containing roman-letter sequences) is never touched
    because the whole token isn't a numeral. Single "i"/"v"/"x" are converted
    too, but those are vanishingly rare as standalone name tokens and the
    GEM-universe scan above found none.
    """
    # Split a hyphen that joins a name stem to a pure-digit or roman tail so the
    # numeral becomes its own token ("sakhalin-2" -> "sakhalin 2"). Only when the
    # tail is a numeral, so hyphenated names like "arzew-bethioua" are untouched.
    s = re.sub(r"-(?=(?:\d+|i{1,3}|iv|v|vi{0,3}|ix|x)\b)", " ", s)
    toks = s.split()
    out = [_ROMAN_TO_ARABIC.get(t, t) for t in toks]
    return " ".join(out)


def _strip_trailing_region(s):
    """Drop a single trailing ', <subnational region>' segment from an already
    lower-cased name, only if the comma is not inside an unbalanced parenthetical.

    'chaozhou, guangdong'        -> 'chaozhou'
    'caofeidian (tangshan), hebei' -> 'caofeidian (tangshan)'
    'tortue flng (gimi flng, greater tortue ahmeyim phase 1)' -> unchanged
    'yangshan, shanghai expansion' -> unchanged (expansion-fold handles it)
    """
    m = _TRAILING_REGION_RE.search(s)
    if not m:
        return s
    head = s[: m.start()]
    # The comma must close at the top paren level: if `head` has more '(' than ')'
    # the comma is inside a still-open parenthetical — leave it.
    if head.count("(") > head.count(")"):
        return s
    return head.strip()


def normalize_terminal_name(s):
    """Strip common GEM-style suffixes and prefixes for matching.
    
    Keeps the distinctive site/sponsor name; drops "LNG Terminal", "FSRU", etc.
    Examples:
        "Sabine Pass LNG Terminal"           -> "sabine pass"
        "Cedar FLNG Terminal"                -> "cedar"
        "Stade FSRU"                         -> "stade"
        "Gibbstown Deepwater Port LNG Terminal" -> "gibbstown"
    """
    if s is None:
        return ""
    # Fold diacritics so GIIGNL's accent-stripped spelling matches GEM's accented
    # one: "Pecem" and "Pecém FSRU" both reduce to "pecem"; "Świnoujście" →
    # "swinoujscie". Display names keep their accents — only this matching form is
    # folded. Done before lowercasing/suffix-stripping (both operate on ASCII).
    s = _strip_diacritics(str(s)).lower().strip()
    # Drop zero-width characters that some PDFs embed mid-token (GIIGNL typesets
    # "S(2 )" with a U+200B between the digit and the paren, which would otherwise
    # leave the designator token unmatchable against GEM's "s(2"). Covers ZWSP,
    # ZWNJ, ZWJ, and BOM/ZWNBSP.
    s = re.sub("[​‌‍﻿]", "", s)
    # Drop apostrophes (straight ' and curly ’) so a name spelled with one folds to
    # the apostrophe-free / pinyin form: GIIGNL "Hua'an" → "huaan" matches GEM's
    # transliterated alias "shenzhen huaan lng project"; "Nan'ao" → "nanao". This
    # joins the token (removes, not space-splits) — pinyin romanizations drop the
    # syllable-boundary apostrophe entirely. Display names keep their apostrophes.
    s = s.replace("'", "").replace("’", "")
    # Strip a trailing facility-type tag in parentheses — "Prelude (FLNG)",
    # "Ravenna (FSRU)" — so the parenthesized form matches GEM's suffix form
    # ("Prelude FLNG Terminal" -> "prelude"). The tag is kept in the displayed
    # site_name (it's only dropped here, for matching).
    s = re.sub(r"\s*\((?:fsru|flng|fsu|fru|fpso)\)\s*$", "", s)
    # Strip a trailing ", <subnational region>" tag (matching only — display keeps
    # it). GIIGNL frequently appends a province/state to Chinese, Indonesian,
    # Canadian, UAE, etc. regas sites — "Chaozhou, Guangdong", "Saint John, New
    # Brunswick", "Ruwais, Abu Dhabi" — that GEM never carries in the TerminalName,
    # so the comma defeats the otherwise-clean substring/token match against GEM's
    # "Chaozhou LNG Terminal". Conservative gates: comma-anchored; the trailing
    # segment is alpha words only (letters/space/dot/apostrophe — no digits, no
    # second comma), so it never eats a code or a multi-comma name; the comma must
    # NOT sit inside an unclosed parenthetical (protects "Tortue FLNG (Gimi FLNG,
    # Greater Tortue Ahmeyim Phase 1)"); and a trailing "Expansion"/"Extension"
    # word is preserved (the report-side expansion-fold keys off it on the RAW
    # name). GEM TerminalNames carry no commas, so this is a no-op on the GEM side.
    s = _strip_trailing_region(s)
    # Strip common suffixes (order matters — longer first)
    suffixes = [
        " deepwater port lng terminal",
        " flng terminal",
        " lng terminal",
        " regasification terminal",
        " liquefaction terminal",
        " import terminal",
        " export terminal",
        " terminal",
        " fsru",
        " flng",
        " fsu",
        " fru",
    ]
    for suf in suffixes:
        if s.endswith(suf):
            s = s[:-len(suf)]
            break
    # Strip "LNG " prefix for projects named "LNG Canada", "LNG Quebec", etc.
    if s.startswith("lng "):
        s = s[4:]
    # Canonicalize roman→Arabic numerals so "Sakhalin II" matches "Sakhalin-2".
    s = _canon_numerals(s)
    return s.strip()


def main():
    """CLI smoke test."""
    samples_country = ["USA", "United States", "U.S.", "Türkiye", "Turkey", "PRC", "Korea, South"]
    samples_entity = [
        "TotalEnergies", "Total", "Total SA",
        "Cheniere Energy", "Cheniere",
        "Höegh LNG", "Hoegh Evi",
        "Sempra Infrastructure", "Sempra",
    ]
    samples_capacity = [(5.2, "mtpa"), (7.5, "bcm/y"), (1.0, "bcf/d"), (0.6, "MMcf/d")]
    samples_terminal = [
        "Sabine Pass LNG Terminal",
        "Cedar FLNG Terminal",
        "Stade FSRU",
        "LNG Canada Terminal",
        "Gibbstown Deepwater Port LNG Terminal",
    ]
    samples_ownership = [
        "ENI 50%, EGAS 40%, EGPC 10%",
        "Cheniere",
        "Shell, Total, BP",
    ]
    print("Country:")
    for s in samples_country:
        print(f"  {s!r:30} -> {normalize_country(s)!r}")
    print("\nEntity:")
    for s in samples_entity:
        print(f"  {s!r:30} -> {normalize_entity(s)!r}")
    print("\nCapacity (mtpa):")
    for v, u in samples_capacity:
        print(f"  {v} {u:10} -> {to_mtpa(v, u):.3f} mtpa")
    print("\nTerminal name:")
    for s in samples_terminal:
        print(f"  {s!r:45} -> {normalize_terminal_name(s)!r}")
    print("\nOwnership parsing:")
    for s in samples_ownership:
        print(f"  {s!r:40} -> {parse_entity_list(s)}")


if __name__ == "__main__":
    main()
