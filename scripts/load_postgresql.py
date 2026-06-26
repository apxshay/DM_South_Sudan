#!/usr/bin/env python3
"""Load Phase 2 processed datasets into PostgreSQL / PostGIS.

Applies schema.sql, loads tables in FK order, and prints validation counts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from db.db_config import postgres_config  # noqa: E402
from project_paths import (  # noqa: E402
    PROCESSED_ADMIN,
    PROCESSED_DISPLACEMENT_SITES,
    PROCESSED_HEALTH_FACILITIES,
    PROCESSED_NETWORK,
    PROCESSED_REFERENCE,
    PROCESSED_ROADS_HOTOSM,
)

SCHEMA_SQL = ROOT / "src" / "db" / "postgresql" / "schema.sql"
ROAD_UNLIMITED_CAPACITY = 999_999_999

EXPECTED_COUNTS = {
    "admin_states": 11,
    "admin_counties": 79,
    "admin_payams": 512,
    "logistical_hubs": 5,
    "health_facilities": 2251,
    "displacement_sites": 77,
    "road_nodes": 24779,
    "road_edges": 62345,
    "poi_connectors": 2094,
    "routing_edges": 66533,
    "facility_road_access": 2017,
}


def connect():
    cfg = postgres_config()
    return psycopg2.connect(cfg.dsn)


def apply_schema(conn, reset: bool = False) -> None:
    if reset:
        with conn.cursor() as cur:
            cur.execute(
                """
                DROP TABLE IF EXISTS facility_road_access CASCADE;
                DROP TABLE IF EXISTS routing_edges CASCADE;
                DROP TABLE IF EXISTS poi_connectors CASCADE;
                DROP TABLE IF EXISTS road_edges CASCADE;
                DROP TABLE IF EXISTS road_nodes CASCADE;
                DROP TABLE IF EXISTS logistical_hubs CASCADE;
                DROP TABLE IF EXISTS displacement_sites CASCADE;
                DROP TABLE IF EXISTS health_facilities CASCADE;
                DROP TABLE IF EXISTS admin_payams CASCADE;
                DROP TABLE IF EXISTS admin_counties CASCADE;
                DROP TABLE IF EXISTS admin_states CASCADE;
                DROP VIEW IF EXISTS v_state_humanitarian_stats CASCADE;
                """
            )
        conn.commit()
    sql = SCHEMA_SQL.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def _copy_csv(conn, table: str, columns: list[str], df: pd.DataFrame) -> None:
    from io import StringIO

    buf = StringIO()
    df[columns].to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)
    cols = ", ".join(columns)
    with conn.cursor() as cur:
        cur.copy_expert(
            f"COPY {table} ({cols}) FROM STDIN WITH (FORMAT csv, NULL '\\N')",
            buf,
        )
    conn.commit()


def load_admin(conn) -> None:
    _copy_csv(
        conn,
        "admin_states",
        ["state_code", "state_name"],
        pd.read_csv(PROCESSED_ADMIN / "admin_states.csv"),
    )
    _copy_csv(
        conn,
        "admin_counties",
        ["county_code", "state_code", "county_name"],
        pd.read_csv(PROCESSED_ADMIN / "admin_counties.csv"),
    )
    _copy_csv(
        conn,
        "admin_payams",
        ["payam_code", "county_code", "state_code", "payam_name"],
        pd.read_csv(PROCESSED_ADMIN / "admin_payams.csv"),
    )


def load_health_facilities(conn) -> None:
    df = pd.read_csv(PROCESSED_HEALTH_FACILITIES / "health_facilities_with_capacity.csv")
    rows = []
    for _, row in df.iterrows():
        lat = row["latitude"] if pd.notna(row["latitude"]) else None
        lon = row["longitude"] if pd.notna(row["longitude"]) else None
        geom_wkt = None
        if pd.notna(lat) and pd.notna(lon):
            geom_wkt = f"POINT({lon} {lat})"
        rows.append(
            (
                row["facility_id"],
                row["facility_name"],
                row["facility_type"],
                row["state_code"] if pd.notna(row["state_code"]) else None,
                row["state_name"] if pd.notna(row["state_name"]) else None,
                row["county_code"] if pd.notna(row["county_code"]) else None,
                row["payam_code"] if pd.notna(row["payam_code"]) else None,
                lat,
                lon,
                bool(row["has_coordinates"]),
                int(row["admission_capacity"]) if pd.notna(row["admission_capacity"]) else None,
                row["source"] if pd.notna(row["source"]) else None,
                row["merge_status"] if pd.notna(row["merge_status"]) else None,
                row["who_site_name"] if pd.notna(row["who_site_name"]) else None,
                row["ss_facilities_code"] if pd.notna(row["ss_facilities_code"]) else None,
                geom_wkt,
                geom_wkt,
            )
        )
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO health_facilities (
                facility_id, facility_name, facility_type, state_code, state_name,
                county_code, payam_code, latitude, longitude, has_coordinates,
                admission_capacity, source, merge_status, who_site_name,
                ss_facilities_code, geom
            ) VALUES %s
            """,
            rows,
            template=(
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "CASE WHEN %s IS NULL THEN NULL ELSE ST_SetSRID(ST_GeomFromText(%s), 4326) END)"
            ),
        )
    conn.commit()


def load_displacement_sites(conn) -> None:
    sites = pd.read_csv(PROCESSED_DISPLACEMENT_SITES / "displacement_sites_canonical.csv")
    poi = pd.read_csv(PROCESSED_NETWORK / "poi_nodes.csv")
    poi_ds = poi[poi["poi_type"] == "displacement_site"][
        ["poi_node_id", "nearest_road_node_id", "snap_distance_m"]
    ]
    df = sites.merge(poi_ds, left_on="site_id", right_on="poi_node_id", how="left")
    rows = []
    for _, row in df.iterrows():
        rows.append(
            (
                row["site_id"],
                row["source_ssid"],
                row["site_name"],
                row["state_code"] if pd.notna(row["state_code"]) else None,
                row["state_name"] if pd.notna(row["state_name"]) else None,
                row["county_code"] if pd.notna(row["county_code"]) else None,
                row["payam_code"] if pd.notna(row["payam_code"]) else None,
                row["payam_name"] if pd.notna(row["payam_name"]) else None,
                row["latitude"],
                row["longitude"],
                int(row["idp_individuals"]),
                int(row["idp_households"]) if pd.notna(row["idp_households"]) else None,
                row["settlement_type"] if pd.notna(row["settlement_type"]) else None,
                row["accessibility"] if pd.notna(row["accessibility"]) else None,
                int(row["nearest_road_node_id"]) if pd.notna(row["nearest_road_node_id"]) else None,
                float(row["snap_distance_m"]) if pd.notna(row["snap_distance_m"]) else None,
                f"POINT({row['longitude']} {row['latitude']})",
            )
        )
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO displacement_sites (
                site_id, source_ssid, site_name, state_code, state_name,
                county_code, payam_code, payam_name, latitude, longitude,
                idp_individuals, idp_households, settlement_type, accessibility,
                nearest_road_node_id, snap_distance_m, geom
            ) VALUES %s
            """,
            rows,
            template=(
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "ST_SetSRID(ST_GeomFromText(%s), 4326))"
            ),
        )
    conn.commit()


def load_logistical_hubs(conn) -> None:
    df = pd.read_csv(PROCESSED_REFERENCE / "logistical_hubs.csv")
    rows = []
    for _, row in df.iterrows():
        rows.append(
            (
                row["hub_id"],
                row["facility_id"],
                row["hub_name"],
                row["state_code"] if pd.notna(row["state_code"]) else None,
                row["role"] if pd.notna(row["role"]) else None,
                row["latitude"],
                row["longitude"],
                row["facility_type"] if pd.notna(row["facility_type"]) else None,
                int(row["admission_capacity"]) if pd.notna(row["admission_capacity"]) else None,
                f"POINT({row['longitude']} {row['latitude']})",
            )
        )
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO logistical_hubs (
                hub_id, facility_id, hub_name, state_code, role,
                latitude, longitude, facility_type, admission_capacity, geom
            ) VALUES %s
            """,
            rows,
            template=(
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "ST_SetSRID(ST_GeomFromText(%s), 4326))"
            ),
        )
    conn.commit()


def load_road_nodes(conn) -> None:
    gdf = gpd.read_file(PROCESSED_ROADS_HOTOSM / "road_nodes.gpkg")
    rows = [
        (int(r.node_id), float(r.lon), float(r.lat), int(r.degree), r.geometry.wkt)
        for r in gdf.itertuples(index=False)
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO road_nodes (node_id, lon, lat, degree, geom)
            VALUES %s
            """,
            rows,
            template="(%s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))",
        )
    conn.commit()


def load_road_edges(conn) -> None:
    gdf = gpd.read_file(PROCESSED_ROADS_HOTOSM / "road_edges.gpkg")
    rows = []
    for r in gdf.itertuples(index=False):
        oneway = bool(r.oneway) if pd.notna(r.oneway) else None
        reversed_val = str(r.reversed) if pd.notna(r.reversed) else None
        rows.append(
            (
                int(r.edge_id),
                int(r.start_node_id),
                int(r.end_node_id),
                float(r.length_m),
                r.highway if pd.notna(r.highway) else None,
                oneway,
                reversed_val,
                ROAD_UNLIMITED_CAPACITY,
                None,
                r.name if pd.notna(r.name) else None,
                r.geometry.wkt,
            )
        )
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO road_edges (
                edge_id, start_node_id, end_node_id, length_m, highway, oneway,
                reversed, capacity, osm_id, name, geom
            ) VALUES %s
            """,
            rows,
            template=(
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "ST_SetSRID(ST_GeomFromText(%s), 4326))"
            ),
            page_size=2000,
        )
    conn.commit()


def load_poi_connectors(conn) -> None:
    gdf = gpd.read_file(PROCESSED_NETWORK / "connector_edges.gpkg")
    rows = []
    for r in gdf.itertuples(index=False):
        capacity = int(r.capacity) if pd.notna(r.capacity) else None
        rows.append(
            (
                int(r.edge_id),
                str(r.poi_node_id),
                str(r.poi_type),
                int(r.end_node_id),
                float(r.length_m),
                capacity,
                r.geometry.wkt,
            )
        )
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO poi_connectors (
                edge_id, poi_node_id, poi_type, road_node_id, length_m, capacity, geom
            ) VALUES %s
            """,
            rows,
            template="(%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326))",
        )
    conn.commit()


def load_facility_road_access(conn) -> None:
    _copy_csv(
        conn,
        "facility_road_access",
        ["facility_id", "poi_node_id", "road_node_id", "connector_length_m", "facility_type"],
        pd.read_csv(PROCESSED_NETWORK / "facility_road_access.csv"),
    )


def _parse_oneway(value) -> bool | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes"}:
        return True
    if text in {"false", "f", "0", "no"}:
        return False
    return None


def load_routing_edges(conn) -> None:
    df = pd.read_csv(PROCESSED_NETWORK / "routing_edges.csv", low_memory=False)
    rows = []
    for r in df.itertuples(index=False):
        capacity = None
        if pd.notna(r.capacity) and str(r.capacity).strip() != "":
            capacity = int(float(r.capacity))
        rows.append(
            (
                int(r.edge_id),
                str(r.edge_type),
                str(r.start_node_kind),
                str(r.start_node_id),
                str(r.end_node_kind),
                str(r.end_node_id),
                float(r.length_m),
                capacity,
                r.highway if pd.notna(r.highway) else None,
                _parse_oneway(r.oneway),
                r.poi_type if pd.notna(r.poi_type) else None,
                r.poi_node_id if pd.notna(r.poi_node_id) else None,
            )
        )
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO routing_edges (
                edge_id, edge_type, start_node_kind, start_node_id, end_node_kind,
                end_node_id, length_m, capacity, highway, oneway, poi_type, poi_node_id
            ) VALUES %s
            """,
            rows,
            page_size=1000,
        )
    conn.commit()


def load_all(conn) -> None:
    load_admin(conn)
    load_health_facilities(conn)
    load_displacement_sites(conn)
    load_logistical_hubs(conn)
    load_road_nodes(conn)
    load_road_edges(conn)
    load_poi_connectors(conn)
    load_facility_road_access(conn)
    load_routing_edges(conn)


def table_counts(conn) -> dict[str, int]:
    tables = list(EXPECTED_COUNTS.keys())
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
    return counts


def smoke_test_q1(conn) -> dict:
    camp_id = "SSD-DS-SS0101_0005"
    hospital_id = "SSD-HF-000055"
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM displacement_sites ds
            JOIN poi_connectors pc ON pc.poi_node_id = ds.site_id
            WHERE ds.site_id = %s
            """,
            (camp_id,),
        )
        camp_connector = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(*) FROM health_facilities hf
            JOIN facility_road_access fra ON fra.facility_id = hf.facility_id
            JOIN poi_connectors pc ON pc.poi_node_id = hf.facility_id
            WHERE hf.facility_id = %s
            """,
            (hospital_id,),
        )
        hospital_connector = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM logistical_hubs WHERE facility_id = %s",
            (hospital_id,),
        )
        hub_row = cur.fetchone()[0]
        cur.execute(
            """
            SELECT COUNT(*) FROM facility_road_access
            WHERE facility_type IN ('Hospital', 'PHCC')
            """
        )
        routable_facilities = cur.fetchone()[0]
    return {
        "camp_connector": camp_connector,
        "hospital_connector": hospital_connector,
        "hub_row": hub_row,
        "routable_facilities": routable_facilities,
    }


def validate_extensions(conn) -> dict[str, str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT extname, extversion
            FROM pg_extension
            WHERE extname IN ('postgis', 'pgrouting')
            ORDER BY extname
            """
        )
        return {row[0]: row[1] for row in cur.fetchall()}
    checks = []
    with conn.cursor() as cur:
        for table in ("health_facilities", "road_nodes", "road_edges", "poi_connectors"):
            cur.execute(
                f"""
                SELECT BOOL_AND(ST_IsValid(geom))
                FROM (SELECT geom FROM {table} WHERE geom IS NOT NULL LIMIT 100) s
                """
            )
            checks.append(cur.fetchone()[0])
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Drop and recreate schema")
    parser.add_argument("--schema-only", action="store_true", help="Apply schema only")
    args = parser.parse_args()

    conn = connect()
    try:
        apply_schema(conn, reset=args.reset)
        if not args.schema_only:
            load_all(conn)
        counts = table_counts(conn)
        smoke = smoke_test_q1(conn) if not args.schema_only else {}
        geom_ok = validate_geometry_samples(conn) if not args.schema_only else []

        print("PostgreSQL load complete.")
        extensions = validate_extensions(conn)
        if extensions:
            print("Extensions:")
            for name, version in extensions.items():
                print(f"  {name}: {version}")
        for table, expected in EXPECTED_COUNTS.items():
            actual = counts.get(table, 0)
            status = "OK" if actual == expected else "MISMATCH"
            print(f"  {table}: {actual} (expected {expected}) [{status}]")
        if smoke:
            print("Q1 smoke prerequisites:")
            for key, value in smoke.items():
                print(f"  {key}: {value}")
        if geom_ok:
            print(f"Geometry validity spot-checks (100 rows each): {geom_ok}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
