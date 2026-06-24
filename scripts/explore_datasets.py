#!/usr/bin/env python3
"""Phase 1 dataset exploration — profiles raw datasets without transformation."""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "docs" / "phase1_profile.json"

HOTOSM_FILTERED = RAW / "roads_hotosm" / "filtered" / "roads_lines_filtered.gpkg"
HOTOSM_HIGHWAY_KEEP = ("primary", "secondary", "tertiary", "unclassified")


def profile_series(series: pd.Series) -> dict:
    return {
        "dtype": str(series.dtype),
        "non_null": int(series.notna().sum()),
        "null_count": int(series.isna().sum()),
        "null_pct": round(100 * series.isna().mean(), 2),
        "unique": int(series.nunique()),
    }


def profile_roads() -> dict:
    shp = RAW / "roads" / "SSD_road_network" / "SSD_Road_network.shp"
    gdf = gpd.read_file(shp)
    return {
        "source": "HDX — South Sudan: Road Network",
        "path": str(shp.relative_to(ROOT)),
        "format": "ESRI Shapefile (EPSG:4326)",
        "row_count": len(gdf),
        "geometry_types": gdf.geometry.geom_type.value_counts().to_dict(),
        "bounds": list(gdf.total_bounds),
        "columns": {col: profile_series(gdf[col]) for col in gdf.columns if col != "geometry"},
        "value_counts": {
            col: gdf[col].value_counts(dropna=False).head(10).astype(str).to_dict()
            for col in ["type", "status", "capacity", "speed"]
        },
    }


def profile_roads_hotosm() -> dict:
    source_shp = RAW / "roads_hotosm" / "roads_lines.shp"
    if not HOTOSM_FILTERED.exists():
        if not source_shp.exists():
            raise FileNotFoundError("HOT OSM roads not found; download and filter first.")
        gdf = gpd.read_file(source_shp)
        gdf = gdf[gdf["highway"].isin(HOTOSM_HIGHWAY_KEEP)].copy()
        HOTOSM_FILTERED.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(HOTOSM_FILTERED, driver="GPKG")

    gdf = gpd.read_file(HOTOSM_FILTERED)
    key_cols = ["highway", "surface", "oneway", "bridge"]
    return {
        "source": "HDX — Roads of South Sudan (HOT OSM)",
        "source_url": "https://data.humdata.org/dataset/hotosm_ssd_roads",
        "path": str(HOTOSM_FILTERED.relative_to(ROOT)),
        "original_path": str(source_shp.relative_to(ROOT)) if source_shp.exists() else None,
        "format": "GeoPackage (EPSG:4326), filtered from OSM lines",
        "filter": {"column": "highway", "values": list(HOTOSM_HIGHWAY_KEEP)},
        "row_count_original": int(gpd.read_file(source_shp).shape[0]) if source_shp.exists() else None,
        "row_count_filtered": len(gdf),
        "geometry_types": gdf.geometry.geom_type.value_counts().to_dict(),
        "bounds": list(gdf.total_bounds),
        "null_geometries": int(gdf.geometry.isna().sum()),
        "invalid_geometries": int((~gdf.geometry.is_valid).sum()),
        "columns": {col: profile_series(gdf[col]) for col in gdf.columns if col != "geometry"},
        "value_counts": {
            col: gdf[col].value_counts(dropna=False).head(15).astype(str).to_dict()
            for col in key_cols
            if col in gdf.columns
        },
        "highway_counts": gdf["highway"].value_counts().astype(int).to_dict(),
    }


def profile_health() -> dict:
    files = {
        "who_2025": RAW / "health_facilities" / "original" / "who-master-facility-list_april2025.xlsx",
        "ss_2023": RAW / "health_facilities" / "original" / "ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx",
    }
    result = {}
    for key, path in files.items():
        xl = pd.ExcelFile(path)
        result[key] = {"file": path.name, "sheets": {}}
        for sheet in xl.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            result[key]["sheets"][sheet] = {
                "row_count": len(df),
                "columns": {str(c): profile_series(df[c]) for c in df.columns},
            }
    return result


def profile_idp() -> dict:
    result = {}
    for path in sorted((RAW / "idp" / "original").glob("*.csv")):
        df = pd.read_csv(path)
        result[path.name] = {
            "row_count": len(df),
            "columns": {c: profile_series(df[c]) for c in df.columns},
        }
    return result


def _displacement_main_sheet(xl: pd.ExcelFile) -> str:
    for sheet in xl.sheet_names:
        lower = sheet.lower()
        if "dict" in lower or lower == "notes" or "data_dictionary" in lower:
            continue
        return sheet
    return xl.sheet_names[0]


def _skip_metadata_row(df: pd.DataFrame) -> pd.DataFrame:
    id_cols = [c for c in df.columns if "ssid" in str(c).lower()]
    if not id_cols:
        return df
    first = df[id_cols[0]].iloc[0]
    if isinstance(first, str) and first.startswith("#"):
        return df.iloc[1:].copy()
    return df


def profile_displacement_sites() -> dict:
    base = RAW / "displacement_sites" / "original"
    result = {"rounds": {}, "canonical_round": None}
    latest = None
    for path in sorted(base.glob("*.xlsx")):
        xl = pd.ExcelFile(path)
        main_sheet = _displacement_main_sheet(xl)
        df = _skip_metadata_row(pd.read_excel(path, sheet_name=main_sheet))
        round_info = {
            "file": path.name,
            "main_sheet": main_sheet,
            "all_sheets": xl.sheet_names,
            "site_count": len(df),
            "column_count": len(df.columns),
            "columns": {str(c): profile_series(df[c]) for c in df.columns},
        }
        result["rounds"][path.name] = round_info
        if latest is None or path.name.startswith("hdx_ssd-dtm"):
            latest = path.name
    result["canonical_round"] = latest
    return result


def main() -> None:
    profile = {
        "roads": profile_roads(),
        "roads_hotosm": profile_roads_hotosm(),
        "health_facilities": profile_health(),
        "idp": profile_idp(),
        "displacement_sites": profile_displacement_sites(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(profile, indent=2))
    print(f"Profile written to {OUT}")


if __name__ == "__main__":
    main()
