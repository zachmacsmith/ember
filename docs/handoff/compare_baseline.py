"""
docs/handoff/compare_baseline.py
================================
Re-run the acceptance fingerprints on the current tree and compare
them, cell by cell, with the frozen baseline in docs/handoff/baseline/
(the s3.127 rewrite at the commit that carries this folder). Prints
better / same / worse per cell and per cell class, on the engine's own
answer (tail="none", WORK budgets, so the result never depends on the
machine's load — only on the code).

Usage:
    .venv/bin/python docs/handoff/compare_baseline.py            # all fingerprint cells
    .venv/bin/python docs/handoff/compare_baseline.py smoke      # K8, K10, path60, K100 (~1 min)
    .venv/bin/python docs/handoff/compare_baseline.py board      # + the 10-cell board's `new` arm
                                                                  #   vs baseline/rewrite_board_new-newmm.csv

Tolerances: a cell is "same" within max(0.05, 2% of the baseline ACL);
turán and the dense cells are expected EXACT (template values).
"""
import csv
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "baseline")
DATA = os.path.normpath(os.path.join(HERE, "..", "paper2", "data"))
sys.path.insert(0, DATA)

CLASSES = {
    "dense": ("K8", "K10", "K100", "K140", "spin_glass_n163", "turan_n162"),
    "expander": ("ER100_d10",),
    "lattice": ("grid_200", "honeycomb_200", "king_graph_196", "path60"),
    "small-world/regular": ("ws_n486", "regular_n316"),
}


def _cls(cell):
    for k, cells in CLASSES.items():
        if cell in cells:
            return k
    return "other"


def _verdict(new, old):
    if new is None or old is None:
        return "n/a"
    tol = max(0.05, 0.02 * old)
    if new < old - tol:
        return "BETTER"
    if new > old + tol:
        return "WORSE"
    return "same"


def fingerprints(smoke):
    import plane_fingerprint as pf
    cells = pf.CELLS
    if smoke:
        cells = [c for c in cells if c[0] in ("K8", "K10", "path60", "K100")]
    jobs = [(n, f, s, sd, m, t) for (n, f, s, seeds, m, t) in cells
            for sd in seeds]
    base = {(r["cell"], r["seed"]): r for r in json.load(
        open(os.path.join(BASE, "plane_fingerprint_step6-dedupe.json")))}
    print(f"fingerprints ({len(jobs)} jobs) vs baseline "
          f"plane_fingerprint_step6-dedupe.json")
    rows = []
    with ProcessPoolExecutor(max_workers=min(8, len(jobs))) as ex:
        for row in ex.map(pf._run, jobs):
            rows.append(row)
    print(f"{'cell':<14}{'seed':>5}{'baseline':>10}{'now':>8}  verdict   "
          f"max_chain base/now  certified  stopped_by")
    counts = {}
    for r in rows:
        b = base.get((r["cell"], r["seed"]))
        v = _verdict(r["acl"], b["acl"] if b else None)
        counts.setdefault(_cls(r["cell"]), []).append(v)
        print(f"{r['cell']:<14}{r['seed']:>5}{(b or {}).get('acl'):>10}"
              f"{r['acl']:>8}  {v:<8}  {(b or {}).get('max_chain')}/"
              f"{r['max_chain']}          {r['certified']}      "
              f"{r['stopped_by']}")
    print("\nby class:", {k: dict((x, v.count(x)) for x in set(v))
                          for k, v in counts.items()})
    return rows


def board():
    import rewrite_board as rb
    base = {}
    with open(os.path.join(BASE, "rewrite_board_new-newmm.csv")) as fh:
        for r in csv.DictReader(fh):
            if r["arm"] == "new" and r["acl"] not in ("", "None"):
                base[(r["cell"], int(r["seed"]))] = float(r["acl"])
    jobs = [(c, f, g, "new", s) for (c, f, g) in rb.BOARD
            for s in (rb.DEEP_SEEDS if c in rb.DEEP_CELLS else rb.SEEDS)]
    print(f"\nboard `new` arm ({len(jobs)} jobs) vs baseline "
          f"rewrite_board_new-newmm.csv — this takes a while")
    per_cell = {}
    with ProcessPoolExecutor(max_workers=min(24, len(jobs))) as ex:
        for r in ex.map(rb._run, jobs):
            b = base.get((r["cell"], r["seed"]))
            per_cell.setdefault(r["cell"], []).append((r["acl"], b))
            print(f"{r['cell']:<16} s{r['seed']}: base={b} now={r['acl']} "
                  f"{_verdict(r['acl'], b)}", flush=True)
    print(f"\n{'cell':<16}{'baseline':>10}{'now':>8}  verdict")
    for cell, pairs in per_cell.items():
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        if not pairs:
            continue
        now = sum(a for a, _ in pairs) / len(pairs)
        old = sum(b for _, b in pairs) / len(pairs)
        print(f"{cell:<16}{old:>10.3f}{now:>8.3f}  {_verdict(now, old)}"
              f"  [{_cls(cell)}]")


def main():
    args = sys.argv[1:]
    t0 = time.perf_counter()
    fingerprints(smoke="smoke" in args)
    if "board" in args:
        board()
    print(f"\ndone in {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
