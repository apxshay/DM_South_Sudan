#!/usr/bin/env python3
"""Interactive geospatial validation map for South Sudan raw datasets."""

from __future__ import annotations

import sys
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
from folium import FeatureGroup

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "output"
OUTPUT_HTML = OUTPUT_DIR / "south_sudan_data_validation.html"

ROADS_HOTOSM = RAW / "roads_hotosm" / "filtered" / "roads_lines_filtered.gpkg"
ROADS_HOTOSM_SOURCE = RAW / "roads_hotosm" / "roads_lines.shp"
HOTOSM_HIGHWAY_KEEP = frozenset({"primary", "secondary", "tertiary", "unclassified"})

HIGHWAY_STYLES = {
    "primary": {"color": "#1a1a1a", "weight": 3, "opacity": 0.9},
    "secondary": {"color": "#4d4d4d", "weight": 2.5, "opacity": 0.85},
    "tertiary": {"color": "#737373", "weight": 2, "opacity": 0.8},
    "unclassified": {"color": "#a6a6a6", "weight": 1.5, "opacity": 0.75},
}
HIGHWAY_LAYER_NAMES = {
    "primary": "Primary Roads",
    "secondary": "Secondary Roads",
    "tertiary": "Tertiary Roads",
    "unclassified": "Unclassified Roads",
}
DISPLACEMENT_XLSX = (
    RAW
    / "displacement_sites"
    / "original"
    / "hdx_ssd-dtm-mobility-tracking-r11-site-assessment-dataset.xlsx"
)
HEALTH_XLSX = (
    RAW
    / "health_facilities"
    / "original"
    / "ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx"
)

MAP_CENTER = (7.5, 30.0)
MAP_ZOOM = 6

# Approximate South Sudan bounding box (lat/lon)
SSD_LAT_MIN, SSD_LAT_MAX = 3.5, 12.6
SSD_LON_MIN, SSD_LON_MAX = 24.4, 35.0


def load_hotosm_roads() -> gpd.GeoDataFrame:
    if not ROADS_HOTOSM.exists():
        if not ROADS_HOTOSM_SOURCE.exists():
            raise FileNotFoundError(
                f"HOT OSM roads not found. Expected {ROADS_HOTOSM_SOURCE}"
            )
        gdf = gpd.read_file(ROADS_HOTOSM_SOURCE)
        gdf = gdf[gdf["highway"].isin(HOTOSM_HIGHWAY_KEEP)].copy()
        ROADS_HOTOSM.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(ROADS_HOTOSM, driver="GPKG")

    gdf = gpd.read_file(ROADS_HOTOSM)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs("EPSG:4326")
    if "highway" not in gdf.columns:
        raise ValueError("HOT OSM roads missing required column: 'highway'")
    return gdf


def load_displacement_sites(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Displacement sites file not found: {path}")
    df = pd.read_excel(path, sheet_name="MT11 SA")

    id_col = "b01.location.ssid"
    if id_col not in df.columns:
        raise ValueError(f"Displacement sheet missing column: {id_col}")

    # Drop HXL metadata row (e.g. #geo+lon, #b01.location.ssid)
    first_val = df[id_col].iloc[0]
    if isinstance(first_val, str) and first_val.startswith("#"):
        df = df.iloc[1:].copy()

    required = ["b10.gps.lon", "b11.gps.lat", "b02.location.name", "c02.idp.ind"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Displacement sheet missing columns: {missing}")

    df["b10.gps.lon"] = pd.to_numeric(df["b10.gps.lon"], errors="coerce")
    df["b11.gps.lat"] = pd.to_numeric(df["b11.gps.lat"], errors="coerce")
    df["c02.idp.ind"] = pd.to_numeric(df["c02.idp.ind"], errors="coerce")

    valid = (
        df["b10.gps.lon"].notna()
        & df["b11.gps.lat"].notna()
        & df["b10.gps.lon"].between(SSD_LON_MIN, SSD_LON_MAX)
        & df["b11.gps.lat"].between(SSD_LAT_MIN, SSD_LAT_MAX)
    )
    return df.loc[valid].copy()


def load_hospitals(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Health facilities file not found: {path}")
    df = pd.read_excel(path, sheet_name="Health Facilities & Codes")

    required = ["Latitude", "Longitude", "Facility_Name", "County", "Type"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Health facilities sheet missing columns: {missing}")

    df = df.loc[df["Type"].astype(str).str.strip().str.lower() == "hospital"].copy()

    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    valid = (
        df["Latitude"].notna()
        & df["Longitude"].notna()
        & df["Latitude"].between(SSD_LAT_MIN, SSD_LAT_MAX)
        & df["Longitude"].between(SSD_LON_MIN, SSD_LON_MAX)
    )
    return df.loc[valid].copy()


def add_hotosm_road_layers(m: folium.Map, roads_gdf: gpd.GeoDataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}

    for highway in ("primary", "secondary", "tertiary", "unclassified"):
        subset = roads_gdf[roads_gdf["highway"] == highway]
        if subset.empty:
            counts[highway] = 0
            continue

        layer = FeatureGroup(name=HIGHWAY_LAYER_NAMES[highway], show=True)
        style = HIGHWAY_STYLES[highway]

        def style_fn(_feature, s=style):
            return s

        folium.GeoJson(
            subset[["highway", "name", "geometry"]],
            style_function=style_fn,
            tooltip=folium.GeoJsonTooltip(
                fields=["highway", "name"],
                aliases=["Highway", "Name"],
                localize=True,
                sticky=False,
            ),
        ).add_to(layer)
        layer.add_to(m)
        counts[highway] = len(subset)

    return counts


def add_displacement_sites(m: folium.Map, sites_df: pd.DataFrame) -> int:
    layer = FeatureGroup(name="Displacement Sites", show=True)

    for _, row in sites_df.iterrows():
        name = row.get("b02.location.name", "Unknown site")
        idp_count = row.get("c02.idp.ind")
        idp_display = int(idp_count) if pd.notna(idp_count) else "N/A"

        popup_html = (
            f"<b>{name}</b><br>"
            f"IDP individuals: {idp_display:,}"
            if isinstance(idp_display, int)
            else f"<b>{name}</b><br>IDP individuals: {idp_display}"
        )

        folium.CircleMarker(
            location=[row["b11.gps.lat"], row["b10.gps.lon"]],
            radius=6,
            color="#b30000",
            fill=True,
            fill_color="#e31a1c",
            fill_opacity=0.85,
            weight=1,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=str(name),
        ).add_to(layer)

    layer.add_to(m)
    return len(sites_df)


def add_hospitals(m: folium.Map, hospitals_df: pd.DataFrame) -> int:
    layer = FeatureGroup(name="Hospitals", show=True)

    for _, row in hospitals_df.iterrows():
        name = row.get("Facility_Name", "Unknown hospital")
        county = row.get("County", "N/A")
        popup_html = f"<b>{name}</b><br>County: {county}"

        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=5,
            color="#006400",
            fill=True,
            fill_color="#33a02c",
            fill_opacity=0.9,
            weight=1,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=str(name),
        ).add_to(layer)

    layer.add_to(m)
    return len(hospitals_df)


def build_map() -> folium.Map:
    try:
        roads_gdf = load_hotosm_roads()
    except Exception as exc:
        print(f"ERROR loading HOT OSM roads: {exc}", file=sys.stderr)
        raise

    try:
        sites_df = load_displacement_sites(DISPLACEMENT_XLSX)
    except Exception as exc:
        print(f"ERROR loading displacement sites: {exc}", file=sys.stderr)
        raise

    try:
        hospitals_df = load_hospitals(HEALTH_XLSX)
    except Exception as exc:
        print(f"ERROR loading hospitals: {exc}", file=sys.stderr)
        raise

    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles="CartoDB positron",
        control_scale=True,
    )

    road_counts = add_hotosm_road_layers(m, roads_gdf)
    site_count = add_displacement_sites(m, sites_df)
    hospital_count = add_hospitals(m, hospitals_df)

    folium.LayerControl(collapsed=False).add_to(m)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    m.save(str(OUTPUT_HTML))

    total_roads = sum(road_counts.values())
    print("Data validation map summary:")
    print(f"  HOT OSM roads (total):     {total_roads}")
    for highway in ("primary", "secondary", "tertiary", "unclassified"):
        print(f"    {highway:14} {road_counts[highway]}")
    print(f"  Displacement sites loaded: {site_count}")
    print(f"  Hospitals loaded:          {hospital_count}")
    print(f"  Output saved to:           {OUTPUT_HTML}")

    return m


def main() -> int:
    try:
        build_map()
    except Exception as exc:
        print(f"Failed to build validation map: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
