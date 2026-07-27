# Importing each module triggers @register_algorithm decorators,
# populating ALGORITHM_REGISTRY in registry.py.
from ember_qc.algorithms import minorminer   # noqa: F401
from ember_qc.algorithms import charme       # noqa: F401
from ember_qc.algorithms import atom         # noqa: F401
from ember_qc.algorithms import oct          # noqa: F401
from ember_qc.algorithms import pssa         # noqa: F401
from ember_qc.algorithms import minorminer_forked  # noqa: F401
from ember_qc.algorithms import factored     # noqa: F401
from ember_qc.algorithms import paper3       # noqa: F401

# Load any user-defined custom algorithms from the user data directory.
from ember_qc.algorithms._loader import load_user_algorithms
load_user_algorithms()
