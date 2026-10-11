"""GEMSDOE64 — Expected-DTI-optimal hidden-fault prediction for the DOE GEMS Prize.

DrivenData competition 306.  Lane: *Expected-DTI-optimal selection* — replace heuristic dot
spacing with a decision rule derived from the competition's own metric, verified numerically
before it is ever pointed at a submission slot.

Submodules
----------
``grid``      canonical grid, footprint, catalogue and scored-domain constants, all measured
              from the hash-pinned official rasters.
``metric``    an independent re-implementation of the official DTI metric plus the closed-form
              algebra (``dti_algebra``) and the marginal-gain rule (``expected_gain``).
``emission``  exact greedy emission machinery used to validate the rule on synthetic rasters.

``scripts/emit_and_ship.py`` holds the production emitter (its ``Ensemble`` class carries the
sparse multi-draw state needed at full grid scale) and is importable as a module.
"""

__all__ = ["grid", "metric", "emission"]
__version__ = "1.0.0"
