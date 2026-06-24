# Road Network Topology — OSMnx Graph Extraction

**Project:** South Sudan RDBMS vs Graph DB comparison  
**Date:** 2026-06-24  
**Status:** Complete — processed graph ready for Neo4j / PostgreSQL modeling

---

## 1. Purpose

Phase 1 established that the HOT OSM road export contains **line segments only** — no explicit node identifiers or T-junction connectivity (see `docs/phase1_data_understanding.md`, Section 3.5).

For shortest-path and reachability queries in a graph database, the road network must be a **proper graph**: nodes at intersections and dead-ends, edges connecting them, with T-junctions correctly split.

This work produces that graph using **OSMnx**, which:

1. Reads native OpenStreetMap topology (nodes + ways)
2. Splits T-junctions automatically
3. Simplifies away curve/shape-point nodes, keeping only true intersections

---

## 2. Approach

### 2.1 Why OSMnx instead of raw line shapefiles?

Raw HOT OSM exports are line segments without intersection nodes. Snapping consecutive vertices fails at T-junctions where one road meets another mid-segment. OSMnx builds topology from native OSM node–way structure and simplifies to intersection/dead-end nodes only.

### 2.2 Chosen pipeline

| Step | Tool | Description |
|------|------|-------------|
| Download | [Geofabrik](https://download.geofabrik.de/africa/south-sudan.html) | South Sudan `.osm.pbf` extract (~130 MB) |
| Filter | `osmium tags-filter` | Keep `primary`, `secondary`, `tertiary`, `unclassified` (matches Phase 1 HOT OSM filter) |
| Convert | `osmium cat -f osm` | Filtered PBF → OSM XML |
| Graph build | `ox.graph.graph_from_xml(..., simplify=True)` | OSMnx constructs and simplifies the network |
| Export | GeoPandas | Node/edge GeoPackages and CSVs |

**Note:** Live Overpass download via `graph_from_bbox` was attempted but requires ~2,500 sub-queries for the full country and timed out. The Geofabrik extract uses the **same OSMnx topology engine** and is the standard approach for country-scale networks.

### 2.3 Dependencies added

- `osmnx>=2.0` (pip)
- `osmium-tool` (conda-forge)

See `environment.yml` and `requirements.txt`.

---

## 3. Outputs

All files under `data/processed/roads_hotosm/` (excluded from git — regenerate locally):

| File | Description |
|------|-------------|
| `road_nodes.gpkg` / `road_nodes.csv` | 24,779 point nodes (`node_id`, `lon`, `lat`, `degree`) |
| `road_edges.gpkg` / `road_edges.csv` | 62,345 routable edges (`edge_id`, `start_node_id`, `end_node_id`, `highway`, `length_m`, `osm_id`, …) |
| `topology_summary.json` | Machine-readable build statistics |

### 3.1 Graph statistics

| Metric | Value |
|--------|-------|
| Nodes | 24,779 |
| Edges | 62,345 |
| Junction nodes (degree ≥ 3) | 17,795 |
| Endpoint nodes (degree = 1) | 2 |
| Total edge length | 79,442 km |

**Highway class distribution (edges):**

| `highway` | Count |
|-----------|-------|
| unclassified | 51,954 |
| tertiary | 4,048 |
| primary | 3,928 |
| secondary | 2,347 |
| merged types (e.g. `unclassified\|tertiary`) | 68 |

Edge counts exceed the Phase 1 HDX snapshot (20,512 ways) because the Geofabrik extract reflects **current live OSM** with broader coverage.

### 3.2 Interim files (cached, gitignored)

| Path | Description |
|------|-------------|
| `data/raw/roads_hotosm/original/south-sudan-latest.osm.pbf` | Geofabrik country extract |
| `data/interim/osmnx/south_sudan_roads_filtered.osm.pbf` | Highway-filtered PBF |
| `data/interim/osmnx/south_sudan_roads_filtered.osm` | Filtered OSM XML for OSMnx |

---

## 4. Validation map

**Script:** `scripts/visualize_road_topology.py`  
**Output:** `output/south_sudan_road_topology_validation.html`

Interactive Folium map with **toggleable layers** (layer control, top-right):

| Layer | Contents |
|-------|----------|
| Road Network Nodes | 24,779 nodes (toggle off to hide) |
| Edges — Primary / Secondary / Tertiary / Unclassified | Road segments by highway class |
| Displacement Sites | IOM DTM Round 11 (77 sites) |
| Hospitals | SS 2023 master list (68 with valid coordinates) |

The original Phase 1 validation map (`output/south_sudan_data_validation.html`) is unchanged.

---

## 5. Neo4j import shape (Phase 3 preview)

The processed road graph maps to a property graph. Phase 2 will extend it with facility and camp nodes:

- **Node labels:** `RoadNode`, `HealthFacility`, `DisplacementSite`
- **Relationships:** `ROAD_SEGMENT` (road edges), `CONNECTOR` (POI to nearest road node)
- **Road segment properties:** `edge_id`, `osm_id`, `highway`, `length_m`, …

Full augmented model will be defined in Phase 2 schema documents.

---

## 6. Regenerate

```powershell
conda activate dm-south-sudan
python scripts\build_road_network_topology.py
python scripts\visualize_road_topology.py
```

First run downloads ~130 MB from Geofabrik and takes ~1–2 minutes to build the graph. Subsequent runs reuse cached interim files.

**macOS / Linux (conda):**

```bash
conda activate dm-south-sudan
python scripts/build_road_network_topology.py
python scripts/visualize_road_topology.py
```

---

## 7. Design decisions resolved

| Decision | Resolution |
|----------|------------|
| Primary road network for graph DB | **OSMnx processed graph** from live OSM (Geofabrik), not raw HDX line shapefile |
| Highway filter | `primary`, `secondary`, `tertiary`, `unclassified` (consistent with Phase 1) |
| Node definition | Intersections and dead-ends only (OSMnx `simplify_graph`) |
| T-junction handling | OSMnx native topology |

Remaining Phase 2 work:

| Topic | Planned approach |
|-------|------------------|
| Health facilities | Merge WHO 2025 + SS 2023 into canonical dataset |
| Displacement sites | IOM DTM Round 11; snap to road graph |
| POI–road linking | Nearest intersection node + connector edge |
| IDMC national data | National context only; not in spatial graph |

See `docs/phase2_data_modeling.md`.
