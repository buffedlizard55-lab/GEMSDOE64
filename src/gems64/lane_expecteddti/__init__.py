"""Expected-DTI-optimal selection lane — supplementary modules.

This subpackage holds only what the shared ``gems64`` modules do not already provide.  It keeps
**no private fork** of the grid, the metric, the kernel, the marginal rule, the validator or the
submission writer:

===========================================  ==============================================
need                                          where it comes from
===========================================  ==============================================
grid constants (W/H/EPSG/transform/pixel)     ``gems64.grid`` (imported, not redefined)
footprint / catalogue loaders, band names     :mod:`.gridext` (adds to the shared grid)
kernel, lattice offsets, alpha/beta, DTI      ``gems64.metric`` (imported, not redefined)
marginal rule ``k > alpha*DTI``               ``gems64.metric.marginal_inclusion_threshold``
brute-force metric oracle                     ``gems64.metric.dti_bruteforce``
whole-grid ``best_cover`` / ``kmax_field``    :mod:`.metricext` (adds to the shared metric)
component record with S/M/K, ``dti_algebra``  :mod:`.metricext`
multi-draw exact emitter state                :mod:`.engine`
synthetic-scale verification helpers          :mod:`.emission`
===========================================  ==============================================

``metricext`` also provides thin *adapters* (``dti_binary``, ``dti_bruteforce``) that delegate to
the shared implementations and only rename ``tp``/``fp``/``fn`` to the official subscripted
``TP_w``/``FP_w``/``FN_w`` used in this lane's evidence files.  The arithmetic is the shared
module's, so there is exactly one implementation of the metric in this repository.
"""

from gems64.lane_expecteddti import engine, emission, gridext, metricext  # noqa: F401

__all__ = ["engine", "emission", "gridext", "metricext"]
