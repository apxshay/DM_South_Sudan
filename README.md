# DM South Sudan — Data Management Project

Master's degree project comparing **PostgreSQL (RDBMS)** and **Neo4j (graph DB)** on humanitarian and infrastructure data from **South Sudan**.

**Repository:** [github.com/apxshay/DM_South_Sudan](https://github.com/apxshay/DM_South_Sudan)

## Quick start

Raw datasets and processed outputs are **not in git** (see `.gitignore`). After cloning, run the bootstrap scripts once to download data and generate local artifacts.

### Windows 10 + Miniforge (recommended)

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
| Single script | `python scripts/merge_health_facilities.py` (with conda env active) |

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
```

### Validation maps

| Map | Command | Output |
|-----|---------|--------|
| Phase 1 raw data | `visualize_data_validation.py` | `output/south_sudan_data_validation.html` |
| Road topology graph | `visualize_road_topology.py` | `output/south_sudan_road_topology_validation.html` |

Open either HTML file in a browser. The topology map includes **toggleable layers** for road nodes, edges (by highway class), displacement sites, and hospitals.

## Requirements

- **Windows / macOS / Linux:** Miniforge or Conda with `conda-forge` (GeoPandas/GDAL, osmium-tool) — **recommended**
- **macOS/Linux alternative:** Python 3.11+ venv (partial support; road topology may fail without osmium)
- Network access for HDX dataset download (~600 MB total; HOT OSM roads ~50 MB compressed)
- Network access for Geofabrik OSM extract (~130 MB; road topology script)
- No `curl` or `unzip` required — downloads use pure Python (`requests` + `zipfile`) or OSMnx/Geofabrik

## Project structure

```
├── AGENT.md / AGENT_PHASE2.md
├── environment.yml          # Conda environment (all platforms)
├── requirements.txt         # pip fallback for venv setups
├── data/
│   ├── raw/                 # HDX datasets + Geofabrik OSM extract (not in git)
│   ├── processed/           # Road graph, canonical health facilities (not in git)
│   └── interim/             # OSMnx build intermediates (not in git)
├── docs/
│   ├── phase1_data_understanding.md
│   ├── phase1_profile.json
│   ├── road_network_topology.md
│   └── phase2_data_modeling.md
├── output/                  # Generated HTML maps (not in git)
└── scripts/
    ├── setup.ps1 / setup_conda.sh / setup.sh
    ├── bootstrap.ps1 / bootstrap.sh
    ├── resolve_python.sh
    ├── download_datasets.py / download_datasets.sh
    ├── explore_datasets.py
    ├── visualize_data_validation.py
    ├── build_road_network_topology.py
    ├── visualize_road_topology.py
    └── merge_health_facilities.py
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

**Phase 2 — Data Modeling:** in progress.

| Step | Status | Script |
|------|--------|--------|
| Health facility reconciliation | Complete | `merge_health_facilities.py` |
| Network integration (POI → road graph) | Pending | — |
| Relational + graph schema design | Pending | — |

Progress log: `docs/phase2_data_modeling.md`. Phase 2 agent instructions: `AGENT_PHASE2.md`.
