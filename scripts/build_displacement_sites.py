#!/usr/bin/env python3
"""Build canonical displacement site table from IOM DTM Round 11.

Outputs under data/processed/displacement_sites/:
  - displacement_sites_canonical.csv
  - displacement_sites_canonical.gpkg
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import PROCESSED_DISPLACEMENT_SITES, ensure_project_dirs  # noqa: E402
from visualize_data_validation import DISPLACEMENT_XLSX, load_displacement_sites  # noqa: E402


def displacement_site_id(ssid: object) -> str:
    text = str(ssid).strip()
    if text.startswith("ssid_"):
        text = text[5:]
    return f"SSD-DS-{text}"


def build_canonical(raw_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in raw_df.iterrows():
        rows.append(
            {
                "site_id": displacement_site_id(row["b01.location.ssid"]),
                "source_ssid": str(row["b01.location.ssid"]).strip(),
                "site_name": row["b02.location.name"],
                "state_code": row.get("b05.state.pcode"),
                "state_name": row.get("b04.state.name"),
                "county_code": row.get("b07.county.pcode"),
                "county_name": row.get("b06.county.name"),
                "payam_code": row.get("b09.payam.pcode"),
                "payam_name": row.get("b08.payam.name"),
                "latitude": float(row["b11.gps.lat"]),
                "longitude": float(row["b10.gps.lon"]),
                "idp_individuals": int(row["c02.idp.ind"]),
                "idp_households": int(row["c01.idp.hh"]),
                "settlement_type": row.get("b14.settlement.type"),
                "accessibility": row.get("b13.accessibility"),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    ensure_project_dirs()
    PROCESSED_DISPLACEMENT_SITES.mkdir(parents=True, exist_ok=True)

    if not DISPLACEMENT_XLSX.exists():
        print(f"ERROR: displacement file not found: {DISPLACEMENT_XLSX}", file=sys.stderr)
        return 1

    raw_df = load_displacement_sites(DISPLACEMENT_XLSX)
    df = build_canonical(raw_df)
    geometry = [Point(row["longitude"], row["latitude"]) for _, row in df.iterrows()]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    csv_path = PROCESSED_DISPLACEMENT_SITES / "displacement_sites_canonical.csv"
    gpkg_path = PROCESSED_DISPLACEMENT_SITES / "displacement_sites_canonical.gpkg"
    df.to_csv(csv_path, index=False)
    gdf.to_file(gpkg_path, driver="GPKG")

    print("Displacement sites canonical table written:")
    print(f"  {csv_path} ({len(df)} sites)")
    print(f"  {gpkg_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
