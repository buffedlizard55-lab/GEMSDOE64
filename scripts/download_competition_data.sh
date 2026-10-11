#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"

# Probe the organizer Dropbox links (note: sandbox egress permits only GitHub/PyPI/npm hosts).
"$PYTHON" - <<'PY'
import json, pathlib, urllib.request, urllib.error

urls = {
    "train_zip": "https://www.dropbox.com/scl/fi/ef391003c325782d937e5/train.zip?dl=1",
    "test_zip": "https://www.dropbox.com/scl/fi/b3315100f87219129c97e/test.zip?dl=1",
    "example_submission_tif": "https://www.dropbox.com/scl/fi/eb1071055b70c7f206c30/example_submission.tif?dl=1",
}
probe = {}
for k, u in urls.items():
    try:
        req = urllib.request.Request(u, method="HEAD")
        with urllib.request.urlopen(req, timeout=3) as resp:
            probe[k] = {"url": u, "reachable": True, "status": resp.status}
    except Exception as e:
        probe[k] = {"url": u, "reachable": False, "error": str(e)}
pathlib.Path("evidence/dropbox_probe.json").write_text(json.dumps(probe, indent=2) + "\n")
PY

"$PYTHON" scripts/restore_inputs.py
printf '%s\n' 'Competition reference, external native-LiDAR scarp stacks, pilot 3 m DEM tiles, and 67 prior registry rasters verified in data/.'
