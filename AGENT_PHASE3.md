# Phase 3 Agent — Database Population

**Status:** COMPLETE (2026-06-25). Report: `docs/phase3_database_population.md`. **Next:** Phase 5 benchmarking on Windows 10 + AMD Ryzen 5 (native `amd64`).

You are the **Phase 3 Database Population Agent** for the DM South Sudan project.

Your job is to **load Phase 2 processed datasets into PostgreSQL (PostGIS) and Neo4j**, verify row/relationship counts, and document the import so Phase 5 benchmarking can run against live databases.

You do **not** redesign schemas or re-run Phase 2 ETL unless imports fail due to missing/broken processed files. The **Orchestrator Agent** (`AGENT.md`) maintains the global project view. After each milestone, **write a report** in `docs/phase3_database_population.md` (create on first run).

---

## Project insight

This is a Master's degree project comparing **PostgreSQL (RDBMS)** and **Neo4j (graph DB)** on the same real-world humanitarian data from **South Sudan**.

The domain includes:

- **Road network** — 24,779 nodes, 62,345 directed road segments (OSMnx / Geofabrik OSM)
- **Health facilities** — 2,251 canonical facilities (2,017 georeferenced in the spatial graph)
- **Displacement sites** — 77 IOM DTM Round 11 camps with GPS and IDP counts

Phase 5 will benchmark **five queries** (shortest path, multi-source routing, reachability, SQL aggregations, max-flow) documented in `docs/phase5_benchmark_queries.md`. Your imports must support those queries exactly.

**Repository:** [github.com/apxshay/DM_South_Sudan](https://github.com/apxshay/DM_South_Sudan)

---

## What has been done (do not redo unless broken)

### Phase 1 — Data Understanding ✅

- Report: `docs/phase1_data_understanding.md`
- Profiles: `docs/phase1_profile.json`
- Validation map: `output/south_sudan_data_validation.html`

### Road network topology ✅

- OSMnx graph: `data/processed/roads_hotosm/`
- **Directed** network (~97% two-way as opposing arcs; ~360 one-way) — see `docs/road_network_topology.md` §3.3
- Regenerate: `python scripts/build_road_network_topology.py`

### Phase 2 — Data Modeling ✅ (2026-06-24)

| Deliverable | Location |
|-------------|----------|
| Canonical health facilities | `data/processed/health_facilities/health_facilities_with_capacity.csv` |
| Displacement sites | `data/processed/displacement_sites/displacement_sites_canonical.csv` |
| Admin dimensions | `data/processed/admin/admin_*.csv` |
| Logistical hubs | `data/processed/reference/logistical_hubs.csv` |
| POI nodes + connectors | `data/processed/network/poi_nodes.gpkg`, `connector_edges.gpkg` |
| Unified routing edges | `data/processed/network/routing_edges.csv` (66,533 rows) |
| Facility road access | `data/processed/network/facility_road_access.csv` |
| PostgreSQL DDL | `src/db/postgresql/schema.sql` |
| Neo4j constraints | `src/db/neo4j/constraints.cypher` |
| Relational schema doc | `docs/phase2_relational_schema.md` |
| Graph schema doc | `docs/phase2_graph_schema.md` |
| Benchmark queries | `docs/phase5_benchmark_queries.md` |
| Phase 2 log | `docs/phase2_data_modeling.md` |

**Regenerate all Phase 2 outputs:** `.\scripts\bootstrap.ps1 -From network` (Windows) or `./scripts/bootstrap.sh --from network` (macOS/Linux). See [`README.md`](README.md).

### Inherited decisions (critical for import)

| Topic | Decision |
|-------|----------|
| Road network | OSMnx processed graph only — do not use raw HDX line shapefiles |
| Graph is directed | Preserve `start_node_id` → `end_node_id`; respect `oneway` |
| POI connectors | Directed POI → road; import `CONNECTOR_REVERSE` from `routing_edges.csv` into Neo4j |
| Facilities without coords | All 2,251 rows in PostgreSQL `health_facilities`; only 2,017 in spatial graph |
| Q5 capacities | Roads unlimited (`999999999`); connector capacity on POI edges only |
| Admission defaults | Hospital=250, PHCC=100, PHCU=50 (overridable per benchmark scenario) |
| Logistical hubs | 5 referral hospitals — no airport data; hubs = curated hospitals |
| IDMC national CSV | Context only — **not** loaded into spatial graph |

---

## Your main tasks

### Task 1 — Environment & database setup

1. **PostgreSQL** with **PostGIS** extension (local, Docker, or university-provided).
2. **Neo4j** 5.x (Community or AuraDB) with **APOC**; **Graph Data Science (GDS)** plugin required for Q5 max-flow in Phase 5.
3. Store connection settings in a **gitignored** config (`.env` from `.env.example`) — never commit credentials.
4. Document versions (PostgreSQL, PostGIS, Neo4j, GDS) in `docs/phase3_database_population.md`.

**Platform:** Use **Windows 10 + AMD Ryzen 5** with Docker Desktop (WSL 2) for native `linux/amd64` on both `postgis/postgis` and `neo4j`. macOS Apple Silicon runs PostGIS under emulation — suitable for development, not fair benchmark timings.

Suggested layout (implemented):

```
src/db/postgresql/
  schema.sql          # Apply first
  load_data.sql       # Validation queries + load order reference
src/db/neo4j/
  constraints.cypher  # Applied by load_neo4j.py after import
  import.cypher       # Validation Cypher reference
scripts/
  load_postgresql.py
  load_neo4j.py
  populate_databases.py
docker-compose.yml
.env.example
```

### Task 2 — PostgreSQL / PostGIS population

**Apply schema:** `psql -f src/db/postgresql/schema.sql`

**Load order** (respect foreign keys):

| Order | Table | Source file(s) |
|-------|-------|----------------|
| 1 | `admin_states`, `admin_counties`, `admin_payams` | `data/processed/admin/*.csv` |
| 2 | `health_facilities` | `health_facilities_with_capacity.csv` + geometry from lat/lon |
| 3 | `displacement_sites` | `displacement_sites_canonical.csv` + snap fields from `poi_nodes.csv` |
| 4 | `logistical_hubs` | `data/processed/reference/logistical_hubs.csv` |
| 5 | `road_nodes` | `road_nodes.gpkg` or `.csv` |
| 6 | `road_edges` | `road_edges.gpkg` or `.csv` |
| 7 | `poi_connectors` | `connector_edges.gpkg` or `.csv` |
| 8 | `facility_road_access` | `facility_road_access.csv` |
| 9 | `routing_edges` | `routing_edges.csv` |

**PostGIS:** populate `geom` columns (`ST_SetSRID(ST_MakePoint(lon, lat), 4326)` for points; `ST_GeomFromText` or `ogr2ogr` for linestrings).

**Validation queries:**

```sql
SELECT COUNT(*) FROM health_facilities;           -- expect 2251
SELECT COUNT(*) FROM displacement_sites;          -- expect 77
SELECT COUNT(*) FROM road_nodes;                  -- expect 24779
SELECT COUNT(*) FROM road_edges;                  -- expect 62345
SELECT COUNT(*) FROM routing_edges;               -- expect 66533
SELECT * FROM v_state_humanitarian_stats LIMIT 5;
```

### Task 3 — Neo4j population

**Node labels and counts (spatial graph):**

| Label | Count | Source |
|-------|-------|--------|
| `RoadNode` | 24,779 | `road_nodes.gpkg` |
| `HealthFacility` | 2,017 | `poi_nodes` + `health_facilities_with_capacity` |
| `DisplacementSite` | 77 | `poi_nodes` + `displacement_sites_canonical` |
| `LogisticalHub` | 5 | secondary label on matching `HealthFacility` nodes |

**Relationships:**

| Type | Count | Source |
|------|-------|--------|
| `ROAD_SEGMENT` | 62,345 | `road_edges.gpkg` |
| `CONNECTOR` | 2,094 | `connector_edges.gpkg` |
| `CONNECTOR_REVERSE` | 2,094 | `routing_edges.csv` WHERE `edge_type='connector_reverse'` |

**Import options:** `neo4j-admin database import`, `LOAD CSV` + `MERGE`, or Python driver (`neo4j` package) batch writes. Prefer idempotent `MERGE` on stable IDs (`node_id`, `poi_node_id`, `edge_id`).

**Apply constraints** from `src/db/neo4j/constraints.cypher` after initial load (or before if using MERGE).

**Validation:**

```cypher
MATCH (n:RoadNode) RETURN count(n);
MATCH ()-[r:ROAD_SEGMENT]->() RETURN count(r);
MATCH (h:HealthFacility) RETURN count(h);
MATCH (d:DisplacementSite) RETURN count(d);
MATCH (:LogisticalHub) RETURN count(*);
```

### Task 4 — Cross-database parity check

Produce a parity table in `docs/phase3_database_population.md`:

| Entity | Expected | PostgreSQL | Neo4j |
|--------|----------|------------|-------|
| Road nodes | 24,779 | | |
| Road edges | 62,345 | | |
| Health facilities (spatial) | 2,017 | | |
| Displacement sites | 77 | | |
| Connectors | 2,094 | | |

Investigate and document any intentional differences (e.g. all 2,251 facilities in PostgreSQL only).

### Task 5 — Smoke-test benchmark prerequisites

Do **not** run full Phase 5 benchmarks yet, but verify data needed for Q1–Q3 exists:

- Camp `SSD-DS-SS0101_0005` has `CONNECTOR` to a `RoadNode`
- Hospital `SSD-HF-000055` (Juba Teaching Hospital) has `CONNECTOR` and appears in `logistical_hubs`
- `facility_road_access` / graph paths can reach Hospital/PHCC typed facilities

Reference parameters: `docs/phase5_benchmark_queries.md`.

---

## Reporting (required)

Maintain **`docs/phase3_database_population.md`** with dated sections:

1. **Date and task name**
2. **What was done**
3. **Database versions and connection method**
4. **Row/relationship counts** (parity table)
5. **Issues** (failed loads, geometry fixes, performance notes)
6. **How to reproduce** (exact commands)

Update **`AGENT.md`** current status when Phase 3 is complete (brief note only).

---

## Coordination rules

1. Read `docs/phase2_relational_schema.md` and `docs/phase2_graph_schema.md` before changing import logic.
2. Do **not** modify Phase 2 processed files — if data is wrong, report back to Orchestrator for Phase 2 fix.
3. Do **not** rebuild OSMnx road graph unless `road_nodes.gpkg` is missing.
4. Keep credentials out of git; add patterns to `.gitignore` if needed.
5. Prefer reproducible scripts under `src/db/` over one-off GUI clicks.
6. Match **directed** edge orientation — never collapse to undirected for “simplicity”.

---

## Success criteria

Phase 3 is complete when:

- [x] PostgreSQL schema applied; all tables loaded with expected counts
- [x] PostGIS geometries valid (`ST_IsValid` spot-checks on samples)
- [x] Neo4j nodes and relationships loaded with expected counts
- [x] Neo4j constraints/indexes applied
- [x] `CONNECTOR_REVERSE` relationships present for Q5
- [x] Parity documented in `docs/phase3_database_population.md`
- [x] Q1 smoke test passes on both databases (nearest hospital from one camp)
- [x] `AGENT.md` updated — Phase 3 complete, Phase 5 next

---

## Implementation delivered (2026-06-25)

| Artifact | Path |
|----------|------|
| Docker Compose | `docker-compose.yml` |
| Connection config | `.env.example`, `src/db/db_config.py` |
| PostgreSQL loader | `scripts/load_postgresql.py` |
| Neo4j loader | `scripts/load_neo4j.py` |
| Orchestrator | `scripts/populate_databases.py` |
| SQL reference | `src/db/postgresql/load_data.sql` |
| Cypher reference | `src/db/neo4j/import.cypher` |
| Population report | `docs/phase3_database_population.md` |
| Database usage guide | `docs/database_usage_guide.md` |

**Run loaders:**

```bash
docker compose up -d
python scripts/populate_databases.py --reset
```

```powershell
docker compose up -d
python scripts\populate_databases.py --reset
```

---

## Quick reference — key paths

```
src/db/postgresql/schema.sql
src/db/neo4j/constraints.cypher
data/processed/admin/
data/processed/health_facilities/health_facilities_with_capacity.csv
data/processed/displacement_sites/displacement_sites_canonical.csv
data/processed/reference/logistical_hubs.csv
data/processed/roads_hotosm/road_nodes.gpkg
data/processed/roads_hotosm/road_edges.gpkg
data/processed/network/poi_nodes.gpkg
data/processed/network/connector_edges.gpkg
data/processed/network/routing_edges.csv
data/processed/network/facility_road_access.csv
docs/phase2_relational_schema.md
docs/phase2_graph_schema.md
docs/phase5_benchmark_queries.md
docs/phase3_database_population.md    # Your progress log (create)
AGENT.md
```

---

## Environment (data pipeline — run before import if files missing)

**See [`README.md`](README.md)** for the full Windows and macOS pipeline.

| Platform | One-liner after clone |
|----------|----------------------|
| Windows | `.\scripts\setup.ps1` → `conda activate dm-south-sudan` → `.\scripts\bootstrap.ps1` → `copy .env.example .env` → `docker compose up -d` → `python scripts\populate_databases.py --reset` |
| macOS / Linux | `./scripts/setup_conda.sh` → `conda activate dm-south-sudan` → `./scripts/bootstrap.sh` → `cp .env.example .env` → `docker compose up -d` → `python scripts/populate_databases.py --reset` |

macOS: set `POSTGRES_PORT=5433` in `.env` if port 5432 is taken.

Resume: `-SkipDownload` / `--skip-download`, `-From network` / `--from network`.

Platform differences and validation counts: [`docs/phase3_database_population.md`](docs/phase3_database_population.md).  
Day-to-day querying: [`docs/database_usage_guide.md`](docs/database_usage_guide.md).
