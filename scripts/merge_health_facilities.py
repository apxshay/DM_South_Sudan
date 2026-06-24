#!/usr/bin/env python3
"""Merge WHO 2025 and SS 2023 health facility lists into one canonical dataset.

Outputs under data/processed/health_facilities/:
  - health_facilities_canonical.csv / .gpkg
  - health_facilities_merge_log.csv
  - health_facilities_merge_summary.json
"""

from __future__ import annotations

import json
import re
import sys
from math import radians, sin, cos, sqrt, atan2
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from health_facility_admin import harmonize_state_codes, load_admin_reference  # noqa: E402
from project_paths import PROCESSED_HEALTH_FACILITIES, RAW, ensure_project_dirs  # noqa: E402

WHO_PATH = RAW / "health_facilities" / "original" / "who-master-facility-list_april2025.xlsx"
SS_PATH = (
    RAW
    / "health_facilities"
    / "original"
    / "ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx"
)
WHO_SHEET = "hsf_master_facility_list_202403"
SS_SHEET = "Health Facilities & Codes"

# Approximate South Sudan bounding box (WGS84) for coordinate validation.
SSD_LAT_MIN, SSD_LAT_MAX = 3.4, 12.7
SSD_LON_MIN, SSD_LON_MAX = 24.0, 36.0

# Max distance (m) for coordinate-assisted payam-centroid state inference.
COORD_STATE_MAX_M = 30_000.0


def normalize_name(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text


def clean_code(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>"} else text


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * radius_m * atan2(sqrt(a), sqrt(1 - a))


def valid_coords(lat: object, lon: object) -> bool:
    if pd.isna(lat) or pd.isna(lon):
        return False
    lat_f, lon_f = float(lat), float(lon)
    return SSD_LAT_MIN <= lat_f <= SSD_LAT_MAX and SSD_LON_MIN <= lon_f <= SSD_LON_MAX


def choose_coords(
    who_lat: object,
    who_lon: object,
    ss_lat: object,
    ss_lon: object,
) -> tuple[float | None, float | None, str]:
    who_ok = valid_coords(who_lat, who_lon)
    ss_ok = valid_coords(ss_lat, ss_lon)
    if who_ok and ss_ok:
        return float(who_lat), float(who_lon), "who_preferred"
    if who_ok:
        return float(who_lat), float(who_lon), "who_only"
    if ss_ok:
        return float(ss_lat), float(ss_lon), "ss_only"
    return None, None, "missing"


def load_who() -> pd.DataFrame:
    df = pd.read_excel(WHO_PATH, sheet_name=WHO_SHEET)
    df = df.rename(
        columns={
            "site": "facility_name",
            "state_code": "state_code",
            "county_code": "county_code",
            "payam_code": "payam_code",
            "latitude": "latitude",
            "longitude": "longitude",
        }
    )
    df["source_file"] = "who_2025"
    df["who_row"] = df.index
    df["who_site_name"] = df["facility_name"]
    df["ss_facilities_code"] = pd.NA
    df["facility_type"] = "unknown"
    df["norm_name"] = df["facility_name"].map(normalize_name)
    df["state_code"] = df["state_code"].map(clean_code)
    df["county_code"] = df["county_code"].map(clean_code)
    df["payam_code"] = df["payam_code"].map(clean_code)
    return df


def load_ss() -> pd.DataFrame:
    df = pd.read_excel(SS_PATH, sheet_name=SS_SHEET)
    df = df.rename(
        columns={
            "Facility_Name": "facility_name",
            "State_Code": "state_code",
            "County_Code": "county_code",
            "Payam_Code ": "payam_code",
            "Type": "facility_type",
            "Facilities_Code": "ss_facilities_code",
            "Latitude": "latitude",
            "Longitude": "longitude",
        }
    )
    df["source_file"] = "ss_2023"
    df["ss_row"] = df.index
    df["who_site_name"] = pd.NA
    df["norm_name"] = df["facility_name"].map(normalize_name)
    df["state_code"] = df["state_code"].map(clean_code)
    df["county_code"] = df["county_code"].map(clean_code)
    df["payam_code"] = df["payam_code"].map(clean_code)
    df["ss_facilities_code"] = df["ss_facilities_code"].astype("Int64").astype(str).replace("<NA>", pd.NA)
    return df


def build_match_key(norm_name: str, *codes: str) -> str:
    return "|".join([norm_name, *[clean_code(c) for c in codes]])


def one_to_one_keys(left: pd.DataFrame, right: pd.DataFrame, key_col: str) -> set[str]:
    left_counts = left[key_col].value_counts()
    right_counts = right[key_col].value_counts()
    shared = set(left[key_col]) & set(right[key_col])
    return {key for key in shared if left_counts.get(key, 0) == 1 and right_counts.get(key, 0) == 1}


def append_log(
    logs: list[dict],
    *,
    match_stage: str,
    merge_status: str,
    who_row: int | None,
    ss_row: int | None,
    facility_name: str,
    match_key: str,
    notes: str = "",
) -> None:
    logs.append(
        {
            "match_stage": match_stage,
            "merge_status": merge_status,
            "who_row": who_row,
            "ss_row": ss_row,
            "facility_name": facility_name,
            "match_key": match_key,
            "notes": notes,
        }
    )


def merge_record(who_row: pd.Series | None, ss_row: pd.Series | None, merge_status: str) -> dict:
    if who_row is not None and ss_row is not None:
        source = "merged"
        lat, lon, _ = choose_coords(
            who_row["latitude"],
            who_row["longitude"],
            ss_row["latitude"],
            ss_row["longitude"],
        )
        facility_name = ss_row["facility_name"] if pd.notna(ss_row["facility_name"]) else who_row["facility_name"]
        facility_type = ss_row["facility_type"] if pd.notna(ss_row["facility_type"]) else "unknown"
        state_code = ss_row["state_code"] or who_row["state_code"]
        county_code = ss_row["county_code"] or who_row["county_code"]
        payam_code = ss_row["payam_code"] or who_row["payam_code"]
        ss_code = ss_row["ss_facilities_code"]
        who_name = who_row["who_site_name"]
    elif who_row is not None:
        source = "who_2025"
        lat = float(who_row["latitude"]) if valid_coords(who_row["latitude"], who_row["longitude"]) else None
        lon = float(who_row["longitude"]) if lat is not None else None
        facility_name = who_row["facility_name"]
        facility_type = "unknown"
        state_code = who_row["state_code"]
        county_code = who_row["county_code"]
        payam_code = who_row["payam_code"]
        ss_code = pd.NA
        who_name = who_row["who_site_name"]
    else:
        assert ss_row is not None
        source = "ss_2023"
        lat = float(ss_row["latitude"]) if valid_coords(ss_row["latitude"], ss_row["longitude"]) else None
        lon = float(ss_row["longitude"]) if lat is not None else None
        facility_name = ss_row["facility_name"]
        facility_type = ss_row["facility_type"]
        state_code = ss_row["state_code"]
        county_code = ss_row["county_code"]
        payam_code = ss_row["payam_code"]
        ss_code = ss_row["ss_facilities_code"]
        who_name = pd.NA

    return {
        "source": source,
        "facility_name": facility_name,
        "facility_type": facility_type if pd.notna(facility_type) else "unknown",
        "state_code": state_code,
        "county_code": county_code,
        "payam_code": payam_code,
        "latitude": lat,
        "longitude": lon,
        "who_site_name": who_name,
        "ss_facilities_code": ss_code,
        "merge_status": merge_status,
        "has_coordinates": lat is not None and lon is not None,
        "who_row": who_row["who_row"] if who_row is not None else pd.NA,
        "ss_row": ss_row["ss_row"] if ss_row is not None else pd.NA,
    }


def run_merge() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    who = load_who()
    ss = load_ss()

    who["key_name_payam"] = [build_match_key(n, p) for n, p in zip(who["norm_name"], who["payam_code"])]
    who["key_name_county"] = [build_match_key(n, c) for n, c in zip(who["norm_name"], who["county_code"])]
    ss["key_name_payam"] = [build_match_key(n, p) for n, p in zip(ss["norm_name"], ss["payam_code"])]
    ss["key_name_county"] = [build_match_key(n, c) for n, c in zip(ss["norm_name"], ss["county_code"])]

    who_unmatched = who.copy()
    ss_unmatched = ss.copy()
    logs: list[dict] = []
    merged_rows: list[dict] = []

    def apply_stage(
        stage_name: str,
        key_col: str,
        *,
        coord_check: bool = False,
    ) -> None:
        nonlocal who_unmatched, ss_unmatched
        keys = one_to_one_keys(who_unmatched, ss_unmatched, key_col)
        if coord_check:
            filtered: set[str] = set()
            for key in keys:
                w = who_unmatched[who_unmatched[key_col] == key].iloc[0]
                s = ss_unmatched[ss_unmatched[key_col] == key].iloc[0]
                if w["norm_name"] != s["norm_name"]:
                    continue
                if valid_coords(w["latitude"], w["longitude"]) and valid_coords(
                    s["latitude"], s["longitude"]
                ):
                    dist = haversine_m(
                        float(w["latitude"]),
                        float(w["longitude"]),
                        float(s["latitude"]),
                        float(s["longitude"]),
                    )
                    if dist <= COORD_MATCH_MAX_M:
                        filtered.add(key)
                elif w["county_code"] and w["county_code"] == s["county_code"]:
                    filtered.add(key)
            keys = filtered

        matched_who_rows: set[int] = set()
        matched_ss_rows: set[int] = set()

        for key in sorted(keys):
            w = who_unmatched[who_unmatched[key_col] == key].iloc[0]
            s = ss_unmatched[ss_unmatched[key_col] == key].iloc[0]
            merged_rows.append(merge_record(w, s, "matched"))
            append_log(
                logs,
                match_stage=stage_name,
                merge_status="matched",
                who_row=int(w["who_row"]),
                ss_row=int(s["ss_row"]),
                facility_name=str(w["facility_name"]),
                match_key=key,
            )
            matched_who_rows.add(int(w["who_row"]))
            matched_ss_rows.add(int(s["ss_row"]))

        who_unmatched = who_unmatched[~who_unmatched["who_row"].isin(matched_who_rows)].copy()
        ss_unmatched = ss_unmatched[~ss_unmatched["ss_row"].isin(matched_ss_rows)].copy()

    apply_stage("name_payam", "key_name_payam")
    apply_stage("name_county", "key_name_county")

    # Tertiary name-only matching is intentionally disabled — see health_facilities_data_quality.md.

    for _, w in who_unmatched.iterrows():
        merged_rows.append(merge_record(w, None, "who_only"))
        append_log(
            logs,
            match_stage="none",
            merge_status="who_only",
            who_row=int(w["who_row"]),
            ss_row=None,
            facility_name=str(w["facility_name"]),
            match_key="",
        )

    for _, s in ss_unmatched.iterrows():
        merged_rows.append(merge_record(None, s, "ss_only"))
        append_log(
            logs,
            match_stage="none",
            merge_status="ss_only",
            who_row=None,
            ss_row=int(s["ss_row"]),
            facility_name=str(s["facility_name"]),
            match_key="",
        )

    canonical = pd.DataFrame(merged_rows)
    canonical["_merge_seq"] = range(len(canonical))

    admin_df = pd.read_excel(SS_PATH, sheet_name="Admin_data")
    admin_ref = load_admin_reference(admin_df)

    canonical, state_audit = harmonize_state_codes(
        canonical,
        admin_ref,
        coord_max_distance_m=COORD_STATE_MAX_M,
    )

    canonical = canonical.sort_values(
        ["state_code", "county_code", "payam_code", "facility_name"],
        na_position="last",
    ).reset_index(drop=True)
    canonical.insert(0, "facility_id", [f"SSD-HF-{i:06d}" for i in range(1, len(canonical) + 1)])

    if not state_audit.empty:
        id_map = canonical[["_merge_seq", "facility_id"]]
        state_audit = state_audit.merge(id_map, on="_merge_seq", how="left")
        state_audit = state_audit.drop(columns=["_merge_seq"])

    canonical = canonical.drop(columns=["_merge_seq"])

    # Flag duplicate SS facility codes retained for traceability.
    dup_codes = canonical["ss_facilities_code"].dropna()
    dup_codes = dup_codes[dup_codes.duplicated(keep=False)]
    if not dup_codes.empty:
        canonical["ss_code_duplicate"] = canonical["ss_facilities_code"].isin(set(dup_codes))
    else:
        canonical["ss_code_duplicate"] = False

    invalid_states = canonical[~canonical["state_code"].isin([f"SS{i:02d}" for i in range(11)])]

    summary = {
        "who_source_rows": len(who),
        "ss_source_rows": len(ss),
        "canonical_rows": len(canonical),
        "merge_status_counts": canonical["merge_status"].value_counts().astype(int).to_dict(),
        "source_counts": canonical["source"].value_counts().astype(int).to_dict(),
        "facility_type_counts": canonical["facility_type"].value_counts().astype(int).to_dict(),
        "with_coordinates": int(canonical["has_coordinates"].sum()),
        "without_coordinates": int((~canonical["has_coordinates"]).sum()),
        "without_coordinates_policy": (
            "Retained in both PostgreSQL and Neo4j for fair comparison; "
            "only has_coordinates=true rows receive graph connector edges in Task 1."
        ),
        "duplicate_ss_facilities_code_rows": int(canonical["ss_code_duplicate"].sum()),
        "match_stage_counts": pd.Series([log["match_stage"] for log in logs if log["merge_status"] == "matched"])
        .value_counts()
        .astype(int)
        .to_dict(),
        "tertiary_name_matching": "disabled_by_design",
        "state_code_method_counts": canonical["state_code_method"].value_counts().astype(int).to_dict(),
        "state_code_corrections": int((canonical["state_code"] != canonical["state_code_original"]).sum()),
        "invalid_state_codes_remaining": int(len(invalid_states)),
        "state_harmonization_audit_rows": int(len(state_audit)),
    }

    log_df = pd.DataFrame(logs)
    return canonical, log_df, state_audit, summary


def write_outputs(
    canonical: pd.DataFrame,
    log_df: pd.DataFrame,
    state_audit: pd.DataFrame,
    summary: dict,
) -> None:
    ensure_project_dirs()
    out_dir = PROCESSED_HEALTH_FACILITIES
    out_dir.mkdir(parents=True, exist_ok=True)

    export_cols = [
        "facility_id",
        "source",
        "facility_name",
        "facility_type",
        "state_code",
        "state_name",
        "state_code_original",
        "state_code_method",
        "county_code",
        "payam_code",
        "latitude",
        "longitude",
        "has_coordinates",
        "who_site_name",
        "ss_facilities_code",
        "ss_code_duplicate",
        "merge_status",
        "who_row",
        "ss_row",
    ]
    canonical[export_cols].to_csv(out_dir / "health_facilities_canonical.csv", index=False)

    geometry = [
        Point(row.longitude, row.latitude) if row.has_coordinates else None
        for row in canonical.itertuples()
    ]
    gdf = gpd.GeoDataFrame(canonical[export_cols], geometry=geometry, crs="EPSG:4326")
    gdf.to_file(out_dir / "health_facilities_canonical.gpkg", driver="GPKG")

    log_df.to_csv(out_dir / "health_facilities_merge_log.csv", index=False)
    state_audit.to_csv(out_dir / "health_facilities_state_harmonization_log.csv", index=False)
    (out_dir / "health_facilities_merge_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"Canonical facilities: {len(canonical)} rows")
    print(f"  With coordinates: {summary['with_coordinates']}")
    print(f"  Merge status: {summary['merge_status_counts']}")
    print(f"Outputs written to {out_dir}")


def main() -> None:
    if not WHO_PATH.exists() or not SS_PATH.exists():
        raise FileNotFoundError(
            "Health facility source files missing. Run: python scripts/download_datasets.py"
        )
    canonical, log_df, state_audit, summary = run_merge()
    write_outputs(canonical, log_df, state_audit, summary)


if __name__ == "__main__":
    main()
