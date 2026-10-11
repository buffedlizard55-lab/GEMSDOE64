#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" scripts/restore_inputs.py
printf '%s\n' 'Only pinned audit inputs were restored. Official training acquisition and shared feature cache remain blocked.' >&2
exit 2
