# DM South Sudan — Data Management Project

Master's degree project comparing **PostgreSQL (RDBMS)** and **Neo4j (graph DB)** on humanitarian and infrastructure data from **South Sudan**.

**Repository:** [github.com/apxshay/DM_South_Sudan](https://github.com/apxshay/DM_South_Sudan)

## Quick start

Raw datasets and processed outputs are **not in git** (see `.gitignore`). After cloning, run the bootstrap scripts once to download data and generate local artifacts.

### Windows 10 + AMD Ryzen 5 (recommended for benchmarks)

This is the **recommended platform** for Phase 3 database population and Phase 5 benchmarking. Both Docker images (`postgis/postgis`, `neo4j`) run **native `linux/amd64`** on Ryzen — no CPU emulation.

**Prerequisites:** [Miniforge](https://github.com/conda-forge/miniforge/releases) (x86_64), [Docker Desktop](https://www.docker.com/products/docker-desktop/) with WSL 2, virtualization enabled in BIOS.

```powershell
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan

.\scripts\setup.ps1
conda activate dm-south-sudan
.\scripts\bootstrap.ps1

copy .env.example .env
docker compose up -d
python scripts\populate_databases.py --reset
```

Full Phase 3 checklist, validation queries, and troubleshooting: **`docs/phase3_database_population.md`** (Windows section).

### Windows 10 + Miniforge — data pipeline only

```powershell
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan

.\scripts\setup.ps1
conda activate dm-south-sudan
.\scripts\bootstrap.ps1
```

### macOS / Linux + Miniforge (recommended)

```bash
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan

chmod +x scripts/*.sh
./scripts/setup_conda.sh
conda activate dm-south-sudan
./scripts/bootstrap.sh
```

Install Miniforge if needed: [conda-forge/miniforge releases](https://github.com/conda-forge/miniforge/releases) (choose macOS Apple Silicon, Intel, or Linux).

### macOS / Linux (venv fallback)

```bash
./scripts/setup.sh
./scripts/bootstrap.sh
```

The venv path uses pip-only GeoPandas and **may not include `osmium-tool`**, which the road topology script needs. Prefer `./scripts/setup_conda.sh` for the full pipeline.

### Resume where you left off

All bootstrap scripts are safe to re-run. Generated files live under `data/raw/`, `data/processed/`, and `output/` (local only).

| Situation | Command |
|-----------|---------|
| Fresh clone, full rebuild | `./scripts/bootstrap.sh` (macOS/Linux) or `.\scripts\bootstrap.ps1` (Windows) |
| Raw data already downloaded | `./scripts/bootstrap.sh --skip-download` |
| Re-run Phase 2 merge only | `./scripts/bootstrap.sh --from merge` |
| Re-run Phase 2 network integration | `./scripts/bootstrap.sh --from network` or `.\scripts\bootstrap.ps1 -From network` |
| Phase 3 — populate databases | `docker compose up -d` then `python scripts/populate_databases.py --reset` |
| Phase 3 — PostgreSQL only | `python scripts/load_postgresql.py --reset` |
| Phase 3 — Neo4j only | `python scripts/load_neo4j.py --reset` |
| Single script | `python scripts/merge_health_facilities.py` or `python scripts/integrate_network.py` (with conda env active) |

### Conda on any OS (manual steps)

```bash
conda env create -f environment.yml   # or: conda env update -f environment.yml --prune
conda activate dm-south-sudan
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

### Validation maps

| Map | Command | Output |
|-----|---------|--------|
| Phase 1 raw data | `visualize_data_validation.py` | `output/south_sudan_data_validation.html` |
| Road topology graph | `visualize_road_topology.py` | `output/south_sudan_road_topology_validation.html` |
| Augmented network (POIs + connectors) | `visualize_augmented_network.py` | `output/south_sudan_augmented_network_validation.html` |

Open any HTML file in a browser. The augmented network map shows road graph layers plus POI nodes and connector edges (including a review layer for snaps > 5 km).

## Requirements

- **Windows / macOS / Linux:** Miniforge or Conda with `conda-forge` (GeoPandas/GDAL, osmium-tool) — **recommended**
- **Phase 3 / Phase 5:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine (Linux)
- **Benchmarking:** Windows 10 + AMD Ryzen 5 (or any native `amd64` host) so PostgreSQL and Neo4j run without emulation — see `docs/phase3_database_population.md`
- **macOS/Linux alternative:** Python 3.11+ venv (partial support; road topology may fail without osmium)
- Network access for HDX dataset download (~600 MB total; HOT OSM roads ~50 MB compressed)
- Network access for Geofabrik OSM extract (~130 MB; road topology script)
- No `curl` or `unzip` required — downloads use pure Python (`requests` + `zipfile`) or OSMnx/Geofabrik

## Project structure

```
├── AGENT.md / AGENT_PHASE2.md / AGENT_PHASE3.md
├── docker-compose.yml       # PostGIS + Neo4j (Phase 3)
├── .env.example             # DB connection template (copy to .env)
├── environment.yml          # Conda environment (all platforms)
├── requirements.txt         # pip fallback for venv setups
├── data/
│   ├── raw/                 # HDX datasets + Geofabrik OSM extract (not in git)
│   ├── processed/           # Road graph, facilities, network, admin (not in git)
│   └── interim/             # OSMnx build intermediates (not in git)
├── docs/
│   ├── phase1_data_understanding.md
│   ├── phase1_profile.json
│   ├── road_network_topology.md
│   ├── phase2_data_modeling.md
│   ├── phase2_relational_schema.md
│   ├── phase2_graph_schema.md
│   ├── phase3_database_population.md
│   └── phase5_benchmark_queries.md
├── src/db/
│   ├── db_config.py
│   ├── postgresql/schema.sql
│   ├── postgresql/load_data.sql
│   ├── neo4j/constraints.cypher
│   └── neo4j/import.cypher
├── output/                  # Generated HTML maps (not in git)
└── scripts/
    ├── setup.ps1 / setup_conda.sh / setup.sh
    ├── bootstrap.ps1 / bootstrap.sh
    ├── populate_databases.py
    ├── load_postgresql.py
    ├── load_neo4j.py
    ├── resolve_python.sh
    ├── download_datasets.py
    ├── explore_datasets.py
    ├── visualize_data_validation.py
    ├── build_road_network_topology.py
    ├── visualize_road_topology.py
    ├── merge_health_facilities.py
    ├── integrate_network.py
    ├── visualize_augmented_network.py
    ├── build_admin_dimensions.py
    ├── build_displacement_sites.py
    ├── build_reference_data.py
    └── prepare_db_import_layers.py
```

## Datasets

| Domain | Source | Local path |
|--------|-----------|------------|
| Roads (humanitarian) | [South Sudan: Road Network](https://data.humdata.org/dataset/south-sudan-road-network_hdx) | `data/raw/roads/` |
| Roads (HOT OSM) | [Roads of South Sudan](https://data.humdata.org/dataset/hotosm_ssd_roads) | `data/raw/roads_hotosm/` |
| Roads (Geofabrik OSM) | [Geofabrik — South Sudan](https://download.geofabrik.de/africa/south-sudan.html) | `data/raw/roads_hotosm/original/` |
| Health facilities | [South Sudan - Health Facilities](https://data.humdata.org/dataset/south-sudan-health-facilities) | `data/raw/health_facilities/` |
| IDP displacements | [South Sudan - IDPs (IDMC)](https://data.humdata.org/dataset/idmc-idp-data-ssd) | `data/raw/idp/` |
| Displacement sites | [IOM DTM Site Assessment](https://data.humdata.org/dataset/south-sudan-displacement-data-site-assessment-iom-dtm) | `data/raw/displacement_sites/` |

See `data/raw/README.md` for raw data details. Processed outputs: `data/processed/README.md`.

HOT OSM shapefile roads are filtered to `primary`, `secondary`, `tertiary`, and `unclassified` highway types. The OSMnx road graph uses the same highway filter on live Geofabrik OSM data.

## Current phase

**Phase 1 — Data Understanding:** complete. See `docs/phase1_data_understanding.md`.

**Road network topology:** complete (2026-06-24). OSMnx graph with 24,779 nodes and 62,345 edges. See `docs/road_network_topology.md`.

**Phase 2 — Data Modeling:** complete (2026-06-24).

| Step | Status | Script / doc |
|------|--------|----------------|
| Health facility reconciliation | Complete | `merge_health_facilities.py` |
| Network integration (POI → road graph) | Complete | `integrate_network.py` |
| Admin dimensions + reference data | Complete | `build_admin_dimensions.py`, `build_reference_data.py` |
| DB import layers | Complete | `prepare_db_import_layers.py` |
| Relational + graph schemas | Complete | `docs/phase2_relational_schema.md`, `docs/phase2_graph_schema.md` |
| Benchmark queries (Q1–Q5) | Complete | `docs/phase5_benchmark_queries.md` |

Progress log: `docs/phase2_data_modeling.md`. Agent instructions: `AGENT_PHASE2.md` (complete).

**Phase 3 — Database Population:** complete (2026-06-25). Loaders, Docker Compose, and validation documented in `docs/phase3_database_population.md`.

| Step | Status | Script / doc |
|------|--------|----------------|
| Docker Compose (PostGIS + Neo4j + GDS) | Complete | `docker-compose.yml` |
| PostgreSQL loader | Complete | `scripts/load_postgresql.py` |
| Neo4j loader | Complete | `scripts/load_neo4j.py` |
| Orchestrator | Complete | `scripts/populate_databases.py` |
| Population report | Complete | `docs/phase3_database_population.md` |

**Run on Windows 10 + Ryzen 5:** see README quick start and `docs/phase3_database_population.md` (Windows section).

**Phase 5 — Benchmarking:** next. Run Q1–Q5 from `docs/phase5_benchmark_queries.md` on the Ryzen machine for fair `amd64` timings.
