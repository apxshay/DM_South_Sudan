"""Shared project paths and directory bootstrap."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED_ROADS_HOTOSM = PROCESSED / "roads_hotosm"
PROCESSED_HEALTH_FACILITIES = PROCESSED / "health_facilities"
PROCESSED_NETWORK = PROCESSED / "network"
ROADS_HOTOSM_FILTERED = RAW / "roads_hotosm" / "filtered" / "roads_lines_filtered.gpkg"

DATA_DIRS = [
    RAW / "roads" / "original",
    RAW / "roads_hotosm" / "original",
    RAW / "roads_hotosm" / "filtered",
    RAW / "health_facilities" / "original",
    RAW / "idp" / "original",
    RAW / "displacement_sites" / "original",
    PROCESSED,
    PROCESSED_ROADS_HOTOSM,
    PROCESSED_HEALTH_FACILITIES,
    PROCESSED_NETWORK,
    ROOT / "data" / "interim" / "osmnx",
    ROOT / "data" / "interim",
    ROOT / "output",
]


def ensure_project_dirs() -> None:
    for path in DATA_DIRS:
        path.mkdir(parents=True, exist_ok=True)
