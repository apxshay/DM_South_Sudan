# DM South Sudan — Data Management Project

Master's degree project comparing **PostgreSQL (RDBMS)** and **Neo4j (graph DB)** on humanitarian and infrastructure data from **South Sudan**.

**Repository:** [github.com/apxshay/DM_South_Sudan](https://github.com/apxshay/DM_South_Sudan)

## Quick start

### Windows 10 + Miniforge (recommended)

```powershell
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan

# In PowerShell (or "Miniforge Prompt"):
.\scripts\setup.ps1
conda activate dm-south-sudan

python scripts\download_datasets.py
python scripts\explore_datasets.py
python scripts\visualize_data_validation.py

# Road network graph (OSMnx) + topology validation map:
python scripts\build_road_network_topology.py
python scripts\visualize_road_topology.py
```

### macOS / Linux (venv)

```bash
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan

./scripts/setup.sh
./scripts/download_datasets.sh
data_env/bin/python scripts/explore_datasets.py
data_env/bin/python scripts/visualize_data_validation.py
data_env/bin/python scripts/build_road_network_topology.py
data_env/bin/python scripts/visualize_road_topology.py
```

### Conda on any OS (manual)

```bash
conda env create -f environment.yml
conda activate dm-south-sudan
python scripts/create_dirs.py
python scripts/download_datasets.py
python scripts/explore_datasets.py
python scripts/visualize_data_validation.py
python scripts/build_road_network_topology.py
python scripts/visualize_road_topology.py
```

### Validation maps

| Map | Command | Output |
|-----|---------|--------|
| Phase 1 raw data | `visualize_data_validation.py` | `output/south_sudan_data_validation.html` |
| Road topology graph | `visualize_road_topology.py` | `output/south_sudan_road_topology_validation.html` |

Open either HTML file in a browser. The topology map includes **toggleable layers** for road nodes, edges (by highway class), displacement sites, and hospitals.

## Requirements

- **Windows:** Miniforge or Conda with `conda-forge` channel (GeoPandas/GDAL, osmium-tool)
- **macOS/Linux:** Python 3.11+ venv, or Conda as above
- Network access for HDX dataset download (~600 MB total; HOT OSM roads ~50 MB compressed)
- Network access for Geofabrik OSM extract (~130 MB; road topology script)
- No `curl` or `unzip` required — downloads use pure Python (`requests` + `zipfile`) or OSMnx/Geofabrik

## Project structure

```
├── AGENT.md
├── environment.yml          # Conda environment (Windows / cross-platform)
├── requirements.txt         # pip fallback for venv setups
├── data/
│   ├── raw/                 # HDX datasets + Geofabrik OSM extract (not in git)
│   ├── processed/           # OSMnx road graph nodes/edges (not in git)
│   └── interim/             # OSMnx build intermediates (not in git)
├── docs/
│   ├── phase1_data_understanding.md
│   ├── phase1_profile.json
│   └── road_network_topology.md   # Road graph extraction report
├── output/                  # Generated HTML maps (not in git)
└── scripts/
    ├── setup.ps1 / setup.sh
    ├── download_datasets.py
    ├── explore_datasets.py
    ├── visualize_data_validation.py
    ├── build_road_network_topology.py   # OSMnx graph extraction
    └── visualize_road_topology.py       # Topology validation map
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

See `data/raw/README.md` for raw data details. Processed road graph: `data/processed/README.md`.

HOT OSM shapefile roads are filtered to `primary`, `secondary`, `tertiary`, and `unclassified` highway types. The OSMnx road graph uses the same highway filter on live Geofabrik OSM data.

## Current phase

**Phase 1 — Data Understanding:** complete. See `docs/phase1_data_understanding.md`.

**Road network topology (2026-06-24):** complete. OSMnx graph with 24,779 nodes and 62,345 edges. See `docs/road_network_topology.md`.

**Next milestone:** Phase 2 — Data Modeling (relational + graph schemas for PostgreSQL and Neo4j).
