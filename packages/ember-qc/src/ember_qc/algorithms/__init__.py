# Importing each module triggers @register_algorithm decorators,
# populating ALGORITHM_REGISTRY in registry.py.
from ember_qc.algorithms import minorminer   # noqa: F401
from ember_qc.algorithms import charme       # noqa: F401
from ember_qc.algorithms import atom         # noqa: F401
from ember_qc.algorithms import oct          # noqa: F401
from ember_qc.algorithms import pssa         # noqa: F401
from ember_qc.algorithms import reweave   # noqa: F401  (base engine + reweave-base)

# Candidate algorithms exploring CLAUDE.md §3.1-3.4 (see docs/candidate-algorithms/).
# These import their heavy optional deps (POT / torch / OR-Tools) lazily inside
# embed(), so registering the classes here is safe even when those deps are absent.
from ember_qc.algorithms import srgw         # noqa: F401  (3.1 srGW; needs POT)
from ember_qc.algorithms import diffembed    # noqa: F401  (3.2 differentiable; needs torch)
from ember_qc.algorithms import multilevel   # noqa: F401  (3.3 multilevel V-cycle)
from ember_qc.algorithms import lns_cpsat    # noqa: F401  (3.4 LNS + CP-SAT; needs OR-Tools)

# Production Reweave family (reweave / -thorough / -stacked / -cold), wrapping
# the base engine with the verified optimizations (bounded routing + dirty-set +
# spur). Imported after the candidates so the multilevel placement that
# reweave-stacked seeds from is registered first.
from ember_qc.algorithms import reweave_opt  # noqa: F401

# Search-guidance variants: the vertex-ordering lever (rw_order: reweave-cold-<order>)
# and the rip-up-selection lever (rw_ripup: reweave-ripup-<policy>). Both build on
# the optimized router, so they import after reweave_opt.
from ember_qc.algorithms import rw_order      # noqa: F401  (ordering lever)
from ember_qc.algorithms import rw_ripup      # noqa: F401  (rip-up selection lever)
from ember_qc.algorithms import minorminer_guided  # noqa: F401  (order-guided MM via quickpass)
from ember_qc.algorithms import minorminer_forked  # noqa: F401  (order-guided MM via the var_order fork)

# Load any user-defined custom algorithms from the user data directory.
from ember_qc.algorithms._loader import load_user_algorithms
load_user_algorithms()
