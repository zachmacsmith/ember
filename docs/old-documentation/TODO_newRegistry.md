The target state is unambiguously better. The reasons are concrete, not aesthetic.

**Why the current structure is problematic:**

A 590-line `registry.py` that contains algorithm implementations, a registry dict, a base class, a decorator, and validation helpers is doing five different jobs. Any change to any algorithm requires touching the same file. Adding a new algorithm means editing a file that also contains infrastructure code. The PSSA explicit function call pattern is a one-off that doesn't generalise — every new algorithm needs a different registration mechanism.

More practically: the custom algorithm feature you just designed becomes impossible with the current structure. If algorithms live in `registry.py`, you can't load user-defined algorithms dynamically at runtime without importing and modifying that file. The whole user algorithm directory design depends on the import-triggers-registration pattern.

**The target state is correct. Here's the migration precisely:**

**Step 1 — Strip `registry.py` to infrastructure only (~100 lines):**

```python
# registry.py — after migration, contains only:

ALGORITHM_REGISTRY: dict[str, type] = {}

class EmbeddingAlgorithm:
    _requires: list[str] = []
    _binary: Path | None = None
    version: str = ""

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        from ember_qc.algorithms._availability import check_available
        return check_available(cls._requires, cls._binary)

    def embed(self, source_graph, target_graph, **kwargs) -> dict:
        raise NotImplementedError

def register_algorithm(cls):
    ALGORITHM_REGISTRY[cls.name] = cls
    return cls

def list_algorithms():
    for name, cls in ALGORITHM_REGISTRY.items():
        available, reason = cls.is_available()
        yield {'name': name, 'version': cls.version,
               'available': available, 'reason': reason}

def validate_embedding(source_graph, embedding) -> bool:
    ...
```

**Step 2 — Extract each algorithm family into its own file:**

Pull the minorminer variants out of `registry.py` into `algorithms/minorminer_variants.py`. Pull clique into `algorithms/clique.py`. Pull ATOM into `algorithms/atom/atom.py`. Pull OCT variants into `algorithms/oct/oct.py`. Each file gets `@register_algorithm` on its classes directly — no function call pattern, no centralised registration.

**Step 3 — Fix `algorithms/__init__.py`:**

```python
# triggers registration for all built-in algorithms
from ember_qc.algorithms import minorminer_variants  # noqa: F401
from ember_qc.algorithms import clique               # noqa: F401
from ember_qc.algorithms.pssa import improved_pssa   # noqa: F401
from ember_qc.algorithms.charme import charme        # noqa: F401
from ember_qc.algorithms.atom import atom            # noqa: F401
from ember_qc.algorithms.oct import oct              # noqa: F401

# load user custom algorithms
from ember_qc.algorithms._loader import load_user_algorithms
load_user_algorithms()
```

**Step 4 — Fix `registry.py` imports:**

```python
# At bottom of registry.py, after all class/function definitions:
import ember_qc.algorithms  # noqa: F401 — triggers all registrations
```

**One circular import risk to handle:**

`algorithms/minorminer_variants.py` imports `EmbeddingAlgorithm` and `register_algorithm` from `registry.py`. `registry.py` imports `ember_qc.algorithms` at the bottom. This works as long as the `import ember_qc.algorithms` line is at the _bottom_ of `registry.py` — after all the infrastructure classes and functions are defined. If it's at the top, you get a circular import. This is the one thing to verify during migration.

**Migration order to minimise breakage:**

1. Create all the new algorithm files first, with their classes copied in
2. Verify the new files work in isolation (`python -c "from ember_qc.algorithms import minorminer_variants"`)
3. Add `algorithms/__init__.py` imports one at a time, running tests after each
4. Only then strip the implementations out of `registry.py`
5. Run the full test suite

Do it incrementally rather than all at once — the risk of a hard-to-diagnose circular import or missing registration is real if you do it in one large commit.

```
algorithms/
├── __init__.py
├── _availability.py
├── _loader.py
├── minorminer_variants.py    # 4 classes, ~80 lines
├── clique.py                 # 1-2 classes, ~40 lines
├── pssa/
│   ├── __init__.py
│   └── improved_pssa.py      # substantial — your own algorithm
├── charme/
│   ├── __init__.py
│   └── charme.py             # ~50 lines including guard
├── atom/
│   ├── __init__.py
│   └── atom.py               # ~40 lines including binary check
└── oct/
    ├── __init__.py
    └── oct.py                # ~60 lines for 6 variants
```

