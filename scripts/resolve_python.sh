#!/usr/bin/env bash
# Resolve the Python interpreter for this project (conda env or local venv).
# Usage: source scripts/resolve_python.sh   OR   PYTHON="$(scripts/resolve_python.sh)"

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

resolve_python() {
  if [[ -n "${CONDA_DEFAULT_ENV:-}" ]] && [[ "$CONDA_DEFAULT_ENV" == "dm-south-sudan" ]] && command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi

  if command -v conda >/dev/null 2>&1; then
    if conda env list | awk '{print $1}' | grep -qx "dm-south-sudan"; then
      echo "conda run --no-capture-output -n dm-south-sudan python"
      return 0
    fi
  fi

  if [[ -x "$ROOT/data_env/bin/python" ]]; then
    echo "$ROOT/data_env/bin/python"
    return 0
  fi

  if [[ -x "$ROOT/data_env/Scripts/python.exe" ]]; then
    echo "$ROOT/data_env/Scripts/python.exe"
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi

  return 1
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  resolve_python
fi
