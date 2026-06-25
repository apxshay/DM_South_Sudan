# Phase 2 — Data Modeling

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Status:** Complete  
**Last updated:** 2026-06-24

---

## Overview

Phase 2 prepares import-ready datasets and schemas for PostgreSQL and Neo4j. Phase 3 will load these into the databases.

---

## Planned work

| Step | Description | Status |
|------|-------------|--------|
| Health facility reconciliation | Merge WHO 2025 and SS 2023 into one canonical table | Complete |
| Network integration | Connect facilities (~1,900) and displacement sites (77) to road graph via connector edges | Complete |
| Relational schema | PostgreSQL/PostGIS tables, keys, geometry columns | Complete |
| Graph schema | Neo4j node labels, relationship types, properties | Complete |
| Benchmark query spec | Canonical Q1–Q5 templates for Phase 5 | Complete |

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

### 2026-06-24 — Task 1: Network integration

**Summary:** Connected 2,017 health facilities and 77 IOM DTM Round 11 displacement sites to the OSMnx road graph via straight-line connector edges. Each POI is a first-class node snapped to the nearest road intersection node, with junction preference when distance is comparable. All 2,094 georeferenced POIs received a connector; none were left disconnected.

**Outputs:**
- `data/processed/network/poi_nodes.gpkg` / `.csv` (2,094 POI nodes)
- `data/processed/network/connector_edges.gpkg` / `.csv` (2,094 connectors)
- `data/processed/network/road_graph_augmented_edges.gpkg` / `.csv` (64,439 edges = 62,345 road + 2,094 connectors)
- `data/processed/network/network_integration_summary.json`
- `data/processed/network/poi_snap_review.csv` (666 POIs with snap distance > 5 km)
- `output/south_sudan_augmented_network_validation.html`

**Decisions:**
- **Connector semantics:** straight-line geodesic snap (not a surveyed walking path); suitable for routing access links in Phase 3.
- **Distance metric:** haversine geodesic (WGS84) for both nearest-node search and `snap_distance_m`.
- **Nearest-node search:** scikit-learn `BallTree` with haversine metric, *k*=25 candidates per POI.
- **Junction preference:** among nodes within `nearest_dist × 1.10 + 250 m`, prefer the closest node with `degree ≥ 3` (434 POIs used a junction over the absolute nearest node).
- **POI node IDs:** reuse canonical `SSD-HF-*` facility IDs; displacement sites use `SSD-DS-{ssid}` (stable, distinct from OSM `node_id`).
- **Review threshold:** flag POIs with `snap_distance_m > 5,000` for manual review.

**Issues:** 666 POIs (31.8%) snap farther than 5 km from the nearest road node — median snap is 1.5 km but the mean is 10.5 km due to sparse OSM road coverage in remote areas. Worst case: ~183 km (health facility). These remain connected for graph completeness but should be treated cautiously in reachability analysis. 234 health facilities without coordinates are excluded from the spatial graph (retained in canonical table for PostgreSQL).

**Reproduce:**
```bash
python scripts/integrate_network.py
python scripts/visualize_augmented_network.py
```

---

### 2026-06-24 — Task 3: Schema design, data enrichments, benchmark queries

**Summary:** Validated five benchmark queries (Q1–Q5) against processed datasets; enriched admin dimensions, displacement sites, logistical hubs, and connector capacities; produced aligned PostgreSQL/PostGIS and Neo4j schemas plus canonical query templates for Phase 5.

**Outputs:**
- `data/processed/admin/admin_states.csv` (11), `admin_counties.csv` (79), `admin_payams.csv` (512)
- `data/processed/displacement_sites/displacement_sites_canonical.csv` / `.gpkg` (77)
- `data/processed/reference/logistical_hubs.csv` (5 referral hospitals)
- `data/processed/health_facilities/health_facilities_with_capacity.csv` / `.gpkg` (2,251 + `admission_capacity`)
- `data/processed/network/routing_edges.csv` / `graph_edges_directed.csv` (66,533 directed edges)
- `data/processed/network/facility_road_access.csv` (2,017)
- `docs/phase2_relational_schema.md`, `src/db/postgresql/schema.sql`
- `docs/phase2_graph_schema.md`, `src/db/neo4j/constraints.cypher`
- `docs/phase5_benchmark_queries.md`

**Decisions:**
- **Query suite:** keep all five user queries with revisions (directed edges, correct labels, hub = referral hospital).
- **Q4:** per-state POI/IDP stats; national primary+secondary road km only (no state polygons on roads).
- **Q5 capacity:** unlimited `ROAD_SEGMENT`; synthetic capacity on `CONNECTOR` only (camp=`idp_individuals`, hospital=`admission_capacity`); added `connector_reverse` edges for max-flow into hospitals.
- **Admission defaults:** Hospital=250, PHCC=100, PHCU=50.
- **Routing layer:** unified `routing_edges` with `start_node_kind` / `end_node_kind` (`road`|`poi`).

**Issues:** Q5 max-flow not native SQL (application-layer NetworkX on PostgreSQL); Neo4j requires GDS plugin. 651 `unknown` facility types excluded from Q1/Q2 routing.

**Reproduce:**
```bash
python scripts/build_admin_dimensions.py
python scripts/build_displacement_sites.py
python scripts/build_reference_data.py
python scripts/prepare_db_import_layers.py
```

---

## Phase 3 — Database population (2026-06-25)

**Summary:** Docker Compose stack, PostgreSQL/Neo4j loaders, and population report added. Databases populated from `data/processed/` with expected counts; Q1 smoke prerequisites verified.

**Deliverables:**
- `docker-compose.yml`, `.env.example`, `src/db/db_config.py`
- `scripts/load_postgresql.py`, `scripts/load_neo4j.py`, `scripts/populate_databases.py`
- `docs/phase3_database_population.md`

**Recommended host for benchmarks:** Windows 10 + AMD Ryzen 5 (native `linux/amd64` for both PostGIS and Neo4j).

**Reproduce (Windows):**
```powershell
copy .env.example .env
docker compose up -d
python scripts\populate_databases.py --reset
```

See `docs/phase3_database_population.md` for full setup, validation, and troubleshooting.

---

## References

- `docs/phase1_data_understanding.md` — Section 4 (health facilities)
- `docs/road_network_topology.md` — processed road graph (24,779 nodes, 62,345 edges)
- `docs/phase2_relational_schema.md` — PostgreSQL/PostGIS DDL
- `docs/phase2_graph_schema.md` — Neo4j model
- `docs/phase5_benchmark_queries.md` — Q1–Q5 templates
- `docs/phase3_database_population.md` — Phase 3 loaders + Windows setup
- `AGENT_PHASE3.md` — Phase 3 agent instructions (complete)
- `data/processed/roads_hotosm/` — road nodes and edges inputs
