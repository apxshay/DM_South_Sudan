#!/usr/bin/env bash
# Run the full data pipeline (Phase 1 + Phase 2 completed steps) on macOS/Linux.
# Safe to re-run: scripts cache raw downloads and processed outputs locally.
#
# Usage:
#   ./scripts/bootstrap.sh                 # setup check + download + all steps
#   ./scripts/bootstrap.sh --skip-download # reuse existing data/raw/
#   ./scripts/bootstrap.sh --from merge    # run merge_health_facilities only
#
# Prerequisites: ./scripts/setup_conda.sh  (recommended)
#             or ./scripts/setup.sh       (venv; road topology needs osmium-tool)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKIP_DOWNLOAD=0
FROM_STEP="all"

usage() {
  cat <<EOF
Usage: ./scripts/bootstrap.sh [OPTIONS]

Options:
  --skip-download   Skip HDX raw dataset download (use existing data/raw/)
  --from STEP       Start at STEP: explore | validate | roads | topology | merge | network
  -h, --help        Show this help

Requires a configured environment:
  ./scripts/setup_conda.sh   (recommended on macOS/Linux)
  ./scripts/setup.sh         (venv fallback)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-download) SKIP_DOWNLOAD=1; shift ;;
    --from)
      FROM_STEP="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

PYTHON="$("$ROOT/scripts/resolve_python.sh")" || {
  echo "ERROR: Python not found. Run ./scripts/setup_conda.sh or ./scripts/setup.sh first." >&2
  exit 1
}

run_step() {
  local name="$1"
  shift
  echo ""
  echo "==> $name"
  # shellcheck disable=SC2086
  $PYTHON "$@"
}

should_run() {
  local step="$1"
  case "$FROM_STEP" in
    all) return 0 ;;
    explore)
      [[ "$step" =~ ^(explore|validate|roads|topology|merge|network)$ ]]
      ;;
    validate)
      [[ "$step" =~ ^(validate|roads|topology|merge|network)$ ]]
      ;;
    roads)
      [[ "$step" =~ ^(roads|topology|merge|network)$ ]]
      ;;
    topology)
      [[ "$step" =~ ^(topology|merge|network)$ ]]
      ;;
    merge)
      [[ "$step" =~ ^(merge|network)$ ]]
      ;;
    network)
      [[ "$step" == "network" ]]
      ;;
    *)
      echo "Unknown --from step: $FROM_STEP" >&2
      exit 1
      ;;
  esac
}

echo "Using Python: $PYTHON"
run_step "Creating directories" "$ROOT/scripts/create_dirs.py"

if [[ "$SKIP_DOWNLOAD" -eq 0 ]] && should_run explore; then
  run_step "Downloading raw datasets (HDX)" "$ROOT/scripts/download_datasets.py"
elif [[ "$SKIP_DOWNLOAD" -eq 1 ]]; then
  echo ""
  echo "==> Skipping download (--skip-download)"
fi

if should_run explore; then
  run_step "Phase 1 profiling" "$ROOT/scripts/explore_datasets.py"
fi

if should_run validate; then
  run_step "Phase 1 validation map" "$ROOT/scripts/visualize_data_validation.py"
fi

if should_run roads; then
  run_step "Road network topology (OSMnx)" "$ROOT/scripts/build_road_network_topology.py"
fi

if should_run topology; then
  run_step "Road topology validation map" "$ROOT/scripts/visualize_road_topology.py"
fi

if should_run merge; then
  run_step "Phase 2 - health facility merge" "$ROOT/scripts/merge_health_facilities.py"
fi

if should_run network; then
  run_step "Phase 2 - network integration" "$ROOT/scripts/integrate_network.py"
  run_step "Augmented network validation map" "$ROOT/scripts/visualize_augmented_network.py"
  run_step "Phase 2 - admin dimensions" "$ROOT/scripts/build_admin_dimensions.py"
  run_step "Phase 2 - displacement sites" "$ROOT/scripts/build_displacement_sites.py"
  run_step "Phase 2 - reference data" "$ROOT/scripts/build_reference_data.py"
  run_step "Phase 2 - DB import layers" "$ROOT/scripts/prepare_db_import_layers.py"
fi

cat <<EOF

Bootstrap complete.

Generated artifacts (local only, not in git):
  data/raw/          raw HDX + Geofabrik downloads
  data/processed/    road graph, canonical health facilities, augmented network
  output/            HTML validation maps

Open in a browser:
  output/south_sudan_data_validation.html
  output/south_sudan_road_topology_validation.html
  output/south_sudan_augmented_network_validation.html

Next: Phase 3 — see README.md Steps 3-5
  cp .env.example .env   # Windows: copy .env.example .env
  docker compose up -d
  python scripts/populate_databases.py --reset
EOF
