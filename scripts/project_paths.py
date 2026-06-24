"""Shared project paths and directory bootstrap."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

DATA_DIRS = [
    RAW / "roads" / "original",
    RAW / "roads_hotosm" / "original",
    RAW / "roads_hotosm" / "filtered",
    RAW / "health_facilities" / "original",
    RAW / "idp" / "original",
    RAW / "displacement_sites" / "original",
    ROOT / "data" / "processed",
    ROOT / "data" / "interim",
    ROOT / "output",
]


def ensure_project_dirs() -> None:
    for path in DATA_DIRS:
        path.mkdir(parents=True, exist_ok=True)
