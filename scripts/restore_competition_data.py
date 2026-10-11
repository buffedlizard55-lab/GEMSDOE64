#!/usr/bin/env python
"""Restore and hash-verify every competition raster this run needs.

The competition's data page is behind a login this sandbox does not hold, so the bytes come
from public sibling-repository mirrors.  They are **owner-mirrored, not
organizer-authenticated** (IR-30-001), and every file is verified against a pinned SHA-256
before it is used.  Nothing here writes a submission.

    python scripts/restore_competition_data.py            # verify, restore if missing
    python scripts/restore_competition_data.py --check    # verify only, never download

Restores into ``data/official/`` (git-ignored):

    training_features.tif   4371c82e...23bc5   five parts, concatenated in order
    labels.tif              7ba308cc...ae4093  the mapped-fault catalogue (also the field label)
    sample_submission.tif   2176d08e...5d35cbc the grid template; its finite cells are the footprint
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "official"

FEATURES = dict(
    mirror="https://codeload.github.com/buffedlizard55-lab/GEMSDOE/tar.gz/refs/heads/main",
    parts="data/bridge/gems-geodawn-numerical-features.tif.part-",
    n_parts=5,
    out="training_features.tif",
    sha256="4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    bytes=418_912_844,
    note="the organizer's 19-band 100 m GeoDAWN numerical stack",
)
SMALL = dict(
    mirror="https://codeload.github.com/buffedlizard55-lab/GEMSDOE24/tar.gz/refs/heads/main",
    members={
        "data/bridge/labels.tif": (
            "labels.tif", "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"),
        "data/bridge/sample_submission.tif": (
            "sample_submission.tif",
            "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"),
        "data/bridge/existing_faults.tif": (
            "existing_faults.tif",
            "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"),
    },
    note="grid template and mapped-fault catalogue",
)


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(url: str) -> bytes:
    print(f"  downloading {url}", flush=True)
    with urllib.request.urlopen(url, timeout=900) as r:
        return r.read()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only; never download")
    args = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    ok = True

    target = DEST / FEATURES["out"]
    if target.is_file() and sha256_file(target) == FEATURES["sha256"]:
        print(f"[ok] {target.name} present and hash-verified")
    elif args.check:
        print(f"[MISSING] {target} ({FEATURES['note']})")
        ok = False
    else:
        blob = fetch(FEATURES["mirror"])
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
            names = sorted(n for n in tf.getnames() if ".part-" in n)
            want = [n for n in names if FEATURES["parts"].split("/")[-1] in n.split("/")[-1]]
            if len(want) != FEATURES["n_parts"]:
                raise SystemExit(f"expected {FEATURES['n_parts']} parts, found {len(want)}: {want}")
            parts = [tf.extractfile(n).read() for n in sorted(want)]
        assembled = b"".join(parts)
        digest = sha256_bytes(assembled)
        if digest != FEATURES["sha256"] or len(assembled) != FEATURES["bytes"]:
            raise SystemExit(f"assembled features hash {digest} / {len(assembled)} B does not "
                             f"match the pin {FEATURES['sha256']} / {FEATURES['bytes']} B")
        target.write_bytes(assembled)
        print(f"[restored] {target.name} {len(assembled):,} B sha256 {digest}")

    missing = [m for m, (out, sha) in SMALL["members"].items()
               if not (DEST / out).is_file() or sha256_file(DEST / out) != sha]
    if not missing:
        print("[ok] template, catalogue and existing-faults rasters present and hash-verified")
    elif args.check:
        print(f"[MISSING] {missing}")
        ok = False
    else:
        blob = fetch(SMALL["mirror"])
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
            for member in missing:
                out, sha = SMALL["members"][member]
                data = tf.extractfile(member).read()
                digest = sha256_bytes(data)
                if digest != sha:
                    raise SystemExit(f"{member} hash {digest} does not match the pin {sha}")
                (DEST / out).write_bytes(data)
                print(f"[restored] {out} {len(data):,} B sha256 {digest}")
    print("note: owner-mirrored bytes, hash-pinned but NOT organizer-authenticated.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
