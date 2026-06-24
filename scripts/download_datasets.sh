#!/usr/bin/env bash
# Re-download raw datasets from HDX into data/raw/.
# Usage: ./scripts/download_datasets.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$ROOT/data/raw"
UA="Mozilla/5.0 (compatible; data-management-project/1.0)"
PYTHON="$ROOT/data_env/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: Virtual environment not found. Run ./scripts/setup.sh first." >&2
  exit 1
fi

mkdir -p "$BASE/roads/original" "$BASE/roads_hotosm/original" "$BASE/roads_hotosm/filtered" \
  "$BASE/health_facilities/original" "$BASE/idp/original" "$BASE/displacement_sites/original"

echo "Downloading roads network..."
curl -fsSL -A "$UA" -o "$BASE/roads/original/ssd_road_network.zip" \
  "https://data.humdata.org/dataset/b2fabd55-947b-416d-87d5-8178d96d72c8/resource/f67431a1-355c-4980-8f85-36214d8fe762/download/ssd_road_network.zip"
unzip -o "$BASE/roads/original/ssd_road_network.zip" -d "$BASE/roads"

echo "Downloading HOT OSM roads (large file, may take several minutes)..."
curl -fsSL -A "$UA" -o "$BASE/roads_hotosm/original/hotosm_ssd_roads_osm_shp.zip" \
  "https://production-raw-data-api.s3.amazonaws.com/ISO3/SSD/roads/hotosm_ssd_roads_osm_shp.zip"
unzip -o "$BASE/roads_hotosm/original/hotosm_ssd_roads_osm_shp.zip" -d "$BASE/roads_hotosm"

echo "Filtering HOT OSM roads to primary/secondary/tertiary/unclassified..."
"$PYTHON" "$ROOT/scripts/explore_datasets.py"

echo "Downloading health facilities..."
curl -fsSL -A "$UA" -o "$BASE/health_facilities/original/who-master-facility-list_april2025.xlsx" \
  "https://data.humdata.org/dataset/b60d95d8-c746-4046-93f1-b2dbcb976e29/resource/69256375-d453-4697-b5ac-fbdc8a351b92/download/who-master-facility-list_april2025.xlsx"
curl -fsSL -A "$UA" -o "$BASE/health_facilities/original/ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx" \
  "https://data.humdata.org/dataset/b60d95d8-c746-4046-93f1-b2dbcb976e29/resource/dc7413b0-f68d-4c1f-b15e-cdd433a93d3d/download/ss_final_master_list_of-hfs-_codes_2023_20240615.xlsx"

echo "Downloading IDP data..."
curl -fsSL -A "$UA" -o "$BASE/idp/original/internal-displacements-new-displacements-idps_ssd.csv" \
  "https://data.humdata.org/dataset/d24a21b4-7fa3-4716-85b3-a5e024bf7385/resource/38cd1457-0871-46a5-b3c3-f16bf671f993/download/internal-displacements-new-displacements-idps_ssd.csv"
curl -fsSL -A "$UA" -o "$BASE/idp/original/internal-displacements-new-displacements-associated-with-disasters_ssd.csv" \
  "https://data.humdata.org/dataset/d24a21b4-7fa3-4716-85b3-a5e024bf7385/resource/81eba499-c364-4e44-a078-7a4018aaf6d1/download/internal-displacements-new-displacements-associated-with-disasters_ssd.csv"

echo "Downloading IOM DTM displacement site assessments..."
curl -fsSL -A "$UA" -o "$BASE/displacement_sites/original/hdx_ssd-dtm-mobility-tracking-r11-site-assessment-dataset.xlsx" \
  "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/cb439fdf-23b4-4116-9ff2-a28d6c341e0f/download/hdx_ssd-dtm-mobility-tracking-r11-site-assessment-dataset.xlsx"
curl -fsSL -A "$UA" -o "$BASE/displacement_sites/original/hdx_iom_dtm_ssd_mt10_sa.xlsx" \
  "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/6e5f4d02-e58c-4a10-87b6-927c01774f27/download/hdx_iom_dtm_ssd_mt10_sa.xlsx"
curl -fsSL -A "$UA" -o "$BASE/displacement_sites/original/dtm-south-sudan-site-assessment-round-8.xlsx" \
  "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/0f0d6424-56e6-41fb-9ded-93e00c914a7b/download/dtm-south-sudan-site-assessment-round-8.xlsx"
curl -fsSL -A "$UA" -o "$BASE/displacement_sites/original/dtm-south-sudan-site-assessment-round-6.xlsx" \
  "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/aefba509-0751-4bad-9e76-ba95cbdcf8ea/download/dtm-south-sudan-site-assessment-round-6.xlsx"
curl -fsSL -A "$UA" -o "$BASE/displacement_sites/original/dtm-south-sudan-site-assessment-round-5.xlsx" \
  "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/fea0a3cd-e16c-4fa7-9b66-7580d0fa2cdc/download/dtm-south-sudan-site-assessment-round-5.xlsx"
curl -fsSL -A "$UA" -o "$BASE/displacement_sites/original/dtm-south-sudan-site-assessment-round-4.xlsx" \
  "https://data.humdata.org/dataset/b93c9a24-2399-4b57-a886-99e98394e265/resource/8134f6e2-1218-41b3-8290-9aa3256bb21f/download/dtm-south-sudan-site-assessment-round-4.xlsx"

echo "Done."
