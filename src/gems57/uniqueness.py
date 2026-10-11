"""Literal parallel-run gates, fail closed on incomplete registries.

No density exemption, reverse-overlap clearance or private definition of dots:
positive finite pixels are the inherited support definition. That makes a
whole-footprint soft registry surface a universal overlap blocker; the audit
reports the problem, rather than quietly changing the owner's protocol.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import binary_dilation
from scipy.stats import rankdata, spearmanr
from .metric import RADIUS_PX

RHO_LIMIT = 0.90
OVERLAP_LIMIT = 0.70
JACCARD_LIMIT = 0.50
ROOT = Path(__file__).resolve().parents[2]


def _dots(a):
    a = np.asarray(a)
    return np.isfinite(a) & (a > 0)


def _near(support, radius_px=RADIUS_PX):
    r = int(np.ceil(radius_px))
    yy, xx = np.mgrid[-r:r+1, -r:r+1]
    return binary_dilation(support, structure=yy*yy+xx*xx <= radius_px*radius_px)


def dot_overlap(mine, theirs, radius_px=RADIUS_PX):
    m, t = _dots(mine), _dots(theirs)
    if m.shape != t.shape:
        raise ValueError('overlap grid shape mismatch')
    if not m.any() or not t.any():
        return 0.0
    return float(_near(t, radius_px)[m].mean())


def _jaccard(a, b):
    u = int((a | b).sum())
    return float((a & b).sum() / u) if u else 0.0


def summarize_registry_rows(rows, *, registry_rasters_expected, complete_accessible_scan,
                            source_errors, candidate_meta, scope):
    """Apply the same literal thresholds to already hash-verified comparison rows.

    This allows a complete immutable prior audit to be extended with only newly
    published blobs, instead of re-downloading hundreds of unchanged rasters.
    The caller must prove candidate identity and the completeness/count of the
    combined registry before passing ``complete_accessible_scan=True``.
    """
    rows = list(rows)
    source_errors = list(source_errors or [])
    expected = int(registry_rasters_expected)
    checked = [r for r in rows if 'error' not in r]
    errors = [r for r in rows if 'error' in r]
    complete = bool(complete_accessible_scan and expected == len(rows)
                    and not errors and not source_errors)
    # The inherited stop gate is literal: only Spearman > 0.90 or forward
    # 3-pixel overlap > 0.70 (plus byte/pixel identity safeguards) can block.
    # Jaccard is reported for diagnosis, never substituted as a new threshold.
    flags = [r for r in checked if any(r.get(k, False) for k in (
        'duplicate_by_rho', 'duplicate_by_overlap',
        'identical_bytes', 'identical_decoded_predictions'))]
    rank_rows = [r for r in checked if r.get('spearman_full_footprint') is not None]
    worst_rho = max(rank_rows, key=lambda r: r['spearman_full_footprint'], default=None)
    worst_ov = max(checked, key=lambda r: r['my_dots_within_3px_of_theirs'], default=None)
    worst_jac = max(checked, key=lambda r: r['jaccard_dot_sets'], default=None)
    my_dot_count = int(candidate_meta['my_dots'])
    norm = bool(candidate_meta['candidate_rank_variation'])
    unique = complete and my_dot_count > 0 and norm and not flags
    return dict(
        my_file=candidate_meta.get('my_file'), evidence_class='REGISTRY-MEASUREMENT',
        my_dots=my_dot_count,
        candidate_decoded_sha256=candidate_meta.get('candidate_decoded_sha256'),
        candidate_file_sha256=candidate_meta.get('candidate_file_sha256'),
        rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT, jaccard_limit=JACCARD_LIMIT,
        registry_rasters_expected=expected, registry_rasters_checked=len(checked),
        complete_accessible_scan=complete, missing_or_invalid=len(errors),
        source_errors=source_errors,
        worst_spearman_full_footprint=(worst_rho['spearman_full_footprint'] if worst_rho else None),
        worst_rho_submission=(worst_rho['submission'] if worst_rho else None),
        worst_dot_overlap=(worst_ov['my_dots_within_3px_of_theirs'] if worst_ov else None),
        worst_overlap_submission=(worst_ov['submission'] if worst_ov else None),
        worst_jaccard_dot_sets=(worst_jac['jaccard_dot_sets'] if worst_jac else None),
        worst_jaccard_submission=(worst_jac['submission'] if worst_jac else None),
        byte_unique_among_checked=bool(checked) and not any(r.get('identical_bytes', False) for r in checked),
        pixel_unique_among_checked=bool(checked) and not any(r.get('identical_decoded_predictions', False) for r in checked),
        duplicate_count=len(flags), unique=bool(unique), rows=rows,
        jaccard_diagnostic_only=True,
        verdict='promote-to-selector-only' if unique else 'negative',
        stop_required=bool(flags or not complete or not my_dot_count or not norm),
        candidate_rank_variation=norm,
        scope=scope)


def merge_registry_audits(previous, extension, *, registry_rasters_expected,
                          complete_accessible_scan=True, scope=None):
    """Extend a full prior raster audit with a checked delta and keep fail-closed.

    Both audits must describe the same exact candidate bytes and decoded pixels.
    Duplicate file hashes are retained once; contradictory measurements for one
    SHA256 are rejected rather than averaged or silently overwritten.
    """
    identity_keys = ('candidate_file_sha256', 'candidate_decoded_sha256', 'my_dots',
                     'candidate_rank_variation')
    for key in identity_keys:
        if previous.get(key) != extension.get(key):
            raise ValueError(f'cannot merge audits with different candidate {key}')
    if any(previous.get(key) != extension.get(key)
           for key in ('rho_limit', 'overlap_limit', 'jaccard_limit')):
        raise ValueError('cannot merge audits with different uniqueness thresholds')
    if not previous.get('complete_accessible_scan'):
        raise ValueError('base audit is not a complete accessible registry scan')
    if not extension.get('complete_accessible_scan'):
        raise ValueError('registry delta is incomplete')
    if previous.get('missing_or_invalid') or extension.get('missing_or_invalid'):
        raise ValueError('registry audit contains missing or invalid raster rows')
    if previous.get('source_errors') or extension.get('source_errors'):
        raise ValueError('registry audit contains source errors')

    merged = {}
    for row in [*previous['rows'], *extension['rows']]:
        if 'error' in row:
            raise ValueError('cannot extend a registry audit with an errored row')
        digest = row.get('sha256')
        if not digest:
            raise ValueError('registry audit row has no content SHA256')
        old = merged.get(digest)
        if old is not None:
            for metric in ('my_dots_within_3px_of_theirs', 'spearman_full_footprint',
                           'jaccard_dot_sets', 'identical_bytes',
                           'identical_decoded_predictions'):
                if old.get(metric) != row.get(metric):
                    raise ValueError(f'conflicting registry measurements for SHA256 {digest}: {metric}')
            sources = set(old.get('sources', []))
            if old.get('submission'):
                sources.add(old['submission'])
            if row.get('submission'):
                sources.add(row['submission'])
            sources.update(row.get('sources', []))
            old['sources'] = sorted(sources)
        else:
            merged[digest] = dict(row)
            sources = set(row.get('sources', []))
            if row.get('submission'):
                sources.add(row['submission'])
            merged[digest]['sources'] = sorted(sources)
    rows = sorted(merged.values(), key=lambda r: (r.get('repo', ''), r.get('submission', ''), r['sha256']))
    meta = {k: previous.get(k) for k in identity_keys}
    meta['my_file'] = previous.get('my_file')
    expected = int(registry_rasters_expected)
    complete = bool(complete_accessible_scan and len(rows) == expected)
    result = summarize_registry_rows(
        rows, registry_rasters_expected=expected,
        complete_accessible_scan=complete,
        source_errors=[], candidate_meta=meta,
        scope=scope or 'Indexed public owner-repository inventory; not a complete organizer registry. External, private, unlinked, inaccessible, and later-written sources may be absent.',
    )
    result['phase'] = extension.get('phase', previous.get('phase'))
    result['reviewed_utc'] = extension.get('reviewed_utc')
    result['submission_slots_used'] = int(previous.get('submission_slots_used', 0))
    result['incremental_extension'] = dict(
        base_rasters=previous.get('registry_rasters_checked'),
        newly_discovered_rasters=extension.get('registry_rasters_checked'),
        deduplicated_rasters=expected,
    )
    return result


def surface_rho(mine, theirs, valid):
    m = np.asarray(mine, np.float32)[valid]
    t = np.asarray(theirs, np.float32)[valid]
    mb, tb = _dots(m), _dots(t)
    union = mb | tb
    rho_union = float('nan')
    if union.sum() > 10 and mb[union].any() and tb[union].any() and not (mb[union].all() or tb[union].all()):
        rho_union = float(spearmanr(m[union], t[union]).statistic)
    rho = float(spearmanr(m, t).statistic) if np.ptp(m) and np.ptp(t) else float('nan')
    return dict(spearman_on_dot_union=rho_union, n_dot_union=int(union.sum()),
                jaccard_dot_sets=_jaccard(mb,tb), spearman_full_footprint=rho)


def _sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for c in iter(lambda: stream.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def records_from_index(index):
    if isinstance(index, list):
        return index, False, ["Legacy list has no complete-inventory certificate; diagnostic only"]
    if not isinstance(index, dict) or 'rasters' not in index:
        raise ValueError('registry must be a list or a full inventory with rasters')
    records = [dict(repo=r['repo_first'], submission=r['sources'][0], file=r['cache_file'],
                    sha256=r['sha256'], sources=r['sources']) for r in index['rasters']]
    # Historical /tmp inventory never had a completeness certificate; file checks
    # below still prevent it from passing when all ephemeral caches disappear.
    complete = index.get('complete_accessible_scan', False)
    return records, bool(complete), index.get('errors', [])


def compare_array_to_registry(mine, registry_index, footprint, *, file_sha256=None,
                              include_reverse=True, progress=None, expected_grid=None):
    mine = np.asarray(mine, np.float32)
    fp = np.asarray(footprint, bool)
    if mine.ndim != 2 or mine.shape != fp.shape or not fp.any():
        raise ValueError('candidate / footprint grid mismatch or empty footprint')
    if not np.isfinite(mine).all() or (mine < 0).any() or (mine > 1).any():
        raise ValueError('candidate must already be finite in [0,1]')
    if (mine[~fp] > 0).any():
        raise ValueError('positive candidate mass outside footprint')
    idx = registry_index if isinstance(registry_index, (list, dict)) else json.loads(Path(registry_index).read_text())
    records, inventory_complete, source_errors = records_from_index(idx)
    rows = []
    values = mine[fp]
    ranks = rankdata(values).astype(np.float64)
    ranks -= ranks.mean()
    norm = float(np.linalg.norm(ranks))
    my_support = _dots(mine) & fp
    my_dot_count = int(my_support.sum())
    my_near = _near(my_support) if include_reverse else None
    decoded_digest = hashlib.sha256(np.ascontiguousarray(mine).tobytes()).hexdigest()
    for i, rec in enumerate(records):
        p = Path(rec['file'])
        if not p.is_absolute():
            p = ROOT / p
        base = dict(repo=rec.get('repo'), submission=rec.get('submission',p.name), file=str(p))
        try:
            if not p.exists():
                raise FileNotFoundError('missing registry file; cannot certify uniqueness')
            digest = _sha(p)
            if not rec.get('sha256'):
                raise ValueError('registry entry has no SHA256 pin')
            if digest != rec['sha256']:
                raise ValueError('registry SHA256 pin mismatch')
            with rasterio.open(p) as src:
                if src.count != 1 or src.shape != mine.shape:
                    raise ValueError('registry grid or band-count mismatch')
                if expected_grid is not None and (src.shape, src.crs, src.transform) != expected_grid:
                    raise ValueError('registry CRS/transform differs from reference')
                if mine.shape == (3730,3292):
                    from .grid import TRANSFORM
                    if src.crs is None or src.crs.to_epsg()!=32611 or src.transform != TRANSFORM:
                        raise ValueError('registry CRS/transform mismatch')
                theirs = src.read(1).astype(np.float32)
            if not np.isfinite(theirs[fp]).all() or np.any((theirs[fp] < 0) | (theirs[fp] > 1)):
                raise ValueError('registry predictions invalid inside footprint')
            theirs = np.where(np.isfinite(theirs), theirs, 0.0)
            # Outside-footprint values are ignored for support and pixel identity.
            theirs[~fp] = 0
            tv = theirs[fp]
            support = (theirs > 0) & fp
            tb = support[fp]
            # Exact Spearman with tied ranks; candidate ranks are reused for all priors.
            if norm == 0 or np.ptp(tv) == 0:
                rho = None
            elif np.all((tv == 0) | (tv == 1)):
                nt = int(tb.sum()); n = len(tv)
                rho = float(ranks[tb].sum() / (norm * np.sqrt(nt*(n-nt)/n)))
            else:
                tr = rankdata(tv).astype(np.float64)
                tr -= tr.mean()
                rho = float(np.dot(ranks,tr)/(norm*np.linalg.norm(tr)))
            ov = float(_near(support)[my_support].mean()) if my_dot_count else 0.0
            reverse = float(my_near[support].mean()) if include_reverse and support.any() else 0.0
            jac = _jaccard(my_support, support)
            their_decoded = hashlib.sha256(np.ascontiguousarray(theirs).tobytes()).hexdigest()
            row = {**base, 'sha256':digest, 'decoded_sha256':their_decoded,
                'their_dots':int(support.sum()), 'my_dots_within_3px_of_theirs':ov,
                'their_dots_within_3px_of_mine':reverse, 'spearman_full_footprint':rho,
                'jaccard_dot_sets':jac,
                'identical_bytes':bool(file_sha256 and digest==file_sha256),
                'identical_decoded_predictions':bool(their_decoded==decoded_digest),
                'duplicate_by_rho':bool(rho is not None and rho > RHO_LIMIT),
                'duplicate_by_overlap':bool(ov > OVERLAP_LIMIT),
                'duplicate_by_jaccard':bool(jac > JACCARD_LIMIT)}
            rows.append(row)
        except (OSError, ValueError, rasterio.errors.RasterioError) as e:
            rows.append({**base, 'error':str(e)})
        if progress:
            progress(i+1,len(records),rows[-1])
    complete = inventory_complete and bool(records) and not source_errors
    return summarize_registry_rows(
        rows,
        registry_rasters_expected=len(records),
        complete_accessible_scan=complete,
        source_errors=source_errors,
        candidate_meta=dict(
            my_file=None,
            my_dots=my_dot_count,
            candidate_decoded_sha256=decoded_digest,
            candidate_file_sha256=file_sha256,
            candidate_rank_variation=norm > 0,
        ),
        scope='All hash-verified accessible entries in the indexed public owner-repository inventory; not a complete organizer registry. External/private/unlinked/inaccessible files may be absent. Reverse overlap is diagnostic only.',
    )


def compare_to_registry(mine_path, registry_index, footprint, **kwargs):
    mine_path = Path(mine_path)
    with rasterio.open(mine_path) as src:
        if src.count != 1:
            raise ValueError('candidate must be single band')
        expected = kwargs.get('expected_grid')
        if expected is not None and (src.shape, src.crs, src.transform) != expected:
            raise ValueError('candidate CRS/shape/transform differs from reference')
        if expected is None and src.shape == (3730, 3292):
            from .grid import TRANSFORM
            if src.crs is None or src.crs.to_epsg() != 32611 or src.transform != TRANSFORM:
                raise ValueError('candidate differs from pinned competition grid')
        mine = src.read(1)
    result = compare_array_to_registry(mine, registry_index, footprint,
        file_sha256=_sha(mine_path), **kwargs)
    result['my_file'] = str(mine_path)
    return result


def saturation_certificate(registry_path, footprint, catalogue=None, *, expected_grid=None):
    """Certify whether one prior covers every allowed cell within the literal 3 px halo.

    Supply ``expected_grid=(shape, crs, transform)`` when using this as a
    pre-placement gate. A coincidentally equal-shaped raster on a different
    map grid is not a valid witness.
    """
    fp = np.asarray(footprint, bool)
    if fp.ndim != 2 or not fp.any():
        raise ValueError('empty or non-2D footprint')
    if catalogue is not None and np.asarray(catalogue).shape != fp.shape:
        raise ValueError('catalogue / footprint grid mismatch')
    allowed = fp if catalogue is None else fp & ~np.asarray(catalogue, bool)
    if not allowed.any():
        raise ValueError('empty allowed domain cannot certify a meaningful blocker')
    with rasterio.open(registry_path) as src:
        if src.shape != fp.shape or src.count != 1:
            raise ValueError('witness grid mismatch')
        if expected_grid is not None and (src.shape, src.crs, src.transform) != expected_grid:
            raise ValueError('witness CRS/transform differs from reference grid')
        a = src.read(1)
    positive = _dots(a) & fp
    covered = _near(positive)
    uncovered = int((allowed & ~covered).sum())
    return dict(evidence_class='REGISTRY-MEASUREMENT', witness_file=str(registry_path),
        witness_sha256=_sha(registry_path), positive_pixels=int(positive.sum()),
        allowed_pixels=int(allowed.sum()), uncovered_allowed_pixels=uncovered,
        covered_allowed_fraction=float(covered[allowed].mean()),
        universal_overlap_blocker=uncovered==0, overlap_limit=OVERLAP_LIMIT,
        support_definition='finite prediction > 0 (inherited literal support rule)',
        overlap_radius_pixels=float(RADIUS_PX),
        implication=(f'Every nonempty candidate dot in the allowed domain is within {RADIUS_PX:g} pixels of a positive prior pixel; forward overlap is therefore 1.0, above the 0.70 gate.' if uncovered==0 else 'No universal blockage established.'))


# --------------------------------------------------------------------------- #
# Diagnostic certificate for the dense-prior case.
#
# The literal gate above is inherited protocol: positive finite pixels are dots,
# and >70 % of my dots within 3 px of any single prior's dots is a stop. That
# rule is only informative for priors that are *emission sets*. A prior that
# carries positive mass at (almost) every footprint cell makes the forward
# overlap ~1.0 for every non-empty candidate, so the criterion cannot separate a
# copy from an original. This certificate measures that degeneracy with matched
# random controls and reports it alongside -- never instead of -- the literal
# verdict. No exemption is taken here; the caller keeps the literal gate
# fail-closed and publishes both numbers.
# --------------------------------------------------------------------------- #

def dense_prior_certificate(mine, *, registry_index, footprint, radius_px=RADIUS_PX,
                            control_draws=32, seed=64, allowed=None, subsample=300_000,
                            file_sha256=None, expected_grid=None):
    records = registry_index.get('rasters', registry_index) if isinstance(registry_index, dict) \
        else registry_index
    records = list(records)
    mine = np.asarray(mine, dtype=np.float32)
    footprint = np.asarray(footprint, bool)
    if mine.shape != footprint.shape:
        raise ValueError('candidate/footprint shape mismatch')
    my_dots = _dots(mine) & footprint
    n_mine = int(my_dots.sum())
    if n_mine == 0:
        raise ValueError('candidate carries no positive cells inside the footprint')
    rng = np.random.default_rng(seed)
    pool_mask = np.asarray(allowed, bool) & footprint if allowed is not None else footprint
    pool = np.flatnonzero(pool_mask.ravel())
    if pool.size == 0:
        raise ValueError('empty control pool')
    # Controls are kept as flat index arrays (n_mine x control_draws, ~10 MB)
    # rather than full boolean masks (12 MB each): the overlap of a control set
    # with a prior is a gather into that prior's dilated support.
    control_idx = np.empty((int(control_draws), min(n_mine, pool.size)), dtype=np.int64)
    for k in range(int(control_draws)):
        control_idx[k] = pool[rng.choice(pool.size, size=min(n_mine, pool.size), replace=False)]
    controls = [control_idx[k] for k in range(int(control_draws))]
    sample_n = int(min(subsample, int(footprint.sum())))
    sample_idx = rng.choice(np.flatnonzero(footprint.ravel()), size=sample_n, replace=False)
    rows, errors = [], []
    for record in records:
        path = Path(str(record.get('cache_file', '')))
        try:
            with rasterio.open(path) as ds:
                theirs = ds.read(1)
                if expected_grid is not None:
                    got = (ds.height, ds.width, ds.crs, ds.transform)
                    want = (int(expected_grid[0]), int(expected_grid[1]),
                            rasterio.crs.CRS.from_user_input(expected_grid[2]), expected_grid[3])
                    if got != want and (got[0], got[1], str(got[2])) != (want[0], want[1], str(want[2])):
                        raise ValueError('prior grid differs from the candidate grid')
        except Exception as exc:                                     # noqa: BLE001
            errors.append(dict(file=str(path), error=f'{type(exc).__name__}: {exc}'))
            continue
        if theirs.shape != mine.shape:
            errors.append(dict(file=str(path), error='shape mismatch'))
            continue
        sup = _dots(theirs) & footprint
        support_fraction = float(sup.sum() / max(int(footprint.sum()), 1))
        fwd = dot_overlap(mine, theirs, radius_px)
        rev = dot_overlap(theirs, mine, radius_px) if sup.any() else 0.0
        jac = _jaccard(my_dots, sup)
        try:
            t = theirs.ravel()[sample_idx].astype(float)
            m = mine.ravel()[sample_idx].astype(float)
            ok = np.isfinite(t)
            rho = float(spearmanr(m[ok], t[ok]).statistic) if ok.sum() > 10 and np.unique(t[ok]).size > 1 else 0.0
        except Exception:                                            # noqa: BLE001
            rho = None
        near_coverage = 0.0
        if sup.any():
            near_mask = _near(sup, radius_px)
            near_coverage = float(near_mask[footprint].mean())
            near_t = near_mask.ravel()
            ctrl = [float(near_t[idx].mean()) for idx in controls]
            del near_t, near_mask
        else:
            ctrl = [0.0] * int(control_draws)
        dense = support_fraction > 0.5
        row = dict(
            file=str(path), repo=record.get('repo_first'), submission=record.get('submission'),
            prior_sha256=record.get('sha256'), prior_bytes=record.get('bytes'),
            positive_pixels=int(sup.sum()), support_fraction=support_fraction,
            dense_prior=bool(dense),
            my_dots_within_3px_of_theirs=fwd, their_dots_within_3px_of_mine=rev,
            jaccard_dot_sets=jac, spearman_subsample=rho, spearman_subsample_n=int(sample_n),
            identical_bytes=bool(file_sha256 and record.get('sha256') == file_sha256),
            near_coverage_within_radius=float(near_coverage),
            control_overlap_min=float(np.min(ctrl)), control_overlap_median=float(np.median(ctrl)),
            control_overlap_max=float(np.max(ctrl)),
            # The criterion can only separate a copy from an original if matched
            # random controls do NOT already exceed the limit. Saturation is
            # therefore measured (controls), never assumed from support size.
            criterion_unsatisfiable=bool(np.min(ctrl) >= OVERLAP_LIMIT),
            duplicate_by_overlap=bool(fwd > OVERLAP_LIMIT),
            duplicate_by_reverse_overlap=bool(rev > OVERLAP_LIMIT),
            duplicate_by_rho=bool(rho is not None and abs(rho) > RHO_LIMIT),
        )
        rows.append(row)
    checked = [r for r in rows]
    informative = [r for r in rows if not r['criterion_unsatisfiable']]
    worst_ov = max(informative, key=lambda r: r['my_dots_within_3px_of_theirs'], default=None)
    worst_rho = max([r for r in rows if r['spearman_subsample'] is not None],
                    key=lambda r: abs(r['spearman_subsample']), default=None)
    literal_unique = bool(not [r for r in rows if r['identical_bytes'] or r['duplicate_by_overlap']
                               or r['duplicate_by_rho']])
    identity_flags = [r for r in rows if r['identical_bytes'] or r['duplicate_by_rho']]
    diagnostic_flags = identity_flags + [
        r for r in informative if r['duplicate_by_overlap'] or r['duplicate_by_reverse_overlap']]
    return dict(
        schema='gems64-dense-prior-certificate-v1',
        evidence_class='REGISTRY-MEASUREMENT',
        candidate_file_sha256=file_sha256, my_dots=n_mine,
        radius_px=float(radius_px), rho_limit=RHO_LIMIT, overlap_limit=OVERLAP_LIMIT,
        registry_rasters_checked=len(checked), errors=errors,
        control_draws=int(control_draws), control_pool_cells=int(pool.size),
        dense_priors=[dict(file=Path(r['file']).name, support_fraction=r['support_fraction'],
                           positive_pixels=r['positive_pixels'],
                           near_coverage_within_radius=r['near_coverage_within_radius'],
                           my_dots_within_3px_of_theirs=r['my_dots_within_3px_of_theirs'],
                           control_overlap_min=r['control_overlap_min'],
                           control_overlap_median=r['control_overlap_median'])
                      for r in rows if r['dense_prior']],
        saturating_priors=[dict(file=Path(r['file']).name, support_fraction=r['support_fraction'],
                                positive_pixels=r['positive_pixels'],
                                near_coverage_within_radius=r['near_coverage_within_radius'],
                                my_dots_within_3px_of_theirs=r['my_dots_within_3px_of_theirs'],
                                control_overlap_min=r['control_overlap_min'])
                           for r in rows if r['criterion_unsatisfiable']],
        informative_priors=len(informative),
        worst_overlap_informative=(worst_ov['my_dots_within_3px_of_theirs'] if worst_ov else None),
        worst_overlap_informative_file=(Path(worst_ov['file']).name if worst_ov else None),
        worst_abs_spearman=(abs(worst_rho['spearman_subsample']) if worst_rho else None),
        worst_abs_spearman_file=(Path(worst_rho['file']).name if worst_rho else None),
        byte_and_pixel_unique=bool(not any(r['identical_bytes'] for r in rows)),
        literal_verdict_unique=literal_unique,
        diagnostic_verdict_unique=bool(not diagnostic_flags),
        unsatisfiable_criteria=[Path(r['file']).name for r in rows if r['criterion_unsatisfiable']],
        unsatisfiable_reason=("matched random controls in the same emission domain already exceed "
                              "the 70 % forward-overlap limit, so the criterion cannot separate a "
                              "copy from an original for these priors"),
        rows=rows,
        scope=registry_index.get('scope') if isinstance(registry_index, dict) else None)
