#!/usr/bin/env python3
"""Prepare import-ready network layers for PostgreSQL and Neo4j.

Reads processed road topology, connectors, and reference capacity data; writes:
  - data/processed/network/connector_edges.gpkg (updated with capacity)
  - data/processed/network/graph_edges_directed.csv
  - data/processed/network/facility_road_access.csv
  - data/processed/network/routing_edges.csv
  - updates network_integration_summary.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import (  # noqa: E402
    PROCESSED_DISPLACEMENT_SITES,
    PROCESSED_HEALTH_FACILITIES,
    PROCESSED_NETWORK,
    PROCESSED_ROADS_HOTOSM,
    ensure_project_dirs,
)

ROAD_UNLIMITED_CAPACITY = 999_999_999

POI_NODES = PROCESSED_NETWORK / "poi_nodes.gpkg"
CONNECTORS = PROCESSED_NETWORK / "connector_edges.gpkg"
ROAD_EDGES = PROCESSED_ROADS_HOTOSM / "road_edges.gpkg"
FACILITIES_CAP = PROCESSED_HEALTH_FACILITIES / "health_facilities_with_capacity.csv"
DISPLACEMENT = PROCESSED_DISPLACEMENT_SITES / "displacement_sites_canonical.csv"
SUMMARY = PROCESSED_NETWORK / "network_integration_summary.json"


def load_poi_capacity() -> dict[str, int | None]:
    """Map poi_node_id -> connector capacity (outbound POI to road)."""
    caps: dict[str, int | None] = {}

    if FACILITIES_CAP.exists():
        fac = pd.read_csv(FACILITIES_CAP)
        for _, row in fac.iterrows():
            if not row.get("has_coordinates"):
                continue
            caps[str(row["facility_id"])] = (
                int(row["admission_capacity"])
                if pd.notna(row.get("admission_capacity"))
                else None
            )

    if DISPLACEMENT.exists():
        sites = pd.read_csv(DISPLACEMENT)
        for _, row in sites.iterrows():
            caps[str(row["site_id"])] = int(row["idp_individuals"])

    return caps


def enrich_connectors(connectors: gpd.GeoDataFrame, poi_caps: dict[str, int | None]) -> gpd.GeoDataFrame:
    out = connectors.copy()
    capacities = []
    for _, row in out.iterrows():
        poi_id = str(row["poi_node_id"])
        capacities.append(poi_caps.get(poi_id))
    out["capacity"] = capacities
    return out


def road_edges_directed(road_edges: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    for _, row in road_edges.iterrows():
        highway = row.get("highway")
        if isinstance(highway, str) and "|" in highway:
            highway = highway.split("|")[0]
        rows.append(
            {
                "edge_id": int(row["edge_id"]),
                "edge_type": "road_segment",
                "start_node_kind": "road",
                "start_node_id": str(int(row["start_node_id"])),
                "end_node_kind": "road",
                "end_node_id": str(int(row["end_node_id"])),
                "length_m": float(row["length_m"]),
                "capacity": ROAD_UNLIMITED_CAPACITY,
                "highway": highway,
                "oneway": row.get("oneway"),
                "poi_type": None,
                "poi_node_id": None,
            }
        )
    return pd.DataFrame(rows)


def connector_edges_directed(connectors: gpd.GeoDataFrame) -> pd.DataFrame:
    rows = []
    next_id = 900_000_001
    for _, row in connectors.iterrows():
        edge_id = int(row["edge_id"])
        poi_id = str(row["poi_node_id"])
        road_id = str(int(row["end_node_id"]))
        length_m = float(row["length_m"])
        capacity = row.get("capacity")
        cap_val = int(capacity) if pd.notna(capacity) else None

        rows.append(
            {
                "edge_id": edge_id,
                "edge_type": "connector",
                "start_node_kind": "poi",
                "start_node_id": poi_id,
                "end_node_kind": "road",
                "end_node_id": road_id,
                "length_m": length_m,
                "capacity": cap_val,
                "highway": None,
                "oneway": None,
                "poi_type": row.get("poi_type"),
                "poi_node_id": poi_id,
            }
        )
        rows.append(
            {
                "edge_id": next_id,
                "edge_type": "connector_reverse",
                "start_node_kind": "road",
                "start_node_id": road_id,
                "end_node_kind": "poi",
                "end_node_id": poi_id,
                "length_m": length_m,
                "capacity": cap_val,
                "highway": None,
                "oneway": None,
                "poi_type": row.get("poi_type"),
                "poi_node_id": poi_id,
            }
        )
        next_id += 1
    return pd.DataFrame(rows)


def build_facility_road_access(poi_nodes: gpd.GeoDataFrame) -> pd.DataFrame:
    hf = poi_nodes.loc[poi_nodes["poi_type"] == "health_facility"].copy()
    return pd.DataFrame(
        {
            "facility_id": hf["facility_id"],
            "poi_node_id": hf["poi_node_id"],
            "road_node_id": hf["nearest_road_node_id"].astype("int64"),
            "connector_length_m": hf["snap_distance_m"],
            "facility_type": hf["facility_type"],
        }
    )


def update_summary(summary: dict, routing: pd.DataFrame, connectors: gpd.GeoDataFrame) -> dict:
    summary = dict(summary)
    summary["import_layers"] = {
        "graph_edges_directed": "data/processed/network/graph_edges_directed.csv",
        "routing_edges": "data/processed/network/routing_edges.csv",
        "facility_road_access": "data/processed/network/facility_road_access.csv",
    }
    summary["capacity_model"] = {
        "road_segment": "unlimited (999999999)",
        "connector_outbound": "camp=idp_individuals; hospital=admission_capacity by type",
        "connector_reverse": "same capacity as outbound (for max-flow into hospitals)",
        "q5_note": "Benchmark scenario may override evacuees/hospital_free_slots per query",
    }
    summary["routing_edge_counts"] = {
        "total": int(len(routing)),
        "road_segment": int((routing["edge_type"] == "road_segment").sum()),
        "connector": int((routing["edge_type"] == "connector").sum()),
        "connector_reverse": int((routing["edge_type"] == "connector_reverse").sum()),
    }
    summary["connectors_with_capacity"] = int(connectors["capacity"].notna().sum())
    return summary


def main() -> int:
    ensure_project_dirs()

    required = [POI_NODES, CONNECTORS, ROAD_EDGES]
    missing = [p for p in required if not p.exists()]
    if missing:
        print("ERROR: run integrate_network.py first. Missing:", ", ".join(map(str, missing)), file=sys.stderr)
        return 1

    if not FACILITIES_CAP.exists() or not DISPLACEMENT.exists():
        print("ERROR: run build_reference_data.py and build_displacement_sites.py first.", file=sys.stderr)
        return 1

    poi_nodes = gpd.read_file(POI_NODES)
    connectors = gpd.read_file(CONNECTORS)
    road_edges = gpd.read_file(ROAD_EDGES)

    poi_caps = load_poi_capacity()
    connectors = enrich_connectors(connectors, poi_caps)

    road_df = road_edges_directed(road_edges)
    conn_df = connector_edges_directed(connectors)
    routing = pd.concat([road_df, conn_df], ignore_index=True)

    facility_access = build_facility_road_access(poi_nodes)

    connectors.to_file(CONNECTORS, driver="GPKG")
    pd.DataFrame(connectors.drop(columns="geometry")).to_csv(
        PROCESSED_NETWORK / "connector_edges.csv", index=False
    )

    routing_path = PROCESSED_NETWORK / "graph_edges_directed.csv"
    routing_edges_path = PROCESSED_NETWORK / "routing_edges.csv"
    routing.to_csv(routing_path, index=False)
    routing.to_csv(routing_edges_path, index=False)

    access_path = PROCESSED_NETWORK / "facility_road_access.csv"
    facility_access.to_csv(access_path, index=False)

    if SUMMARY.exists():
        summary = json.loads(SUMMARY.read_text())
    else:
        summary = {}
    summary = update_summary(summary, routing, connectors)
    SUMMARY.write_text(json.dumps(summary, indent=2))

    print("DB import layers written:")
    print(f"  {CONNECTORS} (capacity column added)")
    print(f"  {routing_path} ({len(routing):,} directed edges)")
    print(f"  {routing_edges_path}")
    print(f"  {access_path} ({len(facility_access):,} facilities)")
    print(f"  {SUMMARY} (updated)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
