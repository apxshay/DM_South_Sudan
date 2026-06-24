# Processed Data

Generated datasets derived from raw HDX/OSM sources. Not committed to git (see `.gitignore`).

## Road network topology (`roads_hotosm/`)

Built by `scripts/build_road_network_topology.py` using OSMnx.

| File | Description |
|------|-------------|
| `road_nodes.gpkg` / `road_nodes.csv` | Graph nodes (intersections + dead-ends) |
| `road_edges.gpkg` / `road_edges.csv` | Graph edges (routable road segments) |
| `topology_summary.json` | Build statistics |

See `docs/road_network_topology.md` for methodology and graph statistics.

**Regenerate:**

```bash
python scripts/build_road_network_topology.py
```
