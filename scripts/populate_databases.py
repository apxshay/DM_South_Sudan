#!/usr/bin/env python3
"""Populate PostgreSQL/PostGIS and Neo4j from Phase 2 processed datasets."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-only", action="store_true")
    parser.add_argument("--neo4j-only", action="store_true")
    parser.add_argument("--reset", action="store_true", help="Drop/recreate PostgreSQL schema; clear Neo4j graph")
    args = parser.parse_args()

    py = sys.executable
    status = 0

    if not args.neo4j_only:
        pg_cmd = [py, "scripts/load_postgresql.py"]
        if args.reset:
            pg_cmd.append("--reset")
        status |= run(pg_cmd)

    if not args.postgres_only:
        neo_cmd = [py, "scripts/load_neo4j.py"]
        if args.reset:
            neo_cmd.append("--reset")
        status |= run(neo_cmd)

    return status


if __name__ == "__main__":
    raise SystemExit(main())
