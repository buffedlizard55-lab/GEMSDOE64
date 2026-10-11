#!/usr/bin/env python3
"""GEMSDOE64 lane runner: lidar scarp geometry -> gated candidate or negative.

Three experiments, in the order the lane protocol demands:

E1  instrument 1 (``sgmc_off``): per-component leakage canaries, then the lane
    composite against a terrain-class-matched control, a mass-matched random
    control, the owner-reported champion artifact and a distance-only control,
    with a paired 20 km block bootstrap and a range-front split.
E2  instrument 2 (``catalogue_hide``): whole-component hide-and-recover on the
    shared split, as a no-harm / faint-scarp sensitivity check.
E3  emission: size sweep on instrument 1, blue-noise placement, cultural mask,
    registry comparison under the literal and discriminating readings, the
    shared writer, the on-disk validator, and the promotion gates.

Every number written to ``evidence/`` carries its instrument and its evidence
class.  Nothing here is an organizer score and no submission slot is used.

Usage
-----
    python scripts/run_lane.py --experiments e1,e2,e3
    python scripts/run_lane.py --experiments e3 --emit     # build the TIFF
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems57 import evaluate_holdout, metric, spatial, submission_writer, uniqueness  # noqa: E402
from gems64 import instrument, lane, registry_policy  # noqa: E402

DATA = ROOT / "data" / "inputs"
EVID = ROOT / "evidence"
DOWNLOADS = ROOT / "docs" / "downloads"

ABLATION_SURFACES = ("amp_snr", "amp_mean", "amp_max", "step", "cross", "relief", "base",
                     "crest", "frac", "vergence", "coh", "replicate3m", "declared_composite")
WORK = ROOT / "work"


# --------------------------------------------------------------------------- #
# loading                                                                      #
# --------------------------------------------------------------------------- #
def read_band(path: Path, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(band)


def _valid_codes(state: dict) -> np.ndarray:
    """Raw uint8 ``valid`` codes from the 2 m chain (decode needs codes, not metres)."""
    with rasterio.open(DATA / "lidar_scarp_features_u8.tif") as src:
        return src.read(lane.LIDAR_CHANNELS.index("valid") + 1)


def load_all() -> dict:
    """Load every input, decode it, and assert the shared grid facts."""
    receipt = json.loads((EVID / "input_assembly.json").read_text())
    if not receipt["complete"]:
        raise RuntimeError("input assembly receipt is incomplete; refusing to run")
    sample = read_band(DATA / "sample_submission.tif")
    footprint = np.isfinite(sample)
    catalogue_raw = read_band(DATA / "existing_faults.tif")
    catalogue = (catalogue_raw > 0) & footprint

    bands = {}
    with rasterio.open(DATA / "lidar_scarp_features_u8.tif") as src:
        if src.descriptions != tuple(lane.LIDAR_CHANNELS):
            raise ValueError(f"lidar scarp band order changed: {src.descriptions}")
        for i, name in enumerate(lane.LIDAR_CHANNELS):
            if name == "strike":            # not used by this lane; do not hold the array
                continue
            bands[name] = lane.decode_lidar(src.read(i + 1), name)

    h52 = {}
    with rasterio.open(DATA / "h52_scarp3m_100m.tif") as src:
        if src.descriptions != tuple(lane.H52_CHANNELS):
            raise ValueError(f"h52 band order changed: {src.descriptions}")
        for i, name in enumerate(lane.H52_CHANNELS):
            if name not in ("cover", "h_gate12", "sigma_mean"):
                continue
            h52[name] = lane.decode_h52(src.read(i + 1), name)

    sgmc = read_band(DATA / "derived_sgmc_faults_100m.tif") > 0
    road = read_band(DATA / "tiger_road_distance_m.tif")
    claim = read_band(DATA / "blm_closed_claim_distance_m.tif")
    return dict(sample=sample, footprint=footprint, catalogue=catalogue, bands=bands,
                h52=h52, sgmc=sgmc, road=road, claim=claim, receipt=receipt)


# --------------------------------------------------------------------------- #
# shared lane state                                                            #
# --------------------------------------------------------------------------- #
CHOSEN_SURFACE = "amp_snr"
SURFACE_RATIONALE = (
    "amp_snr = sqrt(ex_max * ex_mean) is the lane's SNR-weighted scarplet amplitude. "
    "The pre-declared composite (amp 0.45 / coh 0.30 / 3 m replication 0.25) was measured "
    "and rejected: both extra terms reduce credit per dot on instrument 1. The ablation is "
    "recorded in evidence/e0_ablation.json; amp_snr is the best measured physically named "
    "component and the only one used for placement.")
DEFAULT_N = 37654          # matched to the owner-reported champion's mass for comparability


def lane_domain(state: dict, *, exclude_catalogue_ring_px: float = 3.0,
                use_claims: bool = False, catalogue: np.ndarray | None = None) -> dict:
    """Everything the lane needs before ranking: masks, components, eligibility."""
    footprint = state["footprint"]
    cat = state["catalogue"] if catalogue is None else np.asarray(catalogue, bool)
    comps = state.get("_comps")
    if comps is None:
        comps = lane.lane_components(state["bands"], state["h52"])
        state["_comps"] = comps
        state["bands"] = None
    covered = lane.lidar_covered(_valid_codes(state), min_fraction=0.5)
    cultural = lane.cultural_mask(state["road"], state["claim"] if use_claims else None)
    eligible = footprint & ~cat & covered & ~cultural["masked"]
    if exclude_catalogue_ring_px:
        eligible &= instrument.distance_px(cat) > float(exclude_catalogue_ring_px)
    return dict(comps=comps, covered=covered, cultural=cultural, eligible=eligible, cat=cat,
                footprint=footprint)


# --------------------------------------------------------------------------- #
# E1: instrument 1 (sgmc_off) -- canaries, size sweep, controls, bootstrap      #
# --------------------------------------------------------------------------- #
def experiment_1(state: dict, *, sizes=(24000, 50000, 80000, 120000, 160000),
                 spacing_px=1.5, draws=1000, chosen_n=None, use_claims=False) -> dict:
    dom = lane_domain(state, use_claims=use_claims)
    footprint, cat, comps = dom["footprint"], dom["cat"], dom["comps"]
    eligible = dom["eligible"]
    truth, truth_receipt = instrument.sgmc_off_truth(state["sgmc"], cat, footprint)
    active = footprint & ~cat
    fold = instrument.fold_for_truth(truth, footprint, cat)

    canaries = {name: instrument.auc(comps[name], truth, active) for name in
                ("amp_max", "amp_mean", "amp_snr", "frac", "step", "crest", "base",
                 "paired_curv", "vergence", "cross", "coh", "relief", "replicate3m")}

    surface = lane.rank01(comps[CHOSEN_SURFACE], eligible)
    arm_dots, arms = {}, {}
    for n in sizes:
        dots = lane.poisson_disk(surface, eligible, n, spacing_px)
        name = f"lane_{n // 1000}k"
        arm_dots[name] = dots
        arms[name] = instrument.terms_for(dots, fold, footprint)
    chosen = chosen_n or DEFAULT_N
    chosen_name = f"lane_{chosen // 1000}k"
    if chosen_name not in arms:
        dots = lane.poisson_disk(surface, eligible, chosen, spacing_px)
        arm_dots[chosen_name] = dots
        arms[chosen_name] = instrument.terms_for(dots, fold, footprint)

    rng = np.random.default_rng(20261011)
    flat = np.flatnonzero(eligible)
    for n in (sizes[-1], chosen):
        rand = np.zeros(eligible.shape, bool)
        rand.ravel()[rng.choice(flat, size=min(n, flat.size), replace=False)] = True
        arm_dots[f"random_{n // 1000}k"] = rand
        arms[f"random_{n // 1000}k"] = instrument.terms_for(rand, fold, footprint)
    terrain = instrument.terrain_matched_control(arm_dots[chosen_name], comps["relief"],
                                                 comps["step"], eligible)
    arm_dots[f"terrain_matched_{chosen // 1000}k"] = terrain
    arms[f"terrain_matched_{chosen // 1000}k"] = instrument.terms_for(terrain, fold, footprint)
    terrain_big = instrument.terrain_matched_control(arm_dots[f"lane_{sizes[-1] // 1000}k"],
                                                     comps["relief"], comps["step"], eligible)
    arm_dots[f"terrain_matched_{sizes[-1] // 1000}k"] = terrain_big
    arms[f"terrain_matched_{sizes[-1] // 1000}k"] = instrument.terms_for(terrain_big, fold, footprint)
    far = np.zeros(eligible.shape, bool)
    far.ravel()[flat[np.argsort(-instrument.distance_px(cat)[eligible])[:chosen]]] = True
    arm_dots[f"distance_only_{chosen // 1000}k"] = far
    arms[f"distance_only_{chosen // 1000}k"] = instrument.terms_for(far, fold, footprint)

    champion = _champion(state)
    champion_note = None
    if champion is not None:
        arr, note = champion
        arm_dots["champion_h33_2_b2"] = arr & active
        arms["champion_h33_2_b2"] = instrument.terms_for(arm_dots["champion_h33_2_b2"], fold, footprint)
        champion_note = note

    # Ablation at a fixed budget: each single component and the pre-declared
    # composite, on instrument 1 only.  This is what rejected the composite; it is
    # recorded as a selection aid, never as a promotion measurement.
    abl_n = 24000
    ablation = {}
    for name in ABLATION_SURFACES:
        surf = (lane.composite(comps, eligible) if name == "declared_composite"
                else lane.rank01(comps[name], eligible))
        d = lane.poisson_disk(surf, eligible, abl_n, spacing_px)
        t = instrument.terms_for(d, fold, footprint)
        ablation[name] = dict(surface=name, dots=abl_n,
                              dti=instrument.pooled_dti(t, n_dots=abl_n)["dti"],
                              credit_per_dot=instrument.credit_per_dot(t, int(d.sum())))

    pooled = instrument.block_bootstrap_arms(arms, candidate=chosen_name, draws=draws)

    # Ring robustness: the evaluator's truth is "off the mapped catalogue" but it still
    # contains cells inside the 3 px halo the lane itself must avoid.  Re-score the
    # decision arms on a stricter truth (>= 800 m from the catalogue) to test whether a
    # gain is just the halo of the mapped pattern rather than off-catalogue discovery.
    strict_truth, strict_receipt = instrument.sgmc_off_truth(state["sgmc"], cat, footprint,
                                                             min_px=8.0)
    strict_fold = instrument.fold_for_truth(strict_truth, footprint, cat)
    strict_names = [chosen_name, f"terrain_matched_{chosen // 1000}k"]
    if champion is not None:
        strict_names.append("champion_h33_2_b2")
    strict_arms = {name: instrument.terms_for(arm_dots[name], strict_fold, footprint)
                   for name in strict_names}
    strict = dict(instrument=strict_receipt,
                  pooled=instrument.block_bootstrap_arms(strict_arms, candidate=chosen_name,
                                                         draws=draws))
    front_mask, front_receipt = instrument.range_front_blocks(cat, comps["relief"], footprint)
    h, w = footprint.shape
    block_side = 200
    ncols = (w + block_side - 1) // block_side
    nrows = (h + block_side - 1) // block_side
    block_front = np.zeros(nrows * ncols, bool)
    fy, fx = np.nonzero(front_mask)                      # ~85k cells, not a full-grid mgrid
    if fy.size:
        block_front[np.unique((fy // block_side) * ncols + (fx // block_side))] = True
    front_share = float(block_front.mean())
    strict["interior"] = instrument.stratified_summary(strict_arms, ~block_front)
    strict["interior_paired"] = instrument.stratified_paired(strict_arms, ~block_front,
                                                             chosen_name, draws=draws)
    out = dict(
        schema="gems64-e1-v1", evidence_class="PROXY-INSTRUMENT (sgmc_off)",
        generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        evaluator_version=evaluate_holdout.VERSION,
        instrument=truth_receipt,
        surface=dict(chosen=CHOSEN_SURFACE, rationale=SURFACE_RATIONALE,
                     weights=None if CHOSEN_SURFACE != "composite" else None),
        domain=dict(eligible_cells=int(eligible.sum()), footprint=int(footprint.sum()),
                    catalogue=int(cat.sum()), lidar_covered=int(dom["covered"].sum()),
                    cultural_masked_in_footprint=int((dom["cultural"]["masked"] & footprint).sum()),
                    claims_masked=bool(use_claims),
                    catalogue_ring_excluded_px=3.0),
        canaries=canaries,
        ablation=ablation,
        ablation_note=("selection aid on instrument 1 only, at 24 000 dots per surface; the chosen "
                       "surface and the controls are compared at the chosen budget on the same fold"),
        arms={name: dict(dots=int(d.sum()), spacing_px=spacing_px) for name, d in arm_dots.items()},
        credit_per_dot={name: instrument.credit_per_dot(t, max(int(arm_dots[name].sum()), 1))
                        for name, t in arms.items()},
        champion=champion_note,
        pooled=pooled,
        stratified=dict(
            interior=instrument.stratified_summary(arms, ~block_front),
            range_front=instrument.stratified_summary(arms, block_front),
            interior_paired=instrument.stratified_paired(arms, ~block_front, chosen_name,
                                                         draws=draws),
            range_front_paired=instrument.stratified_paired(arms, block_front, chosen_name,
                                                            draws=draws)),
        ring_robustness=strict,
        range_front=front_receipt,
        range_front_block_share=front_share,
        selection_contamination=("the surface choice and the size sweep both used this "
                                 "instrument; treat instrument 1 gains as selection-exposed and "
                                 "instrument 2 / controls as the independent checks"),
    )
    _write(EVID / "e1_sgmc_off.json", out)
    return out


def _champion(state: dict):
    path = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
    if not path.exists():
        return None
    arr = read_band(path) > 0
    note = dict(path=str(path.relative_to(ROOT)),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                dots=int(arr.sum()),
                provenance=("sibling artifact whose 0.2778 is owner-reported with no organizer "
                            "receipt; used here only as an arm on the same instrument"))
    return arr, note


# --------------------------------------------------------------------------- #
# E2: instrument 2 (catalogue hide-and-recover, per-fold rebuilt placement)     #
# --------------------------------------------------------------------------- #
def _published_dots(state: dict, footprint: np.ndarray, comps: dict, *, use_claims: bool,
                   n_dots=None, spacing_px=1.5):
    """The exact dot set the emitted artifact carries, if it has been emitted."""
    if not (DOWNLOADS / "publication.marker").exists() and not list(DOWNLOADS.glob("*.tif")):
        return None
    dom = lane_domain(state, use_claims=use_claims)
    surface = lane.rank01(comps[CHOSEN_SURFACE], dom["eligible"])
    return lane.poisson_disk(surface, dom["eligible"], n_dots or DEFAULT_N, spacing_px)


def experiment_2(state: dict, *, n_dots=None, spacing_px=1.5, draws=1000,
                 use_claims=False) -> dict:
    n_dots = n_dots or DEFAULT_N
    dom = lane_domain(state, use_claims=use_claims)
    footprint, cat, comps = dom["footprint"], dom["cat"], dom["comps"]
    ctx, receipt = instrument.catalogue_instrument(cat, footprint)
    champion = _champion(state)
    rng = np.random.default_rng(7)

    arm_terms, per_fold = {}, {}
    for arm in ("lane_candidate", "random_mass_matched", "terrain_matched",
                *(["champion_h33_2_b2"] if champion else [])):
        arm_terms[arm] = None
    for fold in ctx["folds"]:
        # Placement domain and ranking are rebuilt from the VISIBLE catalogue only.
        elig = (footprint & ~fold["visible"] & dom["covered"] & ~dom["cultural"]["masked"]
                & (instrument.distance_px(fold["visible"]) > 3.0))
        surface = lane.rank01(comps[CHOSEN_SURFACE], elig)
        dots = lane.poisson_disk(surface, elig, n_dots, spacing_px)
        terrain = instrument.terrain_matched_control(dots, comps["relief"], comps["step"], elig,
                                                     seed=13 + fold["fold"])
        pool = np.flatnonzero(elig)
        rand = np.zeros(elig.shape, bool)
        rand.ravel()[rng.choice(pool, size=min(n_dots, pool.size), replace=False)] = True
        arms = {"lane_candidate": dots, "random_mass_matched": rand, "terrain_matched": terrain}
        if champion is not None:
            # Scored exactly as submitted: the evaluator already zeroes cells on the
            # visible catalogue, so masking would not change, and cannot flatter, the arm.
            arms["champion_h33_2_b2"] = champion[0]
        fold_row = dict(receipt=fold["receipt"], eligible_cells=int(elig.sum()))
        for name, arr in arms.items():
            terms = instrument.terms_for(arr, fold, footprint)
            arm_terms[name] = terms if arm_terms[name] is None else arm_terms[name] + terms
            fold_row[name] = instrument.pooled_dti(terms, n_dots=int(arr.sum()))
        per_fold[f"fold{fold['fold']}"] = fold_row
    # Structural diagnostic: the artifact that is actually published excludes the FULL
    # catalogue (not just the visible part), so on this instrument it can recover only
    # withheld pixels that happen to lie outside the 3 px ring.  Scored and reported,
    # never mixed into the candidate/control comparison.
    published = _published_dots(state, footprint, comps, use_claims=use_claims)
    if published is not None:
        as_is = {fold["fold"]: instrument.terms_for(published, fold, footprint)
                 for fold in ctx["folds"]}
        per_fold["published_artifact_as_is"] = {
            f"fold{k}": instrument.pooled_dti(v, n_dots=int(published.sum()))["dti"]
            for k, v in as_is.items()}
        per_fold["published_artifact_as_is"]["pooled"] = instrument.pooled_dti(
            sum(as_is.values()), n_dots=int(published.sum()))["dti"]
        per_fold["published_artifact_as_is"]["note"] = (
            "the published artifact is placed with the full catalogue ring excluded, so it cannot "
            "earn credit on withheld traces by construction; this is a structural diagnostic, not a "
            "harm measurement")
    pooled = instrument.block_bootstrap_arms(arm_terms, candidate="lane_candidate", draws=draws)
    out = dict(schema="gems64-e2-v1",
               evidence_class="HOLDOUT-DTI (catalogue hide-and-recover, proxy instrument)",
               generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               evaluator_version=evaluate_holdout.VERSION,
               split="gems57.spatial.folds (label-blind quadrants, 80 px buffer)",
               instrument=receipt,
               candidate=dict(dots=n_dots, spacing_px=spacing_px, surface=CHOSEN_SURFACE,
                              placement="rebuilt per fold from the visible catalogue only"),
               pooled=pooled, per_fold=per_fold,
               note=("the scored catalogue is masked, so this instrument cannot rank "
                     "off-catalogue arms; it is the protocol-mandated no-harm and "
                     "faint-scarp sensitivity check"))
    _write(EVID / "e2_catalogue_hide.json", out)
    return out


# --------------------------------------------------------------------------- #
# E3: emission, registry comparison, writer, gates                             #
# --------------------------------------------------------------------------- #
def experiment_3(state: dict, *, n_dots=None, spacing_px=1.5, draws=1000,
                 use_claims=False, emit=False, submit_name=None, submit_note=None) -> dict:
    from gems57 import gates, validate

    n_dots = n_dots or DEFAULT_N
    dom = lane_domain(state, use_claims=use_claims)
    footprint, cat, comps = dom["footprint"], dom["cat"], dom["comps"]
    eligible = dom["eligible"]
    surface = lane.rank01(comps[CHOSEN_SURFACE], eligible)
    dots = lane.poisson_disk(surface, eligible, n_dots, spacing_px)
    candidate = dots.astype(np.float32)

    registry = registry_policy.compare(state, candidate, footprint, cat)
    out = dict(schema="gems64-e3-v1",
               generated_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
               evaluator_version=evaluate_holdout.VERSION,
               surface=CHOSEN_SURFACE,
               candidate=dict(dots=int(dots.sum()), spacing_px=spacing_px,
                              eligible_cells=int(eligible.sum()),
                              min_catalogue_distance_px=float(
                                  instrument.distance_px(cat)[dots].min()) if dots.any() else None),
               registry=registry, emitted=False)
    if emit:
        if not submit_name or not submit_note:
            raise ValueError("--submit-name and --submit-note are required with --emit")
        if len(submit_name) > 140 or len(submit_note) > 140:
            raise ValueError("the portal limits the name and note to 140 characters each")
        DOWNLOADS.mkdir(parents=True, exist_ok=True)
        target = DOWNLOADS / submit_name
        if target.exists() or target.with_suffix(".zip").exists() or target.with_suffix(".json").exists():
            raise FileExistsError(f"refusing to overwrite {target}")
        receipt = submission_writer.write_submission(
            target, candidate, str(DATA / "sample_submission.tif"), footprint,
            note=submit_note, name=submit_name, catalogue=cat,
            metadata=dict(surface=CHOSEN_SURFACE, dots=int(dots.sum()), spacing_px=spacing_px,
                          lane="native-resolution lidar scarp channels",
                          registry_verdict=registry["verdict"],
                          duplicate_flags=[r["submission"] for r in registry["rows"]
                                           if r.get("duplicate_by_overlap")]))
        out.update(emitted=True, writer_receipt=receipt,
                   validator=receipt["validator"], format_report=receipt["template_report"],
                   zip_file=receipt["zip_file"], receipt_file=target.with_suffix(".json").name,
                   file=str(target.relative_to(ROOT)),
                   sha256=receipt["sha256"], bytes=receipt["bytes"])
    _write(EVID / "e3_emission.json", out)
    return out


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=_jsonable) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")


def _jsonable(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiments", default="e1,e2")
    ap.add_argument("--n-dots", type=int, default=None,
                    help=f"dot budget (default: DEFAULT_N = {37654})")
    ap.add_argument("--spacing", type=float, default=1.5)
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--emit", action="store_true", help="write the TIFF with the shared writer")
    ap.add_argument("--submit-name", default=None)
    ap.add_argument("--submit-note", default=None)
    args = ap.parse_args()
    state = load_all()
    todo = {e.strip().lower() for e in args.experiments.split(",")}
    if "e1" in todo:
        experiment_1(state, draws=args.draws, chosen_n=args.n_dots, spacing_px=args.spacing)
    if "e2" in todo:
        experiment_2(state, n_dots=args.n_dots, spacing_px=args.spacing, draws=args.draws)
    if "e3" in todo:
        experiment_3(state, n_dots=args.n_dots, spacing_px=args.spacing, draws=args.draws,
                     emit=args.emit, submit_name=args.submit_name, submit_note=args.submit_note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
