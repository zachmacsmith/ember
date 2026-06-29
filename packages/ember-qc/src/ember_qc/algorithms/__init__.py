# Importing each module triggers @register_algorithm decorators,
# populating ALGORITHM_REGISTRY in registry.py.
from ember_qc.algorithms import minorminer   # noqa: F401
from ember_qc.algorithms import charme       # noqa: F401
from ember_qc.algorithms import atom         # noqa: F401
from ember_qc.algorithms import oct          # noqa: F401
from ember_qc.algorithms import pssa         # noqa: F401
from ember_qc.algorithms import pathfinder   # noqa: F401

# Candidate algorithms exploring CLAUDE.md §3.1-3.4 (see docs/candidate-algorithms/).
# These import their heavy optional deps (POT / torch / OR-Tools) lazily inside
# embed(), so registering the classes here is safe even when those deps are absent.
from ember_qc.algorithms import srgw         # noqa: F401  (3.1 srGW; needs POT)
from ember_qc.algorithms import diffembed    # noqa: F401  (3.2 differentiable; needs torch)
from ember_qc.algorithms import multilevel   # noqa: F401  (3.3 multilevel V-cycle)
from ember_qc.algorithms import lns_cpsat    # noqa: F401  (3.4 LNS + CP-SAT; needs OR-Tools)

# Load any user-defined custom algorithms from the user data directory.
from ember_qc.algorithms._loader import load_user_algorithms
load_user_algorithms()
