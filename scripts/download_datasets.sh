#!/usr/bin/env bash
# Re-download raw datasets from HDX into data/raw/.
# Usage: ./scripts/download_datasets.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

resolve_python() {
  if [[ -n "${CONDA_DEFAULT_ENV:-}" ]] && command -v python >/dev/null 2>&1; then
    command -v python
  elif [[ -x "$ROOT/data_env/bin/python" ]]; then
    echo "$ROOT/data_env/bin/python"
  elif [[ -x "$ROOT/data_env/Scripts/python.exe" ]]; then
    echo "$ROOT/data_env/Scripts/python.exe"
  elif command -v python3 >/dev/null 2>&1; then
    command -v python3
  else
    command -v python
  fi
}

PYTHON="$(resolve_python)"
if [[ -z "$PYTHON" ]]; then
  echo "ERROR: Python not found. Run ./scripts/setup.sh or conda activate dm-south-sudan first." >&2
  exit 1
fi

exec "$PYTHON" "$ROOT/scripts/download_datasets.py"
