#!/usr/bin/env python3
"""Build reference tables for Phase 3 import and benchmark queries.

Outputs:
  - data/processed/reference/logistical_hubs.csv
  - data/processed/health_facilities/health_facilities_with_capacity.csv
  - data/processed/health_facilities/health_facilities_with_capacity.gpkg
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import (  # noqa: E402
    PROCESSED_HEALTH_FACILITIES,
    PROCESSED_REFERENCE,
    ensure_project_dirs,
)

CANONICAL = PROCESSED_HEALTH_FACILITIES / "health_facilities_canonical.gpkg"

ADMISSION_CAPACITY_BY_TYPE = {
    "Hospital": 250,
    "PHCC": 100,
    "PHCU": 50,
    "unknown": None,
}

# Curated referral hospitals for Q3 hub reachability (no airport data in project).
LOGISTICAL_HUBS = [
    {
        "hub_id": "HUB-001",
        "facility_id": "SSD-HF-000055",
        "hub_name": "Juba Teaching Hospital",
        "state_code": "SS01",
        "role": "national_referral",
    },
    {
        "hub_id": "HUB-002",
        "facility_id": "SSD-HF-001973",
        "hub_name": "Wau Teaching Hospital",
        "state_code": "SS09",
        "role": "state_referral",
    },
    {
        "hub_id": "HUB-003",
        "facility_id": "SSD-HF-001517",
        "hub_name": "Malakal Teaching Hospital",
        "state_code": "SS07",
        "role": "state_referral",
    },
    {
        "hub_id": "HUB-004",
        "facility_id": "SSD-HF-000629",
        "hub_name": "Bor State Hospital",
        "state_code": "SS03",
        "role": "state_referral",
    },
    {
        "hub_id": "HUB-005",
        "facility_id": "SSD-HF-000859",
        "hub_name": "Rumbek State Hospital",
        "state_code": "SS04",
        "role": "state_referral",
    },
]


def add_admission_capacity(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["admission_capacity"] = out["facility_type"].map(ADMISSION_CAPACITY_BY_TYPE)
    return out


def build_logistical_hubs(facilities: pd.DataFrame) -> pd.DataFrame:
    hub_rows = []
    facility_lookup = facilities.set_index("facility_id")
    for hub in LOGISTICAL_HUBS:
        fid = hub["facility_id"]
        if fid not in facility_lookup.index:
            raise ValueError(f"Logistical hub facility not found: {fid}")
        fac = facility_lookup.loc[fid]
        hub_rows.append(
            {
                **hub,
                "latitude": fac["latitude"],
                "longitude": fac["longitude"],
                "facility_type": fac["facility_type"],
                "admission_capacity": fac["admission_capacity"],
            }
        )
    return pd.DataFrame(hub_rows)


def main() -> int:
    ensure_project_dirs()
    PROCESSED_REFERENCE.mkdir(parents=True, exist_ok=True)

    if not CANONICAL.exists():
        print(f"ERROR: canonical facilities not found: {CANONICAL}", file=sys.stderr)
        return 1

    gdf = gpd.read_file(CANONICAL)
    df = pd.DataFrame(gdf.drop(columns="geometry"))
    enriched = add_admission_capacity(df)

    cap_csv = PROCESSED_HEALTH_FACILITIES / "health_facilities_with_capacity.csv"
    cap_gpkg = PROCESSED_HEALTH_FACILITIES / "health_facilities_with_capacity.gpkg"
    enriched.to_csv(cap_csv, index=False)
    gpd.GeoDataFrame(enriched, geometry=gdf.geometry, crs=gdf.crs).to_file(
        cap_gpkg, driver="GPKG"
    )

    hubs = build_logistical_hubs(enriched)
    hubs_path = PROCESSED_REFERENCE / "logistical_hubs.csv"
    hubs.to_csv(hubs_path, index=False)

    print("Reference data written:")
    print(f"  {cap_csv} ({len(enriched)} facilities with admission_capacity)")
    print(f"  {cap_gpkg}")
    print(f"  {hubs_path} ({len(hubs)} logistical hubs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
