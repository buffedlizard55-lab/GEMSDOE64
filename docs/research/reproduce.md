# Reproduce this lane from scratch

Everything below was executed in this session. There is no step that depends on
private credentials; the only constraint is that the large inputs live outside Git.

## 1. Environment

```bash
cd GEMSDOE64
python3 -m venv .venv
.venv/bin/pip install -r requirements-lock.txt      # numpy, scipy, scikit-learn, rasterio, pytest, markdown
```

## 2. Inputs (hash-pinned mirrors; see `evidence/input_pins.json`)

```bash
# 19-band official stack (5 parts, ~419 MB), reassembled and hash-checked
mkdir -p /tmp/s5 && cd /tmp/s5
git clone --depth 1 --filter=blob:none --sparse https://github.com/buffedlizard55-lab/5GEMSDOE .
git sparse-checkout set data/bridge data/aux_bridge
cat data/bridge/gems-geodawn-numerical-features.tif.part-* > /tmp/training_features.tif
sha256sum /tmp/training_features.tif   # expect 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5

# grid template + catalogue
mkdir -p <repo>/data/bridge && cp data/bridge/{sample_submission.tif,existing_faults.tif} <repo>/data/bridge/

# lidar scarp layer (~37 MB) and the TIGER road distance layer
mkdir -p /tmp/s60 && cd /tmp/s60
git clone --depth 1 --filter=blob:none --sparse https://github.com/buffedlizard55-lab/60GEMSDOE .
git sparse-checkout set data registry docs/data evidence
cp data/external/lidar_scarp_features_u8.tif <repo>/data/external/
# TIGER road distance: 60GEMSDOE registry or GEMSDOE24 data/external/tiger_road_distance_m.tif
```

The sandbox can reach `github.com`, `api.github.com` and `pypi.org` only — USGS
tile hosts are unreachable (`evidence/access_blockers.json`).

## 3. Run

```bash
.venv/bin/python scripts/build_registry_index.py --scan /tmp/s60/registry/rasters \
    --witness /tmp/layers/witness_17_E-proba-multiscale.tif --out evidence/registry_index.json
.venv/bin/python scripts/pin_inputs.py --bridge data/bridge \
    --features /tmp/training_features.tif --lidar data/external/lidar_scarp_features_u8.tif \
    --road-distance data/external/tiger_road_distance_m.tif --out evidence/input_pins.json
.venv/bin/python scripts/run_scarp_lane.py --name g64-lidarscarp-strikeline --draws 600
```

The lane writes `docs/downloads/<name>-<sha12>.tif`, `evidence/run_card.json`
and `evidence/uniqueness_certificate.json`, and prints its memory checkpoints
(`[mem]`) because the sandbox has ~3 GB of RAM.

## 4. Re-verify a published raster independently

```bash
.venv/bin/python scripts/validate_submission.py docs/downloads/<name>-<sha12>.tif
.venv/bin/python scripts/build_uniqueness_certificate.py \
    --raster docs/downloads/<name>-<sha12>.tif --registry evidence/registry_index.json \
    --bridge data/bridge --out /tmp/recheck.json
# expect the same verdicts and per-prior rows as evidence/uniqueness_certificate.json;
# the control pool differs (footprint-minus-catalogue here, the lane's emission
# domain in-run), so compare the verdict fields rather than the JSON bytes.
```

## 5. Site

```bash
.venv/bin/python scripts/build_site.py     # renders docs/*.html from the run card
.venv/bin/python scripts/check_site.py     # links, banner, hash-vs-card, download policy
.venv/bin/python -m pytest -q
```
