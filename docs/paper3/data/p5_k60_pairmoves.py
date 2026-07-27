"""
docs/paper3/data/p5_k60_pairmoves.py
=====================================
P5b-dense — the pre-registered K60 kill-gate probe (proposals/polish.md).

Question: does ANY exact bounded-region move — single-vertex (x1) or the NEW
joint source-adjacent pair move (x2) — improve the K60 clique-template
embedding on Pegasus-16 that §3.26 showed minorminer's full grind cannot
improve? Zero improving pair moves = the pre-registered negative (move-set
completeness evidence for the regime thesis); any improving move is
headline-relevant.

Object under test: the §3.26 template-arm output — busclique K60 chains,
identity assignment, spur-pruned against the (complete) source. The probe
FIRST measures whether that spur-prune is actually a no-op at this scale (the
proposal assumed it is; smoke runs on undersized cliques C4/K12 and P4/K20
showed busclique leaves prunable coverage redundancy, so this is recorded as
data, and all sweeps run on the PRUNED template so x1/x2 counts measure moves
*beyond* the cheap pass).

Sweeps (all deterministic, no seeds):
  x1: exact_repair_1 on every vertex (60), radius 2, each from the same base.
  x2: joint_repair_2 on source-adjacent pairs (K60 -> all 1770 pairs; in a
      valid embedding every source-adjacent pair's chains touch). Pairs are
      ordered by (-combined chain length, u, v); if the projected runtime
      exceeds the budget the sweep truncates to the first 400 pairs in that
      order (the pre-registered subsample rule).

Every move is evaluated against the SAME base embedding, so counts read as
"improving moves available on the template". CSV (one flushed row per move,
--resume supported) next to this file: p5_k60_pairmoves.csv.

Run:
  .venv/bin/python docs/paper3/data/p5_k60_pairmoves.py            # the probe
  .venv/bin/python docs/paper3/data/p5_k60_pairmoves.py --smoke    # K20 on P4
Flags: --smoke | --resume | --limit N | --pair-cap S | --budget-min M
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_var, "1")

import argparse
import sys
import time

import networkx as nx

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from _runner_common import acl, append_row, build_target, load_done_keys, \
    stringify_key  # noqa: E402

from ember_qc.embedding_backend import build_adjacency, is_valid_embedding  # noqa: E402
from ember_qc.algorithms.factored.polish import spur_prune  # noqa: E402
from ember_qc.algorithms.paper3.joint_repair import (  # noqa: E402
    exact_repair_1, joint_repair_2,
)

CSV_MAIN = os.path.join(HERE, "p5_k60_pairmoves.csv")
CSV_SMOKE = os.path.join(HERE, "p5_k60_pairmoves_smoke.csv")

FIELDS = ["topo", "n", "kind", "u", "v", "old_total", "new_total", "improved",
          "subset_of_old", "proven", "region", "nodes", "time"]
KEY_FIELDS = ["topo", "n", "kind", "u", "v"]

PAIR_CAP_S = 5.0          # per-move solver deadline
BUDGET_MIN = 28.0         # soft wall budget; overflow triggers the pre-
SUBSAMPLE = 400           # registered truncation to the first 400 pairs
CALIBRATE_AFTER = 50      # pairs measured before the runtime projection


def template_embedding(topo_name, n):
    """The §3.26 template-arm object: busclique K_n chains, identity
    assignment, spur-pruned against the (complete) source. Returns
    (pruned_embedding, source, target, adj, prune_removed_qubits)."""
    from minorminer.busclique import busgraph_cache
    if topo_name == "P4":            # smoke topology (not an E0 grid member)
        import dwave_networkx as dnx
        target = dnx.pegasus_graph(4)
    else:
        target = build_target(topo_name)
    cache = busgraph_cache(target)
    raw = cache.find_clique_embedding(n)
    chain_list = [[int(q) for q in raw[key]] for key in sorted(raw)]
    emb = {i: chain_list[i] for i in range(n)}
    source = nx.complete_graph(n)
    adj = build_adjacency(target)
    assert is_valid_embedding(emb, source, target, adj=adj), "raw template invalid"
    src_adj = {v: sorted(source.neighbors(v)) for v in source.nodes()}
    pruned = spur_prune(emb, src_adj, adj, deadline=time.perf_counter() + 120)
    assert is_valid_embedding(pruned, source, target, adj=adj), "pruned invalid"
    removed = sum(len(c) for c in emb.values()) - sum(len(c) for c in pruned.values())
    return pruned, source, target, adj, removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="K20 on P4 (fast)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="hard cap on pairs (0 = adaptive: all 1770, "
                         f"truncated to {SUBSAMPLE} if projected over budget)")
    ap.add_argument("--pair-cap", type=float, default=PAIR_CAP_S)
    ap.add_argument("--budget-min", type=float, default=BUDGET_MIN)
    args = ap.parse_args()

    topo, n = ("P4", 20) if args.smoke else ("P16", 60)
    csv_path = CSV_SMOKE if args.smoke else CSV_MAIN
    t_start = time.perf_counter()

    print(f"[p5] building {topo} + busclique K{n} template "
          f"(cold busgraph_cache may take a while)...", flush=True)
    emb, source, target, adj, prune_removed = template_embedding(topo, n)
    total0 = sum(len(c) for c in emb.values())
    print(f"[p5] template: acl={acl(emb):.4f} qubits={total0} "
          f"spur_prune_removed={prune_removed} "
          f"({'NO-OP confirmed' if prune_removed == 0 else 'NOT a no-op'})",
          flush=True)

    done = load_done_keys(csv_path, KEY_FIELDS) if args.resume else set()

    def emit(kind, u, v, out, dt):
        subset = 0
        if out.improved:
            old_set = set(emb[u]) | (set(emb[v]) if v >= 0 else set())
            new_set = set(out.embedding[u]) | (
                set(out.embedding[v]) if v >= 0 else set())
            subset = int(new_set <= old_set)
        append_row(csv_path, FIELDS, {
            "topo": topo, "n": n, "kind": kind, "u": u, "v": v,
            "old_total": out.old_total, "new_total": out.new_total,
            "improved": int(out.improved), "subset_of_old": subset,
            "proven": int(out.proven), "region": out.region_size,
            "nodes": out.nodes, "time": round(dt, 4)})

    # ── x1 sweep ──────────────────────────────────────────────────────────────
    x1_improved = set()
    x1_unproven = 0
    for v in range(n):
        if stringify_key(topo, n, "x1", v, -1) in done:
            continue
        t0 = time.perf_counter()
        out = exact_repair_1(emb, source, target, v, radius=2,
                             deadline=t0 + args.pair_cap)
        if out.improved:
            x1_improved.add(v)
            assert is_valid_embedding(out.embedding, source, target, adj=adj)
        x1_unproven += not out.proven
        emit("x1", v, -1, out, time.perf_counter() - t0)
    print(f"[p5] x1 sweep done: improving={len(x1_improved)}/{n} "
          f"unproven={x1_unproven} elapsed={time.perf_counter()-t_start:.0f}s",
          flush=True)

    # ── x2 sweep (pre-registered ordering + subsample rule) ───────────────────
    pairs = sorted(((u, v) for u in range(n) for v in range(u + 1, n)),
                   key=lambda p: (-(len(emb[p[0]]) + len(emb[p[1]])),
                                  p[0], p[1]))
    if args.limit:
        pairs = pairs[:args.limit]
    x2_improved = []
    x2_beyond_x1 = []
    x2_unproven = 0
    truncated = False
    n_done = 0
    for i, (u, v) in enumerate(pairs):
        if not truncated and args.limit == 0 and n_done == CALIBRATE_AFTER:
            elapsed = time.perf_counter() - t_start
            per_pair = elapsed / max(1, n_done)
            projected = elapsed + per_pair * (len(pairs) - n_done)
            if projected > args.budget_min * 60.0:
                pairs = pairs[:SUBSAMPLE]
                truncated = True
                print(f"[p5] projected {projected/60:.0f} min > budget "
                      f"{args.budget_min:.0f} min -> truncating to first "
                      f"{SUBSAMPLE} pairs (pre-registered rule)", flush=True)
                if i >= len(pairs):
                    break
        if i >= len(pairs):
            break
        if stringify_key(topo, n, "x2", u, v) in done:
            n_done += 1
            continue
        t0 = time.perf_counter()
        out = joint_repair_2(emb, source, target, u, v, radius=2,
                             deadline=t0 + args.pair_cap)
        if out.improved:
            x2_improved.append((u, v, out.old_total - out.new_total))
            assert is_valid_embedding(out.embedding, source, target, adj=adj)
            if u not in x1_improved and v not in x1_improved:
                x2_beyond_x1.append((u, v))
        x2_unproven += not out.proven
        emit("x2", u, v, out, time.perf_counter() - t0)
        n_done += 1

    elapsed = time.perf_counter() - t_start
    print("\n[p5] ==================== VERDICT ====================")
    print(f"[p5] {topo} K{n} template (post spur-prune, qubits={total0}, "
          f"prune removed {prune_removed})")
    print(f"[p5] x1 improving moves : {len(x1_improved)}/{n} "
          f"(unproven {x1_unproven})")
    print(f"[p5] x2 improving moves : {len(x2_improved)}/{len(pairs)} pairs"
          f"{' [TRUNCATED]' if truncated else ''} (unproven {x2_unproven})")
    print(f"[p5] x2 beyond x1       : {len(x2_beyond_x1)} "
          "(pairs where neither endpoint improves alone)")
    if x2_improved:
        saved = [s for _, _, s in x2_improved]
        print(f"[p5] qubits saved per improving pair: min={min(saved)} "
              f"max={max(saved)}")
    print(f"[p5] wall: {elapsed/60:.1f} min; csv: {os.path.basename(csv_path)}")
    print("[p5] =================================================")


if __name__ == "__main__":
    main()
