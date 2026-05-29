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
    "karmol": "karmol",
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
    """Lowercase, strip, collapse whitespace, remove parenthetical content."""
    if s is None:
        return ""
    s = str(s).lower().strip()
    # Remove parenthetical content
    s = re.sub(r"\([^)]*\)", "", s).strip()
    # Strip trailing periods
    s = s.rstrip(".")
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s


def normalize_country(s):
    """Return canonical country name. Unknown inputs returned lowercased/stripped."""
    norm = _normalize_input(s)
    if not norm:
        return ""
    if norm in _COUNTRY_MAP:
        return _COUNTRY_MAP[norm]
    return norm


def normalize_entity(s):
    """Return canonical entity tag. Unknown inputs returned lowercased/stripped."""
    norm = _normalize_input(s)
    if not norm:
        return ""
    # Exact match first
    if norm in _ENTITY_MAP:
        return _ENTITY_MAP[norm]
    # Substring match (longer keys first to avoid false positives)
    for key in sorted(_ENTITY_MAP.keys(), key=len, reverse=True):
        if norm.startswith(key + " ") or norm == key or " " + key + " " in " " + norm + " ":
            return _ENTITY_MAP[key]
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
    out = [text.lower().strip()]
    if _HAS_CHINESE_RE.search(text) or (language or "").lower().startswith("chinese"):
        tx = _transliterate_chinese(text)
        if tx and tx not in out:
            out.append(tx)
    # Hooks for future scripts (Japanese, Korean, Arabic, Russian, etc.)
    # would add their detect-and-transliterate branches here.
    return out


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
    s = str(s).lower().strip()
    # Drop zero-width characters that some PDFs embed mid-token (GIIGNL typesets
    # "S(2 )" with a U+200B between the digit and the paren, which would otherwise
    # leave the designator token unmatchable against GEM's "s(2"). Covers ZWSP,
    # ZWNJ, ZWJ, and BOM/ZWNBSP.
    s = re.sub("[​‌‍﻿]", "", s)
    # Strip a trailing facility-type tag in parentheses — "Prelude (FLNG)",
    # "Ravenna (FSRU)" — so the parenthesized form matches GEM's suffix form
    # ("Prelude FLNG Terminal" -> "prelude"). The tag is kept in the displayed
    # site_name (it's only dropped here, for matching).
    s = re.sub(r"\s*\((?:fsru|flng|fsu|fru|fpso)\)\s*$", "", s)
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
