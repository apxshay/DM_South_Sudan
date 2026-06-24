# Raw Datasets

Source datasets for the South Sudan RDBMS vs Graph DB comparison project.

| Domain | HDX Dataset | Local Path |
|--------|-------------|------------|
| Roads (humanitarian) | [South Sudan: Road Network](https://data.humdata.org/dataset/south-sudan-road-network_hdx) | `roads/` |
| Roads (HOT OSM) | [Roads of South Sudan](https://data.humdata.org/dataset/hotosm_ssd_roads) | `roads_hotosm/` (filtered subset in `filtered/`) |
| Health facilities | [South Sudan - Health Facilities](https://data.humdata.org/dataset/south-sudan-health-facilities) | `health_facilities/` |
| IDP displacements | [South Sudan - Internal Displacements (IDPs)](https://data.humdata.org/dataset/idmc-idp-data-ssd) | `idp/` |
| Displacement sites | [South Sudan Displacement Data - Site Assessment (IOM DTM)](https://data.humdata.org/dataset/south-sudan-displacement-data-site-assessment-iom-dtm) | `displacement_sites/` |

Downloaded files are stored under each folder's `original/` subfolder. Compressed archives are extracted alongside `original/`.

Raw data files are excluded from version control (see `.gitignore`). Re-download using `python scripts/download_datasets.py` (all platforms) or `./scripts/download_datasets.sh` (macOS/Linux).
