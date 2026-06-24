# Raw Datasets

Source datasets for the South Sudan RDBMS vs Graph DB comparison project.

| Domain | HDX Dataset | Local Path |
|--------|-------------|------------|
| Roads (humanitarian) | [South Sudan: Road Network](https://data.humdata.org/dataset/south-sudan-road-network_hdx) | `roads/` |
| Roads (HOT OSM) | [Roads of South Sudan](https://data.humdata.org/dataset/hotosm_ssd_roads) | `roads_hotosm/` (filtered subset in `filtered/`) |
| Roads (Geofabrik OSM) | [Geofabrik — South Sudan](https://download.geofabrik.de/africa/south-sudan.html) | `roads_hotosm/original/south-sudan-latest.osm.pbf` (used by OSMnx topology script) |
| Health facilities | [South Sudan - Health Facilities](https://data.humdata.org/dataset/south-sudan-health-facilities) | `health_facilities/` |
| IDP displacements | [South Sudan - Internal Displacements (IDPs)](https://data.humdata.org/dataset/idmc-idp-data-ssd) | `idp/` |
| Displacement sites | [South Sudan Displacement Data - Site Assessment (IOM DTM)](https://data.humdata.org/dataset/south-sudan-displacement-data-site-assessment-iom-dtm) | `displacement_sites/` |

Downloaded files are stored under each folder's `original/` subfolder. Compressed archives are extracted alongside `original/`.

Raw data files are excluded from version control (see `.gitignore`).

- HDX datasets: `python scripts/download_datasets.py` (all platforms) or `./scripts/download_datasets.sh` (macOS/Linux)
- Geofabrik OSM extract: downloaded automatically by `python scripts/build_road_network_topology.py`
