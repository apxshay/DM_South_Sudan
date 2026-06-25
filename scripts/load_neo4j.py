#!/usr/bin/env python3
"""Load Phase 2 processed datasets into Neo4j.

Creates nodes and directed relationships with MERGE for idempotency,
applies constraints.cypher, and prints validation counts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from db.db_config import neo4j_config  # noqa: E402
from project_paths import (  # noqa: E402
    PROCESSED_DISPLACEMENT_SITES,
    PROCESSED_HEALTH_FACILITIES,
    PROCESSED_NETWORK,
    PROCESSED_REFERENCE,
    PROCESSED_ROADS_HOTOSM,
)

CONSTRAINTS_CYPHER = ROOT / "src" / "db" / "neo4j" / "constraints.cypher"
ROAD_UNLIMITED_CAPACITY = 999_999_999
BATCH_SIZE = 1000

EXPECTED = {
    "RoadNode": 24779,
    "ROAD_SEGMENT": 62345,
    "HealthFacility": 2017,
    "DisplacementSite": 77,
    "CONNECTOR": 2094,
    "CONNECTOR_REVERSE": 2094,
    "LogisticalHub": 5,
}


def _chunks(rows: list, size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def clear_graph(session) -> None:
    session.run("MATCH (n) DETACH DELETE n")


def apply_constraints(session) -> None:
    statements = [
        s.strip()
        for s in CONSTRAINTS_CYPHER.read_text().split(";")
        if s.strip() and not s.strip().startswith("//")
    ]
    for stmt in statements:
        session.run(stmt)


def load_road_nodes(session) -> None:
    gdf = gpd.read_file(PROCESSED_ROADS_HOTOSM / "road_nodes.gpkg")
    rows = [
        {
            "node_id": int(r.node_id),
            "lon": float(r.lon),
            "lat": float(r.lat),
            "degree": int(r.degree),
        }
        for r in gdf.itertuples(index=False)
    ]
    for batch in _chunks(rows, BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (n:RoadNode {node_id: row.node_id})
            SET n.lon = row.lon, n.lat = row.lat, n.degree = row.degree
            """,
            rows=batch,
        )


def load_health_facilities(session) -> None:
    poi = gpd.read_file(PROCESSED_NETWORK / "poi_nodes.gpkg")
    poi = poi[poi["poi_type"] == "health_facility"]
    caps = pd.read_csv(PROCESSED_HEALTH_FACILITIES / "health_facilities_with_capacity.csv")
    caps = caps[caps["has_coordinates"]][["facility_id", "admission_capacity"]]
    df = poi.merge(caps, on="facility_id", how="left")
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            {
                "poi_node_id": str(r.poi_node_id),
                "facility_id": str(r.facility_id),
                "name": str(r.facility_name),
                "facility_type": str(r.facility_type),
                "state_code": str(r.state_code) if pd.notna(r.state_code) else None,
                "admission_capacity": int(r.admission_capacity)
                if pd.notna(r.admission_capacity)
                else None,
                "lat": float(r.latitude),
                "lon": float(r.longitude),
                "nearest_road_node_id": int(r.nearest_road_node_id),
                "snap_distance_m": float(r.snap_distance_m),
            }
        )
    for batch in _chunks(rows, BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (h:HealthFacility {poi_node_id: row.poi_node_id})
            SET h.facility_id = row.facility_id,
                h.name = row.name,
                h.facility_type = row.facility_type,
                h.state_code = row.state_code,
                h.admission_capacity = row.admission_capacity,
                h.lat = row.lat,
                h.lon = row.lon,
                h.nearest_road_node_id = row.nearest_road_node_id,
                h.snap_distance_m = row.snap_distance_m
            """,
            rows=batch,
        )


def load_displacement_sites(session) -> None:
    poi = gpd.read_file(PROCESSED_NETWORK / "poi_nodes.gpkg")
    poi = poi[poi["poi_type"] == "displacement_site"]
    sites = pd.read_csv(PROCESSED_DISPLACEMENT_SITES / "displacement_sites_canonical.csv")
    df = poi.merge(
        sites,
        left_on="poi_node_id",
        right_on="site_id",
        how="inner",
        suffixes=("_poi", "_site"),
    )
    rows = []
    for r in df.itertuples(index=False):
        state_code = r.state_code_site if pd.notna(r.state_code_site) else r.state_code_poi
        rows.append(
            {
                "poi_node_id": str(r.poi_node_id),
                "site_id": str(r.site_id),
                "name": str(r.site_name),
                "state_code": str(state_code) if pd.notna(state_code) else None,
                "idp_individuals": int(r.idp_individuals),
                "idp_households": int(r.idp_households)
                if pd.notna(r.idp_households)
                else None,
                "lat": float(r.latitude_site),
                "lon": float(r.longitude_site),
                "nearest_road_node_id": int(r.nearest_road_node_id),
                "snap_distance_m": float(r.snap_distance_m),
            }
        )
    for batch in _chunks(rows, BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MERGE (d:DisplacementSite {poi_node_id: row.poi_node_id})
            SET d.site_id = row.site_id,
                d.name = row.name,
                d.state_code = row.state_code,
                d.idp_individuals = row.idp_individuals,
                d.idp_households = row.idp_households,
                d.lat = row.lat,
                d.lon = row.lon,
                d.nearest_road_node_id = row.nearest_road_node_id,
                d.snap_distance_m = row.snap_distance_m
            """,
            rows=batch,
        )


def load_logistical_hubs(session) -> None:
    hubs = pd.read_csv(PROCESSED_REFERENCE / "logistical_hubs.csv")
    rows = [
        {
            "hub_id": str(r.hub_id),
            "facility_id": str(r.facility_id),
            "hub_name": str(r.hub_name),
            "state_code": str(r.state_code) if pd.notna(r.state_code) else None,
            "role": str(r.role) if pd.notna(r.role) else None,
        }
        for r in hubs.itertuples(index=False)
    ]
    session.run(
        """
        UNWIND $rows AS row
        MATCH (h:HealthFacility {facility_id: row.facility_id})
        SET h:LogisticalHub
        SET h.hub_id = row.hub_id,
            h.hub_name = row.hub_name,
            h.role = row.role
        """,
        rows=rows,
    )


def load_road_segments(session) -> None:
    gdf = gpd.read_file(PROCESSED_ROADS_HOTOSM / "road_edges.gpkg")
    rows = []
    for r in gdf.itertuples(index=False):
        rows.append(
            {
                "edge_id": int(r.edge_id),
                "start_node_id": int(r.start_node_id),
                "end_node_id": int(r.end_node_id),
                "length_m": float(r.length_m),
                "highway": str(r.highway) if pd.notna(r.highway) else None,
                "oneway": bool(r.oneway) if pd.notna(r.oneway) else None,
                "capacity": ROAD_UNLIMITED_CAPACITY,
            }
        )
    for batch in _chunks(rows, BATCH_SIZE):
        session.run(
            """
            UNWIND $rows AS row
            MATCH (a:RoadNode {node_id: row.start_node_id})
            MATCH (b:RoadNode {node_id: row.end_node_id})
            MERGE (a)-[r:ROAD_SEGMENT {edge_id: row.edge_id}]->(b)
            SET r.length_m = row.length_m,
                r.highway = row.highway,
                r.oneway = row.oneway,
                r.capacity = row.capacity
            """,
            rows=batch,
        )


def _load_connector_batches(session, rows: list[dict], poi_label: str) -> None:
    for batch in _chunks(rows, BATCH_SIZE):
        session.run(
            f"""
            UNWIND $rows AS row
            MATCH (poi:{poi_label} {{poi_node_id: row.poi_node_id}})
            MATCH (road:RoadNode {{node_id: row.road_node_id}})
            MERGE (poi)-[r:CONNECTOR {{edge_id: row.edge_id}}]->(road)
            SET r.length_m = row.length_m, r.capacity = row.capacity
            """,
            rows=batch,
        )


def load_connectors(session) -> None:
    gdf = gpd.read_file(PROCESSED_NETWORK / "connector_edges.gpkg")
    health_rows: list[dict] = []
    site_rows: list[dict] = []
    for r in gdf.itertuples(index=False):
        row = {
            "edge_id": int(r.edge_id),
            "poi_node_id": str(r.poi_node_id),
            "road_node_id": int(r.end_node_id),
            "length_m": float(r.length_m),
            "capacity": int(r.capacity) if pd.notna(r.capacity) else None,
        }
        if str(r.poi_type) == "health_facility":
            health_rows.append(row)
        else:
            site_rows.append(row)
    _load_connector_batches(session, health_rows, "HealthFacility")
    _load_connector_batches(session, site_rows, "DisplacementSite")


def _load_connector_reverse_batches(session, rows: list[dict], poi_label: str) -> None:
    for batch in _chunks(rows, BATCH_SIZE):
        session.run(
            f"""
            UNWIND $rows AS row
            MATCH (road:RoadNode {{node_id: row.road_node_id}})
            MATCH (poi:{poi_label} {{poi_node_id: row.poi_node_id}})
            MERGE (road)-[r:CONNECTOR_REVERSE {{edge_id: row.edge_id}}]->(poi)
            SET r.length_m = row.length_m, r.capacity = row.capacity
            """,
            rows=batch,
        )


def load_connector_reverse(session) -> None:
    df = pd.read_csv(PROCESSED_NETWORK / "routing_edges.csv", low_memory=False)
    df = df[df["edge_type"] == "connector_reverse"]
    health_rows: list[dict] = []
    site_rows: list[dict] = []
    for r in df.itertuples(index=False):
        row = {
            "edge_id": int(r.edge_id),
            "poi_node_id": str(r.poi_node_id),
            "road_node_id": int(r.start_node_id),
            "length_m": float(r.length_m),
            "capacity": int(r.capacity) if pd.notna(r.capacity) else None,
        }
        if str(r.poi_type) == "health_facility":
            health_rows.append(row)
        else:
            site_rows.append(row)
    _load_connector_reverse_batches(session, health_rows, "HealthFacility")
    _load_connector_reverse_batches(session, site_rows, "DisplacementSite")


def count_entities(session) -> dict[str, int]:
    queries = {
        "RoadNode": "MATCH (n:RoadNode) RETURN count(n) AS c",
        "ROAD_SEGMENT": "MATCH ()-[r:ROAD_SEGMENT]->() RETURN count(r) AS c",
        "HealthFacility": "MATCH (n:HealthFacility) RETURN count(n) AS c",
        "DisplacementSite": "MATCH (n:DisplacementSite) RETURN count(n) AS c",
        "CONNECTOR": "MATCH ()-[r:CONNECTOR]->() RETURN count(r) AS c",
        "CONNECTOR_REVERSE": "MATCH ()-[r:CONNECTOR_REVERSE]->() RETURN count(r) AS c",
        "LogisticalHub": "MATCH (:LogisticalHub) RETURN count(*) AS c",
    }
    counts = {}
    for label, cypher in queries.items():
        counts[label] = session.run(cypher).single()["c"]
    return counts


def smoke_test_q1(session) -> dict:
    camp_id = "SSD-DS-SS0101_0005"
    hospital_id = "SSD-HF-000055"
    camp_connector = session.run(
        """
        MATCH (c:DisplacementSite {poi_node_id: $camp_id})-[:CONNECTOR]->(:RoadNode)
        RETURN count(c) AS c
        """,
        camp_id=camp_id,
    ).single()["c"]
    hospital_connector = session.run(
        """
        MATCH (h:HealthFacility {facility_id: $hospital_id})-[:CONNECTOR]->(:RoadNode)
        RETURN count(h) AS c
        """,
        hospital_id=hospital_id,
    ).single()["c"]
    hub_count = session.run(
        """
        MATCH (h:HealthFacility:LogisticalHub {facility_id: $hospital_id})
        RETURN count(h) AS c
        """,
        hospital_id=hospital_id,
    ).single()["c"]
    routable = session.run(
        """
        MATCH (h:HealthFacility)-[:CONNECTOR]->(:RoadNode)
        WHERE h.facility_type IN ['Hospital', 'PHCC']
        RETURN count(h) AS c
        """
    ).single()["c"]
    return {
        "camp_connector": camp_connector,
        "hospital_connector": hospital_connector,
        "hub_count": hub_count,
        "routable_facilities": routable,
    }


def load_all(session, reset: bool = False) -> None:
    if reset:
        clear_graph(session)
    load_road_nodes(session)
    load_health_facilities(session)
    load_displacement_sites(session)
    load_road_segments(session)
    load_connectors(session)
    load_connector_reverse(session)
    load_logistical_hubs(session)
    apply_constraints(session)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Clear graph before import")
    args = parser.parse_args()

    cfg = neo4j_config()
    driver = GraphDatabase.driver(cfg.uri, auth=(cfg.user, cfg.password))
    try:
        with driver.session() as session:
            load_all(session, reset=args.reset)
            counts = count_entities(session)
            smoke = smoke_test_q1(session)

        print("Neo4j load complete.")
        for label, expected in EXPECTED.items():
            actual = counts.get(label, 0)
            status = "OK" if actual == expected else "MISMATCH"
            print(f"  {label}: {actual} (expected {expected}) [{status}]")
        print("Q1 smoke prerequisites:")
        for key, value in smoke.items():
            print(f"  {key}: {value}")
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
