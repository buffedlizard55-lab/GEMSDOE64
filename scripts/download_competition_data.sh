#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" scripts/restore_inputs.py
printf '%s\n' 'Competition reference rasters, native-lidar scarp stacks, cultural masks, pilot 3 m DEM tiles, and 70 registry rasters restored and SHA256-verified.'
