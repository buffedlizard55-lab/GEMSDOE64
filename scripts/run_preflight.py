#!/usr/bin/env python3
"""Record the saturation certificate for 17GEMSDOE_E-proba-multiscale.tif without overwriting the promoted run card."""
from pathlib import Path
import hashlib
import json
import numpy as np
import rasterio
from gems57.uniqueness import saturation_certificate


def main() -> None:
    w_path = Path("data/registry/17GEMSDOE__17GEMSDOE_E-proba-multiscale.tif")
    if not w_path.exists():
        w_path = Path("data/registry/17GEMSDOE_E-proba-multiscale.tif")
    paths = {
        "sample": Path("data/reference/sample_submission.tif"),
        "catalogue": Path("data/reference/existing_faults.tif"),
        "witness": w_path,
    }
    expected = {
        "sample": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
        "catalogue": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
        "witness": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
    }
    for name, path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            raise ValueError(f"input pin mismatch: {name}")
    with rasterio.open(paths["sample"]) as src:
        footprint = np.isfinite(src.read(1))
        grid = (src.shape, src.crs, src.transform)
    with rasterio.open(paths["catalogue"]) as src:
        if (src.shape, src.crs, src.transform) != grid:
            raise ValueError("catalogue grid mismatch")
        catalogue = (src.read(1) > 0) & footprint
    certificate = saturation_certificate(paths["witness"], footprint, catalogue, expected_grid=grid)
    certificate.update(
        source_commit="6fc71d19d49dca4960d5434bd81b6dd06fcc030a",
        source_path="docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif",
        repository="buffedlizard55-lab/17GEMSDOE",
        note="Non-geological space-filling continuous probability surface (99.42% > 0, 100.0% 3-px halo). Excluded from the 62-raster geological overlap check and documented in evidence/registry_audit_67.json.",
    )
    Path("evidence/registry_blocker.json").write_text(json.dumps(certificate, indent=2) + "\n")
    print(json.dumps({"ok": True, "universal_overlap_blocker": certificate["universal_overlap_blocker"]}, indent=2))


if __name__ == "__main__":
    main()
