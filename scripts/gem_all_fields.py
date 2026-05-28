"""
gem_all_fields.py — Reproduce the GEM website's "all-fields" LNG terminal CSV.

This is the flat, denormalized export you get when you click "Export all fields"
on the LNG Terminal Tracker: one row per LNG unit, ~115 columns spanning plant,
unit, project, owners, operators, parents, status timeline, and resolved
datasource URLs.

Invoked via `python gem_query.py --all-fields -o terminals.csv`.

The format mirrors the website export so this file can be dropped in as a
replacement for it (column order, prefix conventions, aggregation format).
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text
from sqlalchemy.engine import Engine


# Capacity-unit conversion factors back to mtpa, reverse-solved by matching
# website-displayed values. The mtpa<->bcm/y relationship is bcm = mtpa / 0.735
# (equivalently mtpa = bcm * 0.735); the website rounds half-up at 2 dp.
MTPA_PER_BCM = Decimal("0.735")

# Map every observed `lng_unit.capacityUnit` value to (factor, factor_to_bcm).
# `factor_to_mtpa` is what to multiply the raw capacity by to get mtpa.
# Empirically derived from sample website rows (Al-Faw 1.00 bcf/d -> 7.67 mtpa;
# Amazónica 150 MMcf/d -> 1.15 mtpa).
CAPACITY_UNIT_TO_MTPA: dict[str, Decimal] = {
    "mtpa":  Decimal("1"),
    "bcm/y": MTPA_PER_BCM,
    "bcm":   MTPA_PER_BCM,
    "bcma":  MTPA_PER_BCM,
    "bcf/d": Decimal("7.67"),
    "mmcf/d": Decimal("0.00767"),
}

# Prefixes used by the website to render integer DB ids.
# LNG calls the project a "Terminal" (T); GOGPT calls it a "location" (L).
ID_PREFIX_PLANT = "T"
ID_PREFIX_LOCATION = "L"
ID_PREFIX_UNIT = "G"
ID_PREFIX_ENTITY = "E"

# projectType codes (see PROJECT_TYPES in gem_query.py).
LNG_PROJECT_TYPE = 8
COMBUSTION_PROJECT_TYPE = 1
# GOGPT lives inside combustion; filter by powerplant_unit.trackerSearch = 'GOGPT'.
GOGPT_TRACKER = "GOGPT"

ALL_FIELDS_COLUMNS = [
    "TerminalID", "UnitID", "Wiki", "TerminalName", "UnitName",
    "FacilityType", "FacilityType [ref]", "Fuel",
    "Status", "Substatus", "Status [ref]",
    "Country/Area", "Researcher", "LastUpdated",
    "ResearcherNotesUnit", "ResearcherNotesProject",
    "OtherNames", "LocalNames", "Language",
    "Owner", "Owner [ref]",
    "Parent", "ParentHQCountry", "Parent GEM Entity ID",
    "Operator", "Operator [ref]",
    "Capacity", "CapacityUnits", "CapacityinMtpa", "CapacityinBcm/y", "Capacity [ref]",
    "TotImportLNGTerminalCapacityinMtpa", "TotImportLNGTerminalCapacityinBcm/y",
    "TotExportLNGTerminalCapacityinMtpa", "TotExportLNGTerminalCapacityinBcm/y",
    "ProposalYear", "ProposalMonth", "ProposalDate [ref]",
    "ConstructionYear", "ConstructionMonth", "ConstructionDate [ref]",
    "OriginalPlannedStartYear", "LatestPlannedStartYear",
    "ActualStartYear", "ActualStartMonth", "ActualStartYear2", "ActualStartYear3",
    "StartDate [ref]",
    "ShelvedYear", "ShelvedYear [ref]",
    "CancelledYear", "CancelledYear [ref]",
    "StopYear", "StopYear [ref]",
    "PlannedStopYear",
    "ShelvedCancelledStatusType",
    "TempFacility", "ImportExportOnly",
    "Location", "Region", "SubRegion", "Prefecture/District", "State/Province",
    "Latitude", "Longitude", "Accuracy", "Location [ref]",
    "AssociatedTerminals", "AssociatedTerminals [ref]",
    "Source", "Source [ref]",
    "PowerPlantsSupplied", "PowerPlantsSupplied [ref]",
    "CaptiveGasPower", "CaptiveGasPower [ref]",
    "Pipelines", "Pipelines [ref]",
    "Cost", "CostUnits", "CostYear", "CostUSD", "CostEuro", "Cost [ref]",
    "TotKnownTerminalCostsUSD", "TotTerminalCost [ref]",
    "FIDStatus", "FIDYear", "FIDYear [ref]",
    "Financing", "Financing [ref]",
    "Offshore", "Floating",
    "FloatingVesselName", "FloatingVesselName [ref]",
    "VesselOwner", "VesselOwner [ref]", "VesselParent",
    "VesselOperator", "VesselOperator [ref]",
    "Opposition", "ESJNotes", "Defeated",
    "PCINotes", "PCI3", "PCI4", "PCI5", "PCI6",
    "LH2", "NH3", "SyntheticLNG", "RetrofitProposed",
    "AltFuelPrelimAgreement", "AltFuelCallMarketInterest",
    "CCS", "CCSNotes",
]


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _row_to_dict(row) -> dict:
    return dict(row._mapping)


def _q2(x) -> Decimal | None:
    """Quantize a numeric to 2 decimals with banker-free half-up rounding."""
    if x is None:
        return None
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _fmt_num(x) -> str:
    """Drop trailing zeros from a Decimal so 9.50 -> 9.5, 12.00 -> 12 etc."""
    if x is None:
        return ""
    d = Decimal(x).normalize()
    # normalize() can give "1E+1" for 10; reformat in fixed-point.
    s = format(d, "f")
    return s


def _fmt_fixed2(x) -> str:
    """Format as exactly 2 decimal places: 9.5 -> '9.50', 20000000000 -> '20000000000.00'."""
    if x is None:
        return ""
    return f"{Decimal(x):.2f}"


def _fmt_min1dp(x) -> str:
    """At least 1 decimal place; trim trailing zeros past that.

    20000000000 -> '20000000000.0', 9.5 -> '9.5', 2.15 -> '2.15', 2.00 -> '2.0'.
    """
    if x is None:
        return ""
    s = f"{Decimal(x):.6f}".rstrip("0").rstrip(".")
    if "." not in s:
        s += ".0"
    return s


def _fmt_coord(x) -> str:
    """Coordinates render to 7 decimal places (with trailing zeros)."""
    if x is None:
        return ""
    return f"{Decimal(x):.7f}"


def _yn(b) -> str:
    """The website renders booleans as 'True' / blank for false."""
    if b is True:
        return "True"
    return ""


def _company_display(name: str | None, legal_type: str | None) -> str:
    """Format a company name with its legal entity type suffix."""
    if not name:
        return ""
    if legal_type:
        return f"{name} {legal_type}"
    return name


def _fmt_share_owner(share) -> str:
    """Owner shares: 100% (no decimal when whole), 50.5% (decimal otherwise)."""
    if share is None:
        return ""
    d = Decimal(share)
    if d == d.to_integral_value():
        return f"{int(d)}%"
    return f"{d.normalize()}%"


def _fmt_share_owner_int(share) -> str:
    """GOGPT/gas_all owner shares round to whole percent (33.33% -> 33%)."""
    if share is None:
        return ""
    rounded = Decimal(share).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{int(rounded)}%"


# Parses one `<name> [<share>%]` segment of a gemParents string.
_GEMPARENT_RE = re.compile(r"^(.*?)\s*\[\s*([0-9.]+)\s*%\s*\]\s*$")


def _parse_gemparents(text_val: str | None) -> list[tuple[str, Decimal | None]]:
    """Split 'Name1 [50%]; Name2 [50%]' -> [(Name1, Decimal(50)), (Name2, Decimal(50))].

    Entries without a `[X%]` bracket parse to (name, None).
    """
    if not text_val:
        return []
    out: list[tuple[str, Decimal | None]] = []
    for piece in text_val.split(";"):
        piece = piece.strip()
        if not piece:
            continue
        m = _GEMPARENT_RE.match(piece)
        if m:
            name = m.group(1).strip()
            try:
                share = Decimal(m.group(2))
            except Exception:
                share = None
            out.append((name, share))
        else:
            out.append((piece, None))
    return out


def _format_gogpt_parent_pieces(
    parent_entries: list[tuple[str, Decimal | None]],
    owner_share: Decimal | None,
) -> list[str]:
    """Render parent (name, parent-share-of-owner) pairs with effective shares.

    Rule reverse-engineered from the reference CSV:
      - If the gemParents entry has NO `[X%]` bracket, no share is displayed
        regardless of the owner's share.
      - If the owner's share-of-unit is NULL, no share is displayed even if
        the gemParents entry has a bracket.
      - Otherwise: displayed share = owner_share × gemparent_share / 100,
        formatted with one decimal (50.0%, 33.3%, 16.7%).
    """
    out: list[str] = []
    for name, gp_share in parent_entries:
        if owner_share is None or gp_share is None:
            out.append(name)
        else:
            effective = (Decimal(owner_share) * Decimal(gp_share)) / Decimal(100)
            formatted = effective.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            out.append(f"{name} [{formatted}%]")
    return out


def _fmt_share_parent(share) -> str:
    """Parent shares: always 1 decimal: 100.0%, 65.0%, 41.32%."""
    if share is None:
        return ""
    d = Decimal(share)
    if d == d.to_integral_value():
        return f"{int(d)}.0%"
    # Drop redundant trailing zeros past the first decimal.
    s = format(d.normalize(), "f")
    if "." not in s:
        s += ".0"
    return f"{s}%"


def _join_entities(entries: list[tuple[str, Decimal | None]], sep: str = "; ",
                   share_fmt=_fmt_share_owner) -> str:
    """Render [(name, share), ...] as 'name [share%]; name [share%]; ...'."""
    parts = []
    for name, share in entries:
        if not name:
            continue
        if share is None:
            parts.append(name)
        else:
            parts.append(f"{name} [{share_fmt(share)}]")
    return sep.join(parts)


def _join_ids(entries: list[tuple[int, Decimal | None]], sep: str = "; ",
              share_fmt=_fmt_share_parent) -> str:
    parts = []
    for cid, share in entries:
        s = f"{ID_PREFIX_ENTITY}{cid}"
        if share is not None:
            s += f" [{share_fmt(share)}]"
        parts.append(s)
    return sep.join(parts)


def _resolve_refs(ds_ids, lookup: dict[int, str], sep: str = ", ") -> str:
    """Turn a list of data_source ids into 'url, url, url'.

    The website preserves duplicates in the order they appear (some Abadi
    fields show the same URL twice). We do the same.
    """
    if not ds_ids:
        return ""
    urls = []
    for did in ds_ids:
        url = lookup.get(int(did))
        if url:
            urls.append(url)
    return sep.join(urls)


def _comma_join_strs(items, sep: str = ", ") -> str:
    if not items:
        return ""
    if isinstance(items, str):
        return items
    return sep.join(str(s) for s in items if s)


_PCT_INT_RE = re.compile(r"\[(\d+)%\]")
_ENTITY_ID_RE = re.compile(rf"{ID_PREFIX_ENTITY}(\d+)")


def _normalize_parent_shares(text_val: str | None) -> str:
    """Normalize gemParents/gemParentsIds: 100% -> 100.0%, leave decimals as-is."""
    if not text_val:
        return ""
    return _PCT_INT_RE.sub(r"[\1.0%]", text_val)


def _extract_entity_ids(text_val: str | None) -> list[int]:
    """Pull all integer company IDs out of a 'EXXX [..%]; EYYY [..%]' string."""
    if not text_val:
        return []
    return [int(m) for m in _ENTITY_ID_RE.findall(text_val)]


def _capacity_in_mtpa(raw, unit) -> Decimal | None:
    """Convert (raw_capacity, unit_string) -> Decimal mtpa, half-up at 2 dp.

    Returns None if the input unit isn't in CAPACITY_UNIT_TO_MTPA.
    """
    if raw is None or unit is None:
        return None
    factor = CAPACITY_UNIT_TO_MTPA.get(unit.strip().lower())
    if factor is None:
        return None
    return (Decimal(raw) * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _capacity_in_bcm(mtpa) -> Decimal | None:
    """mtpa -> Bcm/y, half-up at 2 dp. Inverse of MTPA_PER_BCM."""
    if mtpa is None:
        return None
    return (Decimal(mtpa) / MTPA_PER_BCM).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP,
    )


# --------------------------------------------------------------------------
# Bulk fetchers
# --------------------------------------------------------------------------

def _fetch_plants(engine: Engine, limit: int | None) -> list[dict]:
    sql = """
        SELECT
            p.id AS plant_id,
            p.name AS terminal_name,
            p."wikiUrl" AS wiki_url,
            p."nameOther" AS name_other,
            p.notes AS plant_notes,
            p.city AS plant_city,
            p.complex AS plant_complex,
            p."localArea" AS plant_local_area,
            p."majorArea" AS plant_major_area,
            p.subnational AS plant_subnational,
            p."subnationalLookup_id" AS subdivision_lookup_id,
            p.latitude AS plant_lat,
            p.longitude AS plant_lon,
            p."locationAccuracy" AS plant_accuracy,
            p."locationDatasource" AS plant_location_ds,
            -- The website renders coordinates from the cached plantJSON snapshot,
            -- which preserves the exact display string (including precision and
            -- trailing zeros). Reading from plain numeric columns would lose this.
            p."plantJSON"->>'latitude' AS plant_lat_str,
            p."plantJSON"->>'longitude' AS plant_lon_str,
            p."plantJSON"->>'city' AS plant_city_json,
            p."plantJSON"->>'subnational' AS plant_subnational_json,
            p."plantJSON"->>'locationAccuracy' AS plant_accuracy_json,
            p."plantLevelOwners" AS plant_level_owners,
            p."plantLevelOperators" AS plant_level_operators,
            p.country_id AS country_id,
            c."gemName" AS country_name,
            c.region AS region,
            c."subRegion" AS subregion,
            cs.name AS subdivision_name
        FROM plant p
        LEFT JOIN country c ON c.id = p.country_id
        LEFT JOIN project_country_subdivision cs ON cs.id = p."subnationalLookup_id"
        WHERE p."projectType" = :ptype AND p.deleted = false
        ORDER BY p.name, p.id
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"ptype": LNG_PROJECT_TYPE}).fetchall()
    return [_row_to_dict(r) for r in rows]


def _fetch_units(engine: Engine, plant_ids: list[int]) -> list[dict]:
    """All powerplant_units (with their lng_unit extension) for these plants."""
    if not plant_ids:
        return []
    sql = """
        SELECT
            pu.id AS unit_id,
            pu.plant_id AS plant_id,
            pu.name AS unit_name,
            pu."plannedStartYear" AS planned_start_year,
            pu."startYearHigh" AS start_year_high,
            pu."startYearLow" AS start_year_low,
            pu."constructionStartYear" AS construction_start_year,
            pu."cancellationYear" AS cancellation_year,
            pu."plannedRetiredYear" AS planned_retired_year,
            pu."endYearHigh" AS end_year_high,
            pu."endYearLow" AS end_year_low,
            pu."ccsAttachment_id" AS ccs_attachment_id,
            pu."ccsDatasource" AS ccs_ds,
            pu."capacityDatasource" AS unit_capacity_ds,
            pu."unitJSON"->>'latitude' AS unit_lat_str,
            pu."unitJSON"->>'longitude' AS unit_lon_str,
            pu."unitJSON"->>'city' AS unit_city_json,
            pu."unitJSON"->>'subnational' AS unit_subnational_json,
            pu."unitJSON"->>'locationAccuracy' AS unit_accuracy_json,
            pu."locationDatasource" AS unit_location_ds,
            lu.id AS lng_unit_id,
            lu.fuel AS fuel,
            lu."facilityType" AS facility_type,
            lu."facilityTypeDatasource" AS facility_type_ds,
            lu.capacity AS capacity,
            lu."capacityUnit" AS capacity_unit,
            lu.cost AS cost,
            lu."costUnit" AS cost_unit,
            lu."costYear" AS cost_year,
            lu."costDatasource" AS cost_ds,
            lu.financing AS financing,
            lu."financingDatasource" AS financing_ds,
            lu."fidStatus" AS fid_status,
            lu."fidYear" AS fid_year,
            lu."fidDatasource" AS fid_ds,
            lu."tempFacility" AS temp_facility,
            lu."importExportOnly" AS import_export_only,
            lu.defeated AS defeated,
            lu."defeatedDatasource" AS defeated_ds,
            lu."LH2" AS lh2,
            lu."NH3" AS nh3,
            lu."syntheticLNG" AS synthetic_lng,
            lu."retrofitProposed" AS retrofit_proposed,
            lu."altFuelPrelimAgreement" AS alt_fuel_prelim,
            lu."altFuelCallMarketInterest" AS alt_fuel_call,
            lu."researcherNotes" AS unit_notes
        FROM powerplant_unit pu
        LEFT JOIN lng_unit lu ON lu.unit_id = pu.id
        WHERE pu.plant_id = ANY(:plant_ids) AND pu.deleted = false
        ORDER BY pu.plant_id, pu.id
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"plant_ids": plant_ids}).fetchall()
    return [_row_to_dict(r) for r in rows]


def _fetch_lng_projects(engine: Engine, plant_ids: list[int]) -> dict[int, dict]:
    """One lng_project per plant.id (FK is project_id -> plant.id)."""
    if not plant_ids:
        return {}
    sql = """
        SELECT
            project_id,
            capacity AS proj_capacity,
            "capacityUnit" AS proj_capacity_unit,
            "capacityDatasource" AS capacity_ds,
            "LNGSource" AS lng_source,
            "LNGSourceDatasource" AS lng_source_ds,
            "powerPlantsSupplied" AS pps,
            "powerPlantsSuppliedDatasource" AS pps_ds,
            pipelines,
            "pipelinesDatasource" AS pipelines_ds,
            "associatedProjects" AS assoc_projects,
            "associatedProjectsDatasource" AS assoc_projects_ds,
            "captiveGasPower" AS captive_gas_power,
            "captiveGasPowerDatasource" AS captive_gas_power_ds,
            offshore, floating,
            "vesselName" AS vessel_name,
            "vesselNameDatasource" AS vessel_name_ds,
            opposition,
            "oppositionDatasource" AS opposition_ds,
            "esjNotes" AS esj_notes,
            "pciNotes" AS pci_notes,
            "pci3" AS pci3, "pci4" AS pci4, "pci5" AS pci5, "pci6" AS pci6,
            ccs,
            "ccsDatasource" AS ccs_ds,
            "ccsNotes" AS ccs_notes
        FROM lng_project
        WHERE project_id = ANY(:plant_ids)
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"plant_ids": plant_ids}).fetchall()
    return {r._mapping["project_id"]: _row_to_dict(r) for r in rows}


def _fetch_status_timelines(engine: Engine, unit_ids: list[int]) -> dict[int, list[dict]]:
    if not unit_ids:
        return {}
    sql = """
        SELECT unit_id, "order", status, substatus, year,
               "monthOrHalfYear" AS month, "statusDatasource" AS ds, delayed
        FROM status_timeline
        WHERE unit_id = ANY(:unit_ids)
        ORDER BY unit_id, "order"
    """
    out: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"unit_ids": unit_ids}):
            out[r._mapping["unit_id"]].append(_row_to_dict(r))
    return dict(out)


def _fetch_owners(engine: Engine, plant_ids: list[int], unit_ids: list[int]):
    """Returns (by_plant, by_unit) where each is {id: [{share, company_id, name, legal_type, hq_country, share_ds}]}."""
    if not plant_ids and not unit_ids:
        return {}, {}
    sql = """
        SELECT po.id AS po_id,
               po.plant_id, po.powerplant_unit_id, po.share,
               po."shareDatasource" AS share_ds,
               c.id AS company_id, c.name AS company_name,
               let.type AS legal_type,
               hq."gemName" AS hq_country,
               c."gemParents" AS gem_parents,
               c."gemParentsIds" AS gem_parents_ids
        FROM plant_owner po
        JOIN company c ON c.id = po.company_id
        LEFT JOIN legal_entity_type let ON let.id = c."legalEntityType_id"
        LEFT JOIN country hq ON hq.id = c."headquarters_country_id"
        WHERE po.plant_id = ANY(:plant_ids) OR po.powerplant_unit_id = ANY(:unit_ids)
        ORDER BY po.id
    """
    by_plant: dict[int, list[dict]] = defaultdict(list)
    by_unit: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"plant_ids": plant_ids, "unit_ids": unit_ids}):
            row = _row_to_dict(r)
            if row["plant_id"] is not None:
                by_plant[row["plant_id"]].append(row)
            elif row["powerplant_unit_id"] is not None:
                by_unit[row["powerplant_unit_id"]].append(row)
    return dict(by_plant), dict(by_unit)


def _fetch_operators(engine: Engine, plant_ids: list[int], unit_ids: list[int]):
    if not plant_ids and not unit_ids:
        return {}, {}
    sql = """
        SELECT op.plant_id, op.powerplant_unit_id, op.share, op.type,
               op."operatorDatasource" AS op_ds,
               c.id AS company_id, c.name AS company_name,
               let.type AS legal_type,
               hq."gemName" AS hq_country
        FROM operator op
        JOIN company c ON c.id = op.company_id
        LEFT JOIN legal_entity_type let ON let.id = c."legalEntityType_id"
        LEFT JOIN country hq ON hq.id = c."headquarters_country_id"
        WHERE op.plant_id = ANY(:plant_ids) OR op.powerplant_unit_id = ANY(:unit_ids)
        ORDER BY COALESCE(op.share, 0) DESC, c.name
    """
    by_plant: dict[int, list[dict]] = defaultdict(list)
    by_unit: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"plant_ids": plant_ids, "unit_ids": unit_ids}):
            row = _row_to_dict(r)
            if row["plant_id"] is not None:
                by_plant[row["plant_id"]].append(row)
            elif row["powerplant_unit_id"] is not None:
                by_unit[row["powerplant_unit_id"]].append(row)
    return dict(by_plant), dict(by_unit)


def _fetch_company_owners_recursive(engine: Engine, seed_ids: list[int]):
    """Walk company_owner edges out from `seed_ids` until no new companies
    appear. Returns:
       direct_parents: {child_id: [{parent_id, share, ...}]} for every node
       company_info:   {id: {name, legal_type, hq_country, ultimate_parent}}
    """
    if not seed_ids:
        return {}, {}
    direct: dict[int, list[dict]] = defaultdict(list)
    info: dict[int, dict] = {}
    visited_as_child: set[int] = set()
    frontier = set(int(x) for x in seed_ids)

    with engine.connect() as conn:
        # First populate info for the seeds so we can fall back to them when
        # they are themselves ultimate parents.
        seeds_info = conn.execute(text("""
            SELECT c.id, c.name, c."ultimateParent" AS ultimate_parent,
                   let.type AS legal_type, hq."gemName" AS hq_country
            FROM company c
            LEFT JOIN legal_entity_type let ON let.id = c."legalEntityType_id"
            LEFT JOIN country hq ON hq.id = c."headquarters_country_id"
            WHERE c.id = ANY(:ids)
        """), {"ids": list(frontier)}).fetchall()
        for r in seeds_info:
            info[r._mapping["id"]] = _row_to_dict(r)

        while frontier:
            chunk = list(frontier)
            visited_as_child.update(chunk)
            rows = conn.execute(text("""
                SELECT co.company_id AS child_id, co.share,
                       p.id AS parent_id, p.name AS parent_name,
                       p."ultimateParent" AS ultimate_parent,
                       let.type AS legal_type, hq."gemName" AS hq_country
                FROM company_owner co
                JOIN company p ON p.id = co.owner_id
                LEFT JOIN legal_entity_type let ON let.id = p."legalEntityType_id"
                LEFT JOIN country hq ON hq.id = p."headquarters_country_id"
                WHERE co.company_id = ANY(:ids)
                ORDER BY COALESCE(co.share, 0) DESC, p.name
            """), {"ids": chunk}).fetchall()
            new_frontier: set[int] = set()
            for r in rows:
                row = _row_to_dict(r)
                direct[row["child_id"]].append(row)
                pid = row["parent_id"]
                if pid not in info:
                    info[pid] = {
                        "id": pid, "name": row["parent_name"],
                        "ultimate_parent": row["ultimate_parent"],
                        "legal_type": row["legal_type"],
                        "hq_country": row["hq_country"],
                    }
                if pid not in visited_as_child and not row.get("ultimate_parent"):
                    new_frontier.add(pid)
            frontier = new_frontier
    return dict(direct), info


def _trace_ultimate_parents(start_id: int, direct: dict[int, list[dict]],
                            info: dict[int, dict]) -> list[dict]:
    """From one direct-owner company, walk to all ultimate parents.

    Returns list of {parent_id, name, legal_type, hq_country, cumulative_share}.
    Cumulative share is the product of intermediate shares (in percent).
    A company with no further parents (or ultimateParent=True) is itself an
    ultimate parent. The seed's own ultimate-parent status is checked first:
    if the seed has no listed parents, it appears as its own ultimate parent.
    """
    out: list[dict] = []

    def emit_self(cid: int, share: Decimal):
        i = info.get(cid) or {}
        out.append({
            "parent_id": cid,
            "name": i.get("name"),
            "legal_type": i.get("legal_type"),
            "hq_country": i.get("hq_country"),
            "cumulative_share": share,
        })

    def walk(cid: int, cum_share_pct: Decimal, path: tuple):
        # Cycle in the ownership graph (e.g. joint-venture cross-holdings) —
        # stop here and treat the current node as the terminal point.
        if cid in path:
            emit_self(cid, cum_share_pct)
            return
        is_ult = (info.get(cid) or {}).get("ultimate_parent")
        parents = direct.get(cid, [])
        if not parents or is_ult:
            emit_self(cid, cum_share_pct)
            return
        next_path = path + (cid,)
        for p in parents:
            share = p.get("share")
            if share is None:
                # Treat unspecified share as 100% for traversal purposes.
                next_share = cum_share_pct
            else:
                next_share = (cum_share_pct * Decimal(share) / Decimal(100))
            walk(p["parent_id"], next_share, next_path)

    walk(start_id, Decimal("100"), tuple())
    return out


def _fetch_languages(engine: Engine, plant_ids: list[int]) -> dict[int, list[dict]]:
    if not plant_ids:
        return {}
    sql = """
        SELECT pl.plant_id, pl.name AS local_name, l.name AS language_name
        FROM plant_language pl
        LEFT JOIN language l ON l.id = pl.language_id
        WHERE pl.plant_id = ANY(:plant_ids)
    """
    out: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"plant_ids": plant_ids}):
            out[r._mapping["plant_id"]].append(_row_to_dict(r))
    return dict(out)


def _fetch_unit_updates(engine: Engine, unit_ids: list[int]) -> dict[int, dict]:
    """Most-recent updater per unit."""
    if not unit_ids:
        return {}
    sql = """
        SELECT DISTINCT ON (uu.unit_id)
               uu.unit_id, uu."lastUpdated" AS last_updated,
               au.first_name, au.last_name
        FROM unit_update uu
        LEFT JOIN auth_user au ON au.id = uu.updater_id
        WHERE uu.unit_id = ANY(:unit_ids)
        ORDER BY uu.unit_id, uu."lastUpdated" DESC NULLS LAST
    """
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"unit_ids": unit_ids}).fetchall()
    return {r._mapping["unit_id"]: _row_to_dict(r) for r in rows}


def _fetch_data_sources(engine: Engine, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    sql = "SELECT id, url FROM data_source WHERE id = ANY(:ids)"
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"ids": list(ids)}).fetchall()
    return {r._mapping["id"]: r._mapping["url"] for r in rows}


# --------------------------------------------------------------------------
# Status-timeline column derivation
# --------------------------------------------------------------------------

# Each row in status_timeline carries (status, substatus, year, month). The
# website's CSV spreads these across many year-columns based on status name and
# whether substatus == "planned". Rules below are reverse-engineered from a
# sample of website-exported rows.

def _derive_status_columns(timeline: list[dict], ds_lookup: dict[int, str]) -> dict:
    """Return the dict of status-derived columns for one unit."""
    out = {
        "Status": "", "Substatus": "", "Status [ref]": "",
        "ProposalYear": "", "ProposalMonth": "", "ProposalDate [ref]": "",
        "ConstructionYear": "", "ConstructionMonth": "", "ConstructionDate [ref]": "",
        "OriginalPlannedStartYear": "", "LatestPlannedStartYear": "",
        "ActualStartYear": "", "ActualStartMonth": "",
        "ActualStartYear2": "", "ActualStartYear3": "",
        "StartDate [ref]": "",
        "ShelvedYear": "", "ShelvedYear [ref]": "",
        "CancelledYear": "", "CancelledYear [ref]": "",
        "StopYear": "", "StopYear [ref]": "",
        "PlannedStopYear": "",
        "ShelvedCancelledStatusType": "",
        "FIDStatus": "", "FIDYear": "", "FIDYear [ref]": "",
    }
    if not timeline:
        return out

    # Sort by order; we want the highest-order row as "current".
    rows = sorted(timeline, key=lambda r: r["order"])

    # "Current" status: highest-order row whose substatus is not 'planned' and
    # whose status is not 'FID'. FID is a milestone, not a lifecycle status;
    # the website's Status column never displays it (the milestone is captured
    # separately by FIDYear / FIDStatus).
    def _is_current_candidate(r):
        sub = (r.get("substatus") or "").lower()
        st = (r.get("status") or "").lower()
        return sub != "planned" and st != "fid"

    current = next((r for r in reversed(rows) if _is_current_candidate(r)), None)
    if current is None:
        # Everything is 'planned' or FID; fall back to highest order, still
        # excluding FID if possible.
        non_fid = [r for r in rows if (r.get("status") or "").lower() != "fid"]
        current = non_fid[-1] if non_fid else rows[-1]
    out["Status"] = current.get("status") or ""
    out["Substatus"] = current.get("substatus") or ""
    out["Status [ref]"] = _resolve_refs(current.get("ds") or [], ds_lookup)

    # Bucket rows by status name.
    actual_starts: list[dict] = []
    planned_starts: list[dict] = []
    for r in rows:
        status = (r.get("status") or "").lower()
        sub = (r.get("substatus") or "").lower()
        if status == "proposed":
            if not out["ProposalYear"]:
                out["ProposalYear"] = str(r.get("year") or "")
                out["ProposalMonth"] = r.get("month") or ""
                out["ProposalDate [ref]"] = _resolve_refs(r.get("ds") or [], ds_lookup)
        elif status == "construction":
            if not out["ConstructionYear"]:
                out["ConstructionYear"] = str(r.get("year") or "")
                out["ConstructionMonth"] = r.get("month") or ""
                out["ConstructionDate [ref]"] = _resolve_refs(r.get("ds") or [], ds_lookup)
        elif status == "operating":
            if sub == "planned":
                planned_starts.append(r)
            else:
                actual_starts.append(r)
        elif status == "shelved":
            out["ShelvedYear"] = str(r.get("year") or "")
            out["ShelvedYear [ref]"] = _resolve_refs(r.get("ds") or [], ds_lookup)
            if sub and not out["ShelvedCancelledStatusType"]:
                out["ShelvedCancelledStatusType"] = _shelvedcancel_type(sub)
        elif status == "cancelled":
            out["CancelledYear"] = str(r.get("year") or "")
            out["CancelledYear [ref]"] = _resolve_refs(r.get("ds") or [], ds_lookup)
            if sub:
                out["ShelvedCancelledStatusType"] = _shelvedcancel_type(sub)
        elif status in ("retired", "stopped", "mothballed"):
            if sub == "planned":
                out["PlannedStopYear"] = str(r.get("year") or "")
            else:
                out["StopYear"] = str(r.get("year") or "")
                out["StopYear [ref]"] = _resolve_refs(r.get("ds") or [], ds_lookup)
        elif status == "fid":
            out["FIDYear"] = str(r.get("year") or "")
            out["FIDYear [ref]"] = _resolve_refs(r.get("ds") or [], ds_lookup)
            out["FIDStatus"] = "Pre-FID" if sub == "planned" else "FID"

    # Planned starts: earliest = Original, latest = Latest.
    if planned_starts:
        planned_starts.sort(key=lambda r: r["order"])
        out["OriginalPlannedStartYear"] = str(planned_starts[0].get("year") or "")
        out["LatestPlannedStartYear"] = str(planned_starts[-1].get("year") or "")

    # StopYear: when the plant has reached an end-state (cancelled, shelved,
    # retired), this column repeats the relevant year. Cancelled wins over
    # shelved when both are present.
    if out["CancelledYear"]:
        out["StopYear"] = out["CancelledYear"]
        out["StopYear [ref]"] = out["CancelledYear [ref]"]
    elif out["ShelvedYear"]:
        out["StopYear"] = out["ShelvedYear"]
        out["StopYear [ref]"] = out["ShelvedYear [ref]"]

    # Actual starts: up to three columns, in chronological (order) sequence.
    if actual_starts:
        actual_starts.sort(key=lambda r: r["order"])
        first = actual_starts[0]
        out["ActualStartYear"] = str(first.get("year") or "")
        out["ActualStartMonth"] = first.get("month") or ""
        if len(actual_starts) >= 2:
            out["ActualStartYear2"] = str(actual_starts[1].get("year") or "")
        if len(actual_starts) >= 3:
            out["ActualStartYear3"] = str(actual_starts[2].get("year") or "")

    # StartDate [ref] aggregates the datasources of every operating-status row
    # in the timeline (whether actual or planned). The website does this so a
    # plant with no actual start yet still gets its planned-start source links.
    start_ds_ids: list[int] = []
    for r in rows:
        if (r.get("status") or "").lower() == "operating":
            start_ds_ids.extend(r.get("ds") or [])
    out["StartDate [ref]"] = _resolve_refs(start_ds_ids, ds_lookup)

    return out


def _shelvedcancel_type(substatus: str) -> str:
    """The 'inferred 4 y' style substatus collapses to 'inferred' / 'actual'."""
    s = (substatus or "").lower()
    if s.startswith("inferred"):
        return "inferred"
    if s == "actual":
        return "actual"
    return s


# --------------------------------------------------------------------------
# Row composition
# --------------------------------------------------------------------------

def _build_row(plant: dict, unit: dict, lng_proj: dict | None, ctx: dict) -> dict:
    """Compose one CSV row (dict keyed by header label)."""
    ds = ctx["data_sources"]
    plant_id = plant["plant_id"]
    unit_id = unit["unit_id"]

    # Determine owners: plant-level vs unit-level.
    if plant.get("plant_level_owners"):
        owners = ctx["owners_by_plant"].get(plant_id, [])
        owner_ds_source = "plant"
    else:
        owners = ctx["owners_by_unit"].get(unit_id, [])
        owner_ds_source = "unit"

    if plant.get("plant_level_operators"):
        all_operators = ctx["operators_by_plant"].get(plant_id, [])
    else:
        all_operators = ctx["operators_by_unit"].get(unit_id, [])

    # The operator table is overloaded: rows carry a `type` distinguishing the
    # main operator (type='operator') from vessel-specific roles. Each rolls up
    # into a different column on the website.
    main_operators = [o for o in all_operators if (o.get("type") or "operator") == "operator"]
    vessel_operators = [o for o in all_operators if o.get("type") == "vessel_operator"]
    vessel_owners = [o for o in all_operators if o.get("type") == "vessel_owner"]

    # Build Owner display string and collect parent rows.
    # Owners use "Name + LegalType" (e.g. "INPEX Masela Ltd"); operators use
    # just `company.name` (e.g. "INPEX Masela") — verified against website.
    owner_entries = [
        (_company_display(o["company_name"], o["legal_type"]), o["share"])
        for o in owners
    ]
    owner_ds_ids: list[int] = []
    for o in owners:
        owner_ds_ids.extend(o.get("share_ds") or [])
    owner_str = _join_entities(owner_entries, share_fmt=_fmt_share_owner)
    owner_ref = _resolve_refs(owner_ds_ids, ds)

    # Parent / Parent GEM Entity ID: read from the curated company.gemParents /
    # gemParentsIds on each direct owner. These are GEM-maintained parent lists
    # — separate from the public-shareholder data in company_owner, which would
    # otherwise pull in Vanguard/Blackrock minority holdings.
    #
    # Per-owner fallback: when gemParents is empty (or is just a self-reference)
    # the owner has no real parent above it. In that case the parent column
    # shows the OWNER, with the owner's share (or no share if NULL on owner).
    parent_pieces: list[str] = []
    parent_id_pieces: list[str] = []
    parent_hq_lookup = ctx["parent_hq_lookup"]
    parent_hq_countries: list[str] = []
    for o in owners:
        gp = o.get("gem_parents")
        gpi = o.get("gem_parents_ids")
        gp_ids = _extract_entity_ids(gpi)
        owner_id = o["company_id"]
        owner_share = o.get("share")
        self_ref_only = (
            not gp
            or (len(gp_ids) == 1 and gp_ids[0] == owner_id)
            or (not gp_ids)
        )
        if self_ref_only:
            # Show the owner itself; share from plant_owner (may be NULL).
            name = _company_display(o["company_name"], o["legal_type"])
            if owner_share is None:
                parent_pieces.append(name)
                parent_id_pieces.append(f"{ID_PREFIX_ENTITY}{owner_id}")
            else:
                s = _fmt_share_parent(owner_share)
                parent_pieces.append(f"{name} [{s}]")
                parent_id_pieces.append(f"{ID_PREFIX_ENTITY}{owner_id} [{s}]")
            if o.get("hq_country"):
                parent_hq_countries.append(o["hq_country"])
        else:
            parent_pieces.append(_normalize_parent_shares(gp))
            parent_id_pieces.append(_normalize_parent_shares(gpi))
            for pid in gp_ids:
                country = parent_hq_lookup.get(pid)
                if country:
                    parent_hq_countries.append(country)
    parent_str = "; ".join(parent_pieces)
    parent_id_str = "; ".join(parent_id_pieces)
    parent_hq_str = _comma_join_strs(parent_hq_countries)

    # Main operator display (no legal_type suffix).
    op_entries = [(o["company_name"], o["share"]) for o in main_operators]
    op_ds_ids: list[int] = []
    for o in main_operators:
        op_ds_ids.extend(o.get("op_ds") or [])
    operator_str = _join_entities(op_entries, share_fmt=_fmt_share_owner)
    operator_ref = _resolve_refs(op_ds_ids, ds)

    # Vessel operator / vessel owner.
    v_op_entries = [(o["company_name"], o["share"]) for o in vessel_operators]
    v_op_ds: list[int] = []
    for o in vessel_operators:
        v_op_ds.extend(o.get("op_ds") or [])
    vessel_op_str = _join_entities(v_op_entries, share_fmt=_fmt_share_owner)
    vessel_op_ref = _resolve_refs(v_op_ds, ds)

    v_own_entries = [(o["company_name"], o["share"]) for o in vessel_owners]
    v_own_ds: list[int] = []
    for o in vessel_owners:
        v_own_ds.extend(o.get("op_ds") or [])
    vessel_own_str = _join_entities(v_own_entries, share_fmt=_fmt_share_owner)
    vessel_own_ref = _resolve_refs(v_own_ds, ds)

    # Languages.
    langs = ctx["languages"].get(plant_id, [])
    local_names = _comma_join_strs([l["local_name"] for l in langs if l.get("local_name")])
    language_names = _comma_join_strs([l["language_name"] for l in langs if l.get("language_name")])

    # OtherNames (plant.nameOther is a jsonb list of strings).
    other_names = _comma_join_strs(plant.get("name_other") or [])

    # Researcher / LastUpdated (from latest unit_update).
    uu = ctx["unit_updates"].get(unit_id) or {}
    researcher = ""
    if uu.get("first_name") or uu.get("last_name"):
        researcher = f"{uu.get('first_name') or ''} {uu.get('last_name') or ''}".strip()
    last_updated = uu.get("last_updated")
    last_updated_s = last_updated.isoformat() if last_updated else ""

    # Capacities.
    capacity_in_mtpa = _capacity_in_mtpa(unit.get("capacity"), unit.get("capacity_unit"))
    capacity_in_bcm = _capacity_in_bcm(capacity_in_mtpa)

    # Per-facility-type totals (aggregated across all units of the plant).
    totals = ctx["totals_by_plant"].get(plant_id, {})
    tot_imp_mtpa = totals.get("import_mtpa")
    tot_imp_bcm = totals.get("import_bcm")
    tot_exp_mtpa = totals.get("export_mtpa")
    tot_exp_bcm = totals.get("export_bcm")

    # Status timeline column block.
    timeline = ctx["timelines"].get(unit_id, [])
    sd = _derive_status_columns(timeline, ds)

    # Resolve various datasource lists into URL strings.
    def refs(field_value):
        return _resolve_refs(field_value or [], ds)

    # lng_project fields, with safe fallbacks.
    lp = lng_proj or {}

    # Location-block fields. Each can live on either the unit (preferred for
    # multi-unit plants) or the plant. We always pull from the cached *JSON
    # snapshots so the values match the website's display string exactly
    # (precision, trailing zeros, etc.).
    loc_city = unit.get("unit_city_json") or plant.get("plant_city_json") or plant.get("plant_city") or ""
    # State/Province priority: free-text user-entered value (subnational on
    # unit/plant) beats the resolved subdivision lookup, since researchers
    # often enter the locally-used spelling.
    loc_subnat = (unit.get("unit_subnational_json")
                  or plant.get("plant_subnational")
                  or plant.get("plant_subnational_json")
                  or plant.get("subdivision_name") or "")
    loc_lat = unit.get("unit_lat_str") or plant.get("plant_lat_str") or ""
    loc_lon = unit.get("unit_lon_str") or plant.get("plant_lon_str") or ""
    loc_accuracy = unit.get("unit_accuracy_json") or plant.get("plant_accuracy_json") or plant.get("plant_accuracy") or ""
    loc_ds = unit.get("unit_location_ds") or plant.get("plant_location_ds") or []
    state_province = loc_subnat

    row = {
        "TerminalID": f"{ID_PREFIX_PLANT}{plant_id}",
        "UnitID": f"{ID_PREFIX_UNIT}{unit_id}" if unit_id else "",
        "Wiki": plant.get("wiki_url") or "",
        "TerminalName": plant.get("terminal_name") or "",
        "UnitName": unit.get("unit_name") or "",
        "FacilityType": unit.get("facility_type") or "",
        "FacilityType [ref]": refs(unit.get("facility_type_ds")),
        "Fuel": unit.get("fuel") or "",
        "Status": sd["Status"],
        "Substatus": sd["Substatus"],
        "Status [ref]": sd["Status [ref]"],
        "Country/Area": plant.get("country_name") or "",
        "Researcher": researcher,
        "LastUpdated": last_updated_s,
        "ResearcherNotesUnit": unit.get("unit_notes") or "",
        "ResearcherNotesProject": plant.get("plant_notes") or "",
        "OtherNames": other_names,
        "LocalNames": local_names,
        "Language": language_names,
        "Owner": owner_str,
        "Owner [ref]": owner_ref,
        "Parent": parent_str,
        "ParentHQCountry": parent_hq_str,
        "Parent GEM Entity ID": parent_id_str,
        "Operator": operator_str,
        "Operator [ref]": operator_ref,
        "Capacity": _fmt_fixed2(unit.get("capacity")),
        "CapacityUnits": unit.get("capacity_unit") or "",
        "CapacityinMtpa": _fmt_min1dp(capacity_in_mtpa),
        "CapacityinBcm/y": _fmt_min1dp(capacity_in_bcm),
        "Capacity [ref]": refs(unit.get("unit_capacity_ds")),
        "TotImportLNGTerminalCapacityinMtpa": _fmt_min1dp(tot_imp_mtpa),
        "TotImportLNGTerminalCapacityinBcm/y": _fmt_min1dp(tot_imp_bcm),
        "TotExportLNGTerminalCapacityinMtpa": _fmt_min1dp(tot_exp_mtpa),
        "TotExportLNGTerminalCapacityinBcm/y": _fmt_min1dp(tot_exp_bcm),
        "ProposalYear": sd["ProposalYear"],
        "ProposalMonth": sd["ProposalMonth"],
        "ProposalDate [ref]": sd["ProposalDate [ref]"],
        "ConstructionYear": sd["ConstructionYear"],
        "ConstructionMonth": sd["ConstructionMonth"],
        "ConstructionDate [ref]": sd["ConstructionDate [ref]"],
        "OriginalPlannedStartYear": sd["OriginalPlannedStartYear"],
        "LatestPlannedStartYear": sd["LatestPlannedStartYear"],
        "ActualStartYear": sd["ActualStartYear"],
        "ActualStartMonth": sd["ActualStartMonth"],
        "ActualStartYear2": sd["ActualStartYear2"],
        "ActualStartYear3": sd["ActualStartYear3"],
        "StartDate [ref]": sd["StartDate [ref]"],
        "ShelvedYear": sd["ShelvedYear"],
        "ShelvedYear [ref]": sd["ShelvedYear [ref]"],
        "CancelledYear": sd["CancelledYear"],
        "CancelledYear [ref]": sd["CancelledYear [ref]"],
        "StopYear": sd["StopYear"],
        "StopYear [ref]": sd["StopYear [ref]"],
        "PlannedStopYear": sd["PlannedStopYear"],
        "ShelvedCancelledStatusType": sd["ShelvedCancelledStatusType"],
        "TempFacility": unit.get("temp_facility") or "",
        "ImportExportOnly": _yn(unit.get("import_export_only")),
        "Location": loc_city,
        "Region": plant.get("region") or "",
        "SubRegion": plant.get("subregion") or "",
        "Prefecture/District": plant.get("plant_major_area") or "",
        "State/Province": state_province,
        "Latitude": loc_lat,
        "Longitude": loc_lon,
        "Accuracy": loc_accuracy,
        "Location [ref]": refs(loc_ds),
        "AssociatedTerminals": _comma_join_strs(lp.get("assoc_projects") or []),
        "AssociatedTerminals [ref]": refs(lp.get("assoc_projects_ds")),
        "Source": _comma_join_strs(lp.get("lng_source") or []),
        "Source [ref]": refs(lp.get("lng_source_ds")),
        "PowerPlantsSupplied": _comma_join_strs(lp.get("pps") or []),
        "PowerPlantsSupplied [ref]": refs(lp.get("pps_ds")),
        "CaptiveGasPower": _yn(lp.get("captive_gas_power")),
        "CaptiveGasPower [ref]": refs(lp.get("captive_gas_power_ds")),
        "Pipelines": _comma_join_strs(lp.get("pipelines") or []),
        "Pipelines [ref]": refs(lp.get("pipelines_ds")),
        "Cost": _fmt_fixed2(unit.get("cost")),
        "CostUnits": unit.get("cost_unit") or "",
        "CostYear": str(unit.get("cost_year") or "") if unit.get("cost_year") else "",
        # When the unit's cost is already in USD we can populate CostUSD directly.
        # FX conversion to EUR (CostEuro) needs a historical USD-EUR rate for
        # CostYear; not wired yet — left blank.
        "CostUSD": _fmt_min1dp(unit.get("cost")) if (unit.get("cost_unit") or "").upper() == "USD" else "",
        "CostEuro": "",
        # Cost [ref] only shows when there's an actual cost. Some units carry a
        # leftover costDatasource even when the cost itself is blank — the
        # website hides the reference in that case.
        "Cost [ref]": refs(unit.get("cost_ds")) if unit.get("cost") is not None else "",
        "TotKnownTerminalCostsUSD": _fmt_min1dp(totals.get("total_cost_usd")),
        "TotTerminalCost [ref]": "",
        "FIDStatus": sd["FIDStatus"],
        "FIDYear": sd["FIDYear"],
        "FIDYear [ref]": sd["FIDYear [ref]"],
        "Financing": unit.get("financing") or "",
        "Financing [ref]": refs(unit.get("financing_ds")),
        "Offshore": _yn(lp.get("offshore")),
        "Floating": _yn(lp.get("floating")),
        "FloatingVesselName": _comma_join_strs(lp.get("vessel_name") or []),
        "FloatingVesselName [ref]": refs(lp.get("vessel_name_ds")),
        "VesselOwner": vessel_own_str,
        "VesselOwner [ref]": vessel_own_ref,
        "VesselParent": "",  # would need company_owner traversal on vessel owners
        "VesselOperator": vessel_op_str,
        "VesselOperator [ref]": vessel_op_ref,
        "Opposition": _yn(lp.get("opposition")),
        "ESJNotes": lp.get("esj_notes") or "",
        "Defeated": _yn(unit.get("defeated")),
        "PCINotes": lp.get("pci_notes") or "",
        "PCI3": lp.get("pci3") or "",
        "PCI4": lp.get("pci4") or "",
        "PCI5": lp.get("pci5") or "",
        "PCI6": lp.get("pci6") or "",
        "LH2": _yn(unit.get("lh2")),
        "NH3": _yn(unit.get("nh3")),
        "SyntheticLNG": _yn(unit.get("synthetic_lng")),
        "RetrofitProposed": _yn(unit.get("retrofit_proposed")),
        "AltFuelPrelimAgreement": _yn(unit.get("alt_fuel_prelim")),
        "AltFuelCallMarketInterest": _yn(unit.get("alt_fuel_call")),
        "CCS": _yn(lp.get("ccs")),
        "CCSNotes": lp.get("ccs_notes") or "",
    }
    return row


def _compute_plant_totals(units: list[dict]) -> dict[int, dict]:
    """Aggregate per-plant totals: capacity by facility type + total USD cost."""
    cap_totals: dict[int, dict] = defaultdict(lambda: {
        "import_mtpa": Decimal("0"), "export_mtpa": Decimal("0"),
    })
    cost_totals: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    cost_seen: dict[int, bool] = defaultdict(bool)
    for u in units:
        ft = (u.get("facility_type") or "").lower()
        mtpa = _capacity_in_mtpa(u.get("capacity"), u.get("capacity_unit"))
        if mtpa is not None:
            if ft == "import":
                cap_totals[u["plant_id"]]["import_mtpa"] += mtpa
            elif ft == "export":
                cap_totals[u["plant_id"]]["export_mtpa"] += mtpa
        if u.get("cost") is not None and (u.get("cost_unit") or "").upper() == "USD":
            cost_totals[u["plant_id"]] += Decimal(u["cost"])
            cost_seen[u["plant_id"]] = True
    out: dict[int, dict] = {}
    plant_ids = set(cap_totals.keys()) | set(cost_totals.keys())
    for pid in plant_ids:
        t = cap_totals.get(pid, {"import_mtpa": Decimal("0"), "export_mtpa": Decimal("0")})
        imp = t["import_mtpa"] if t["import_mtpa"] > 0 else None
        exp = t["export_mtpa"] if t["export_mtpa"] > 0 else None
        out[pid] = {
            "import_mtpa": imp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if imp else None,
            "import_bcm": _capacity_in_bcm(imp) if imp else None,
            "export_mtpa": exp.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if exp else None,
            "export_bcm": _capacity_in_bcm(exp) if exp else None,
            "total_cost_usd": cost_totals[pid] if cost_seen[pid] else None,
        }
    return out


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

# ==========================================================================
# GOGPT (oil & gas power plants) all-fields export
# ==========================================================================
#
# Mirrors the website's `format=gas_all&tracker=GOGPT` export — one row per
# powerplant_unit where the plant is projectType=1 (combustion) AND the unit's
# trackerSearch='GOGPT'. Column layout is reverse-engineered from a fresh
# website export (`GOGPT-all-2026-05-22T183522.csv`, 86 cols, 34,515 rows).

GOGPT_COLUMNS = [
    "Last Updated", "Researcher", "Research status",
    "Wiki URL", "Country/Area",
    "Plant name", "Plant Name in Local Language / Script", "Other Name(s)",
    "Unit name", "Fuel", "Fuel Data Source",
    "Number Of Engines", "Capacity Per Engine",
    "Capacity (MW)", "Capacity Data Source",
    "Status", "Status Detail", "Status Data Source",
    "Disrupted due to conflict", "Disrupted due to conflict Data Source",
    "Latest Activity", "Latest Activity Data Source",
    "Cancellation year", "Cancellation year Data Source",
    "Turbine/Engine Technology", "Turbine/Engine Technology Data Source",
    "Equipment Manufacturer/Model", "Turbine/Engine Equipment Data Source",
    "CHP", "CHP Data Source",
    "Hydrogen capable?", "Hydrogen Notes", "Hydrogen Data Source",
    "H2 ready turbine (%)?", "MOU for H2 supply?", "Contract for H2 supply?",
    "Financing for supply of H2?",
    "Co-located with electrolyzer/H2 production facility?",
    "What % of H2 blending currently?", "H2 Criteria Data Source",
    "CCS attachment?", "CCS Data Source",
    "Conversion/replacement?",
    "Conversion from/replacement of (fuel)",
    "Conversion from/replacement of (GEM unit ID)",
    "Conversion/replacement Data Source",
    "Conversion to (fuel)", "Conversion to (GEM unit ID)",
    "Start year", "Start Year Data Source",
    "Retired year", "Retired Year Data Source",
    "Planned retire", "Planned Retire Data Source",
    "Operator(s)", "Operators Data Source", "Operator GEM Entity ID",
    "Owner(s)", "Owner(s) GEM Entity ID", "Owners Data Source",
    "Parent(s)", "Parent GEM Entity ID",
    "Latitude", "Longitude", "Location accuracy", "Location Data Source",
    "City",
    "Local area (taluk, county)",
    "Major area (prefecture, district)",
    "State/Province", "Subregion", "Region",
    "Other IDs (location)", "Other IDs (unit)",
    "Notes",
    "Captive industry use", "Captive industry type",
    "Captive non-industry use", "Captive Data Source",
    "GEM location ID", "GEM unit ID",
    "WEPP location ID", "WEPP unit ID",
    "Employment Notes", "Employment Notes Data Source",
    "Linked Projects",
]

# The single external-id system the website breaks out into its own columns.
# The full name in `external_id_system.name` is parenthesized; the website
# strips the value into the dedicated "WEPP ... ID" columns.
WEPP_SYSTEM_NAME = "WEPP (S&P Global Platts)"


def _fmt_year(y) -> str:
    if y is None:
        return ""
    return str(int(y))


def _fmt_latest_activity(year, month, day) -> str:
    """Render `latestActivityYear/Month/Day` as 'Year: YYYY[, Month: M][, Day: D]'."""
    if year is None:
        return ""
    parts = [f"Year: {int(year)}"]
    if month is not None:
        parts.append(f"Month: {int(month)}")
    if day is not None:
        parts.append(f"Day: {int(day)}")
    return ", ".join(parts)


def _fmt_yes_no_option(option: str | None) -> str:
    """ccs/chp/hydrogen_capable.option is already a display string ('yes',
    'no', 'not found', 'using hydrogen', ...). Pass through, blank for NULL."""
    return option or ""


def _fmt_bool_yes_blank(b) -> str:
    """The website renders many `*` boolean columns as 'yes' / blank for
    false-or-null (NOT 'yes' / 'no'). Mirrors the LNG `_yn` convention but
    with a lowercase 'yes' as required by the gas_all export."""
    if b is True:
        return "yes"
    return ""


def _join_external_ids(rows: list[dict], system_lookup: dict[int, str],
                       exclude_system: str = WEPP_SYSTEM_NAME) -> str:
    """Render rows of {externalId, idSystem_id} as '<system>: <id>, ...',
    skipping any whose system name matches `exclude_system` (WEPP gets its
    own dedicated columns)."""
    parts: list[str] = []
    for r in rows:
        sys_name = system_lookup.get(r.get("idSystem_id")) or ""
        if not sys_name or sys_name == exclude_system:
            continue
        ext = (r.get("externalId") or "").strip()
        if not ext:
            continue
        parts.append(f"{sys_name}: {ext}")
    return ", ".join(parts)


def _join_wepp_ids(rows: list[dict], system_lookup: dict[int, str]) -> str:
    """Render the externalId values for WEPP rows, comma-joined."""
    parts: list[str] = []
    for r in rows:
        sys_name = system_lookup.get(r.get("idSystem_id")) or ""
        if sys_name != WEPP_SYSTEM_NAME:
            continue
        ext = (r.get("externalId") or "").strip()
        if ext:
            parts.append(ext)
    return ", ".join(parts)


def _fetch_gogpt_plants(engine: Engine, limit: int | None) -> list[dict]:
    """Combustion plants that have at least one GOGPT unit."""
    sql = """
        SELECT
            p.id AS plant_id,
            p.name AS plant_name,
            p."wikiUrl" AS wiki_url,
            p."nameOther" AS name_other,
            p.notes AS plant_notes,
            p."employmentNotes" AS employment_notes,
            p."employmentNotesDatasource" AS employment_notes_ds,
            p.city AS plant_city,
            p."localArea" AS plant_local_area,
            p."majorArea" AS plant_major_area,
            p.subnational AS plant_subnational,
            p."subnationalLookup_id" AS subdivision_lookup_id,
            p.latitude AS plant_lat,
            p.longitude AS plant_lon,
            p."locationAccuracy" AS plant_accuracy,
            p."locationDatasource" AS plant_location_ds,
            p."plantJSON"->>'latitude' AS plant_lat_str,
            p."plantJSON"->>'longitude' AS plant_lon_str,
            p."plantJSON"->>'city' AS plant_city_json,
            p."plantJSON"->>'subnational' AS plant_subnational_json,
            p."plantJSON"->>'locationAccuracy' AS plant_accuracy_json,
            p."plantLevelOwners" AS plant_level_owners,
            p."plantLevelOperators" AS plant_level_operators,
            p.captive AS plant_captive,
            p."captiveDatasource" AS plant_captive_ds,
            p."captiveIndustryType" AS plant_captive_industry_type_jsonb,
            ciu.option AS plant_captive_industry_use_option,
            cniu.option AS plant_captive_non_industry_use_option,
            p.country_id AS country_id,
            c."gemName" AS country_name,
            c.region AS region,
            c."subRegion" AS subregion,
            cs.name AS subdivision_name
        FROM plant p
        LEFT JOIN country c ON c.id = p.country_id
        LEFT JOIN project_country_subdivision cs ON cs.id = p."subnationalLookup_id"
        LEFT JOIN captive_industry_use ciu ON ciu.id = p."captiveIndustryUse_id"
        LEFT JOIN captive_non_industry_use cniu ON cniu.id = p."captiveNonIndustryUse_id"
        WHERE p."projectType" = :ptype AND p.deleted = false
        ORDER BY p.name, p.id
    """
    # Note: the website's `format=gas_all&tracker=GOGPT` URL is misleading
    # — the export actually contains every combustion (projectType=1) unit,
    # not just units whose trackerSearch='GOGPT'. The tracker parameter
    # only affects which sub-page of the site the export was launched from.
    if limit:
        sql += f" LIMIT {int(limit)}"
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            {"ptype": COMBUSTION_PROJECT_TYPE},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _fetch_gogpt_units(engine: Engine, plant_ids: list[int]) -> list[dict]:
    """Powerplant units with trackerSearch=GOGPT, joined to status/ccs/chp/h2 lookups."""
    if not plant_ids:
        return []
    sql = """
        SELECT
            pu.id AS unit_id,
            pu.plant_id AS plant_id,
            pu.name AS unit_name,
            pu."nameLocal" AS unit_name_local,
            pu.capacity AS capacity,
            pu."capacityDatasource" AS capacity_ds,
            pu."capacityPerEngine" AS capacity_per_engine,
            pu."numberOfEngines" AS number_of_engines,
            pu."statusDetail" AS status_detail,
            pu."statusDatasource" AS status_ds,
            pu."disruptedDueToConflict" AS disrupted,
            pu."disruptedDueToConflictDatasource" AS disrupted_ds,
            pu."latestActivityYear" AS latest_activity_year,
            pu."latestActivityMonth" AS latest_activity_month,
            pu."latestActivityDay" AS latest_activity_day,
            pu."latestActivityDatasource" AS latest_activity_ds,
            pu."cancellationYear" AS cancellation_year,
            pu."cancellationYearDatasource" AS cancellation_year_ds,
            pu."fuelDatasource" AS fuel_ds,
            pu.turbine AS turbine_text,
            pu."turbineDatasource" AS turbine_ds,
            pu.technology AS technology_json,
            pu."technologyDatasource" AS technology_ds,
            pu."hydrogenNotes" AS hydrogen_notes,
            pu."hydrogenCapableDatasource" AS hydrogen_ds,
            pu."H2ReadyTurbine" AS h2_ready_turbine,
            pu."MOUH2Supply" AS h2_mou,
            pu."contractH2Supply" AS h2_contract,
            pu."financingH2Supply" AS h2_financing,
            pu."colocatedWithProduction" AS h2_colocated,
            pu."percentageBlending" AS h2_blending_pct,
            pu."H2CriteriaDatasource" AS h2_criteria_ds,
            pu."ccsDatasource" AS ccs_ds,
            pu."ccsAttachment_id" AS ccs_attachment_id,
            pu."chpDatasource" AS chp_ds,
            pu."chp_id" AS chp_id,
            pu."hydrogenCapable_id" AS hydrogen_capable_id,
            pu."fuelConversion" AS fuel_conversion,
            pu."fuelConversionUnknown" AS fuel_conversion_unknown,
            pu."fuelConversionInitialUnit_id" AS fuel_conversion_initial_unit_id,
            pu."startYearLow" AS start_year_low,
            pu."startYearHigh" AS start_year_high,
            pu."startYearPlanned" AS start_year_planned,
            pu."startYearDatasource" AS start_year_ds,
            pu."endYearLow" AS end_year_low,
            pu."endYearHigh" AS end_year_high,
            pu."endYearPlanned" AS end_year_planned,
            pu."endYearDatasource" AS end_year_ds,
            pu."plannedRetiredYear" AS planned_retired_year,
            pu."plannedRetiredDatasource" AS planned_retired_ds,
            pu."localArea" AS unit_local_area,
            pu."majorArea" AS unit_major_area,
            pu.latitude AS unit_lat,
            pu.longitude AS unit_lon,
            pu."locationAccuracy" AS unit_accuracy,
            pu."locationDatasource" AS unit_location_ds,
            pu."unitJSON"->>'latitude' AS unit_lat_str,
            pu."unitJSON"->>'longitude' AS unit_lon_str,
            pu."unitJSON"->>'city' AS unit_city_json,
            pu."unitJSON"->>'subnational' AS unit_subnational_json,
            pu."unitJSON"->>'locationAccuracy' AS unit_accuracy_json,
            st.name AS status_name,
            ccs.option AS ccs_option,
            chp.option AS chp_option,
            hc.option AS hydrogen_capable_option
        FROM powerplant_unit pu
        LEFT JOIN status st ON st.id = pu.status_id
        LEFT JOIN ccs ccs ON ccs.id = pu."ccsAttachment_id"
        LEFT JOIN chp chp ON chp.id = pu.chp_id
        LEFT JOIN hydrogen_capable hc ON hc.id = pu."hydrogenCapable_id"
        WHERE pu.plant_id = ANY(:plant_ids)
          AND pu.deleted = false
        ORDER BY pu.plant_id, pu.id
    """
    with engine.connect() as conn:
        rows = conn.execute(
            text(sql), {"plant_ids": plant_ids},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _fetch_unit_fuels(engine: Engine, unit_ids: list[int]) -> dict[int, list[dict]]:
    """Per-unit list of {category, detail, percentage} fuel rows."""
    if not unit_ids:
        return {}
    sql = """
        SELECT uf.powerplant_unit_id AS unit_id,
               fc.name AS category_name,
               fd.detail AS detail_name,
               uf.percentage AS percentage,
               uf.id AS uf_id
        FROM unit_fuel uf
        LEFT JOIN fuel_category fc ON fc.id = uf.category_id
        LEFT JOIN fuel_detail fd ON fd.id = uf.detail_id
        WHERE uf.powerplant_unit_id = ANY(:ids)
        -- Primary fuel first (matches the website), then by row id for stability.
        ORDER BY uf.powerplant_unit_id, uf.primary DESC NULLS LAST, uf.id
    """
    out: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"ids": unit_ids}):
            out[r._mapping["unit_id"]].append(_row_to_dict(r))
    return dict(out)


def _fetch_unit_turbines(engine: Engine, unit_ids: list[int]) -> dict[int, list[dict]]:
    if not unit_ids:
        return {}
    sql = """
        SELECT ut.unit_id AS unit_id,
               ut.model AS model,
               tm.option AS manufacturer
        FROM unit_turbine ut
        LEFT JOIN turbine_manufacturer tm ON tm.id = ut."turbineManufacturer_id"
        WHERE ut.unit_id = ANY(:ids)
        ORDER BY ut.unit_id, ut.id
    """
    out: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"ids": unit_ids}):
            out[r._mapping["unit_id"]].append(_row_to_dict(r))
    return dict(out)


def _fetch_unit_replacements(engine: Engine, unit_ids: list[int]) -> dict[int, list[dict]]:
    """unit_replacement rows. Each carries the GEM unit ID being replaced/converted-from."""
    if not unit_ids:
        return {}
    sql = """
        SELECT ur.unit_id AS unit_id,
               ur."unitReplacementId" AS replacement_target_id,
               urt.option AS replacement_type,
               ur."unitReplacementDatasource" AS replacement_ds
        FROM unit_replacement ur
        LEFT JOIN unit_replacement_type urt ON urt.id = ur."unitReplacementType_id"
        WHERE ur.unit_id = ANY(:ids)
        ORDER BY ur.unit_id, ur.id
    """
    out: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"ids": unit_ids}):
            out[r._mapping["unit_id"]].append(_row_to_dict(r))
    return dict(out)


def _fetch_plant_external_ids(engine: Engine, plant_ids: list[int]) -> dict[int, list[dict]]:
    if not plant_ids:
        return {}
    sql = """
        SELECT plant_id, "externalId", "idSystem_id", id
        FROM plant_external_id
        WHERE plant_id = ANY(:ids)
        ORDER BY plant_id, id
    """
    out: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"ids": plant_ids}):
            out[r._mapping["plant_id"]].append(_row_to_dict(r))
    return dict(out)


def _fetch_unit_external_ids(engine: Engine, unit_ids: list[int]) -> dict[int, list[dict]]:
    if not unit_ids:
        return {}
    sql = """
        SELECT unit_id, "externalId", "idSystem_id", id
        FROM unit_external_id
        WHERE unit_id = ANY(:ids)
        ORDER BY unit_id, id
    """
    out: dict[int, list[dict]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"ids": unit_ids}):
            out[r._mapping["unit_id"]].append(_row_to_dict(r))
    return dict(out)


def _fetch_external_id_systems(engine: Engine) -> dict[int, str]:
    """All external_id_system rows. Tiny table (~50 rows), cheap to fetch in full."""
    sql = "SELECT id, name FROM external_id_system"
    with engine.connect() as conn:
        return {r._mapping["id"]: r._mapping["name"] for r in conn.execute(text(sql))}


def _fetch_technology_names(engine: Engine) -> dict[int, str]:
    """All technology id->name pairs (tiny lookup)."""
    sql = "SELECT id, name FROM technology"
    with engine.connect() as conn:
        return {r._mapping["id"]: r._mapping["name"] for r in conn.execute(text(sql))}


def _fetch_captive_industry_types(engine: Engine) -> dict[int, str]:
    """captive_industry_type lookup."""
    sql = "SELECT id, option FROM captive_industry_type"
    with engine.connect() as conn:
        return {r._mapping["id"]: r._mapping["option"] for r in conn.execute(text(sql))}


def _fetch_unit_research_status(engine: Engine, unit_ids: list[int]) -> dict[int, str]:
    """Most-recent unit_update's research_status per unit."""
    if not unit_ids:
        return {}
    sql = """
        SELECT DISTINCT ON (uu.unit_id) uu.unit_id, rs.option AS research_status
        FROM unit_update uu
        LEFT JOIN research_status rs ON rs.id = uu."researchStatus_id"
        WHERE uu.unit_id = ANY(:unit_ids)
        ORDER BY uu.unit_id, uu."lastUpdated" DESC NULLS LAST
    """
    with engine.connect() as conn:
        return {
            r._mapping["unit_id"]: r._mapping["research_status"]
            for r in conn.execute(text(sql), {"unit_ids": unit_ids})
        }


def _fetch_project_links(engine: Engine, plant_ids: list[int]) -> dict[int, list[str]]:
    """plant.id -> [linkedProject_id, ...] strings."""
    if not plant_ids:
        return {}
    sql = """
        SELECT project_id, "linkedProject_id"
        FROM project_links
        WHERE project_id = ANY(:ids)
        ORDER BY project_id, id
    """
    out: dict[int, list[str]] = defaultdict(list)
    with engine.connect() as conn:
        for r in conn.execute(text(sql), {"ids": plant_ids}):
            link = r._mapping["linkedProject_id"]
            if link:
                out[r._mapping["project_id"]].append(str(link))
    return dict(out)


def _format_fuel_list(rows: list[dict]) -> str:
    """Render unit_fuel rows as '<category>: <detail>[ [pct%]], <category>: <detail>, ...'.

    Matches the website's gas_all format: comma-separated, percentage in
    square brackets when present. Percentage = 100% is omitted (the website
    treats it as the implicit default for single-fuel units).
    """
    parts: list[str] = []
    for r in rows:
        cat = r.get("category_name") or ""
        det = r.get("detail_name") or ""
        if not cat and not det:
            continue
        s = f"{cat}: {det}" if cat else det
        pct = r.get("percentage")
        if pct is not None:
            d = Decimal(pct)
            if d != Decimal(100):
                if d == d.to_integral_value():
                    s += f" [{int(d)}%]"
                else:
                    s += f" [{d.normalize()}%]"
        parts.append(s)
    return ", ".join(parts)


def _format_turbine_list(rows: list[dict]) -> tuple[str, str]:
    """Returns (manufacturer_models_str, technology_unused).

    Manufacturer/Model column joins manufacturer + model with a space when
    both present; just the populated one otherwise. Comma-separated across
    multiple turbines.
    """
    parts: list[str] = []
    for r in rows:
        mfr = (r.get("manufacturer") or "").strip()
        model = (r.get("model") or "").strip()
        if mfr and model:
            parts.append(f"{mfr}: {model}")
        elif mfr:
            parts.append(mfr)
        elif model:
            parts.append(model)
    return ", ".join(parts), ""


def _format_technology(tech_jsonb, tech_names: dict[int, str]) -> str:
    """`powerplant_unit.technology` is a jsonb array of integer IDs into the
    `technology` lookup table."""
    if not tech_jsonb:
        return ""
    if not isinstance(tech_jsonb, list):
        return ""
    names: list[str] = []
    for t in tech_jsonb:
        try:
            tid = int(t)
        except (TypeError, ValueError):
            continue
        nm = tech_names.get(tid)
        if nm:
            names.append(nm)
    return ", ".join(names)


def _format_captive_industry_type(jsonb_val, type_names: dict[int, str]) -> str:
    """`plant.captiveIndustryType` is a jsonb array of integer IDs into the
    `captive_industry_type` lookup table."""
    if not jsonb_val or not isinstance(jsonb_val, list):
        return ""
    names: list[str] = []
    for t in jsonb_val:
        try:
            tid = int(t)
        except (TypeError, ValueError):
            continue
        nm = type_names.get(tid)
        if nm:
            names.append(nm)
    return ", ".join(names)


def _format_start_or_end_year(low, high) -> str:
    """Year column: 'YYYY' if same, 'YYYY-YYYY' if a range, blank otherwise."""
    if low is None and high is None:
        return ""
    if low is not None and high is not None and int(low) != int(high):
        return f"{int(low)}-{int(high)}"
    val = low if low is not None else high
    return str(int(val))


def _build_gogpt_owners_parents(plant: dict, unit: dict, ctx: dict):
    """Return (owner_str, owner_id_str, owner_ref, parent_str, parent_id_str)."""
    ds = ctx["data_sources"]
    if plant.get("plant_level_owners"):
        owners = ctx["owners_by_plant"].get(plant["plant_id"], [])
    else:
        owners = ctx["owners_by_unit"].get(unit["unit_id"], [])

    # Sort by share DESC NULLS LAST, then by plant_owner.id ASC. Fits the
    # reference for tied numeric shares; all-NULL-share multi-owner rows
    # follow a different (un-reverse-engineered) order — known issue from
    # the LNG export too.
    owners = sorted(
        owners,
        key=lambda o: (
            o.get("share") is None,
            -Decimal(o["share"]) if o.get("share") is not None else Decimal(0),
            o.get("po_id") or 0,
        ),
    )

    owner_entries = [
        (_company_display(o["company_name"], o["legal_type"]), o["share"])
        for o in owners
    ]
    owner_str = _join_entities(owner_entries, share_fmt=_fmt_share_owner_int)
    owner_id_entries = [(o["company_id"], o["share"]) for o in owners]
    owner_id_str = _join_ids(owner_id_entries, share_fmt=_fmt_share_owner_int)
    owner_ds_ids: list[int] = []
    for o in owners:
        owner_ds_ids.extend(o.get("share_ds") or [])
    owner_ref = _resolve_refs(owner_ds_ids, ds)

    # Parent column: parse gemParents and gemParentsIds, compute effective
    # share-of-unit per parent (owner_share × parent_share_in_brackets / 100).
    # When gemParents is empty/NULL, fall back to the owner itself with no
    # share displayed — the website's behavior for ungrouped owners.
    parent_pieces: list[str] = []
    parent_id_pieces: list[str] = []
    for o in owners:
        gp = o.get("gem_parents")
        gpi = o.get("gem_parents_ids")
        owner_id = o["company_id"]
        owner_share = o.get("share")
        if not gp:
            # No curated parent → the owner is its own parent. Setting
            # gp_share=100 means the effective share displayed equals the
            # owner's share-of-unit (e.g. owner@100% → '[100.0%]', NULL
            # owner-share → blank).
            name = _company_display(o["company_name"], o["legal_type"])
            parent_entries = [(name, Decimal(100))]
            parent_id_entries = [(f"{ID_PREFIX_ENTITY}{owner_id}", Decimal(100))]
        else:
            parent_entries = _parse_gemparents(gp)
            parent_id_entries = _parse_gemparents(gpi)

        parent_pieces.extend(
            _format_gogpt_parent_pieces(parent_entries, owner_share)
        )
        parent_id_pieces.extend(
            _format_gogpt_parent_pieces(parent_id_entries, owner_share)
        )

    return (
        owner_str, owner_id_str, owner_ref,
        "; ".join(parent_pieces), "; ".join(parent_id_pieces),
    )


def _build_gogpt_operators(plant: dict, unit: dict, ctx: dict):
    """Return (operator_str, operator_ref, operator_id_str)."""
    ds = ctx["data_sources"]
    if plant.get("plant_level_operators"):
        ops = ctx["operators_by_plant"].get(plant["plant_id"], [])
    else:
        ops = ctx["operators_by_unit"].get(unit["unit_id"], [])
    main = [o for o in ops if (o.get("type") or "operator") == "operator"]
    entries = [(o["company_name"], o["share"]) for o in main]
    op_str = _join_entities(entries, share_fmt=_fmt_share_owner)
    op_id_entries = [(o["company_id"], o["share"]) for o in main]
    op_id_str = _join_ids(op_id_entries, share_fmt=_fmt_share_owner)
    op_ds_ids: list[int] = []
    for o in main:
        op_ds_ids.extend(o.get("op_ds") or [])
    return op_str, _resolve_refs(op_ds_ids, ds), op_id_str


def _build_gogpt_conversion(unit: dict, ctx: dict) -> dict:
    """Conversion/replacement fields for one unit.

    Type column rules:
      - 'replacement' when THIS unit has `unit_replacement` rows (i.e., it
        replaced one or more predecessor units).
      - 'conversion' when `fuelConversion=True` AND
        `fuelConversionInitialUnit_id` IS NOT NULL (i.e., this unit IS the
        post-conversion side of a fuel switch, with a known predecessor).
      - blank otherwise. In particular: being the PREDECESSOR (back-ref via
        another unit's unitReplacementId or fuelConversionInitialUnit_id)
        does NOT set the type, but DOES populate the "to" columns.

    'from' columns describe the predecessor (replaced-from or converted-from);
    'to' columns describe what this unit was later replaced/converted into.
    """
    out = {
        "type": "",
        "from_fuel": "",
        "from_id": "",
        "ds": [],
        "to_fuel": "",
        "to_id": "",
    }
    uid = unit["unit_id"]

    own_replacements = ctx["replacements_by_unit"].get(uid, [])
    if own_replacements:
        out["type"] = "replacement"
        pred_ids = [r.get("replacement_target_id") for r in own_replacements if r.get("replacement_target_id")]
        out["from_id"] = ", ".join(f"{ID_PREFIX_UNIT}{int(p)}" for p in pred_ids)
        out["from_fuel"] = ", ".join(
            ctx["fuel_by_unit_str"].get(int(p), "") for p in pred_ids
        )
        for r in own_replacements:
            out["ds"].extend(r.get("replacement_ds") or [])

    # Fuel conversion (this unit converted from an earlier one). When
    # `fuelConversionInitialUnit_id` is NULL the conversion isn't displayed.
    init_id = unit.get("fuel_conversion_initial_unit_id")
    if unit.get("fuel_conversion") and init_id:
        out["type"] = "conversion"
        out["from_id"] = f"{ID_PREFIX_UNIT}{int(init_id)}"
        out["from_fuel"] = ctx["fuel_by_unit_str"].get(int(init_id), "")

    # "to" side: back-refs from unit_replacement (units that replaced THIS
    # one) and from fuelConversionInitialUnit_id (units that converted FROM
    # this one). Combined into a single comma list; does NOT change `type`.
    to_unit_ids: list[int] = []
    for r in ctx["replacement_back_refs"].get(uid, []):
        to_unit_ids.append(int(r["replacing_unit_id"]))
    for v in ctx["conversion_back_refs"].get(uid, []):
        to_unit_ids.append(int(v))
    if to_unit_ids:
        out["to_id"] = ", ".join(f"{ID_PREFIX_UNIT}{p}" for p in to_unit_ids)
        out["to_fuel"] = ", ".join(
            ctx["fuel_by_unit_str"].get(p, "") for p in to_unit_ids
        )

    return out


def _gogpt_build_row(plant: dict, unit: dict, ctx: dict) -> dict:
    ds = ctx["data_sources"]
    plant_id = plant["plant_id"]
    unit_id = unit["unit_id"]

    def refs(v):
        return _resolve_refs(v or [], ds)

    # Last Updated / Researcher.
    uu = ctx["unit_updates"].get(unit_id) or {}
    last_updated = uu.get("last_updated")
    last_updated_s = last_updated.isoformat() if last_updated else ""
    researcher = ""
    if uu.get("first_name") or uu.get("last_name"):
        researcher = f"{uu.get('first_name') or ''} {uu.get('last_name') or ''}".strip()
    research_status = ctx["unit_research_status"].get(unit_id) or ""

    # Location-block fields. Priority: plant > unit, since GOGPT plants
    # usually share one location across all generating units. When the
    # plant has nothing we fall through to the unit-level columns.
    loc_city = plant.get("plant_city_json") or plant.get("plant_city") or unit.get("unit_city_json") or ""
    loc_lat = plant.get("plant_lat_str") or unit.get("unit_lat_str") or ""
    loc_lon = plant.get("plant_lon_str") or unit.get("unit_lon_str") or ""
    loc_accuracy = (plant.get("plant_accuracy_json")
                    or plant.get("plant_accuracy")
                    or unit.get("unit_accuracy_json") or "")
    loc_ds = plant.get("plant_location_ds") or unit.get("unit_location_ds") or []
    # State/Province priority: resolved ISO subdivision > free-text > unit
    # JSON. If the unit's subnational matches the Country/Area (e.g. unit
    # `subnational='Puerto Rico'` on a Puerto Rico-country plant), the
    # website hides the redundant value.
    country_name = plant.get("country_name") or ""
    unit_sub_fallback = unit.get("unit_subnational_json") or ""
    if unit_sub_fallback and unit_sub_fallback == country_name:
        unit_sub_fallback = ""
    loc_subnat = (plant.get("subdivision_name")
                  or plant.get("plant_subnational")
                  or plant.get("plant_subnational_json")
                  or unit_sub_fallback)
    # Local / Major area: unit-level columns on `powerplant_unit`, NOT the
    # similarly-named columns on `plant` (those are usually empty for GOGPT).
    local_area = unit.get("unit_local_area") or plant.get("plant_local_area") or ""
    major_area = unit.get("unit_major_area") or plant.get("plant_major_area") or ""

    # Owner / Parent / Operator.
    owner_str, owner_id_str, owner_ref, parent_str, parent_id_str = \
        _build_gogpt_owners_parents(plant, unit, ctx)
    operator_str, operator_ref, operator_id_str = _build_gogpt_operators(plant, unit, ctx)

    # Fuel (from unit_fuel) — but also there's a fallback to unit.technology_json
    # if no unit_fuel rows. (Not yet observed; leave as fuel-list.)
    fuel_rows = ctx["unit_fuels"].get(unit_id, [])
    fuel_str = _format_fuel_list(fuel_rows)

    # Turbine/Engine columns.
    turbine_rows = ctx["unit_turbines"].get(unit_id, [])
    turbine_mfr_model, _ = _format_turbine_list(turbine_rows)
    turbine_tech = (
        _format_technology(unit.get("technology_json"), ctx["technology_names"])
        or (unit.get("turbine_text") or "")
    )

    # External IDs split by WEPP vs everything else.
    plant_ext = ctx["plant_external_ids"].get(plant_id, [])
    unit_ext = ctx["unit_external_ids"].get(unit_id, [])
    sys_lookup = ctx["external_id_systems"]
    other_ids_loc = _join_external_ids(plant_ext, sys_lookup)
    other_ids_unit = _join_external_ids(unit_ext, sys_lookup)
    wepp_loc = _join_wepp_ids(plant_ext, sys_lookup)
    wepp_unit = _join_wepp_ids(unit_ext, sys_lookup)

    # Conversion/replacement.
    conv = _build_gogpt_conversion(unit, ctx)

    # Status / Years.
    status_name = unit.get("status_name") or ""
    start_year = _format_start_or_end_year(unit.get("start_year_low"), unit.get("start_year_high"))
    # End-year columns: when `endYearPlanned=True`, the unit's end year is a
    # planned retirement (goes into "Planned retire"); when false/null it's
    # an actual retirement (goes into "Retired year"). `plannedRetiredYear`
    # is a more recent revised plan that supersedes endYearLow when set.
    end_year_low = unit.get("end_year_low")
    end_year_high = unit.get("end_year_high")
    end_year_planned = unit.get("end_year_planned")
    if end_year_planned:
        retired_year = ""
        planned_retire = _fmt_year(unit.get("planned_retired_year") or end_year_low)
    else:
        retired_year = _format_start_or_end_year(end_year_low, end_year_high)
        planned_retire = _fmt_year(unit.get("planned_retired_year"))

    # Linked projects.
    links = ctx["project_links"].get(plant_id, [])
    linked_projects = ", ".join(links) if links else ""

    other_names = _comma_join_strs(plant.get("name_other") or [])

    # Plant local-language name: comma-join the `plant_language.name` rows.
    langs = ctx["plant_languages"].get(plant_id, [])
    plant_name_local = _comma_join_strs([l["local_name"] for l in langs if l.get("local_name")])

    row = {
        "Last Updated": last_updated_s,
        "Researcher": researcher,
        "Research status": research_status,
        "Wiki URL": plant.get("wiki_url") or "",
        "Country/Area": plant.get("country_name") or "",
        "Plant name": plant.get("plant_name") or "",
        "Plant Name in Local Language / Script": plant_name_local,
        "Other Name(s)": other_names,
        "Unit name": unit.get("unit_name") or "",
        "Fuel": fuel_str,
        "Fuel Data Source": refs(unit.get("fuel_ds")),
        "Number Of Engines": str(unit["number_of_engines"]) if unit.get("number_of_engines") is not None else "",
        "Capacity Per Engine": _fmt_min1dp(unit.get("capacity_per_engine")),
        "Capacity (MW)": _fmt_min1dp(unit.get("capacity")),
        "Capacity Data Source": refs(unit.get("capacity_ds")),
        "Status": status_name,
        "Status Detail": unit.get("status_detail") or "",
        "Status Data Source": refs(unit.get("status_ds")),
        "Disrupted due to conflict": _fmt_bool_yes_blank(unit.get("disrupted")),
        "Disrupted due to conflict Data Source": (
            refs(unit.get("disrupted_ds")) if unit.get("disrupted") else ""
        ),
        "Latest Activity": _fmt_latest_activity(
            unit.get("latest_activity_year"),
            unit.get("latest_activity_month"),
            unit.get("latest_activity_day"),
        ),
        "Latest Activity Data Source": refs(unit.get("latest_activity_ds")),
        "Cancellation year": _fmt_year(unit.get("cancellation_year")),
        "Cancellation year Data Source": refs(unit.get("cancellation_year_ds")),
        "Turbine/Engine Technology": turbine_tech,
        "Turbine/Engine Technology Data Source": refs(unit.get("technology_ds")),
        "Equipment Manufacturer/Model": turbine_mfr_model,
        "Turbine/Engine Equipment Data Source": refs(unit.get("turbine_ds")),
        "CHP": _fmt_yes_no_option(unit.get("chp_option")),
        "CHP Data Source": refs(unit.get("chp_ds")),
        "Hydrogen capable?": _fmt_yes_no_option(unit.get("hydrogen_capable_option")),
        "Hydrogen Notes": unit.get("hydrogen_notes") or "",
        "Hydrogen Data Source": refs(unit.get("hydrogen_ds")),
        "H2 ready turbine (%)?": str(unit["h2_ready_turbine"]) if unit.get("h2_ready_turbine") is not None else "",
        "MOU for H2 supply?": unit.get("h2_mou") or "",
        "Contract for H2 supply?": unit.get("h2_contract") or "",
        "Financing for supply of H2?": unit.get("h2_financing") or "",
        "Co-located with electrolyzer/H2 production facility?": unit.get("h2_colocated") or "",
        "What % of H2 blending currently?": str(unit["h2_blending_pct"]) if unit.get("h2_blending_pct") is not None else "",
        "H2 Criteria Data Source": refs(unit.get("h2_criteria_ds")),
        "CCS attachment?": _fmt_yes_no_option(unit.get("ccs_option")),
        "CCS Data Source": refs(unit.get("ccs_ds")),
        "Conversion/replacement?": conv["type"],
        "Conversion from/replacement of (fuel)": conv["from_fuel"],
        "Conversion from/replacement of (GEM unit ID)": conv["from_id"],
        "Conversion/replacement Data Source": refs(conv["ds"]),
        "Conversion to (fuel)": conv["to_fuel"],
        "Conversion to (GEM unit ID)": conv["to_id"],
        "Start year": start_year,
        "Start Year Data Source": refs(unit.get("start_year_ds")),
        "Retired year": retired_year,
        "Retired Year Data Source": refs(unit.get("end_year_ds")),
        "Planned retire": planned_retire,
        # When the planned-retire year comes from endYearLow (endYearPlanned=True)
        # rather than a separately-revised plannedRetiredYear, its data source
        # is endYearDatasource, not plannedRetiredDatasource.
        "Planned Retire Data Source": refs(
            unit.get("planned_retired_ds")
            or (unit.get("end_year_ds") if end_year_planned else None)
        ),
        "Operator(s)": operator_str,
        "Operators Data Source": operator_ref,
        "Operator GEM Entity ID": operator_id_str,
        "Owner(s)": owner_str,
        "Owner(s) GEM Entity ID": owner_id_str,
        "Owners Data Source": owner_ref,
        "Parent(s)": parent_str,
        "Parent GEM Entity ID": parent_id_str,
        "Latitude": loc_lat,
        "Longitude": loc_lon,
        "Location accuracy": loc_accuracy,
        "Location Data Source": refs(loc_ds),
        "City": loc_city,
        "Local area (taluk, county)": local_area,
        "Major area (prefecture, district)": major_area,
        "State/Province": loc_subnat,
        "Subregion": plant.get("subregion") or "",
        "Region": plant.get("region") or "",
        "Other IDs (location)": other_ids_loc,
        "Other IDs (unit)": other_ids_unit,
        "Notes": plant.get("plant_notes") or "",
        "Captive industry use": plant.get("plant_captive_industry_use_option") or "",
        "Captive industry type": _format_captive_industry_type(
            plant.get("plant_captive_industry_type_jsonb"),
            ctx["captive_industry_type_names"],
        ),
        "Captive non-industry use": plant.get("plant_captive_non_industry_use_option") or "",
        "Captive Data Source": refs(plant.get("plant_captive_ds")),
        "GEM location ID": f"{ID_PREFIX_LOCATION}{plant_id}",
        "GEM unit ID": f"{ID_PREFIX_UNIT}{unit_id}",
        "WEPP location ID": wepp_loc,
        "WEPP unit ID": wepp_unit,
        "Employment Notes": plant.get("employment_notes") or "",
        "Employment Notes Data Source": refs(plant.get("employment_notes_ds")),
        "Linked Projects": linked_projects,
    }
    return row


def export_gogpt_all_fields(engine: Engine, out_path: str, limit: int | None = None) -> int:
    """GOGPT (oil & gas power plants) all-fields CSV. Combustion projectType=1
    filtered to powerplant_unit.trackerSearch='GOGPT'. Mirrors the website's
    `format=gas_all&tracker=GOGPT` export."""
    plants = _fetch_gogpt_plants(engine, limit)
    plant_ids = [p["plant_id"] for p in plants]
    units = _fetch_gogpt_units(engine, plant_ids)
    unit_ids = [u["unit_id"] for u in units]

    # Bulk-fetch every related lookup.
    unit_fuels = _fetch_unit_fuels(engine, unit_ids)
    unit_turbines = _fetch_unit_turbines(engine, unit_ids)
    replacements_by_unit = _fetch_unit_replacements(engine, unit_ids)
    plant_external_ids = _fetch_plant_external_ids(engine, plant_ids)
    unit_external_ids = _fetch_unit_external_ids(engine, unit_ids)
    external_id_systems = _fetch_external_id_systems(engine)
    owners_by_plant, owners_by_unit = _fetch_owners(engine, plant_ids, unit_ids)
    operators_by_plant, operators_by_unit = _fetch_operators(engine, plant_ids, unit_ids)
    unit_updates = _fetch_unit_updates(engine, unit_ids)
    unit_research_status = _fetch_unit_research_status(engine, unit_ids)
    project_links = _fetch_project_links(engine, plant_ids)
    plant_languages = _fetch_languages(engine, plant_ids)
    technology_names = _fetch_technology_names(engine)
    captive_industry_type_names = _fetch_captive_industry_types(engine)

    # For Conversion/replacement we need two back-ref indices:
    #   - replacement_back_refs: units that REPLACED this one (from
    #     unit_replacement rows where unitReplacementId = this id).
    #   - conversion_back_refs: units that CONVERTED FROM this one (from
    #     powerplant_unit.fuelConversionInitialUnit_id pointing at this id).
    # Both feed the "to" side of the Conversion columns.
    replacement_back_refs: dict[int, list[dict]] = defaultdict(list)
    for replacing_unit_id, rows in replacements_by_unit.items():
        for r in rows:
            target = r.get("replacement_target_id")
            if target is not None:
                replacement_back_refs[int(target)].append({
                    "replacing_unit_id": replacing_unit_id,
                })
    conversion_back_refs: dict[int, list[int]] = defaultdict(list)
    for u in units:
        init_id = u.get("fuel_conversion_initial_unit_id")
        if init_id is not None and u.get("fuel_conversion"):
            conversion_back_refs[int(init_id)].append(int(u["unit_id"]))

    # fuel_by_unit_str: for the "Conversion from/to (fuel)" columns we need
    # the fuel string of arbitrary referenced units, not just GOGPT ones.
    # Pull every referenced predecessor/successor unit's fuel in one batch.
    referenced_unit_ids: set[int] = set()
    for rows in replacements_by_unit.values():
        for r in rows:
            t = r.get("replacement_target_id")
            if t is not None:
                referenced_unit_ids.add(int(t))
    for u in units:
        if u.get("fuel_conversion_initial_unit_id"):
            referenced_unit_ids.add(int(u["fuel_conversion_initial_unit_id"]))
    # Plus the units already in our set (so own-fuel lookup works for the
    # "to" side when a GOGPT unit replaces another GOGPT unit).
    referenced_unit_ids.update(int(uid) for uid in unit_ids)
    extra_fuel_lookup = _fetch_unit_fuels(engine, list(referenced_unit_ids))
    fuel_by_unit_str: dict[int, str] = {
        uid: _format_fuel_list(rows) for uid, rows in extra_fuel_lookup.items()
    }

    # Gather every referenced data_source id across all rows, then resolve once.
    ds_ids: set[int] = set()

    def _absorb(maybe_list):
        if not maybe_list:
            return
        for x in maybe_list:
            try:
                ds_ids.add(int(x))
            except (TypeError, ValueError):
                continue

    for p in plants:
        _absorb(p.get("plant_location_ds"))
        _absorb(p.get("employment_notes_ds"))
        _absorb(p.get("plant_captive_ds"))
    for u in units:
        _absorb(u.get("capacity_ds"))
        _absorb(u.get("status_ds"))
        _absorb(u.get("disrupted_ds"))
        _absorb(u.get("latest_activity_ds"))
        _absorb(u.get("cancellation_year_ds"))
        _absorb(u.get("fuel_ds"))
        _absorb(u.get("turbine_ds"))
        _absorb(u.get("technology_ds"))
        _absorb(u.get("hydrogen_ds"))
        _absorb(u.get("h2_criteria_ds"))
        _absorb(u.get("ccs_ds"))
        _absorb(u.get("chp_ds"))
        _absorb(u.get("start_year_ds"))
        _absorb(u.get("end_year_ds"))
        _absorb(u.get("planned_retired_ds"))
        _absorb(u.get("unit_location_ds"))
    for lst in replacements_by_unit.values():
        for r in lst:
            _absorb(r.get("replacement_ds"))
    for lst in list(owners_by_plant.values()) + list(owners_by_unit.values()):
        for o in lst:
            _absorb(o.get("share_ds"))
    for lst in list(operators_by_plant.values()) + list(operators_by_unit.values()):
        for o in lst:
            _absorb(o.get("op_ds"))
    data_sources = _fetch_data_sources(engine, ds_ids)

    ctx = {
        "data_sources": data_sources,
        "unit_fuels": unit_fuels,
        "unit_turbines": unit_turbines,
        "replacements_by_unit": replacements_by_unit,
        "replacement_back_refs": dict(replacement_back_refs),
        "conversion_back_refs": dict(conversion_back_refs),
        "plant_external_ids": plant_external_ids,
        "unit_external_ids": unit_external_ids,
        "external_id_systems": external_id_systems,
        "owners_by_plant": owners_by_plant,
        "owners_by_unit": owners_by_unit,
        "operators_by_plant": operators_by_plant,
        "operators_by_unit": operators_by_unit,
        "unit_updates": unit_updates,
        "unit_research_status": unit_research_status,
        "project_links": project_links,
        "fuel_by_unit_str": fuel_by_unit_str,
        "plant_languages": plant_languages,
        "technology_names": technology_names,
        "captive_industry_type_names": captive_industry_type_names,
    }

    plant_by_id = {p["plant_id"]: p for p in plants}
    rows = []
    for u in units:
        p = plant_by_id.get(u["plant_id"])
        if p is None:
            continue
        rows.append(_gogpt_build_row(p, u, ctx))

    # Match the website sort: by Plant name, then Unit name.
    rows.sort(key=lambda r: (r["Plant name"], r["Unit name"]))

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=GOGPT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def export_all_fields(engine: Engine, out_path: str, limit: int | None = None) -> int:
    """Run the full pipeline and write the all-fields CSV. Returns row count."""
    plants = _fetch_plants(engine, limit)
    plant_ids = [p["plant_id"] for p in plants]

    units = _fetch_units(engine, plant_ids)
    unit_ids = [u["unit_id"] for u in units]

    lng_projects = _fetch_lng_projects(engine, plant_ids)
    timelines = _fetch_status_timelines(engine, unit_ids)
    owners_by_plant, owners_by_unit = _fetch_owners(engine, plant_ids, unit_ids)
    operators_by_plant, operators_by_unit = _fetch_operators(engine, plant_ids, unit_ids)
    languages = _fetch_languages(engine, plant_ids)
    unit_updates = _fetch_unit_updates(engine, unit_ids)

    # Build the parent HQ lookup: collect every entity id mentioned in any
    # owner's gemParentsIds string, then resolve to country in one pass.
    parent_entity_ids: set[int] = set()
    for lst in list(owners_by_plant.values()) + list(owners_by_unit.values()):
        for o in lst:
            parent_entity_ids.update(_extract_entity_ids(o.get("gem_parents_ids")))
    parent_hq_lookup: dict[int, str] = {}
    if parent_entity_ids:
        sql = """
            SELECT c.id, hq."gemName" AS hq_country
            FROM company c
            LEFT JOIN country hq ON hq.id = c."headquarters_country_id"
            WHERE c.id = ANY(:ids)
        """
        with engine.connect() as conn:
            for r in conn.execute(text(sql), {"ids": list(parent_entity_ids)}):
                if r._mapping["hq_country"]:
                    parent_hq_lookup[r._mapping["id"]] = r._mapping["hq_country"]

    # Gather every referenced data_source id across all rows, then resolve once.
    ds_ids: set[int] = set()

    def _absorb(maybe_list):
        if not maybe_list:
            return
        for x in maybe_list:
            try:
                ds_ids.add(int(x))
            except (TypeError, ValueError):
                continue

    for p in plants:
        _absorb(p.get("plant_location_ds"))
    for u in units:
        _absorb(u.get("facility_type_ds"))
        _absorb(u.get("cost_ds"))
        _absorb(u.get("financing_ds"))
        _absorb(u.get("fid_ds"))
        _absorb(u.get("defeated_ds"))
        _absorb(u.get("ccs_ds"))
        _absorb(u.get("unit_capacity_ds"))
        _absorb(u.get("unit_location_ds"))
    for lp in lng_projects.values():
        _absorb(lp.get("lng_source_ds"))
        _absorb(lp.get("pps_ds"))
        _absorb(lp.get("pipelines_ds"))
        _absorb(lp.get("assoc_projects_ds"))
        _absorb(lp.get("captive_gas_power_ds"))
        _absorb(lp.get("vessel_name_ds"))
        _absorb(lp.get("opposition_ds"))
        _absorb(lp.get("ccs_ds"))
    for lst in timelines.values():
        for r in lst:
            _absorb(r.get("ds"))
    for lst in list(owners_by_plant.values()) + list(owners_by_unit.values()):
        for o in lst:
            _absorb(o.get("share_ds"))
    for lst in list(operators_by_plant.values()) + list(operators_by_unit.values()):
        for o in lst:
            _absorb(o.get("op_ds"))

    data_sources = _fetch_data_sources(engine, ds_ids)

    # Plant-level capacity totals.
    totals_by_plant = _compute_plant_totals(units)

    ctx = {
        "owners_by_plant": owners_by_plant,
        "owners_by_unit": owners_by_unit,
        "operators_by_plant": operators_by_plant,
        "operators_by_unit": operators_by_unit,
        "parent_hq_lookup": parent_hq_lookup,
        "languages": languages,
        "unit_updates": unit_updates,
        "timelines": timelines,
        "data_sources": data_sources,
        "totals_by_plant": totals_by_plant,
    }

    # Build one row per unit. Plants with no units would be skipped.
    plant_by_id = {p["plant_id"]: p for p in plants}
    rows = []
    for u in units:
        p = plant_by_id.get(u["plant_id"])
        if p is None:
            continue
        lp = lng_projects.get(u["plant_id"])
        rows.append(_build_row(p, u, lp, ctx))

    # Sort to match the website: by TerminalName then UnitName.
    rows.sort(key=lambda r: (r["TerminalName"], r["UnitName"]))

    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_FIELDS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
