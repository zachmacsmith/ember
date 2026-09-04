"""
docs/paper2/data/plane_fingerprint.py
=====================================
The rewrite's acceptance harness (s3.127). Fingerprints, tail="none",
WORK budgets (max_asks) so the numbers never depend on the box's load:

  K8 / K10 on Z3          certified, mm_skipped, extensions == 0, ACL
  path-60 on Z12          1.017 (single bars via orientation)
  K100 on Z12             7.26 (the clique template)
  turán n162 on Z12       6.000 / max 6 from a RANDOM init, seeds 0-9
  grid_200 on Z12         pre-tail ACL (a floor to stay under: 1.76)

Run it on the current default at step 0 (record), then after every
checkpoint. Any kwargs the engine under test does not know are ignored
by attract_embed, so the same call works for the old and new engines
(`init_mode="random"` is the old engine's random start; the new engine
is random by construction).

Run:  .venv/bin/python docs/paper2/data/plane_fingerprint.py [tag]
Sentinel: done-fingerprint.
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = next((a.split("=", 1)[1] for a in sys.argv[1:]
               if a.startswith("engine=")), None)

CELLS = [
    # name, fabric, loader, seeds, max_asks, timeout
    ("K8", "Z3", ("complete", 8), (0,), 2000, 120),
    ("K10", "Z3", ("complete", 10), (0,), 2000, 120),
    ("path60", "Z12", ("path", 60), (0,), 3000, 300),
    ("K100", "Z12", ("complete", 100), (0,), 10000, 900),
    ("turan_n162", "Z12", ("gid", 2647), tuple(range(10)), 15000, 900),
    ("grid_200", "Z12", ("gid", 1590), (0,), 8000, 900),
]


def _load(spec):
    import networkx as nx
    kind, arg = spec
    if kind == "complete":
        return nx.complete_graph(arg)
    if kind == "path":
        return nx.path_graph(arg)
    from ember_qc.load_graphs import load_graph
    return nx.convert_node_labels_to_integers(load_graph(arg))


def _run(job):
    name, fabric, spec, seed, max_asks, timeout = job
    os.nice(10)
    import dwave_networkx as dnx
    from ember_qc.algorithms.factored import attract_embed
    src = _load(spec)
    tgt = (dnx.zephyr_graph(3, 4) if fabric == "Z3"
           else dnx.zephyr_graph(12, 4))
    t0 = time.perf_counter()
    kw = {"engine": ENGINE} if ENGINE else {}
    r = attract_embed(src, tgt, timeout=timeout, seed=seed, tail="none",
                      max_asks=max_asks, init_mode="random", **kw)
    emb = r.get("embedding") or {}
    d = r.get("diag", {})
    acl = (round(sum(len(c) for c in emb.values()) / len(emb), 3)
           if emb else None)
    mx = max((len(c) for c in emb.values()), default=None)
    return dict(cell=name, seed=seed, acl=acl, max_chain=mx,
                certified=d.get("certified"), mm_skipped=d.get("mm_skipped"),
                extensions=d.get("extensions"), asks=d.get("asks"),
                bookmark_asks=d.get("bookmark_asks"),
                stopped_by=d.get("stopped_by"), pen=d.get("judge_pen",
                                                          d.get("pen")),
                stair=d.get("plane_stair", d.get("stair")),
                error=(r.get("error") or "")[:60] or None,
                wall=round(time.perf_counter() - t0, 1))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("engine=")]
    tag = args[0] if args else time.strftime("%m%d-%H%M")
    jobs = [(n, f, s, sd, m, t) for (n, f, s, seeds, m, t) in CELLS
            for sd in seeds]
    print(f"fingerprint {tag}: {len(jobs)} jobs; load {os.getloadavg()}",
          flush=True)
    rows = []
    with ProcessPoolExecutor(max_workers=min(16, len(jobs))) as ex:
        for row in ex.map(_run, jobs):
            print(f"{row['cell']:<12} s{row['seed']}: acl={row['acl']} "
                  f"mx={row['max_chain']} cert={row['certified']} "
                  f"mmskip={row['mm_skipped']} ext={row['extensions']} "
                  f"asks={row['asks']} bm={row['bookmark_asks']} "
                  f"stop={row['stopped_by']} pen={row['pen']} "
                  f"stair={row['stair']} err={row['error']} "
                  f"({row['wall']}s)", flush=True)
            rows.append(row)
    out = os.path.join(HERE, f"plane_fingerprint_{tag}.json")
    json.dump(rows, open(out, "w"), indent=1)
    tur = [r for r in rows if r["cell"] == "turan_n162"]
    hits = sum(1 for r in tur if r["acl"] == 6.0 and r["max_chain"] == 6)
    print(f"\nturán crystal hits: {hits}/{len(tur)}")
    print("wrote", out)
    print("done-fingerprint", flush=True)


if __name__ == "__main__":
    main()
