#!/usr/bin/env bash
# Restore the cached external layers and the prior-raster registry used by this
# repository. Everything here is a public blob in the owner's sibling
# repositories; no credentials are needed and nothing is fetched from a
# competition endpoint.
#
#   bash scripts/fetch_external.sh [DEST]
#
# DEST defaults to ../_gems64_cache (outside the repository, so the 150 MB of
# rasters never enters git).
set -euo pipefail
DEST="${1:-$(cd "$(dirname "$0")/../.." && pwd)/_gems64_cache}"
SRC_REPO="${SRC_REPO:-60GEMSDOE}"
mkdir -p "$DEST"
echo "fetching https://codeload.github.com/buffedlizard55-lab/${SRC_REPO}/tar.gz/refs/heads/main"
curl -sL -o "$DEST/${SRC_REPO}.tar.gz" \
  "https://codeload.github.com/buffedlizard55-lab/${SRC_REPO}/tar.gz/refs/heads/main"
tar -xzf "$DEST/${SRC_REPO}.tar.gz" -C "$DEST" \
  --wildcards "*/data/external/*" "*/data/geodawn_dem_a2_100m.tif" \
              "*/registry/rasters/*" "*/registry/registry_index.json" 2>/dev/null || true
SRC=$(find "$DEST" -maxdepth 1 -type d -name "${SRC_REPO}-*" | head -1)
echo "external layers: $SRC/data/external"
echo "registry       : $SRC/registry"
echo
echo "export GEMS64_EXTERNAL=$SRC/data/external"
echo "export GEMS64_REGISTRY=$SRC/registry"
