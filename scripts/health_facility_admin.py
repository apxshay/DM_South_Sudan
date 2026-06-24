"""Admin hierarchy helpers for health facility enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from math import radians, sin, cos, sqrt, atan2

import pandas as pd

VALID_STATE_CODES = tuple(f"SS{i:02d}" for i in range(11))


@dataclass(frozen=True)
class AdminReference:
    payam_to_state: dict[str, str]
    county_to_state: dict[str, str]
    payam_to_state_name: dict[str, str]
    county_to_state_name: dict[str, str]
    state_code_to_name: dict[str, str]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * radius_m * atan2(sqrt(a), sqrt(1 - a))


def load_admin_reference(admin_df: pd.DataFrame) -> AdminReference:
    admin = admin_df.copy()
    admin["Payam_Code"] = admin["Payam_Code"].astype(str).str.strip()
    admin["County-Code"] = admin["County-Code"].astype(str).str.strip()
    admin["State_Code"] = admin["State_Code"].astype(str).str.strip()

    payam_to_state = dict(zip(admin["Payam_Code"], admin["State_Code"]))
    county_to_state = dict(zip(admin["County-Code"], admin["State_Code"]))
    payam_to_state_name = dict(zip(admin["Payam_Code"], admin["State"]))
    county_to_state_name = dict(zip(admin["County-Code"], admin["State"]))
    state_code_to_name = (
        admin.drop_duplicates("State_Code")
        .set_index("State_Code")["State"]
        .astype(str)
        .to_dict()
    )
    return AdminReference(
        payam_to_state=payam_to_state,
        county_to_state=county_to_state,
        payam_to_state_name=payam_to_state_name,
        county_to_state_name=county_to_state_name,
        state_code_to_name=state_code_to_name,
    )


def build_payam_centroids(facilities: pd.DataFrame) -> pd.DataFrame:
    """Mean coordinate per payam from georeferenced facilities."""
    georef = facilities[facilities["has_coordinates"]].copy()
    georef = georef[georef["payam_code"].astype(str).str.strip().ne("")]
    if georef.empty:
        return pd.DataFrame(columns=["payam_code", "centroid_lat", "centroid_lon", "facility_count"])

    grouped = (
        georef.groupby("payam_code", as_index=False)
        .agg(
            centroid_lat=("latitude", "mean"),
            centroid_lon=("longitude", "mean"),
            facility_count=("facility_name", "count"),
        )
    )
    return grouped


def infer_state_from_coordinates(
    lat: float,
    lon: float,
    payam_centroids: pd.DataFrame,
    admin: AdminReference,
    *,
    max_distance_m: float,
) -> tuple[str | None, str | None, float | None]:
    if payam_centroids.empty:
        return None, None, None

    best_payam: str | None = None
    best_dist: float | None = None
    for row in payam_centroids.itertuples():
        dist = haversine_m(lat, lon, row.centroid_lat, row.centroid_lon)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_payam = row.payam_code

    if best_payam is None or best_dist is None or best_dist > max_distance_m:
        return None, None, best_dist

    state_code = admin.payam_to_state.get(best_payam)
    state_name = admin.payam_to_state_name.get(best_payam)
    return state_code, state_name, best_dist


def harmonize_state_codes(
    facilities: pd.DataFrame,
    admin: AdminReference,
    *,
    coord_max_distance_m: float = 30_000.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return facilities with harmonized state codes and an audit log."""
    df = facilities.copy()
    payam_centroids = build_payam_centroids(df)
    audits: list[dict] = []

    for idx, row in df.iterrows():
        original = str(row.get("state_code", "") or "").strip()
        payam = str(row.get("payam_code", "") or "").strip()
        county = str(row.get("county_code", "") or "").strip()

        resolved_state = ""
        resolved_name = ""
        method = "source_record"
        notes = ""

        if payam and payam in admin.payam_to_state:
            resolved_state = admin.payam_to_state[payam]
            resolved_name = admin.payam_to_state_name.get(payam, "")
            method = "payam_lookup"
        elif county and county in admin.county_to_state:
            resolved_state = admin.county_to_state[county]
            resolved_name = admin.county_to_state_name.get(county, "")
            method = "county_lookup"
        elif row.get("has_coordinates") and pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
            state_code, state_name, dist = infer_state_from_coordinates(
                float(row["latitude"]),
                float(row["longitude"]),
                payam_centroids,
                admin,
                max_distance_m=coord_max_distance_m,
            )
            if state_code:
                resolved_state = state_code
                resolved_name = state_name or admin.state_code_to_name.get(state_code, "")
                method = "coord_nearest_payam"
                notes = f"nearest_payam_centroid_{dist:.0f}m"
        elif original in VALID_STATE_CODES:
            resolved_state = original
            resolved_name = admin.state_code_to_name.get(original, "")
            method = "source_record"

        if not resolved_state:
            resolved_state = original
            resolved_name = admin.state_code_to_name.get(original, "")
            method = "unresolved"

        changed = resolved_state != original
        if payam and original and resolved_state and original in VALID_STATE_CODES and changed:
            notes = (notes + "; " if notes else "") + "source_state_overridden_by_admin_hierarchy"

        df.at[idx, "state_code_original"] = original
        df.at[idx, "state_code"] = resolved_state
        df.at[idx, "state_name"] = resolved_name
        df.at[idx, "state_code_method"] = method

        if changed:
            audits.append(
                {
                    "_merge_seq": row.get("_merge_seq", idx),
                    "facility_name": row["facility_name"],
                    "state_code_original": original,
                    "state_code": resolved_state,
                    "state_code_method": method,
                    "payam_code": payam,
                    "county_code": county,
                    "notes": notes,
                }
            )

    audit_df = pd.DataFrame(audits)
    return df, audit_df
