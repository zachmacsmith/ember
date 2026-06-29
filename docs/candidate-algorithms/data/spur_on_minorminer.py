"""
Standalone spur-pruning as a cheap improver for plain `minorminer`.

For every (cell, seed) in the eval_variant grid: run minorminer, apply
prune_spurs to its raw embedding, and report ACL before/after, validity, and the
wall-clock cost of the prune itself. This is the "cheap shadow of lns-cpsat":
spur-pruning recovers a similar ACL gain in microseconds instead of CP-SAT
seconds.
"""
from __future__ import annotations
import os, sys, time, statistics as st, warnings
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from eval_candidate import make_targets, make_source  # noqa: E402

from ember_qc.registry import ALGORITHM_REGISTRY                       # noqa: E402
from ember_qc.algorithms.pf_spur import prune_spurs                    # noqa: E402
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402

SEEDS = [0, 1, 2]
GRID = [
    ("ER", 20, 0.5, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6"), ("ER", 30, 0.7, "pegasus_6"),
    ("ER", 40, 0.5, "pegasus_6"), ("ER", 40, 0.7, "pegasus_6"),
    ("ER", 30, 0.5, "pegasus_6_broken5"),
    ("ER", 30, 0.5, "zephyr_4"),
]
LAB = {"pegasus_6": "P6", "pegasus_6_broken5": "P6brk", "zephyr_4": "Z4"}


def acl(emb):
    return st.mean(len(c) for c in emb.values())


def main():
    mm = ALGORITHM_REGISTRY["minorminer"]
    targets = make_targets()
    adjs = {t: build_adjacency(g) for t, g in targets.items()}
    rows = []
    for (fam, n, p, tname) in GRID:
        src = make_source(fam, n, p)
        tgt = targets[tname]
        adj = adjs[tname]
        cell = f"{fam}_n{n}_d{p}_{LAB[tname]}"
        for s in SEEDS:
            res = mm.embed(src, tgt, timeout=60.0, seed=s)
            emb = res.get("embedding") or {}
            if not emb or not is_valid_embedding(emb, src, tgt, adj=adj):
                rows.append((cell, s, None, None, None, None))
                continue
            a0 = acl(emb)
            t0 = time.perf_counter()
            pr = prune_spurs(emb, src, tgt, adj=adj)
            dt = time.perf_counter() - t0
            ok = is_valid_embedding(pr, src, tgt, adj=adj)
            rows.append((cell, s, a0, acl(pr), ok, dt))

    # aggregate per cell
    cells = list(dict.fromkeys(c for (c, *_ ) in rows))
    print(f"\n{'cell':18s} {'mm_ACL':>7s} {'pruned':>7s} {'gain%':>7s} {'prune_s':>9s} {'valid':>6s}")
    print("-" * 60)
    gains = []
    prune_times = []
    for cell in cells:
        rs = [r for r in rows if r[0] == cell and r[2] is not None]
        if not rs:
            print(f"{cell:18s}   (no valid minorminer embeddings)")
            continue
        a0 = st.mean(r[2] for r in rs)
        a1 = st.mean(r[3] for r in rs)
        g = 100 * (a1 - a0) / a0
        dt = st.mean(r[5] for r in rs)
        allok = all(r[4] for r in rs)
        gains.append(g)
        prune_times.append(dt)
        print(f"{cell:18s} {a0:7.3f} {a1:7.3f} {g:+6.1f}% {dt*1e3:8.2f}ms {str(allok):>6s}")
    print("=" * 60)
    print(f"GRID MEAN minorminer+prune vs minorminer: ACL {st.mean(gains):+.1f}%  "
          f"mean prune time {st.mean(prune_times)*1e3:.2f} ms/embedding")


if __name__ == "__main__":
    main()
