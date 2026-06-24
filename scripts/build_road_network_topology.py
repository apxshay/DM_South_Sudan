#!/usr/bin/env python3
"""Build a clean, connected road-network graph for South Sudan using OSMnx.

Downloads the Geofabrik South Sudan OSM extract, filters to the Phase 1
highway classes (primary, secondary, tertiary, unclassified), then lets
OSMnx construct and simplify the graph so T-junctions are split and curve
shape-point nodes are removed.

Outputs under data/processed/roads_hotosm/:
  - road_nodes.gpkg / road_nodes.csv
  - road_edges.gpkg / road_edges.csv
  - topology_summary.json
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import PROCESSED_ROADS_HOTOSM, ensure_project_dirs  # noqa: E402

GEOFABRIK_URL = "https://download.geofabrik.de/africa/south-sudan-latest.osm.pbf"
OSM_PBF = ROOT / "data" / "raw" / "roads_hotosm" / "original" / "south-sudan-latest.osm.pbf"
INTERIM = ROOT / "data" / "interim" / "osmnx"
FILTERED_PBF = INTERIM / "south_sudan_roads_filtered.osm.pbf"
FILTERED_OSM = INTERIM / "south_sudan_roads_filtered.osm"

HIGHWAY_CLASSES = ("primary", "secondary", "tertiary", "unclassified")
HIGHWAY_FILTER = '["highway"~"primary|secondary|tertiary|unclassified"]'

EDGE_COLUMNS = (
    "osm_id",
    "highway",
    "name",
    "length",
    "length_m",
    "oneway",
    "reversed",
    "bridge",
    "surface",
    "maxspeed",
)


def _require_osmium() -> str:
    if shutil.which("osmium") is None:
        raise RuntimeError(
            "osmium CLI not found. Install with: conda install -c conda-forge osmium-tool"
        )
    return "osmium"


def download_geofabrik_extract() -> Path:
    OSM_PBF.parent.mkdir(parents=True, exist_ok=True)
    if OSM_PBF.exists() and OSM_PBF.stat().st_size > 1_000_000:
        print(f"Using cached Geofabrik extract: {OSM_PBF}")
        return OSM_PBF

    print(f"Downloading Geofabrik South Sudan extract (~130 MB) ...")
    print(f"  {GEOFABRIK_URL}")
    with urllib.request.urlopen(GEOFABRIK_URL, timeout=600) as response:  # noqa: S310
        OSM_PBF.write_bytes(response.read())
    print(f"  Saved to {OSM_PBF}")
    return OSM_PBF


def filter_highways_to_osm(source_pbf: Path) -> Path:
    osmium = _require_osmium()
    INTERIM.mkdir(parents=True, exist_ok=True)

    if FILTERED_OSM.exists() and FILTERED_OSM.stat().st_size > 0:
        print(f"Using cached filtered OSM XML: {FILTERED_OSM}")
        return FILTERED_OSM

    tag_args = [f"w/highway={cls}" for cls in HIGHWAY_CLASSES]
    filter_cmd = [
        osmium,
        "tags-filter",
        str(source_pbf),
        *tag_args,
        "-o",
        str(FILTERED_PBF),
        "--overwrite",
    ]
    print("Filtering highways with osmium ...")
    print("  " + " ".join(tag_args))
    subprocess.run(filter_cmd, check=True)

    export_cmd = [
        osmium,
        "cat",
        str(FILTERED_PBF),
        "-f",
        "osm",
        "-o",
        str(FILTERED_OSM),
        "--overwrite",
    ]
    print("Converting filtered network to OSM XML for OSMnx ...")
    subprocess.run(export_cmd, check=True)
    return FILTERED_OSM


def build_graph_from_osm(osm_path: Path):
    ox.settings.log_console = True

    print("Building and simplifying graph with OSMnx ...")
    G = ox.graph.graph_from_xml(
        osm_path,
        bidirectional=False,
        simplify=True,
        retain_all=False,
    )
    return G


def _normalize_attr(value):
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return value


def graph_to_clean_layers(G) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, dict]:
    nodes_gdf, edges_gdf = ox.convert.graph_to_gdfs(G, node_geometry=True, fill_edge_geometry=True)

    nodes_gdf = nodes_gdf.reset_index(names="node_id")
    nodes_gdf = nodes_gdf.rename(columns={"x": "lon", "y": "lat"})
    nodes_gdf["degree"] = nodes_gdf["node_id"].map(dict(G.degree))
    nodes_out = nodes_gdf[["node_id", "lon", "lat", "degree", "geometry"]].copy()

    edges_gdf = edges_gdf.reset_index(names=["start_node_id", "end_node_id", "edge_key"])
    edges_gdf["edge_id"] = range(1, len(edges_gdf) + 1)

    if "length_m" not in edges_gdf.columns:
        edges_gdf["length_m"] = edges_gdf.get("length")

    keep = ["edge_id", "start_node_id", "end_node_id", "edge_key", "length_m"]
    for col in EDGE_COLUMNS:
        if col in edges_gdf.columns and col not in keep:
            keep.append(col)
    keep.append("geometry")
    edges_out = edges_gdf[keep].copy()

    if "osmid" in edges_out.columns:
        edges_out = edges_out.rename(columns={"osmid": "osm_id"})

    for col in edges_out.columns:
        if col != "geometry":
            edges_out[col] = edges_out[col].map(_normalize_attr)

    summary = {
        "source": "Geofabrik South Sudan OSM extract + OSMnx graph_from_xml",
        "geofabrik_url": GEOFABRIK_URL,
        "highway_filter": HIGHWAY_FILTER,
        "highway_classes": list(HIGHWAY_CLASSES),
        "simplified": True,
        "node_count": len(nodes_out),
        "edge_count": len(edges_out),
        "isolated_node_count": int((nodes_out["degree"] == 0).sum()),
        "endpoint_node_count": int((nodes_out["degree"] == 1).sum()),
        "junction_node_count": int((nodes_out["degree"] >= 3).sum()),
        "total_edge_length_km": round(float(edges_out["length_m"].sum()) / 1000, 2),
        "highway_counts": edges_out["highway"].value_counts(dropna=False).astype(int).to_dict()
        if "highway" in edges_out.columns
        else {},
    }
    return nodes_out, edges_out, summary


def save_outputs(nodes_gdf: gpd.GeoDataFrame, edges_gdf: gpd.GeoDataFrame, summary: dict) -> None:
    PROCESSED_ROADS_HOTOSM.mkdir(parents=True, exist_ok=True)

    nodes_gpkg = PROCESSED_ROADS_HOTOSM / "road_nodes.gpkg"
    edges_gpkg = PROCESSED_ROADS_HOTOSM / "road_edges.gpkg"
    nodes_csv = PROCESSED_ROADS_HOTOSM / "road_nodes.csv"
    edges_csv = PROCESSED_ROADS_HOTOSM / "road_edges.csv"
    summary_path = PROCESSED_ROADS_HOTOSM / "topology_summary.json"

    nodes_gdf.to_file(nodes_gpkg, driver="GPKG")
    edges_gdf.to_file(edges_gpkg, driver="GPKG")
    pd.DataFrame(nodes_gdf.drop(columns="geometry")).to_csv(nodes_csv, index=False)
    edges_gdf.drop(columns="geometry").to_csv(edges_csv, index=False)
    summary_path.write_text(json.dumps(summary, indent=2))

    print("Road network topology written:")
    print(f"  Nodes:   {nodes_gpkg} ({summary['node_count']:,})")
    print(f"           {nodes_csv}")
    print(f"  Edges:   {edges_gpkg} ({summary['edge_count']:,})")
    print(f"           {edges_csv}")
    print(f"  Summary: {summary_path}")
    print(f"  Junction nodes (degree >= 3): {summary['junction_node_count']:,}")
    print(f"  Total edge length: {summary['total_edge_length_km']:,} km")


def main() -> int:
    ensure_project_dirs()
    INTERIM.mkdir(parents=True, exist_ok=True)

    try:
        pbf = download_geofabrik_extract()
        osm_path = filter_highways_to_osm(pbf)
        G = build_graph_from_osm(osm_path)
        nodes_gdf, edges_gdf, summary = graph_to_clean_layers(G)
        save_outputs(nodes_gdf, edges_gdf, summary)
    except Exception as exc:
        print(f"ERROR building road network topology: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
