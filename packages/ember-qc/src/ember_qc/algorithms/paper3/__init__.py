"""paper3 algorithm arms (registered as ``p3-*``).

Every module in this directory is auto-imported below, so implementation
work only ever ADDS files here — no shared-line edits, no merge conflicts
across parallel worktrees. Each module registers its arms via
``@register_algorithm("p3-<name>")`` at import time.

Branch charter and measurement rules: docs/paper3/protocol.md.
"""

import importlib
import pkgutil

for _mod in pkgutil.iter_modules(__path__):
    if not _mod.name.startswith("_"):
        importlib.import_module(f"{__name__}.{_mod.name}")
