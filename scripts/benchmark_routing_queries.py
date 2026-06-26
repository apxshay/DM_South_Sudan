#!/usr/bin/env python3
"""Benchmark Q1–Q3 routing queries across three implementation tracks.

Tracks:
  - PG-CTE      — hop-bounded recursive CTE (secondary baseline)
  - PG-pgRouting — pgr_dijkstra / pgr_dijkstraCost (primary PostgreSQL)
  - Neo4j-GDS   — GDS Dijkstra (primary graph)

Run on Windows amd64 with Docker containers healthy. Example:
  conda activate dm-south-sudan
  python scripts/benchmark_routing_queries.py --runs 5 --warmup 1
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERIES = ROOT / "src" / "queries"
PARAMS_FILE = QUERIES / "_benchmark_params.yaml"

POSTGIS = "dm-south-sudan-postgis"
NEO4J = "dm-south-sudan-neo4j"
PG_USER = "dm_ssd"
PG_DB = "dm_south_sudan"
NEO4J_USER = "neo4j"
NEO4J_PASS = "dm_ssd_dev"


@dataclass(frozen=True)
class QuerySpec:
    query_id: str
    track: str
    path: Path
    engine: str  # postgresql | neo4j
    psql_vars: dict[str, str] | None = None
    neo4j_params: dict[str, str] | None = None


def load_params() -> dict:
    text = PARAMS_FILE.read_text(encoding="utf-8")
    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in text.splitlines():
        section_match = re.match(r"^(q\d+):\s*(#.*)?$", line)
        if section_match:
            current = section_match.group(1)
            sections[current] = {}
            continue
        if current and ":" in line and not line.lstrip().startswith("#"):
            key, value = line.split(":", 1)
            sections[current][key.strip()] = value.strip().split("#", 1)[0].strip()
    sections["q3"]["max_distance_m"] = int(sections["q3"]["max_distance_m"])
    return sections


def build_specs(params: dict) -> list[QuerySpec]:
    q1 = params["q1"]
    q2 = params["q2"]
    q3 = params["q3"]
    return [
        QuerySpec(
            "Q1",
            "PG-CTE",
            QUERIES / "postgresql" / "q1_nearest_hospital.sql",
            "postgresql",
            {"camp_id": q1["camp_id"], "max_hops": "30"},
        ),
        QuerySpec(
            "Q1",
            "PG-pgRouting",
            QUERIES / "postgresql" / "q1_nearest_hospital_pgrouting.sql",
            "postgresql",
            {"camp_id": q1["camp_id"]},
        ),
        QuerySpec(
            "Q1",
            "Neo4j-GDS",
            QUERIES / "neo4j" / "q1_nearest_hospital.cypher",
            "neo4j",
            neo4j_params={"camp_id": q1["camp_id"]},
        ),
        QuerySpec(
            "Q2",
            "PG-CTE",
            QUERIES / "postgresql" / "q2_state_camps_to_hospital.sql",
            "postgresql",
            {
                "state_code": q2["state_code"],
                "target_hospital_id": q2["target_hospital_id"],
                "max_hops": "30",
            },
        ),
        QuerySpec(
            "Q2",
            "PG-pgRouting",
            QUERIES / "postgresql" / "q2_state_camps_to_hospital_pgrouting.sql",
            "postgresql",
            {
                "state_code": q2["state_code"],
                "target_hospital_id": q2["target_hospital_id"],
            },
        ),
        QuerySpec(
            "Q2",
            "Neo4j-GDS",
            QUERIES / "neo4j" / "q2_state_camps_to_hospital.cypher",
            "neo4j",
            neo4j_params={
                "state_code": q2["state_code"],
                "target_facility_id": q2["target_hospital_id"],
            },
        ),
        QuerySpec(
            "Q3",
            "PG-CTE",
            QUERIES / "postgresql" / "q3_hub_reachability.sql",
            "postgresql",
            {
                "hub_id": q3["hub_id"],
                "max_distance_m": str(q3["max_distance_m"]),
                "max_hops": "50",
            },
        ),
        QuerySpec(
            "Q3",
            "PG-pgRouting",
            QUERIES / "postgresql" / "q3_hub_reachability_pgrouting.sql",
            "postgresql",
            {
                "hub_id": q3["hub_id"],
                "max_distance_m": str(q3["max_distance_m"]),
            },
        ),
        QuerySpec(
            "Q3",
            "Neo4j-GDS",
            QUERIES / "neo4j" / "q3_hub_reachability.cypher",
            "neo4j",
            neo4j_params={
                "hub_id": q3["hub_id"],
                "max_distance_m": str(q3["max_distance_m"]),
            },
        ),
    ]


def run_postgresql(spec: QuerySpec) -> subprocess.CompletedProcess[str]:
    cmd = [
        "docker",
        "exec",
        "-i",
        POSTGIS,
        "psql",
        "-U",
        PG_USER,
        "-d",
        PG_DB,
        "-q",
        "-t",
    ]
    for key, value in (spec.psql_vars or {}).items():
        cmd.extend(["-v", f"{key}={value}"])
    return subprocess.run(
        cmd,
        input=spec.path.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def run_neo4j(spec: QuerySpec) -> subprocess.CompletedProcess[str]:
    cmd = [
        "docker",
        "exec",
        "-i",
        NEO4J,
        "cypher-shell",
        "-u",
        NEO4J_USER,
        "-p",
        NEO4J_PASS,
    ]
    for key, value in (spec.neo4j_params or {}).items():
        if value.isdigit():
            cmd.extend(["--param", f"{key} => {value}"])
        else:
            cmd.extend(["--param", f"{key} => '{value}'"])
    return subprocess.run(
        cmd,
        input=spec.path.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def execute(spec: QuerySpec) -> tuple[float, str | None]:
    start = time.perf_counter()
    if spec.engine == "postgresql":
        result = run_postgresql(spec)
    else:
        result = run_neo4j(spec)
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        return elapsed, err or f"exit code {result.returncode}"
    return elapsed, None


def benchmark_spec(spec: QuerySpec, warmup: int, runs: int) -> dict:
    is_slow_q2_cte = spec.track == "PG-CTE" and spec.query_id == "Q2"
    effective_warmup = 0 if is_slow_q2_cte else warmup
    effective_runs = 1 if is_slow_q2_cte else runs

    for _ in range(effective_warmup):
        _, err = execute(spec)
        if err:
            return {
                "query_id": spec.query_id,
                "track": spec.track,
                "file": str(spec.path.relative_to(ROOT)),
                "status": "error",
                "error": err,
            }

    timings: list[float] = []
    for _ in range(effective_runs):
        elapsed, err = execute(spec)
        if err:
            return {
                "query_id": spec.query_id,
                "track": spec.track,
                "file": str(spec.path.relative_to(ROOT)),
                "status": "error",
                "error": err,
            }
        timings.append(elapsed)

    return {
        "query_id": spec.query_id,
        "track": spec.track,
        "file": str(spec.path.relative_to(ROOT)),
        "status": "ok",
        "runs": effective_runs,
        "timings_s": [round(t, 3) for t in timings],
        "median_s": round(statistics.median(timings), 3),
        "mean_s": round(statistics.mean(timings), 3),
    }


def print_summary(results: list[dict]) -> None:
    print("\nRouting benchmark summary (median latency, seconds)")
    print("-" * 72)
    print(f"{'Query':<6} {'Track':<14} {'Median (s)':<12} {'Status'}")
    print("-" * 72)
    for row in results:
        median = row.get("median_s", "-")
        status = row.get("status", "?")
        print(f"{row['query_id']:<6} {row['track']:<14} {str(median):<12} {status}")
    print("-" * 72)
    print("Primary comparison: PG-pgRouting vs Neo4j-GDS")
    print("Secondary baseline: PG-CTE")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3, help="Timed runs per query")
    parser.add_argument("--warmup", type=int, default=1, help="Warm-up runs per query")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "output" / "routing_benchmark_results.json",
        help="JSON output path",
    )
    parser.add_argument(
        "--query",
        choices=["Q1", "Q2", "Q3"],
        help="Run a single query id only",
    )
    parser.add_argument(
        "--track",
        choices=["PG-CTE", "PG-pgRouting", "Neo4j-GDS"],
        help="Run a single track only",
    )
    parser.add_argument(
        "--skip-slow-cte",
        action="store_true",
        help="Skip Q2 PG-CTE (15× recursive search; very slow)",
    )
    args = parser.parse_args()

    params = load_params()
    specs = build_specs(params)
    if args.query:
        specs = [s for s in specs if s.query_id == args.query]
    if args.track:
        specs = [s for s in specs if s.track == args.track]
    if args.skip_slow_cte:
        specs = [
            s
            for s in specs
            if not (s.track == "PG-CTE" and s.query_id in ("Q2", "Q3"))
        ]

    results = [benchmark_spec(spec, args.warmup, args.runs) for spec in specs]
    if args.skip_slow_cte:
        for query_id in ("Q2", "Q3"):
            results.append(
                {
                    "query_id": query_id,
                    "track": "PG-CTE",
                    "file": str(
                        (
                            QUERIES
                            / "postgresql"
                            / (
                                "q2_state_camps_to_hospital.sql"
                                if query_id == "Q2"
                                else "q3_hub_reachability.sql"
                            )
                        ).relative_to(ROOT)
                    ),
                    "status": "skipped_slow",
                    "note": "Recursive CTE exceeds practical runtime at national scale; use PG-pgRouting for fair comparison.",
                }
            )
    payload = {
        "platform_note": "Run on Windows amd64 for fair PostGIS vs Neo4j timings.",
        "warmup": args.warmup,
        "runs": args.runs,
        "params_file": str(PARAMS_FILE.relative_to(ROOT)),
        "results": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print_summary(results)
    print(f"\nWrote {args.output}")
    return 0 if all(r["status"] in ("ok", "skipped_slow") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
