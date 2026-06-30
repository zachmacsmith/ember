"""
docs/candidate-algorithms/data/success_probe.py
===============================================
Drop-in-safety check for the order-guided minorminer variants. A single fixed
order reused across all `tries` restarts removes the order diversity stock MM
relies on, so a guided run *could* fail where stock MM succeeds. We force MM into
its *partial-success* regime (a deliberately short timeout on denser cells) and
compare success rates:

  minorminer            stock MM (baseline reliability)
  mmfork-cuthill-nofb   fixed Cuthill order, NO fallback (isolates the risk)
  mmfork-cuthill        fixed order WITH the stock-MM fallback (the shipped variant)
  mmfork-portfolio      always includes a stock-MM config

Expectation: -nofb may dip below MM; -cuthill (fallback) and -portfolio match or
exceed MM. Confirms the shipped variants are >= minorminer in success — genuine
drop-ins, unlike constructive embedders (ATOM) that fail outright.

Usage:  python success_probe.py [--smoke] [timeout]
"""
from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

from ember_qc.registry import ALGORITHM_REGISTRY  # noqa: E402
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.search_orders import ORDERINGS  # noqa: E402
from ember_qc.algorithms.minorminer_forked import forked_find_embedding  # noqa: E402

# Denser cells that, under a short timeout, push stock MM into partial success.
GRID = [
    ("ER", 70, 0.5, "pegasus_6"), ("ER", 80, 0.5, "pegasus_6"),
    ("ER", 60, 0.6, "pegasus_6"), ("ER", 55, 0.7, "pegasus_6"),
]
SMOKE = [("ER", 70, 0.5, "pegasus_6")]
SEEDS = list(range(8))


def _emb(algo, src, tgt, t, s):
    if algo == "mmfork-cuthill-nofb":
        r = forked_find_embedding(src, tgt, order=ORDERINGS["cuthill"](src),
                                  seed=s, timeout=t, fallback=False)
    elif algo == "mmfork-cuthill":
        r = forked_find_embedding(src, tgt, order=ORDERINGS["cuthill"](src),
                                  seed=s, timeout=t, fallback=True)
    else:
        r = ALGORITHM_REGISTRY[algo].embed(src, tgt, timeout=t, seed=s)
    return (r or {}).get("embedding") or None


def main():
    smoke = "--smoke" in sys.argv
    rest = [a for a in sys.argv[1:] if a != "--smoke"]
    timeout = float(rest[0]) if rest else 4.0
    grid = SMOKE if smoke else GRID
    seeds = SEEDS[:3] if smoke else SEEDS
    targets = make_targets()
    # Portfolio omitted here: it always includes a stock-MM config so it is >= MM
    # by construction; this probe isolates the single fixed-order risk + fallback.
    algos = ["minorminer", "mmfork-cuthill-nofb", "mmfork-cuthill"]
    tot = {a: 0 for a in algos}
    print(f"success rate (timeout={timeout}s, {len(seeds)} seeds/cell)\n")
    print(f"{'cell':16s} " + " ".join(f"{a:20s}" for a in algos))
    for (fam, n, p, tname) in grid:
        src = make_source(fam, n, p); tgt = targets[tname]
        adj = build_adjacency(tgt)
        cell = f"{fam}_n{n}_d{p}"
        sc = {a: 0 for a in algos}
        for s in seeds:
            for a in algos:
                e = _emb(a, src, tgt, timeout, s)
                if e and is_valid_embedding(e, src, tgt, adj=adj):
                    sc[a] += 1; tot[a] += 1
        print(f"{cell:16s} " + " ".join(f"{str(sc[a])+'/'+str(len(seeds)):20s}" for a in algos))
    print("\nTOTAL          " + " ".join(f"{str(tot[a])+'/'+str(len(seeds)*len(grid)):20s}" for a in algos))


if __name__ == "__main__":
    main()
