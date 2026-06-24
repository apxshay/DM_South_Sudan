#!/usr/bin/env python3
"""Cross-platform HDX dataset downloader (Windows, macOS, Linux)."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from project_paths import RAW, ensure_project_dirs  # noqa: E402

USER_AGENT = "Mozilla/5.0 (compatible; data-management-project/1.0)"
TIMEOUT = 600

DOWNLOADS: list[tuple[str, Path]] = [
    (
        "https://data.humdata.org/dataset/b2fabd55-947b-416d-87d5-8178d96d72c8/resource/f67431a1-355c-4980-8f85-36214d8fe762/download/ssd_road_network.zip",
        RAW / "roads" / "original" / "ssd_road_network.zip",
    ),
    (
        "https://production-raw-data-api.s3.amazonaws.com/ISO3/SSD/roads/hotosm_ssd_roads_osm_shp.zip",
        RAW / "roads_hotosm" / "original" / "hotosm_ssd_roads_osm_shp.zip",
    ),
    (
        "https://data.humdata.org/dataset/b60d95d8-c746-4046-93f1-b2dbcb976e29/resource/69256375-d453-4697-b5ac-fbdc8a351b92/download/who-master-facility-list_april2025.xlsx",
        RAW / "health_facilities" / "original" / "who-master-facility-list_april2025.xlsx",
    ),
    (
        "https://data.humdata.org/dataset/b60d95d8-c746-4046-93f1-b2dbcb976e29/resource/dc7413b0-f68d-4c1f-b15e-cdd433a93d3d/download/ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx",
        RAW / "health_facilities" / "original" / "ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx",
    ),
    (
        "https://data.humdata.org/dataset/d24a21b4-7fa3-4716-85b3-a5e024bf7385/resource/38cd1457-0871-46a5-b3c3-f16bf671f993/download/internal-displacements-new-displacements-idps_ssd.csv",
        RAW / "idp" / "original" / "internal-displacements-new-displacements-idps_ssd.csv",
    ),
    (
        "https://data.humdata.org/dataset/d24a21b4-7fa3-4716-85b3-a5e024bf7385/resource/81eba499-c364-4e44-a078-7a4018aaf6d1/download/internal-displacements-new-displacements-associated-with-disasters_ssd.csv",
        RAW / "idp" / "original" / "internal-displacements-new-displacements-associated-with-disasters_ssd.csv",
    ),
    (
        "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/cb439fdf-23b4-4116-9ff2-a28d6c341e0f/download/hdx_ssd-dtm-mobility-tracking-r11-site-assessment-dataset.xlsx",
        RAW / "displacement_sites" / "original" / "hdx_ssd-dtm-mobility-tracking-r11-site-assessment-dataset.xlsx",
    ),
    (
        "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/6e5f4d02-e58c-4a10-87b6-927c01774f27/download/hdx_iom_dtm_ssd_mt10_sa.xlsx",
        RAW / "displacement_sites" / "original" / "hdx_iom_dtm_ssd_mt10_sa.xlsx",
    ),
    (
        "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/0f0d6424-56e6-41fb-9ded-93e00c914a7b/download/dtm-south-sudan-site-assessment-round-8.xlsx",
        RAW / "displacement_sites" / "original" / "dtm-south-sudan-site-assessment-round-8.xlsx",
    ),
    (
        "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/aefba509-0751-4bad-9e76-ba95cbdcf8ea/download/dtm-south-sudan-site-assessment-round-6.xlsx",
        RAW / "displacement_sites" / "original" / "dtm-south-sudan-site-assessment-round-6.xlsx",
    ),
    (
        "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/fea0a3cd-e16c-4fa7-9b66-7580d0fa2cdc/download/dtm-south-sudan-site-assessment-round-5.xlsx",
        RAW / "displacement_sites" / "original" / "dtm-south-sudan-site-assessment-round-5.xlsx",
    ),
    (
        "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/8134f6e2-1218-41b3-8290-9aa3256bb21f/download/dtm-south-sudan-site-assessment-round-4.xlsx",
        RAW / "displacement_sites" / "original" / "dtm-south-sudan-site-assessment-round-4.xlsx",
    ),
]

ZIP_EXTRACTS: list[tuple[Path, Path]] = [
    (RAW / "roads" / "original" / "ssd_road_network.zip", RAW / "roads"),
    (RAW / "roads_hotosm" / "original" / "hotosm_ssd_roads_osm_shp.zip", RAW / "roads_hotosm"),
]


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {dest.name} ...")
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT, stream=True)
    response.raise_for_status()
    with dest.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                handle.write(chunk)
    print(f"  Saved to {dest}")


def extract_zip(zip_path: Path, dest_dir: Path) -> None:
    print(f"Extracting {zip_path.name} ...")
    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(dest_dir)
    print(f"  Extracted to {dest_dir}")


def run_filter_step() -> None:
    print("Filtering HOT OSM roads to primary/secondary/tertiary/unclassified ...")
    import explore_datasets

    explore_datasets.main()


def main() -> int:
    ensure_project_dirs()

    for url, dest in DOWNLOADS:
        try:
            download_file(url, dest)
        except requests.RequestException as exc:
            print(f"ERROR downloading {dest.name}: {exc}", file=sys.stderr)
            return 1

    for zip_path, dest_dir in ZIP_EXTRACTS:
        try:
            extract_zip(zip_path, dest_dir)
        except (zipfile.BadZipFile, OSError) as exc:
            print(f"ERROR extracting {zip_path.name}: {exc}", file=sys.stderr)
            return 1

    try:
        run_filter_step()
    except Exception as exc:
        print(f"ERROR during HOT OSM filter/profile step: {exc}", file=sys.stderr)
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
