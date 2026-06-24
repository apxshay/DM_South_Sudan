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
```

### macOS / Linux (venv)

```bash
git clone https://github.com/apxshay/DM_South_Sudan.git
cd DM_South_Sudan

./scripts/setup.sh
./scripts/download_datasets.sh
data_env/bin/python scripts/explore_datasets.py
data_env/bin/python scripts/visualize_data_validation.py
```

### Conda on any OS (manual)

```bash
conda env create -f environment.yml
conda activate dm-south-sudan
python scripts/create_dirs.py
python scripts/download_datasets.py
python scripts/explore_datasets.py
python scripts/visualize_data_validation.py
```

Open `output/south_sudan_data_validation.html` in a browser for the interactive validation map.

## Requirements

- **Windows:** Miniforge or Conda with `conda-forge` channel (GeoPandas/GDAL)
- **macOS/Linux:** Python 3.11+ venv, or Conda as above
- Network access for HDX dataset download (~600 MB total; HOT OSM roads ~50 MB compressed)
- No `curl` or `unzip` required — downloads use pure Python (`requests` + `zipfile`)

## Project structure

```
├── AGENT.md
├── environment.yml          # Conda environment (Windows / cross-platform)
├── requirements.txt         # pip fallback for venv setups
├── data/raw/                # HDX datasets (not in git)
├── docs/                    # Phase 1 reports and profiles
├── output/                  # Generated HTML maps (not in git)
└── scripts/
    ├── setup.ps1            # Windows + Miniforge bootstrap
    ├── setup.sh             # macOS/Linux venv bootstrap
    ├── download_datasets.py # Cross-platform HDX downloader
    ├── explore_datasets.py
    └── visualize_data_validation.py
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
