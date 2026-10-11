#!/usr/bin/env python3
"""Stop on a proven literal registry blocker. No fitting/placement after stop."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import numpy as np
import rasterio
from gems57.uniqueness import saturation_certificate
from gems57.evaluate_holdout import VERSION, implementation_hashes
from gems64.promotion import promotion_decision


def main():
    paths = {'sample': Path('data/reference/sample_submission.tif'),
             'catalogue': Path('data/reference/existing_faults.tif'),
             'witness': Path('data/registry/17GEMSDOE_E-proba-multiscale.tif')}
    expected = {'sample': '2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc',
                'catalogue': '7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093',
                'witness': 'ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be'}
    for name, path in paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            raise ValueError(f'input pin mismatch: {name}')
    with rasterio.open(paths['sample']) as src:
        footprint = np.isfinite(src.read(1))
        grid = (src.shape, src.crs, src.transform)
    with rasterio.open(paths['catalogue']) as src:
        if (src.shape, src.crs, src.transform) != grid:
            raise ValueError('catalogue grid mismatch')
        catalogue = (src.read(1) > 0) & footprint
    certificate = saturation_certificate(paths['witness'], footprint, catalogue, expected_grid=grid)
    certificate.update(source_commit='6fc71d19d49dca4960d5434bd81b6dd06fcc030a',
        source_path='docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif',
        repository='buffedlizard55-lab/17GEMSDOE', candidate_created=False,
        stop_before_placement=True)
    Path('evidence/registry_blocker.json').write_text(json.dumps(certificate, indent=2)+'\n')
    if not certificate['universal_overlap_blocker']:
        raise RuntimeError('Preflight conditions changed. Re-review the lane; this is not an automatic promotion.')
    card_path = Path('evidence/run_card.json')
    card = json.loads(card_path.read_text()) if card_path.exists() else {}
    card.update(schema='gems64-run-card-v1', run_id='g64-edti-20261011-preflight-negative',
        reviewed_utc=datetime.now(timezone.utc).isoformat(),
        hypothesis='Calibrated multi-sensor ridge uncertainty plus exact expected-DTI placement can reduce redundant picks.',
        mechanism='Buffered spatial OOF isotonic probabilities; >=32 provenance-checked model truth draws; exact mean-gain add/backward prune.',
        non_fault_mimic='Differential erosion along lithologic contacts can align topographic and magnetic ridges without fault slip.',
        holdout=dict(evidence_class='NOT_RUN', status='not-run', dti=None, ci95=None,
            evaluator_version=VERSION, withheld_positive_pixels=None,
            reason='Universal registry blocker triggered before model fitting or candidate placement.'),
        correlation_overlap_vs_registry=dict(surface_spearman=None, final_dot_overlap=None,
            candidate_comparisons_performed=False, universal_lower_bound_for_any_nonempty_dots=1.0,
            literal_limit=.70, overlap_radius_pixels=3.0, certificate='registry_blocker.json',
            full_prior_raster_hash_pixel_audit_complete=False),
        raster_sha256=None, candidate_generated=False,
        validator_output=dict(status='not-run-no-production-raster',
            no_nan_inside_footprint=None, values_in_0_1=None, dtype_float32=None,
            crs_shape_transform_match=None, format_pass=None),
        submission_name=None, run_name='g64-edti-20261011-preflight-negative',
        note='Expected-DTI lane stopped: a registry prior blocks every nonempty dot set under the 3-pixel literal overlap rule.',
        verdict='negative', download_allowed=False, submission_slots_used=0,
        organizer_confirmed_score=None, organizer_receipt=None,
        failed_gates=['literal_registry_overlap_universally_blocked', 'no_buffered_oof_cache',
                      'no_same_surface_holdout_comparison', 'no_complete_registry_byte_audit'],
        budget=dict(max_experiments=3, max_hours=2, geological_model_experiments=0,
            mathematical_verification_experiments=1, registry_preflight_audits=1,
            stopped_before_training=True),
        evaluator_implementation_sha256=implementation_hashes(),
        limitation='No production TIFF created. Synthetic unit-test TIFFs are serialization fixtures only and never published.')
    card['submission_note_limit_characters'] = 140
    card['submission_note_character_count'] = len(card['note'])
    assert len(card['note']) <= 140
    assert not promotion_decision({})['download_allowed']
    card_path.write_text(json.dumps(card, indent=2, allow_nan=False)+'\n')
    print('NEGATIVE: universal literal-overlap blocker. No production TIFF, no download, no slot.')


if __name__ == '__main__':
    main()
