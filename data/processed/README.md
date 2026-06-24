# Processed Data

Generated datasets derived from raw HDX/OSM sources. Not committed to git (see `.gitignore`).

## Road network topology (`roads_hotosm/`)

Built by `scripts/build_road_network_topology.py` using OSMnx.

| File | Description |
|------|-------------|
| `road_nodes.gpkg` / `road_nodes.csv` | 24,779 graph nodes (intersections + dead-ends) |
| `road_edges.gpkg` / `road_edges.csv` | 62,345 graph edges (routable road segments) |
| `topology_summary.json` | Build statistics |

See `docs/road_network_topology.md` for methodology.

**Regenerate:**

```bash
python scripts/build_road_network_topology.py
python scripts/visualize_road_topology.py
```

## Health facilities (`health_facilities/`) — Phase 2

Output of health facility reconciliation (WHO 2025 + SS 2023):

| File | Description |
|------|-------------|
| `health_facilities_canonical.gpkg` / `.csv` | Unified facility table (2,251 rows; 2,017 with coordinates) |
| `health_facilities_merge_log.csv` | Match and merge decisions |
| `health_facilities_state_harmonization_log.csv` | State code corrections (24 rows) |
| `health_facilities_merge_summary.json` | Machine-readable merge statistics |
| `health_facilities_data_quality.md` | Merge rules, parity policy, and open items |

**Regenerate:** `python scripts/merge_health_facilities.py`

## Augmented network (`network/`) — Phase 2

Planned output of POI–road integration:

| File | Description |
|------|-------------|
| `poi_nodes.gpkg` / `.csv` | Health facilities + displacement sites as graph nodes |
| `connector_edges.gpkg` / `.csv` | Segments linking each POI to nearest road node |
| `road_graph_augmented_edges.gpkg` | Road edges + connector edges combined |
| `network_integration_summary.json` | Snap distances, counts, validation flags |

See `docs/phase2_data_modeling.md` for Phase 2 progress.
