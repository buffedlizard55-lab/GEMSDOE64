#!/usr/bin/env bash
# Place the organiser's competition data. Requires a DrivenData login, so this
# cannot run inside a credential-free sandbox: run it on a machine where you are
# signed in, then re-run the pipeline.
#
#   bash scripts/download_competition_data.sh
#
# Source: https://www.drivendata.org/competitions/306/competition-doe-gems/data/
set -euo pipefail
DEST="${1:-data/competition}"
mkdir -p "$DEST"
cat <<'EOF'
The four organiser files are:
  training_features.tif   (~419 MB)  sha256 4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5
  labels.tif              (~426 KB)  sha256 7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093
  sample_submission.tif   (~1.6 MB)  sha256 2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc
  1m_DEM_links.csv
Hashes are the ones recorded in GEMSDOE32/data/restore_receipt.json.
labels.tif is byte-identical to existing_faults.tif: the public "labels" raster
is the mapped-fault catalogue, not the scored truth.
EOF
echo "Download them into $DEST from the competition data page, then:"
echo "  sha256sum $DEST/*.tif"
