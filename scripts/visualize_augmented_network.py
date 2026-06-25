#!/usr/bin/env python3
"""Interactive validation map for the augmented road network (POIs + connectors)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
from folium import FeatureGroup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import PROCESSED_NETWORK, PROCESSED_ROADS_HOTOSM  # noqa: E402
from visualize_data_validation import MAP_CENTER, MAP_ZOOM  # noqa: E402
from visualize_road_topology import add_edge_layers, add_node_layer  # noqa: E402

OUTPUT_DIR = ROOT / "output"
OUTPUT_HTML = OUTPUT_DIR / "south_sudan_augmented_network_validation.html"

POI_NODES = PROCESSED_NETWORK / "poi_nodes.gpkg"
CONNECTORS = PROCESSED_NETWORK / "connector_edges.gpkg"
ROAD_NODES = PROCESSED_ROADS_HOTOSM / "road_nodes.gpkg"
ROAD_EDGES = PROCESSED_ROADS_HOTOSM / "road_edges.gpkg"
SUMMARY = PROCESSED_NETWORK / "network_integration_summary.json"


def load_layers() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame]:
    missing = [p for p in (POI_NODES, CONNECTORS, ROAD_NODES, ROAD_EDGES) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Augmented network outputs not found. Run scripts/integrate_network.py first.\n"
            + "\n".join(f"  Missing: {p}" for p in missing)
        )

    poi_nodes = gpd.read_file(POI_NODES)
    connectors = gpd.read_file(CONNECTORS)
    road_nodes = gpd.read_file(ROAD_NODES)
    road_edges = gpd.read_file(ROAD_EDGES)

    for gdf in (poi_nodes, connectors, road_nodes, road_edges):
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs.to_epsg() != 4326:
            gdf.to_crs("EPSG:4326", inplace=True)

    return poi_nodes, connectors, road_nodes, road_edges


def add_connector_layer(m: folium.Map, connectors: gpd.GeoDataFrame) -> dict[str, int]:
    review_layer = FeatureGroup(name="Connectors — review (> 5 km)", show=False)
    normal_layer = FeatureGroup(name="Connectors — within threshold", show=True)

    counts = {"normal": 0, "review": 0}
    for _, row in connectors.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        coords = [(lat, lon) for lon, lat in geom.coords]
        review = bool(row.get("snap_review_flag")) if "snap_review_flag" in row else False
        if not review and "length_m" in row.index:
            review = float(row["length_m"]) > 5000
        layer = review_layer if review else normal_layer
        key = "review" if review else "normal"
        counts[key] += 1
        folium.PolyLine(
            locations=coords,
            color="#d62728" if review else "#ff7f0e",
            weight=1.5 if review else 1,
            opacity=0.85 if review else 0.55,
            dash_array="6,4",
            tooltip=(
                f"{row.get('poi_node_id', '')} → road node {row.get('end_node_id', '')}"
                f" ({row.get('length_m', '')} m)"
            ),
        ).add_to(layer)

    normal_layer.add_to(m)
    review_layer.add_to(m)
    return counts


def add_poi_layers(m: folium.Map, poi_nodes: gpd.GeoDataFrame) -> dict[str, int]:
    layers = {
        "health_facility": FeatureGroup(name="POIs — Health facilities", show=True),
        "displacement_site": FeatureGroup(name="POIs — Displacement sites", show=True),
    }
    styles = {
        "health_facility": {"color": "#1b7837", "fill_color": "#5aae61"},
        "displacement_site": {"color": "#762a83", "fill_color": "#9970ab"},
    }
    counts = {k: 0 for k in layers}

    for _, row in poi_nodes.iterrows():
        poi_type = row.get("poi_type", "health_facility")
        layer = layers.get(poi_type, layers["health_facility"])
        style = styles.get(poi_type, styles["health_facility"])
        counts[poi_type] = counts.get(poi_type, 0) + 1
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=4,
            color=style["color"],
            weight=1,
            fill=True,
            fill_color=style["fill_color"],
            fill_opacity=0.85,
            tooltip=(
                f"{row.get('display_name', row.get('poi_node_id', ''))}"
                f" | snap {row.get('snap_distance_m', '')} m"
            ),
        ).add_to(layer)

    for layer in layers.values():
        layer.add_to(m)
    return counts


def build_map() -> folium.Map:
    poi_nodes, connectors, road_nodes, road_edges = load_layers()

    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles="CartoDB positron",
        control_scale=True,
    )

    edge_counts = add_edge_layers(m, road_edges)
    node_counts = add_node_layer(m, road_nodes)
    connector_counts = add_connector_layer(m, connectors)
    poi_counts = add_poi_layers(m, poi_nodes)

    folium.LayerControl(collapsed=False).add_to(m)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    m.save(str(OUTPUT_HTML))

    summary_note = ""
    if SUMMARY.exists():
        summary = json.loads(SUMMARY.read_text())
        stats = summary.get("snap_distance_stats", {}).get("all_pois", {})
        summary_note = (
            f"  Mean snap distance:      {stats.get('mean_m')} m\n"
            f"  Max snap distance:       {stats.get('max_m')} m\n"
            f"  POIs flagged for review: {summary.get('counts', {}).get('pois_needing_review', 0)}"
        )

    print("Augmented network validation map summary:")
    print(f"  Road edges (total):        {sum(edge_counts.values()):,}")
    print(f"  Road nodes (total):        {node_counts['total']:,}")
    print(f"  POI nodes:                 {len(poi_nodes):,}")
    print(f"    health facilities         {poi_counts.get('health_facility', 0):,}")
    print(f"    displacement sites        {poi_counts.get('displacement_site', 0):,}")
    print(f"  Connector edges:           {sum(connector_counts.values()):,}")
    print(f"    within threshold          {connector_counts.get('normal', 0):,}")
    print(f"    review (> 5 km)           {connector_counts.get('review', 0):,}")
    if summary_note:
        print(summary_note)
    print(f"  Output saved to:           {OUTPUT_HTML}")
    return m


def main() -> int:
    try:
        build_map()
    except Exception as exc:
        print(f"Failed to build augmented network validation map: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
