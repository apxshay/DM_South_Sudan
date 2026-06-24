# Phase 2 — Data Modeling

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Status:** In progress (Task 2 complete)  
**Last updated:** 2026-06-24

---

## Overview

Phase 2 prepares import-ready datasets and schemas for PostgreSQL and Neo4j. Phase 3 will load these into the databases.

---

## Planned work

| Step | Description | Status |
|------|-------------|--------|
| Health facility reconciliation | Merge WHO 2025 and SS 2023 into one canonical table | Complete |
| Network integration | Connect facilities (~1,900) and displacement sites (77) to road graph via connector edges | Pending |
| Relational schema | PostgreSQL/PostGIS tables, keys, geometry columns | Pending |
| Graph schema | Neo4j node labels, relationship types, properties | Pending |

---

## Progress log

### 2026-06-24 — Task 2: Health facility reconciliation

**Summary:** Merged WHO 2025 (1,988 rows) and SS 2023 (1,513 rows) into a canonical table of 2,250 facilities using sequential 1:1 matching on normalized name + admin codes. 1,251 pairs were matched; 737 WHO-only and 262 SS-only rows were retained. 2,016 facilities have valid coordinates for spatial graph integration.

**Outputs:**
- `data/processed/health_facilities/health_facilities_canonical.gpkg` (2,250 rows)
- `data/processed/health_facilities/health_facilities_canonical.csv`
- `data/processed/health_facilities/health_facilities_merge_log.csv`
- `data/processed/health_facilities/health_facilities_merge_summary.json`
- `data/processed/health_facilities/health_facilities_data_quality.md`

**Decisions:**
- Match key priority: (1) normalized name + payam_code, (2) normalized name + county_code, (3) unique normalized name with county agreement or coordinates within 1 km.
- Prefer WHO coordinates when both sources have valid coords; prefer SS for facility type and display name.
- Facilities without valid coordinates are kept in the canonical table but flagged `has_coordinates = false` (234 rows).
- Duplicate SS `Facilities_Code` values (`75020101`, `92040402`) kept with `ss_code_duplicate = true`; unique `facility_id` assigned to each row.

**Issues:** 737 WHO-only facilities lack facility type; 123 SS-only facilities lack coordinates; no admin code crosswalk between WHO (11 state codes) and SS (19 state codes). See `health_facilities_data_quality.md` for full detail.

**Reproduce:** `python scripts/merge_health_facilities.py`

---

### 2026-06-24 — Task 2 remediation: limitations & real-system parity

**Summary:** Addressed Task 2 limitations before network integration. Disabled tertiary name-only matching (production MDM safety). Added state-code harmonization against SS 2023 `Admin_data` with payam → county → coordinate fallback. Documented policy to retain all 2,251 facilities in both PostgreSQL and Neo4j; only 2,017 with coordinates receive graph connector edges.

**Changes:**
- New module `scripts/health_facility_admin.py` — admin reference loading, payam centroids, state harmonization
- Canonical columns added: `state_name`, `state_code_original`, `state_code_method`
- New output: `health_facilities_state_harmonization_log.csv` (24 corrections)
- Tertiary `unique_name` matching removed (+1 canonical row: steward-review pair kept separate)

**Decisions:**
- **Unknown type:** kept (`unknown` is valid in real MDM)
- **No coordinates:** kept in both paradigms; graph connector edges only when `has_coordinates=true`
- **Name-only matching:** disabled — precision over recall; ambiguous pairs stay separate for steward review
- **State codes:** payam lookup authoritative; 18 Abyei fixes (SS11–SS18 and mis-coded WHO rows → SS00); 6 payam/county conflict fixes

**Reproduce:** `python scripts/merge_health_facilities.py`

---

## References

- `docs/phase1_data_understanding.md` — Section 4 (health facilities)
- `docs/road_network_topology.md` — processed road graph (24,779 nodes, 62,345 edges)
- `data/processed/roads_hotosm/` — road nodes and edges inputs
