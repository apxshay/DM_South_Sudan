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
| `health_facilities_with_capacity.gpkg` / `.csv` | Canonical + synthetic `admission_capacity` for Q5 |
| `health_facilities_merge_log.csv` | Match and merge decisions |
| `health_facilities_state_harmonization_log.csv` | State code corrections (24 rows) |
| `health_facilities_merge_summary.json` | Machine-readable merge statistics |

**Regenerate:** `python scripts/merge_health_facilities.py` then `python scripts/build_reference_data.py`

## Admin dimensions (`admin/`)

| File | Description |
|------|-------------|
| `admin_states.csv` | 11 states (SS00–SS10) |
| `admin_counties.csv` | 79 counties |
| `admin_payams.csv` | 512 payams |

**Regenerate:** `python scripts/build_admin_dimensions.py`

## Displacement sites (`displacement_sites/`)

| File | Description |
|------|-------------|
| `displacement_sites_canonical.csv` / `.gpkg` | 77 IOM DTM Round 11 sites with IDP counts and admin codes |

**Regenerate:** `python scripts/build_displacement_sites.py`

## Reference data (`reference/`)

| File | Description |
|------|-------------|
| `logistical_hubs.csv` | 5 curated referral hospitals for Q3 reachability |

**Regenerate:** `python scripts/build_reference_data.py`

## Augmented network (`network/`) — Phase 2

Output of POI–road integration (health facilities + displacement sites):

| File | Description |
|------|-------------|
| `poi_nodes.gpkg` / `.csv` | 2,094 POI nodes (2,017 health facilities + 77 displacement sites) |
| `connector_edges.gpkg` / `.csv` | Connectors with `capacity` column |
| `road_graph_augmented_edges.gpkg` / `.csv` | Road edges + connector edges (64,439 total) |
| `routing_edges.csv` / `graph_edges_directed.csv` | 66,533 directed edges for DB import |
| `facility_road_access.csv` | Facility → road node lookup (2,017 rows) |
| `network_integration_summary.json` | Snap algorithm, counts, capacity model |
| `poi_snap_review.csv` | POIs with snap distance > 5 km (manual review) |

**Regenerate:**
```bash
python scripts/integrate_network.py
python scripts/visualize_augmented_network.py
python scripts/build_displacement_sites.py
python scripts/build_reference_data.py
python scripts/prepare_db_import_layers.py
```

See `docs/phase2_data_modeling.md` for Phase 2 progress. Schemas: `docs/phase2_relational_schema.md`, `docs/phase2_graph_schema.md`.
