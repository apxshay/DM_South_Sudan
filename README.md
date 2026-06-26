# DM South Sudan — Data Management Project

Master's degree project comparing **PostgreSQL (RDBMS)** and **Neo4j (graph DB)** on humanitarian and infrastructure data from **South Sudan**.

**Repository:** [github.com/apxshay/DM_South_Sudan](https://github.com/apxshay/DM_South_Sudan)

---

## Start here

**This README is the main guide** for setting up the project on your machine (Windows or macOS). Phase-specific analysis and design decisions live under `docs/`; agent coordination lives in `AGENT.md`.

| Document | Purpose |
|----------|---------|
| **README.md** (this file) | End-to-end pipeline: environment → data → databases |
| [`docs/database_usage_guide.md`](docs/database_usage_guide.md) | **Day-to-day use:** open Docker, connect, run SQL/Cypher |
| [`docs/phase1_data_understanding.md`](docs/phase1_data_understanding.md) | Phase 1 dataset analysis report |
| [`docs/road_network_topology.md`](docs/road_network_topology.md) | OSMnx road graph methodology |
| [`docs/phase2_data_modeling.md`](docs/phase2_data_modeling.md) | Phase 2 progress log and decisions |
| [`docs/phase2_relational_schema.md`](docs/phase2_relational_schema.md) | PostgreSQL/PostGIS schema |
| [`docs/phase2_graph_schema.md`](docs/phase2_graph_schema.md) | Neo4j schema |
| [`docs/phase3_database_population.md`](docs/phase3_database_population.md) | Phase 3 validation counts, platform notes, issues log |
| [`docs/phase4_pgrouting_adoption_and_routing_queries.md`](docs/phase4_pgrouting_adoption_and_routing_queries.md) | **Phase 4 report:** pgRouting, dual-track queries, pilot benchmarks |
| [`docs/phase4_query_implementation.md`](docs/phase4_query_implementation.md) | Phase 4 technical progress log (discovery queries) |
| [`docs/phase5_benchmark_queries.md`](docs/phase5_benchmark_queries.md) | Q1–Q5 query spec; dual-track benchmark matrix |
| [`AGENT_PHASE4.md`](AGENT_PHASE4.md) | Phase 4 agent instructions (query implementation) |
| [`AGENT.md`](AGENT.md) | Orchestrator status and project overview |

Raw and processed data are **not in git** (see `.gitignore`). After cloning, follow the pipeline below once per machine.

---

## Platform overview

Both platforms run the **same Python scripts and Docker images**. Differences matter for **setup commands**, **PATH**, **Postgres port**, and **benchmark fairness**.

| Topic | Windows 10/11 (x86-64 / Ryzen) | macOS Apple Silicon (M1/M2/M3) | macOS Intel / Linux amd64 |
|-------|--------------------------------|--------------------------------|---------------------------|
| **Python env** | Miniforge + `.\scripts\setup.ps1` | Miniforge + `./scripts/setup_conda.sh` | Same as Apple Silicon |
| **Data pipeline** | `.\scripts\bootstrap.ps1` | `./scripts/bootstrap.sh` | Same |
| **Docker backend** | Docker Desktop + **WSL 2** | Docker Desktop | Docker Desktop or Engine |
| **PostGIS container** | Native `linux/amd64` | **Emulated** `linux/amd64` | Native `linux/amd64` |
| **Neo4j container** | Native `linux/amd64` | Native `linux/arm64` | Native `linux/amd64` |
| **Default Postgres port** | `5432` (usually free) | Often **`5433`** if local Postgres uses 5432 | `5432` or `5433` |
| **Phase 1–3 development** | ✅ Recommended | ✅ Works | ✅ Works |
| **Phase 5 fair benchmarks** | ✅ **Recommended** | ❌ PostGIS penalized | ✅ OK |

**Decision:** Use **Windows 10 + AMD Ryzen 5** (or any native amd64 host) for Phase 5 timing experiments. Use macOS for development, schema work, and query authoring.

---

## Prerequisites

### All platforms

- [Miniforge](https://github.com/conda-forge/miniforge/releases) with `conda-forge` (GeoPandas/GDAL, osmium-tool)
- ~8 GB RAM (16 GB recommended with Docker); ~2 GB disk for images + ~1 GB for data
- Network for HDX download (~600 MB) and Geofabrik OSM extract (~130 MB, cached by topology script)

### Windows (Phase 3 + benchmarks)

- 64-bit Windows 10/11, virtualization enabled (AMD-V / Intel VT-x)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) with **WSL 2** backend
- Open **Miniforge Prompt**, or add to PATH:
  - `%USERPROFILE%\miniforge3\Scripts`
  - `C:\Program Files\Docker\Docker\resources\bin`

### macOS / Linux (Phase 3)

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (macOS) or Docker Engine (Linux)
- `chmod +x scripts/*.sh` once after clone
- If port **5432** is taken: set `POSTGRES_PORT=5433` in `.env` after copying from `.env.example`

### macOS venv fallback (limited)

`./scripts/setup.sh` uses pip-only GeoPandas and may lack `osmium-tool`. Road topology can fail. Prefer `./scripts/setup_conda.sh`.

---

## Full pipeline (Phase 1 → Phase 4)

**pgRouting note:** The PostGIS Docker image (`pgrouting/pgrouting:16-3.5-4.0`) includes pgRouting. You do **not** install it separately. Step 4 starts the image; Step 5 enables the extension via `schema.sql`. See [`docs/phase4_pgrouting_adoption_and_routing_queries.md`](docs/phase4_pgrouting_adoption_and_routing_queries.md) §3.

### Step 0 — Clone

```powershell
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan
```

```bash
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan
chmod +x scripts/*.sh
```

### Step 1 — Python environment

| Windows | macOS / Linux |
|---------|---------------|
| `.\scripts\setup.ps1` | `./scripts/setup_conda.sh` |
| `conda activate dm-south-sudan` | `conda activate dm-south-sudan` |

Creates/updates conda env `dm-south-sudan` from `environment.yml` and project directories.

### Step 2 — Data pipeline (Phase 1 + Phase 2)

Downloads HDX data, builds the OSMnx road graph, merges health facilities, integrates POI connectors, and writes `data/processed/`.

| Windows | macOS / Linux |
|---------|---------------|
| `.\scripts\bootstrap.ps1` | `./scripts/bootstrap.sh` |

**Verify before Phase 3:**

```powershell
dir data\processed\roads_hotosm\road_nodes.gpkg
dir data\processed\network\routing_edges.csv   # expect 66,533 data rows + header
```

```bash
ls data/processed/roads_hotosm/road_nodes.gpkg
wc -l data/processed/network/routing_edges.csv   # expect 66534 lines
```

**Validation maps** (open in a browser under `output/`):

| Map | Script |
|-----|--------|
| Phase 1 raw layers | `visualize_data_validation.py` |
| Road topology | `visualize_road_topology.py` |
| POIs + connectors | `visualize_augmented_network.py` |

### Step 3 — Database configuration

| Windows | macOS / Linux |
|---------|---------------|
| `copy .env.example .env` | `cp .env.example .env` |

Defaults: PostGIS `127.0.0.1:5432`, Neo4j `bolt://127.0.0.1:7687`, password `dm_ssd_dev`.

**macOS only:** if `5432` is in use, edit `.env` → `POSTGRES_PORT=5433`, then `docker compose up -d` again.

### Step 4 — Start databases

Ensure Docker Desktop is running, then:

```powershell
docker compose pull
docker compose up -d
docker compose ps    # wait until both containers are healthy
```

```bash
docker compose pull
docker compose up -d
docker compose ps
```

Neo4j Browser: http://localhost:7474 (user `neo4j`, password from `.env`).

**Images (pinned in `docker-compose.yml`):**

- **PostgreSQL + PostGIS + pgRouting:** `pgrouting/pgrouting:16-3.5-4.0`
- **Neo4j:** `neo4j:5.26-community` (APOC + GDS)

### Step 5 — Populate databases

```powershell
conda activate dm-south-sudan
python scripts\populate_databases.py --reset
```

```bash
conda activate dm-south-sudan
python scripts/populate_databases.py --reset
```

Expected runtime on native amd64: **~5–15 minutes** (Neo4j MERGE is the slowest step).

Load individually if needed:

| Windows | macOS / Linux |
|---------|---------------|
| `python scripts\load_postgresql.py --reset` | `python scripts/load_postgresql.py --reset` |
| `python scripts\load_neo4j.py --reset` | `python scripts/load_neo4j.py --reset` |

### Step 6 — Validate

Quick count checks (password from `.env`, default `dm_ssd_dev`):

**PostgreSQL**

```powershell
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM health_facilities;"
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM road_edges;"
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT COUNT(*) FROM routing_edges;"
docker exec dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan -c "SELECT extname, extversion FROM pg_extension WHERE extname IN ('postgis', 'pgrouting');"
```

Expect extensions: `postgis` (3.x), `pgrouting` (4.0.1).

**Neo4j**

```powershell
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "MATCH (n:RoadNode) RETURN count(n);"
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "MATCH ()-[r:CONNECTOR_REVERSE]->() RETURN count(r);"
docker exec dm-south-sudan-neo4j cypher-shell -u neo4j -p dm_ssd_dev "RETURN gds.version();"
```

**Benchmark host (amd64):** confirm native architecture inside containers:

```powershell
docker exec dm-south-sudan-neo4j uname -m
docker exec dm-south-sudan-postgis uname -m
```

Both should print `x86_64` on Windows/Ryzen.

Full expected counts and Q1 smoke prerequisites: [`docs/phase3_database_population.md`](docs/phase3_database_population.md).

**Using the databases day-to-day** (connect, run queries, GUI tools): [`docs/database_usage_guide.md`](docs/database_usage_guide.md).

### Step 7 — Phase 4 routing queries (Q1–Q3)

After Steps 1–6, run implemented queries from `src/queries/`. The repo is **not mounted** inside Docker — pipe files via stdin (see [`docs/database_usage_guide.md`](docs/database_usage_guide.md) §11).

**Quick Q1 smoke (pgRouting — primary PostgreSQL track):**

```powershell
Get-Content src/queries/postgresql/q1_nearest_hospital_pgrouting.sql |
  docker exec -i dm-south-sudan-postgis psql -U dm_ssd -d dm_south_sudan `
    -v camp_id=SSD-DS-SS0101_0005
```

Expect **Gumbo PHCC**, **5191.26 m**. Full Phase 4 report: [`docs/phase4_pgrouting_adoption_and_routing_queries.md`](docs/phase4_pgrouting_adoption_and_routing_queries.md).

**Optional pilot benchmark** (Windows amd64 only):

```powershell
python scripts/benchmark_routing_queries.py --runs 5 --warmup 1
```

Output: `output/routing_benchmark_results.json`. Use `--skip-slow-cte` to skip impractically slow Q2/Q3 recursive-CTE baselines.

---

## Resume where you left off

Bootstrap scripts are idempotent. Generated files live under `data/raw/`, `data/processed/`, and `output/` (local only).

| Situation | Windows | macOS / Linux |
|-----------|---------|---------------|
| Fresh clone, full rebuild | `.\scripts\bootstrap.ps1` | `./scripts/bootstrap.sh` |
| Raw data already downloaded | `.\scripts\bootstrap.ps1 -SkipDownload` | `./scripts/bootstrap.sh --skip-download` |
| Re-run Phase 2 merge only | `.\scripts\bootstrap.ps1 -From merge` | `./scripts/bootstrap.sh --from merge` |
| Re-run Phase 2 network + import layers | `.\scripts\bootstrap.ps1 -From network` | `./scripts/bootstrap.sh --from network` |
| Phase 3 only (processed data exists) | `docker compose up -d` then `python scripts\populate_databases.py --reset` | same with forward slashes |
| Phase 4 queries only (DBs populated) | `docker compose up -d` then run queries from `src/queries/` | same |
| Upgrade to pgRouting image (keep data) | `docker compose pull` → `up -d` → `CREATE EXTENSION IF NOT EXISTS pgrouting;` | see Phase 4 doc §3.3 |
| Single script | `python scripts\merge_health_facilities.py` (env active) | `python scripts/merge_health_facilities.py` |

**Data pipeline only (skip Docker):** run Step 1 + Step 2 above; skip Steps 3–5.

---

## Troubleshooting

| Problem | Windows | macOS / Linux |
|---------|---------|---------------|
| `conda not found` | Use Miniforge Prompt or add `miniforge3\Scripts` to PATH | `conda init` in your shell; reopen terminal |
| `docker not found` | Install/start Docker Desktop; add `Docker\resources\bin` to PATH | Start Docker Desktop |
| Docker daemon not running | Launch Docker Desktop; wait for stable tray icon | Same |
| Port already allocated | Change `POSTGRES_PORT` or `NEO4J_BOLT_PORT` in `.env` | Same; macOS often needs `POSTGRES_PORT=5433` |
| `role "dm_ssd" does not exist` | Wrong Postgres instance — check `.env` port vs `docker compose ps` | Same |
| `data/processed/... not found` | Run bootstrap (Step 2) | Same |
| Neo4j reset on first load | Wait for `healthy`; retry after ~2 min | Same |
| `function pgr_dijkstraCost does not exist` | pgRouting extension missing | `CREATE EXTENSION IF NOT EXISTS pgrouting;` or re-run Step 5 populate |
| Q2/Q3 PG-CTE query hangs | Expected — recursive CTE at national scale | Use `*_pgrouting.sql` files instead |
| WSL 2 missing (Windows) | Admin PowerShell: `wsl --install`; reboot | — |

More detail: [`docs/phase3_database_population.md`](docs/phase3_database_population.md) (issues log and validation reference).

---

## Project status

| Phase | Status | Report |
|-------|--------|--------|
| Phase 1 — Data understanding | Complete | [`docs/phase1_data_understanding.md`](docs/phase1_data_understanding.md) |
| Road network topology | Complete (24,779 nodes, 62,345 edges) | [`docs/road_network_topology.md`](docs/road_network_topology.md) |
| Phase 2 — Data modeling | Complete | [`docs/phase2_data_modeling.md`](docs/phase2_data_modeling.md) |
| Phase 3 — Database population | Complete | [`docs/phase3_database_population.md`](docs/phase3_database_population.md) |
| Phase 4 — Query implementation | **In progress** (Q1–Q3 done) | [`docs/phase4_pgrouting_adoption_and_routing_queries.md`](docs/phase4_pgrouting_adoption_and_routing_queries.md), [`docs/phase4_query_implementation.md`](docs/phase4_query_implementation.md) |
| Phase 5 — Benchmarking | After Phase 4 complete | [`docs/phase5_benchmark_queries.md`](docs/phase5_benchmark_queries.md) |

---

## Key design decisions

| Topic | Choice |
|-------|--------|
| Primary road network | OSMnx graph in `data/processed/roads_hotosm/` (not raw HDX line shapefiles) |
| Highway filter | `primary`, `secondary`, `tertiary`, `unclassified` |
| Displacement sites | IOM DTM **Round 11** (77 sites, full GPS) |
| IDMC national IDP CSV | Context only — not in spatial graph |
| POI–road linking | Snap to nearest intersection; directed connector edge |
| Graph direction | Preserve directed arcs and `oneway`; import `CONNECTOR_REVERSE` for Q5 |
| Facilities without coordinates | All 2,251 in PostgreSQL; 2,017 in Neo4j spatial graph |
| Benchmark host | Windows amd64 — both DB containers native `x86_64` |
| PostgreSQL routing (Q1–Q3) | **Dual-track:** PG-pgRouting (primary) + PG-CTE (secondary baseline); Neo4j GDS (primary graph) |
| Docker PostGIS image | `pgrouting/pgrouting:16-3.5-4.0` — PostGIS + pgRouting 4.0 in container |

---

## Datasets

| Domain | Source | Local path |
|--------|--------|------------|
| Roads (humanitarian) | [HDX — Road Network](https://data.humdata.org/dataset/south-sudan-road-network_hdx) | `data/raw/roads/` |
| Roads (HOT OSM) | [HDX — Roads of South Sudan](https://data.humdata.org/dataset/hotosm_ssd_roads) | `data/raw/roads_hotosm/` |
| Roads (Geofabrik OSM) | [Geofabrik — South Sudan](https://download.geofabrik.de/africa/south-sudan.html) | `data/raw/roads_hotosm/original/` |
| Health facilities | [HDX — Health Facilities](https://data.humdata.org/dataset/south-sudan-health-facilities) | `data/raw/health_facilities/` |
| IDP displacements | [HDX — IDMC IDPs](https://data.humdata.org/dataset/idmc-idp-data-ssd) | `data/raw/idp/` |
| Displacement sites | [HDX — IOM DTM](https://data.humdata.org/dataset/south-sudan-displacement-data-site-assessment-iom-dtm) | `data/raw/displacement_sites/` |

See [`data/raw/README.md`](data/raw/README.md) and [`data/processed/README.md`](data/processed/README.md).

---

## Project structure

```
├── README.md                 # Main setup guide (this file)
├── AGENT.md / AGENT_PHASE*.md
├── docker-compose.yml        # pgRouting/PostGIS + Neo4j
├── .env.example              # Copy to .env (gitignored)
├── environment.yml           # Conda environment (all platforms)
├── data/raw/                 # HDX + Geofabrik (not in git)
├── data/processed/           # Graph, facilities, network (not in git)
├── docs/                     # Phase reports, schemas, database usage guide
│   ├── database_usage_guide.md
│   ├── phase3_database_population.md
│   ├── phase4_pgrouting_adoption_and_routing_queries.md
│   ├── phase4_query_implementation.md
│   └── phase5_benchmark_queries.md
├── output/                   # HTML maps, routing_benchmark_results.json
├── scripts/                  # setup, bootstrap, ETL, loaders, benchmark_routing_queries.py
└── src/
    ├── db/                   # schema.sql (incl. pgrouting), constraints.cypher
    └── queries/              # Phase 4 SQL/Cypher (postgresql/, neo4j/)
```

---

## Manual pipeline (optional)

If you prefer not to use bootstrap scripts, with `conda activate dm-south-sudan`:

```bash
python scripts/create_dirs.py
python scripts/download_datasets.py
python scripts/explore_datasets.py
python scripts/visualize_data_validation.py
python scripts/build_road_network_topology.py
python scripts/visualize_road_topology.py
python scripts/merge_health_facilities.py
python scripts/integrate_network.py
python scripts/visualize_augmented_network.py
python scripts/build_admin_dimensions.py
python scripts/build_displacement_sites.py
python scripts/build_reference_data.py
python scripts/prepare_db_import_layers.py
```

Same script names on Windows (`python scripts\...`). GeoPandas/GDAL must come from **conda-forge** (`environment.yml`), not pip alone.
