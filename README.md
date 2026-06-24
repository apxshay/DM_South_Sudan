# DM South Sudan — Data Management Project

Master's degree project comparing **PostgreSQL (RDBMS)** and **Neo4j (graph DB)** on humanitarian and infrastructure data from **South Sudan**.

**Repository:** [github.com/apxshay/DM_South_Sudan](https://github.com/apxshay/DM_South_Sudan)

## Quick start

```bash
# 1. Clone and enter the repo
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan

# 2. Create virtual environment and install dependencies
./scripts/setup.sh

# 3. Download raw datasets from HDX (requires curl, unzip, network)
./scripts/download_datasets.sh

# 4. Regenerate data profiles and validation map
data_env/bin/python scripts/explore_datasets.py
data_env/bin/python scripts/visualize_data_validation.py
```

Open `output/south_sudan_data_validation.html` in a browser for the interactive validation map.

## Requirements

- Python 3.11+
- `curl` and `unzip` (for dataset download)
- ~600 MB disk space for raw datasets (HOT OSM roads is ~50 MB compressed)

## Project structure

```
├── AGENT.md                 # Orchestrator agent instructions and project status
├── data/
│   ├── raw/                 # Downloaded HDX datasets (not in git — see data/raw/README.md)
│   ├── processed/           # Future ETL outputs
│   └── interim/             # Future intermediate artifacts
├── docs/
│   ├── phase1_data_understanding.md
│   └── phase1_profile.json
├── output/                  # Generated HTML maps (not in git)
├── scripts/
│   ├── setup.sh             # Environment bootstrap
│   ├── download_datasets.sh # HDX data download
│   ├── explore_datasets.py  # Dataset profiling
│   └── visualize_data_validation.py
└── src/                     # Future ETL, DB, queries, benchmarks
```

## Datasets

| Domain | HDX source | Local path |
|--------|-----------|------------|
| Roads (humanitarian) | [South Sudan: Road Network](https://data.humdata.org/dataset/south-sudan-road-network_hdx) | `data/raw/roads/` |
| Roads (HOT OSM) | [Roads of South Sudan](https://data.humdata.org/dataset/hotosm_ssd_roads) | `data/raw/roads_hotosm/` |
| Health facilities | [South Sudan - Health Facilities](https://data.humdata.org/dataset/south-sudan-health-facilities) | `data/raw/health_facilities/` |
| IDP displacements | [South Sudan - IDPs (IDMC)](https://data.humdata.org/dataset/idmc-idp-data-ssd) | `data/raw/idp/` |
| Displacement sites | [IOM DTM Site Assessment](https://data.humdata.org/dataset/south-sudan-displacement-data-site-assessment-iom-dtm) | `data/raw/displacement_sites/` |

See `data/raw/README.md` for details. HOT OSM roads are filtered to `primary`, `secondary`, `tertiary`, and `unclassified` highway types.

## Current phase

**Phase 1 — Data Understanding** is complete. See `docs/phase1_data_understanding.md`.

**Next milestone:** Phase 2 — Data Modeling.
