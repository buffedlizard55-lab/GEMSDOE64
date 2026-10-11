"""E1 (gating, per lane brief): verify the DTI decision rule numerically on
synthetic rasters BEFORE it is used on real data.

Writes evidence/e1_theorem.json and exits non-zero if any check fails.
"""
from __future__ import annotations
import json, sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from gems64 import theorem

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main() -> int:
    t0 = time.time()
    r1 = theorem.check_threshold_rule(dti=0.30, alpha=0.2)
    r1b = theorem.check_threshold_rule(dti=0.30, alpha=0.5)
    r2 = theorem.check_lipton_generalisation(alpha=0.5)
    r2b = theorem.check_lipton_generalisation(alpha=0.2, seed=11)
    r3 = [theorem.check_greedy_vs_exhaustive(seed=s) for s in (3, 5, 17)]
    out = dict(
        experiment="E1-theorem",
        elapsed_s=round(time.time() - t0, 2),
        threshold_rule_alpha02=r1, threshold_rule_alpha05=r1b,
        lipton_alpha05=r2, lipton_alpha02=r2b, greedy_vs_exhaustive=r3,
        all_ok=bool(all([r1["ok"], r1b["ok"], r2["ok"], r2b["ok"]] +
                        [x["ok"] for x in r3])),
    )
    (ROOT / "evidence" / "e1_theorem.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return 0 if out["all_ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
