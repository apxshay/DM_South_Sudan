#!/usr/bin/env python3
"""Interactive validation map for the OSMnx road network topology."""

from __future__ import annotations

import sys
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
from folium import FeatureGroup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from visualize_data_validation import (  # noqa: E402
    DISPLACEMENT_XLSX,
    HEALTH_XLSX,
    MAP_CENTER,
    MAP_ZOOM,
    add_displacement_sites,
    add_hospitals,
    load_displacement_sites,
    load_hospitals,
)

OUTPUT_DIR = ROOT / "output"
OUTPUT_HTML = OUTPUT_DIR / "south_sudan_road_topology_validation.html"
PROCESSED = ROOT / "data" / "processed" / "roads_hotosm"
NODES_GPKG = PROCESSED / "road_nodes.gpkg"
EDGES_GPKG = PROCESSED / "road_edges.gpkg"

HIGHWAY_ORDER = ("primary", "secondary", "tertiary", "unclassified", "other")
HIGHWAY_STYLES = {
    "primary": {"color": "#1a1a1a", "weight": 3, "opacity": 0.9},
    "secondary": {"color": "#4d4d4d", "weight": 2.5, "opacity": 0.85},
    "tertiary": {"color": "#737373", "weight": 2, "opacity": 0.8},
    "unclassified": {"color": "#a6a6a6", "weight": 1.5, "opacity": 0.75},
    "other": {"color": "#d62728", "weight": 1.5, "opacity": 0.7},
}
HIGHWAY_LAYER_NAMES = {
    "primary": "Edges — Primary",
    "secondary": "Edges — Secondary",
    "tertiary": "Edges — Tertiary",
    "unclassified": "Edges — Unclassified",
    "other": "Edges — Other / Merged",
}

JUNCTION_MIN_DEGREE = 3


def _base_highway(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "other"
    primary = str(value).split("|")[0].strip().lower()
    return primary if primary in HIGHWAY_STYLES else "other"


def load_topology() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    if not NODES_GPKG.exists() or not EDGES_GPKG.exists():
        raise FileNotFoundError(
            "Processed road topology not found. Run scripts/build_road_network_topology.py first."
        )

    nodes = gpd.read_file(NODES_GPKG)
    edges = gpd.read_file(EDGES_GPKG)

    for gdf in (nodes, edges):
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs.to_epsg() != 4326:
            gdf.to_crs("EPSG:4326", inplace=True)

    return nodes, edges


def add_edge_layers(m: folium.Map, edges_gdf: gpd.GeoDataFrame) -> dict[str, int]:
    edges = edges_gdf.copy()
    edges["highway_class"] = edges["highway"].map(_base_highway)
    counts: dict[str, int] = {}

    tooltip_fields = [c for c in ("highway", "length_m", "osm_id", "name") if c in edges.columns]
    tooltip_aliases = {
        "highway": "Highway",
        "length_m": "Length (m)",
        "osm_id": "OSM ID",
        "name": "Name",
    }

    for highway in HIGHWAY_ORDER:
        subset = edges[edges["highway_class"] == highway]
        counts[highway] = len(subset)
        if subset.empty:
            continue

        layer = FeatureGroup(name=HIGHWAY_LAYER_NAMES[highway], show=True)
        style = HIGHWAY_STYLES[highway]

        folium.GeoJson(
            subset[tooltip_fields + ["geometry"]],
            style_function=lambda _feature, s=style: s,
            tooltip=folium.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=[tooltip_aliases[f] for f in tooltip_fields],
                localize=True,
                sticky=False,
            ),
        ).add_to(layer)
        layer.add_to(m)

    return counts


def add_node_layer(m: folium.Map, nodes_gdf: gpd.GeoDataFrame) -> dict[str, int]:
    nodes = nodes_gdf.copy()
    layer = FeatureGroup(name="Road Network Nodes", show=True)

    tooltip_fields = [c for c in ("node_id", "degree", "lon", "lat") if c in nodes.columns]
    tooltip_aliases = {
        "node_id": "Node ID",
        "degree": "Degree",
        "lon": "Longitude",
        "lat": "Latitude",
    }

    folium.GeoJson(
        nodes[tooltip_fields + ["geometry"]],
        marker=folium.CircleMarker(
            radius=3,
            color="#2166ac",
            weight=1,
            fill=True,
            fill_color="#4393c3",
            fill_opacity=0.75,
        ),
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=[tooltip_aliases[f] for f in tooltip_fields],
            localize=True,
            sticky=False,
        ),
    ).add_to(layer)
    layer.add_to(m)

    degree = nodes["degree"] if "degree" in nodes.columns else pd.Series(dtype=int)
    return {
        "total": len(nodes),
        "junction": int((degree >= JUNCTION_MIN_DEGREE).sum()),
        "endpoint": int((degree == 1).sum()),
    }


def build_map() -> folium.Map:
    nodes_gdf, edges_gdf = load_topology()
    sites_df = load_displacement_sites(DISPLACEMENT_XLSX)
    hospitals_df = load_hospitals(HEALTH_XLSX)

    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles="CartoDB positron",
        control_scale=True,
    )

    edge_counts = add_edge_layers(m, edges_gdf)
    node_counts = add_node_layer(m, nodes_gdf)
    site_count = add_displacement_sites(m, sites_df)
    hospital_count = add_hospitals(m, hospitals_df)

    folium.LayerControl(collapsed=False).add_to(m)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    m.save(str(OUTPUT_HTML))

    print("Road topology validation map summary:")
    print(f"  Road edges (total):        {sum(edge_counts.values()):,}")
    for highway in HIGHWAY_ORDER:
        print(f"    {highway:14} {edge_counts.get(highway, 0):,}")
    print(f"  Road nodes (total):        {node_counts['total']:,}")
    print(f"    junction (deg >= 3)       {node_counts['junction']:,}")
    print(f"    endpoint (deg == 1)       {node_counts['endpoint']:,}")
    print(f"  Displacement sites loaded: {site_count}")
    print(f"  Hospitals loaded:          {hospital_count}")
    print(f"  Output saved to:           {OUTPUT_HTML}")
    return m


def main() -> int:
    try:
        build_map()
    except Exception as exc:
        print(f"Failed to build road topology validation map: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
