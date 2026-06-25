#!/usr/bin/env python3
"""Build admin dimension tables from SS 2023 Admin_data sheet.

Outputs under data/processed/admin/:
  - admin_states.csv
  - admin_counties.csv
  - admin_payams.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import PROCESSED_ADMIN, RAW, ensure_project_dirs  # noqa: E402

SS_PATH = (
    RAW
    / "health_facilities"
    / "original"
    / "ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx"
)


def clean_code(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_dimensions(admin_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    admin = admin_df.copy()
    admin["State_Code"] = admin["State_Code"].map(clean_code)
    admin["County-Code"] = admin["County-Code"].map(clean_code)
    admin["Payam_Code"] = admin["Payam_Code"].map(clean_code)
    admin["State"] = admin["State"].astype(str).str.strip()
    admin["County"] = admin["County"].astype(str).str.strip()
    admin["Payam"] = admin["Payam"].astype(str).str.strip()

    states = (
        admin[["State_Code", "State"]]
        .drop_duplicates("State_Code")
        .rename(columns={"State_Code": "state_code", "State": "state_name"})
        .sort_values("state_code")
    )

    counties = (
        admin[["County-Code", "State_Code", "County"]]
        .drop_duplicates("County-Code")
        .rename(
            columns={
                "County-Code": "county_code",
                "State_Code": "state_code",
                "County": "county_name",
            }
        )
        .sort_values(["state_code", "county_code"])
    )

    payams = (
        admin[["Payam_Code", "County-Code", "State_Code", "Payam"]]
        .drop_duplicates("Payam_Code")
        .rename(
            columns={
                "Payam_Code": "payam_code",
                "County-Code": "county_code",
                "State_Code": "state_code",
                "Payam": "payam_name",
            }
        )
        .sort_values(["state_code", "county_code", "payam_code"])
    )

    return states, counties, payams


def main() -> int:
    ensure_project_dirs()
    PROCESSED_ADMIN.mkdir(parents=True, exist_ok=True)

    if not SS_PATH.exists():
        print(f"ERROR: SS 2023 file not found: {SS_PATH}", file=sys.stderr)
        return 1

    admin_df = pd.read_excel(SS_PATH, sheet_name="Admin_data")
    states, counties, payams = build_dimensions(admin_df)

    states_path = PROCESSED_ADMIN / "admin_states.csv"
    counties_path = PROCESSED_ADMIN / "admin_counties.csv"
    payams_path = PROCESSED_ADMIN / "admin_payams.csv"

    states.to_csv(states_path, index=False)
    counties.to_csv(counties_path, index=False)
    payams.to_csv(payams_path, index=False)

    print("Admin dimension tables written:")
    print(f"  {states_path} ({len(states)} states)")
    print(f"  {counties_path} ({len(counties)} counties)")
    print(f"  {payams_path} ({len(payams)} payams)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
