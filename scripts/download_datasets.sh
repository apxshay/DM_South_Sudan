#!/usr/bin/env bash
# Re-download raw datasets from HDX into data/raw/.
# Usage: ./scripts/download_datasets.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$("$ROOT/scripts/resolve_python.sh")" || {
  echo "ERROR: Python not found. Run ./scripts/setup_conda.sh or ./scripts/setup.sh first." >&2
  exit 1
}

exec $PYTHON "$ROOT/scripts/download_datasets.py"
