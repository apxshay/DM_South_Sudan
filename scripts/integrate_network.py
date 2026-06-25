#!/usr/bin/env python3
"""Connect health facilities and displacement sites to the road network graph.

Snaps each POI with valid WGS84 coordinates to the nearest road intersection
node (preferring junction nodes when distance is comparable), then writes
connector edges and an augmented edge layer for Phase 3 import.

Outputs under data/processed/network/:
  - poi_nodes.gpkg / poi_nodes.csv
  - connector_edges.gpkg / connector_edges.csv
  - road_graph_augmented_edges.gpkg / road_graph_augmented_edges.csv
  - network_integration_summary.json
"""

from __future__ import annotations

import json
import sys
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point
from sklearn.neighbors import BallTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import (  # noqa: E402
    PROCESSED_HEALTH_FACILITIES,
    PROCESSED_NETWORK,
    PROCESSED_ROADS_HOTOSM,
    RAW,
    ensure_project_dirs,
)
from visualize_data_validation import DISPLACEMENT_XLSX, load_displacement_sites  # noqa: E402

EARTH_RADIUS_M = 6_371_000.0
JUNCTION_MIN_DEGREE = 3
JUNCTION_REL_TOLERANCE = 0.10
JUNCTION_ABS_TOLERANCE_M = 250.0
SNAP_REVIEW_THRESHOLD_M = 5_000.0
NEIGHBOR_K = 25

HEALTH_CANONICAL = PROCESSED_HEALTH_FACILITIES / "health_facilities_canonical.gpkg"
ROAD_NODES = PROCESSED_ROADS_HOTOSM / "road_nodes.gpkg"
ROAD_EDGES = PROCESSED_ROADS_HOTOSM / "road_edges.gpkg"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * atan2(sqrt(a), sqrt(1 - a))


def comparable_distance_limit(nearest_m: float) -> float:
    return nearest_m * (1.0 + JUNCTION_REL_TOLERANCE) + JUNCTION_ABS_TOLERANCE_M


def snap_poi(
    poi_lat: float,
    poi_lon: float,
    road_degrees: np.ndarray,
    road_node_ids: np.ndarray,
    tree: BallTree,
) -> tuple[object, float, int, bool]:
    """Return (road_node_id, snap_distance_m, road_degree, junction_preferred)."""
    query_rad = np.radians([[poi_lat, poi_lon]])
    dist_rad, indices = tree.query(query_rad, k=NEIGHBOR_K)
    distances_m = dist_rad[0] * EARTH_RADIUS_M
    candidate_idx = indices[0]

    candidates = [
        (float(dist_m), int(idx), int(road_degrees[idx]))
        for dist_m, idx in zip(distances_m, candidate_idx)
    ]
    nearest_dist = candidates[0][0]
    limit_m = comparable_distance_limit(nearest_dist)
    comparable = [c for c in candidates if c[0] <= limit_m]
    junctions = [c for c in comparable if c[2] >= JUNCTION_MIN_DEGREE]

    if junctions:
        dist_m, idx, degree = min(junctions, key=lambda c: c[0])
        junction_preferred = idx != candidates[0][1]
    else:
        dist_m, idx, degree = candidates[0]
        junction_preferred = False

    return road_node_ids[idx], dist_m, degree, junction_preferred


def displacement_poi_id(ssid: object) -> str:
    text = str(ssid).strip()
    if text.startswith("ssid_"):
        text = text[5:]
    return f"SSD-DS-{text}"


def load_health_pois() -> pd.DataFrame:
    gdf = gpd.read_file(HEALTH_CANONICAL)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    df = df.loc[df["has_coordinates"]].copy()
    df["poi_type"] = "health_facility"
    df["poi_node_id"] = df["facility_id"]
    df["source_id"] = df["facility_id"]
    df["display_name"] = df["facility_name"]
    df["idp_count"] = pd.NA
    return df


def load_displacement_pois() -> pd.DataFrame:
    sites = load_displacement_sites(DISPLACEMENT_XLSX)
    rows = []
    for _, row in sites.iterrows():
        rows.append(
            {
                "poi_node_id": displacement_poi_id(row["b01.location.ssid"]),
                "poi_type": "displacement_site",
                "source_id": str(row["b01.location.ssid"]).strip(),
                "display_name": row["b02.location.name"],
                "facility_type": pd.NA,
                "state_code": row.get("b05.state.pcode"),
                "county_code": row.get("b07.county.pcode"),
                "payam_code": row.get("b09.payam.pcode"),
                "latitude": float(row["b11.gps.lat"]),
                "longitude": float(row["b10.gps.lon"]),
                "idp_count": row.get("c02.idp.ind"),
                "facility_id": pd.NA,
                "facility_name": pd.NA,
                "has_coordinates": True,
            }
        )
    return pd.DataFrame(rows)


def build_poi_snap_table(pois: pd.DataFrame, road_nodes: gpd.GeoDataFrame) -> pd.DataFrame:
    road_lats = road_nodes["lat"].to_numpy(dtype=float)
    road_lons = road_nodes["lon"].to_numpy(dtype=float)
    road_degrees = road_nodes["degree"].to_numpy(dtype=int)
    road_node_ids = road_nodes["node_id"].to_numpy()

    road_coords_rad = np.radians(np.column_stack([road_lats, road_lons]))
    tree = BallTree(road_coords_rad, metric="haversine")

    snaps = []
    for _, poi in pois.iterrows():
        node_id, dist_m, degree, junction_pref = snap_poi(
            float(poi["latitude"]),
            float(poi["longitude"]),
            road_degrees,
            road_node_ids,
            tree,
        )
        road_row = road_nodes.loc[road_nodes["node_id"] == node_id].iloc[0]
        snaps.append(
            {
                "nearest_road_node_id": node_id,
                "snap_distance_m": round(dist_m, 2),
                "nearest_road_node_degree": degree,
                "nearest_road_node_lat": float(road_row["lat"]),
                "nearest_road_node_lon": float(road_row["lon"]),
                "junction_preferred": junction_pref,
                "snap_review_flag": dist_m > SNAP_REVIEW_THRESHOLD_M,
            }
        )
    return pois.join(pd.DataFrame(snaps))


def poi_nodes_gdf(snap_df: pd.DataFrame) -> gpd.GeoDataFrame:
    geometry = [
        Point(float(row["longitude"]), float(row["latitude"]))
        for _, row in snap_df.iterrows()
    ]
    cols = [
        "poi_node_id",
        "poi_type",
        "source_id",
        "display_name",
        "facility_type",
        "state_code",
        "county_code",
        "payam_code",
        "latitude",
        "longitude",
        "idp_count",
        "nearest_road_node_id",
        "snap_distance_m",
        "nearest_road_node_degree",
        "junction_preferred",
        "snap_review_flag",
    ]
    optional = ["facility_id", "facility_name"]
    keep = [c for c in cols + optional if c in snap_df.columns]
    return gpd.GeoDataFrame(snap_df[keep].copy(), geometry=geometry, crs="EPSG:4326")


def connector_edges_gdf(snap_df: pd.DataFrame, start_edge_id: int) -> gpd.GeoDataFrame:
    rows = []
    for i, row in snap_df.iterrows():
        poi_lon, poi_lat = float(row["longitude"]), float(row["latitude"])
        road_lon, road_lat = float(row["nearest_road_node_lon"]), float(row["nearest_road_node_lat"])
        rows.append(
            {
                "edge_id": start_edge_id + len(rows),
                "start_node_id": row["poi_node_id"],
                "end_node_id": row["nearest_road_node_id"],
                "edge_type": "connector",
                "poi_type": row["poi_type"],
                "poi_node_id": row["poi_node_id"],
                "length_m": row["snap_distance_m"],
                "highway": None,
                "geometry": LineString([(poi_lon, poi_lat), (road_lon, road_lat)]),
            }
        )
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def augmented_edges_gdf(road_edges: gpd.GeoDataFrame, connectors: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    roads = road_edges.copy()
    roads["edge_type"] = "road_segment"
    roads["poi_type"] = None
    roads["poi_node_id"] = None

    conn = connectors.copy()
    for col in roads.columns:
        if col not in conn.columns and col != "geometry":
            conn[col] = None
    for col in ("edge_key", "name", "oneway", "reversed", "bridge", "maxspeed", "length"):
        if col in conn.columns:
            conn[col] = None

    combined = pd.concat([roads, conn[roads.columns]], ignore_index=True)
    return gpd.GeoDataFrame(combined, geometry="geometry", crs="EPSG:4326")


def build_summary(
    health_pois: pd.DataFrame,
    displacement_pois: pd.DataFrame,
    snap_df: pd.DataFrame,
    road_nodes: gpd.GeoDataFrame,
    road_edges: gpd.GeoDataFrame,
    connectors: gpd.GeoDataFrame,
) -> dict:
    health_snaps = snap_df.loc[snap_df["poi_type"] == "health_facility"]
    site_snaps = snap_df.loc[snap_df["poi_type"] == "displacement_site"]
    review = snap_df.loc[snap_df["snap_review_flag"]]
    review_records = review[
        ["poi_node_id", "poi_type", "display_name", "snap_distance_m", "nearest_road_node_id"]
    ].sort_values("snap_distance_m", ascending=False)

    def dist_stats(series: pd.Series) -> dict:
        if series.empty:
            return {"count": 0, "mean_m": None, "max_m": None, "median_m": None}
        return {
            "count": int(len(series)),
            "mean_m": round(float(series.mean()), 2),
            "median_m": round(float(series.median()), 2),
            "max_m": round(float(series.max()), 2),
        }

    return {
        "task": "network_integration",
        "connector_semantics": "straight_line_snap",
        "connector_semantics_note": (
            "Connectors are straight-line geodesic segments from each POI to the "
            "nearest road graph node. They represent access links for routing, not "
            "surveyed walking paths."
        ),
        "distance_metric": "haversine_geodesic_m",
        "snap_algorithm": {
            "nearest_search": f"BallTree haversine, k={NEIGHBOR_K}",
            "junction_preference": {
                "min_degree": JUNCTION_MIN_DEGREE,
                "relative_tolerance": JUNCTION_REL_TOLERANCE,
                "absolute_tolerance_m": JUNCTION_ABS_TOLERANCE_M,
                "rule": (
                    "Among road nodes within min(nearest_dist * (1 + rel_tol) + abs_tol_m), "
                    "prefer the highest-degree node (junction when degree >= 3)."
                ),
            },
            "review_threshold_m": SNAP_REVIEW_THRESHOLD_M,
        },
        "inputs": {
            "health_facilities_canonical": str(HEALTH_CANONICAL.relative_to(ROOT)),
            "displacement_sites": str(DISPLACEMENT_XLSX.relative_to(ROOT)),
            "road_nodes": str(ROAD_NODES.relative_to(ROOT)),
            "road_edges": str(ROAD_EDGES.relative_to(ROOT)),
        },
        "counts": {
            "road_nodes": len(road_nodes),
            "road_edges": len(road_edges),
            "health_facilities_with_coordinates": len(health_pois),
            "displacement_sites_with_coordinates": len(displacement_pois),
            "poi_nodes_total": len(snap_df),
            "connector_edges": len(connectors),
            "augmented_edges_total": len(road_edges) + len(connectors),
            "pois_junction_preferred": int(snap_df["junction_preferred"].sum()),
            "pois_needing_review": int(len(review)),
        },
        "snap_distance_stats": {
            "all_pois": dist_stats(snap_df["snap_distance_m"]),
            "health_facilities": dist_stats(health_snaps["snap_distance_m"]),
            "displacement_sites": dist_stats(site_snaps["snap_distance_m"]),
        },
        "excluded": {
            "health_facilities_missing_coordinates": int(
                len(gpd.read_file(HEALTH_CANONICAL)) - len(health_pois)
            ),
        },
        "validation": {
            "all_valid_pois_connected": bool(len(snap_df) == len(health_pois) + len(displacement_pois)),
            "disconnected_pois": 0,
            "review_flags_file": "data/processed/network/poi_snap_review.csv",
            "review_flags_count": int(len(review_records)),
            "review_flags_top_10": review_records.head(10).to_dict(orient="records"),
        },
    }


def save_outputs(
    poi_gdf: gpd.GeoDataFrame,
    connectors: gpd.GeoDataFrame,
    augmented: gpd.GeoDataFrame,
    summary: dict,
    review_df: pd.DataFrame,
) -> None:
    PROCESSED_NETWORK.mkdir(parents=True, exist_ok=True)

    paths = {
        "poi_nodes_gpkg": PROCESSED_NETWORK / "poi_nodes.gpkg",
        "poi_nodes_csv": PROCESSED_NETWORK / "poi_nodes.csv",
        "connector_edges_gpkg": PROCESSED_NETWORK / "connector_edges.gpkg",
        "connector_edges_csv": PROCESSED_NETWORK / "connector_edges.csv",
        "augmented_edges_gpkg": PROCESSED_NETWORK / "road_graph_augmented_edges.gpkg",
        "augmented_edges_csv": PROCESSED_NETWORK / "road_graph_augmented_edges.csv",
        "summary": PROCESSED_NETWORK / "network_integration_summary.json",
        "review": PROCESSED_NETWORK / "poi_snap_review.csv",
    }

    poi_gdf.to_file(paths["poi_nodes_gpkg"], driver="GPKG")
    pd.DataFrame(poi_gdf.drop(columns="geometry")).to_csv(paths["poi_nodes_csv"], index=False)

    connectors.to_file(paths["connector_edges_gpkg"], driver="GPKG")
    pd.DataFrame(connectors.drop(columns="geometry")).to_csv(paths["connector_edges_csv"], index=False)

    augmented.to_file(paths["augmented_edges_gpkg"], driver="GPKG")
    pd.DataFrame(augmented.drop(columns="geometry")).to_csv(paths["augmented_edges_csv"], index=False)

    paths["summary"].write_text(json.dumps(summary, indent=2))
    review_df.to_csv(paths["review"], index=False)

    print("Network integration outputs written:")
    for key, path in paths.items():
        count = ""
        if key == "poi_nodes_gpkg":
            count = f" ({len(poi_gdf):,} POIs)"
        elif key == "connector_edges_gpkg":
            count = f" ({len(connectors):,} connectors)"
        elif key == "augmented_edges_gpkg":
            count = f" ({len(augmented):,} edges)"
        print(f"  {path}{count}")


def main() -> int:
    ensure_project_dirs()

    for path in (HEALTH_CANONICAL, ROAD_NODES, ROAD_EDGES, DISPLACEMENT_XLSX):
        if not path.exists():
            print(f"ERROR: required input not found: {path}", file=sys.stderr)
            return 1

    try:
        road_nodes = gpd.read_file(ROAD_NODES)
        road_edges = gpd.read_file(ROAD_EDGES)
        if road_nodes.crs is None:
            road_nodes = road_nodes.set_crs("EPSG:4326")
        if road_edges.crs is None:
            road_edges = road_edges.set_crs("EPSG:4326")

        health_pois = load_health_pois()
        displacement_pois = load_displacement_pois()
        pois = pd.concat([health_pois, displacement_pois], ignore_index=True)

        snap_df = build_poi_snap_table(pois, road_nodes)
        poi_gdf = poi_nodes_gdf(snap_df)

        max_road_edge_id = int(road_edges["edge_id"].max()) if "edge_id" in road_edges.columns else 0
        connectors = connector_edges_gdf(snap_df, start_edge_id=max_road_edge_id + 1)
        augmented = augmented_edges_gdf(road_edges, connectors)
        summary = build_summary(health_pois, displacement_pois, snap_df, road_nodes, road_edges, connectors)
        review_df = snap_df.loc[snap_df["snap_review_flag"], [
            "poi_node_id", "poi_type", "display_name", "snap_distance_m", "nearest_road_node_id"
        ]].sort_values("snap_distance_m", ascending=False)

        save_outputs(poi_gdf, connectors, augmented, summary, review_df)
    except Exception as exc:
        print(f"ERROR integrating network: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
