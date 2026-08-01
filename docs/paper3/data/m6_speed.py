"""§4.13: idle workers=1 speed table (protocol rule 5).

Run on an IDLE machine: .venv/bin/python docs/paper3/data/m6_speed.py
Strictly sequential; writes m6_speed.csv + m6_speed_summary.txt.
"""
from __future__ import annotations

import csv
import os
import statistics as st
import sys
import time
from collections import defaultdict

import networkx as nx
import dwave_networkx as dnx

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _runner_common import make_instance, terminal_polish  # noqa: E402

from ember_qc.benchmark import benchmark_one  # noqa: E402

CELLS = [("P16", 100, 0.3), ("P16", 140, 0.2), ("P16", 140, 1.0),
         ("P16", 160, 0.05), ("Z12", 100, 0.3), ("Z12", 140, 1.0)]
ARMS = ("minorminer", "minorminer-layout", "p3-template", "p3-ate",
        "p3-clmm", "p3-mmpolish")
INST = (101, 102, 103)
SEEDS = (10, 11)
TIMEOUT = 60.0

def main() -> None:
    targets = {"P16": dnx.pegasus_graph(16), "Z12": dnx.zephyr_graph(12)}
    here = os.path.dirname(os.path.abspath(__file__))
    rows = []
    with open(os.path.join(here, "m6_speed.csv"), "w", newline="") as fh:
        wcsv = csv.writer(fh)
        wcsv.writerow(["topo", "n", "p", "inst", "arm", "seed", "success",
                       "acl", "wall"])
        for topo, n, p in CELLS:
            insts = INST if p < 1.0 else (101,)
            for i in insts:
                src = make_instance(n, p, i)
                for arm in ARMS:
                    for s in SEEDS:
                        t0 = time.perf_counter()
                        r = benchmark_one(src, targets[topo], arm,
                                          timeout=TIMEOUT, seed=s)
                        wall = time.perf_counter() - t0
                        ok = int(bool(r.success))
                        acl = r.avg_chain_length if ok else ""
                        wcsv.writerow([topo, n, p, i, arm, s, ok, acl,
                                       f"{wall:.3f}"])
                        fh.flush()
                        rows.append((topo, n, p, arm, ok, wall))
                        print(f"{topo} n{n} p{p} i{i} {arm} s{s}: "
                              f"{'OK' if ok else 'FAIL'} {wall:.1f}s",
                              flush=True)
    out = ["idle workers=1 speed table (median wall s over inst x seeds)", ""]
    byc = defaultdict(lambda: defaultdict(list))
    for topo, n, p, arm, ok, wall in rows:
        byc[(topo, n, p)][arm].append(wall)
    hdr = f"{'cell':18s}" + "".join(f"{a:>18s}" for a in ARMS)
    out += [hdr, "-" * len(hdr)]
    for cell in CELLS:
        line = f"{cell[0]}({cell[1]},{cell[2]}):".ljust(18)
        for a in ARMS:
            w = byc[cell].get(a, [])
            line += f"{st.median(w):18.1f}" if w else f"{'--':>18s}"
        out.append(line)
    text = "\n".join(out)
    print("\n" + text)
    with open(os.path.join(here, "m6_speed_summary.txt"), "w") as fh:
        fh.write(text + "\n")
    print("\nSPEED_TABLE_DONE")

if __name__ == "__main__":
    main()
