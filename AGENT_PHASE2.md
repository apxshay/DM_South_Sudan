# Phase 2 Agent — Data Modeling & Network Integration

You are the **Phase 2 Data Modeling Agent** for the DM South Sudan project.

Your job is to prepare clean, import-ready data models and an **augmented road network graph** that connects humanitarian points of interest to the driveable road network. Phase 3 will load your outputs into PostgreSQL and Neo4j — you do not build databases yet, but everything you produce must be ready for that step.

**Current focus:** Phase 2 is **complete** (2026-06-24). Phase 3 is **complete** (2026-06-25). **Setup on any machine:** [`README.md`](README.md). Phase 3 validation: [`docs/phase3_database_population.md`](../docs/phase3_database_population.md). Do not redo Phase 2 unless outputs are missing or broken.

The **Orchestrator Agent** (`AGENT.md`) maintains the global project view. After each important task, **write a report** in `docs/phase2_data_modeling.md` (see [Reporting & documentation](#reporting--documentation-required)). Keep outputs reproducible under `data/processed/`.

---

## Project insight

This is a Master's degree project comparing **PostgreSQL (RDBMS)** and **Neo4j (graph DB)** on the same real-world humanitarian data from **South Sudan**.

The domain includes:

- **Road network** — driveable OSM roads (primary / secondary / tertiary / unclassified)
- **Health facilities** — ~1,900–2,000 clinics, health centres, and hospitals with coordinates
- **Displacement sites** — ~77 georeferenced refugee/IDP camps (IOM DTM Round 11)

The scientific goal is not only to populate two databases, but to compare how each paradigm handles **interconnected spatial data**: shortest paths, reachability (e.g. nearest hospital from a camp), and infrastructure queries.

For the **graph database**, facilities and camps must be **first-class nodes** in the network, not isolated points. That means each facility/camp connects to the road graph via a **connector edge** to the nearest road intersection node, so pathfinding algorithms can route through them.

**Repository:** [github.com/apxshay/DM_South_Sudan](https://github.com/apxshay/DM_South_Sudan)

---

## What has been done (do not redo unless broken)

### Phase 1 — Data Understanding ✅

- All HDX datasets downloaded, profiled, and documented
- Report: `docs/phase1_data_understanding.md`
- Machine-readable profiles: `docs/phase1_profile.json`
- Validation map (raw layers): `output/south_sudan_data_validation.html`  
  Regenerate: `python scripts/visualize_data_validation.py`

### Road network topology ✅ (2026-06-24)

- A **proper routable road graph** was built with **OSMnx** (Geofabrik South Sudan extract)
- T-junctions are handled correctly; curve shape-point nodes were removed
- Report: `docs/road_network_topology.md`
- Regenerate: `python scripts/build_road_network_topology.py`

| Artifact | Path | Scale |
|----------|------|-------|
| Road nodes | `data/processed/roads_hotosm/road_nodes.gpkg` | 24,779 intersection/dead-end nodes |
| Road edges | `data/processed/roads_hotosm/road_edges.gpkg` | 62,345 segments with `length_m`, `highway`, … |
| Summary | `data/processed/roads_hotosm/topology_summary.json` | Build stats |
| Topology map | `output/south_sudan_road_topology_validation.html` | Toggleable nodes/edges layers |

**Use this graph as the road network.** Do not rebuild from raw HDX line shapefiles — an earlier vertex-snapping approach failed T-junction connectivity.

### Task 2 — Health facility reconciliation ✅ (2026-06-24)

- WHO 2025 and SS 2023 merged into one canonical dataset
- Script: `scripts/merge_health_facilities.py` (helpers: `scripts/health_facility_admin.py`)
- Progress log: `docs/phase2_data_modeling.md` (Task 2 sections)
- Regenerate: `python scripts/merge_health_facilities.py` or `./scripts/bootstrap.sh --from merge`

| Artifact | Path | Scale |
|----------|------|-------|
| Canonical facilities | `data/processed/health_facilities/health_facilities_canonical.gpkg` | 2,251 rows (2,017 with coordinates) |
| Merge log | `data/processed/health_facilities/health_facilities_merge_log.csv` | Match decisions per row |
| Summary | `data/processed/health_facilities/health_facilities_merge_summary.json` | Counts and merge rules applied |
| State harmonization | `data/processed/health_facilities/health_facilities_state_harmonization_log.csv` | 24 corrections |

**Use this file as the health facility source for Task 1.** Do not re-merge unless the canonical outputs are missing or you are explicitly fixing merge logic.

### Resolved decisions (inherit these)

| Topic | Decision |
|-------|----------|
| Primary road network | OSMnx processed graph in `data/processed/roads_hotosm/` |
| Highway filter | `primary`, `secondary`, `tertiary`, `unclassified` |
| Displacement sites source | IOM DTM **Round 11** (77 sites, full GPS) |
| IDMC national IDP data | Context only — no coordinates; not part of the spatial graph |

### Still open (resolved in Phase 2 ✅)

| Topic | Resolution |
|-------|------------|
| Connector edge semantics | Straight-line geodesic snap — see `docs/phase2_data_modeling.md` Task 1 |
| Relational vs. graph schema details | `docs/phase2_relational_schema.md`, `docs/phase2_graph_schema.md` |
| Benchmark queries | `docs/phase5_benchmark_queries.md` (Q1–Q5) |

### Task 3 — Schema design & data enrichments ✅ (2026-06-24)

- Admin dimensions, displacement sites canonical, logistical hubs, admission capacity
- `routing_edges.csv` (66,533 directed edges), `facility_road_access.csv`
- PostgreSQL DDL: `src/db/postgresql/schema.sql`
- Neo4j constraints: `src/db/neo4j/constraints.cypher`
- Scripts: `build_admin_dimensions.py`, `build_displacement_sites.py`, `build_reference_data.py`, `prepare_db_import_layers.py`

See `docs/phase2_data_modeling.md` Task 3 section.

---

## Your two main tasks

> **Start here:** Task 2 is done — proceed with **Task 1** below, then schema design deliverables.

### Task 1 — Connect facilities and camps to the road network *(your primary task)*

**Goal:** Every health facility and displacement site that participates in the graph must be a **node**, linked to the road network by a **connector segment** (edge) to the **nearest road intersection node**.

#### Inputs

| Entity | Source | Approx. count | Key columns |
|--------|--------|---------------|-------------|
| Health facilities | `data/processed/health_facilities/health_facilities_canonical.gpkg` (Task 2 ✅) | 2,017 nodes with valid coordinates (2,251 total; 234 without coords excluded from graph) | `facility_id`, `facility_name`, `facility_type`, `latitude`, `longitude`, admin codes |
| Displacement sites | `data/raw/displacement_sites/original/hdx_ssd-dtm-mobility-tracking-r11-site-assessment-dataset.xlsx` (sheet `MT11 SA`, skip metadata row) | 77 sites | `b01.location.ssid`, `b02.location.name`, `b10.gps.lon`, `b11.gps.lat`, `c02.idp.ind` |
| Road nodes | `data/processed/roads_hotosm/road_nodes.gpkg` | 24,779 | `node_id`, `lon`, `lat`, `degree` |

Prefer **junction nodes** (degree ≥ 3) when snapping if distance is comparable; document if you use nearest node regardless of degree.

#### Algorithm (minimum)

1. Load road nodes into a spatial index (e.g. `scipy.spatial.cKDTree`, GeoPandas `sjoin_nearest`, or BallTree on projected coordinates).
2. For each facility/camp with valid WGS84 coordinates:
   - Find the **nearest road node** (geodesic or projected distance — document which).
   - Record `nearest_road_node_id` and `snap_distance_m`.
3. Create a **connector edge** per POI:
   - `start_node_id` = POI node id (new)
   - `end_node_id` = nearest road `node_id`
   - `edge_type` = `connector` (or `access_path`) — distinguish from road edges
   - `length_m` = geodesic distance POI ↔ road node
   - `geometry` = LineString between POI and road node
4. Assign stable **POI node ids** (do not reuse OSM road `node_id` values).

#### Expected outputs (suggest under `data/processed/network/`)

| File | Contents |
|------|----------|
| `poi_nodes.gpkg` / `.csv` | All facility + camp nodes with type, attributes, `nearest_road_node_id`, `snap_distance_m` |
| `connector_edges.gpkg` / `.csv` | Connector segments linking each POI to its road node |
| `road_graph_augmented_edges.gpkg` | Road edges + connector edges (single edge layer for import) |
| `network_integration_summary.json` | Counts, max/mean snap distance, POIs excluded (missing coords), validation flags |

#### Validation

- Regenerate or extend the validation map to show connectors (optional script: extend `scripts/visualize_road_topology.py` or add `scripts/visualize_augmented_network.py`).
- Flag POIs with snap distance above a threshold (e.g. > 5 km) for manual review.
- No facility/camp with valid coordinates should be left disconnected.

#### Graph DB mental model (for Phase 3)

```
(:HealthFacility {id, name, type, lat, lon, …})
(:DisplacementSite {id, name, idp_count, lat, lon, …})
(:RoadNode {node_id, lat, lon, …})
(:HealthFacility)-[:CONNECTOR {length_m}]->(:RoadNode)
(:DisplacementSite)-[:CONNECTOR {length_m}]->(:RoadNode)
(:RoadNode)-[:ROAD_SEGMENT {highway, length_m, …}]->(:RoadNode)
```

Design relational equivalents in parallel (see Task 3 below).

---

### Task 2 — Reconcile health facility discrepancies (2023 vs 2025) ✅ COMPLETE

> **Status:** Completed 2026-06-24. Outputs exist under `data/processed/health_facilities/`. **Do not redo** unless files are missing or merge logic must be fixed. Use the canonical file as input to Task 1.

**Goal:** Produce **one canonical health-facility dataset** suitable for both PostgreSQL and Neo4j import.

Read **`docs/phase1_data_understanding.md` Section 4** before writing any merge logic.

#### Source files

| File | Path | Rows | Strengths | Weaknesses |
|------|------|------|-----------|------------|
| WHO 2025 | `data/raw/health_facilities/original/who-master-facility-list_april2025.xlsx` | 1,988 | More rows; 94.3% coordinate coverage | No `Type`; no dedicated facility code |
| SS 2023 | `data/raw/health_facilities/original/ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx` | 1,513 | `Type` (PHCU/PHCC/Hospital); `Facilities_Code` | 85.1% coordinate coverage; 2 duplicate codes |

**Cross-file overlap:** ~1,235 normalized facility names appear in both files.

#### Known issues to resolve

| Issue | Severity | Action |
|-------|----------|--------|
| Different schemas and row counts | High | Define unified schema; merge or survivorship rules |
| Duplicate `Facilities_Code` (SS 2023) | High | 2 codes assigned to 2 facilities each — assign unique ids |
| Duplicate names within each file | Medium | 41 (WHO), 33 (SS 2023) — use admin codes + coords to disambiguate |
| Missing coordinates | Medium | 5.7% (WHO), 14.9% (SS 2023) — exclude from spatial graph or impute with justification |
| Column naming (`Payam_Code ` trailing space) | Low | Normalize in ETL |
| `State_Code` cardinality mismatch (SS 2023) | Medium | Document mapping |

#### Expected outputs (suggest under `data/processed/health_facilities/`)

| File | Contents |
|------|----------|
| `health_facilities_canonical.csv` / `.gpkg` | One row per facility with unified columns |
| `health_facilities_merge_log.csv` | Match decisions: merged pairs, SS-only, WHO-only, conflicts |
| `health_facilities_data_quality.md` | Short report: rules applied, exclusions, unresolved conflicts |

#### Suggested unified columns (minimum)

```
facility_id          # stable primary key (your assignment)
source               # who_2025 | ss_2023 | merged
facility_name
facility_type        # PHCU | PHCC | Hospital | unknown
state_code
county_code
payam_code
latitude
longitude
who_site_name        # optional traceability
ss_facilities_code   # optional traceability
merge_status         # matched | ss_only | who_only | conflict
```

Document every merge rule (e.g. match on normalized name + admin codes, prefer WHO coords when both present, prefer SS `Type`).

#### Completed outputs (reference — already on disk)

| File | Status |
|------|--------|
| `health_facilities_canonical.csv` / `.gpkg` | ✅ 2,251 rows |
| `health_facilities_merge_log.csv` | ✅ |
| `health_facilities_merge_summary.json` | ✅ |
| `health_facilities_state_harmonization_log.csv` | ✅ |
| `health_facilities_data_quality.md` | ⚠️ Referenced in docs but not generated — optional to add |

**Reproduce (only if needed):** `python scripts/merge_health_facilities.py`

---

## Additional Phase 2 deliverables (schema design)

After Task 1, produce **data models** for Phase 3:

1. **Relational schema** — tables, PKs/FKs, geometry columns (PostGIS), ER diagram or DDL draft  
   Suggested path: `docs/phase2_relational_schema.md` + optional `src/db/postgresql/schema.sql`

2. **Graph schema** — node labels, relationship types, properties, constraints/indexes  
   Suggested path: `docs/phase2_graph_schema.md` + optional `src/db/neo4j/constraints.cypher`

Both models must represent the **same domain**:

- Road nodes and road segments (from processed topology)
- POI nodes (facilities, displacement sites)
- Connector edges
- Admin hierarchy where useful (state / county / payam)

Reference: `docs/phase1_data_understanding.md`, `docs/road_network_topology.md`.

---

## Environment & scripts

```powershell
conda activate dm-south-sudan
cd DM_South_Sudan

# Ensure road graph exists locally
python scripts\build_road_network_topology.py

# Raw data (if missing)
python scripts\download_datasets.py
```

Place new Phase 2 scripts under `scripts/` or `src/etl/`. Follow patterns in `scripts/project_paths.py` for paths.

**Dependencies already available:** geopandas, shapely, pyproj, pandas, osmnx, folium.

---

## Reporting & documentation (required)

After **each important task or milestone**, write a short report so the Orchestrator and future agents know what was done without reading code. Do not skip this — Phase 3 depends on your documented decisions.

### When to report

| Trigger | Action |
|---------|--------|
| Task 2 complete (health facility merge) | ✅ Done — see `docs/phase2_data_modeling.md`; only report if you change merge logic |
| Task 1 complete (network integration) | Add or update report section + `network_integration_summary.json` |
| Schema design complete | Publish `phase2_relational_schema.md` and `phase2_graph_schema.md` |
| Any non-obvious decision | Log it immediately in the running Phase 2 report |
| Phase 2 fully complete | Finalize master report and update `AGENT.md` current status (brief note only) |

### Master report

Maintain **`docs/phase2_data_modeling.md`** as the single Phase 2 log. Append dated sections as work progresses — do not replace earlier entries.

Each task report section should include:

1. **Date and task name**
2. **What was done** — 2–5 sentences in plain language
3. **Outputs produced** — file paths and row/feature counts
4. **Key decisions** — merge rules, snap algorithm, thresholds, exclusions
5. **Issues & open items** — conflicts unresolved, POIs with large snap distance, data quality flags
6. **How to reproduce** — script names and commands

### Example section format

```markdown
## 2026-06-24 — Task 2: Health facility reconciliation

**Summary:** Merged WHO 2025 and SS 2023 into a canonical table of 1,942 facilities …

**Outputs:**
- `data/processed/health_facilities/health_facilities_canonical.gpkg` (1,942 rows)
- `data/processed/health_facilities/health_facilities_merge_log.csv`

**Decisions:**
- Match key: normalized name + payam_code; prefer WHO coordinates when both present …

**Issues:** 47 facilities excluded (missing coordinates); 3 unresolved name conflicts …

**Reproduce:** `python scripts/merge_health_facilities.py`
```

### Task-specific mini-reports

In addition to sections in `docs/phase2_data_modeling.md`, create focused reports where listed in task outputs:

| Task | Dedicated report file |
|------|------------------------|
| Task 2 | `data/processed/health_facilities/health_facilities_data_quality.md` |
| Task 1 | Summarized in `data/processed/network/network_integration_summary.json`; narrative in master report |
| Schemas | `docs/phase2_relational_schema.md`, `docs/phase2_graph_schema.md` |

### Keep docs in sync

When you finish a task, check whether **`README.md`**, **`AGENT.md`**, or **`data/processed/README.md`** need a one-line status update (e.g. new processed folder). Only update what changed — do not rewrite unrelated sections.

---

## Coordination rules

1. Read Phase 1 and road topology docs before changing assumptions.
2. Do **not** modify `output/south_sudan_data_validation.html` — create new artifacts if needed.
3. Do **not** rebuild the OSMnx road graph unless `road_nodes.gpkg` / `road_edges.gpkg` are missing.
4. Do **not** re-run health facility merge (Task 2) unless `health_facilities_canonical.gpkg` is missing or merge logic is being fixed.
5. Document decisions; flag uncertainties explicitly.
6. Keep raw data read-only — write outputs to `data/processed/`.
7. Prefer incremental, reproducible scripts over one-off notebook steps.
8. **Write a report after each important task** — see [Reporting & documentation](#reporting--documentation-required) above.

---

## Success criteria

Phase 2 is complete when:

- [x] One canonical health facility table exists with documented merge rules (Task 2 ✅)
- [x] ~2,017 facilities (with valid coordinates) each have a nearest road node and connector edge
- [x] ~77 displacement sites each have a nearest road node and connector edge
- [x] Augmented edge/node layers are saved and summarized (`network_integration_summary.json`)
- [x] Relational and graph schemas are documented and aligned with the augmented network
- [x] **`docs/phase2_data_modeling.md`** exists with dated sections for every major task
- [x] Benchmark query spec published (`docs/phase5_benchmark_queries.md`)

Phase 3 agents will use your processed files and schemas to populate PostgreSQL and Neo4j. See **`AGENT_PHASE3.md`**.

---

## Quick reference — key paths

```
data/raw/health_facilities/original/          # Source Excel files
data/raw/displacement_sites/original/         # IOM DTM Round 11
data/processed/roads_hotosm/                  # Road nodes & edges (OSMnx)
data/processed/health_facilities/             # Canonical merge + capacity
data/processed/admin/                         # Admin dimension tables
data/processed/displacement_sites/            # Canonical DTM R11 sites
data/processed/reference/                     # Logistical hubs
data/processed/network/                       # POI nodes, connectors, routing_edges
src/db/postgresql/schema.sql                  # PostgreSQL DDL
src/db/neo4j/constraints.cypher               # Neo4j constraints
docs/phase1_data_understanding.md
docs/road_network_topology.md
docs/phase2_data_modeling.md
docs/phase2_relational_schema.md
docs/phase2_graph_schema.md
docs/phase5_benchmark_queries.md
AGENT_PHASE3.md                               # Next phase instructions
AGENT.md
```
