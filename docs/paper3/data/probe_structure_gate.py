"""
probe_structure_gate.py — the improvement-notes #6 structure-gate probe (v1.2 W4).

Question (item 6, "clmm boundary science"): on Z12, johnson shows the signature
"ate's raw template WINS while clmm's template-SEEDED search LOSES" (ate -0.63 /
clmm +0.23 mean ACL vs MM). Hypothesis: when the source's clique-template
restriction is geometrically good (LOW simulated post-prune score), the right
move is the template itself, not template-seeded search. Candidate v1.3 fix if
supported: a structure gate — prefer template over seeding when the score is low.

Pre-registered read (W4 kickoff): AUC of the TEMPLATE-RESTRICTION SCORE
(simulated post-prune objective / n, computed template-side only via
_template_core's shipped simulator/assignment on zephyr_graph(12)) as a
classifier for the label "ate beats mm AND clmm loses to mm", over >= 30
graphs where all three arms succeeded. LOW score predicts the label.
AUC >= 0.8 -> the structure gate becomes a v1.3 PAPER candidate.

Data: the ARCHIVED Z12 library sweep (§4.11), results/m5full_z12/batch/
results.db, opened READ-ONLY. Families: johnson, kneser, turan, complete,
bipartite, random_planar. ACL column: runs.avg_chain_length (raw ACL; CLI
route — "(instance, trial) pairing [CLI]", single trial, per-arm derived
seeds). Graphs with n > K_max(Z12) = 184 are skipped (no right-sized template).

Mac-only, foreground, no embedding runs. Output: probe_structure_gate.csv +
printed analysis.
"""

import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

import dwave_networkx as dnx
import networkx as nx

from ember_qc.load_graphs import _manifest_by_id, load_graph
from ember_qc.algorithms.paper3 import _template_core as tc

DB = Path("/Users/dabh/ember/results/m5full_z12/batch/results.db")
OUT = Path(__file__).resolve().parent / "probe_structure_gate.csv"
FAMILIES = ("johnson", "kneser", "turan", "complete", "bipartite", "random_planar")
ARMS = ("minorminer", "p3-clmm", "p3-ate")


def rank_auc_low(scores_pos, scores_neg):
    """Hand-rolled Mann-Whitney AUC with midranks; LOW score -> positive.

    Returns P(score_pos < score_neg) + 0.5 * P(tie)."""
    pooled = sorted([(s, 1) for s in scores_pos] + [(s, 0) for s in scores_neg])
    n = len(pooled)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and pooled[j + 1][0] == pooled[i][0]:
            j += 1
        r = 0.5 * (i + j) + 1.0          # average 1-based rank of the tie block
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    r_pos = sum(r for r, (_, lab) in zip(ranks, pooled) if lab == 1)
    npos, nneg = len(scores_pos), len(scores_neg)
    auc_high = (r_pos - npos * (npos + 1) / 2.0) / (npos * nneg)
    return 1.0 - auc_high


def main():
    t_start = time.time()
    fam_of = {gid: e.get("category", "") for gid, e in _manifest_by_id().items()}

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute(
        "SELECT graph_id, graph_name, algorithm, success, avg_chain_length "
        "FROM runs WHERE topology_name='zephyr_12' AND algorithm IN (?,?,?)",
        ARMS).fetchall()
    con.close()

    per = defaultdict(dict)
    gname = {}
    for gid, name, alg, succ, acl in rows:
        if fam_of.get(gid) in FAMILIES:
            per[gid][alg] = (succ, acl)
            gname[gid] = name
    cand = sorted(gid for gid, d in per.items()
                  if len(d) == 3 and all(s and a is not None for s, a in d.values()))
    print(f"candidate graphs (6 families, all three arms succeed): {len(cand)}")

    state = tc.get_target_state(dnx.zephyr_graph(12))
    assert state is not None and state.kmax == 184, "Z12 busclique state"

    recs, skipped = [], defaultdict(int)
    for i, gid in enumerate(cand):
        try:
            G = load_graph(gid)
        except Exception:
            skipped["load_failed"] += 1
            continue
        n = G.number_of_nodes()
        if n < 1:
            skipped["empty"] += 1
            continue
        if n > state.kmax:
            skipped["n_gt_kmax"] += 1
            continue
        tpl = tc.ordered_template(state, n)
        if tpl is None:
            skipped["no_template"] += 1
            continue
        chains, pos = tpl
        verts = tc._sorted_nodes(G)
        slots, info = tc.assign_slots(G, verts, pos)   # shipped simulator+assign
        score = info["obj_final"] / n                  # simulated post-prune ACL
        mm = per[gid]["minorminer"][1]
        clmm = per[gid]["p3-clmm"][1]
        ate = per[gid]["p3-ate"][1]
        recs.append({
            "graph_id": gid, "graph_name": gname[gid], "family": fam_of[gid],
            "n": n, "density": round(nx.density(G), 6), "score": round(score, 4),
            "mm_acl": mm, "ate_acl": ate, "clmm_acl": clmm,
            "d_ate": round(ate - mm, 6), "d_clmm": round(clmm - mm, 6),
            "label": int(ate < mm and clmm > mm),
        })
        if (i + 1) % 200 == 0:
            print(f"  scored {i + 1}/{len(cand)} ({time.time() - t_start:.0f}s)",
                  flush=True)

    cols = list(recs[0].keys())
    with open(OUT, "w") as f:
        f.write(",".join(cols) + "\n")
        for r in recs:
            f.write(",".join(str(r[c]) for c in cols) + "\n")
    print(f"scored {len(recs)} graphs -> {OUT.name}; skipped: {dict(skipped)}")

    pos = [r for r in recs if r["label"]]
    neg = [r for r in recs if not r["label"]]
    print(f"\n== pre-registered read: AUC(low score -> 'ate beats mm AND clmm "
          f"loses to mm') ==")
    print(f"graphs {len(recs)} (positives {len(pos)}, negatives {len(neg)})")
    if len(recs) < 30 or not pos or not neg:
        print("INSUFFICIENT DATA for the AUC read (need >= 30 with both classes)")
    else:
        auc = rank_auc_low([r["score"] for r in pos], [r["score"] for r in neg])
        print(f"AUC = {auc:.3f}   (0.5 = uninformative; >= 0.8 -> structure "
              f"gate becomes a v1.3 PAPER candidate)")

    print(f"\n== per-family score distributions and quadrants "
          f"(d_ate vs d_clmm signs; ACL column: raw avg_chain_length, "
          f"(instance, trial) pairing [CLI]) ==")
    hdr = (f"{'family':<15}{'n':>5}{'pos':>5}{'score.mean':>11}{'med':>7}"
           f"{'min':>7}{'max':>8}{'d_ate.mean':>11}{'d_clmm.mean':>12}"
           f"{'ateW.clmmL':>11}{'ateW.clmmW':>11}{'ateL':>6}")
    print(hdr)
    for famname in FAMILIES:
        fr = [r for r in recs if r["family"] == famname]
        if not fr:
            print(f"{famname:<15}{0:>5}")
            continue
        sc = [r["score"] for r in fr]
        q_pos = sum(r["label"] for r in fr)
        q_ww = sum(1 for r in fr if r["d_ate"] < 0 and r["d_clmm"] < 0)
        q_l = sum(1 for r in fr if r["d_ate"] >= 0)
        print(f"{famname:<15}{len(fr):>5}{q_pos:>5}{mean(sc):>11.3f}"
              f"{median(sc):>7.2f}{min(sc):>7.2f}{max(sc):>8.2f}"
              f"{mean(r['d_ate'] for r in fr):>11.4f}"
              f"{mean(r['d_clmm'] for r in fr):>12.4f}"
              f"{q_pos:>11}{q_ww:>11}{q_l:>6}")

    if pos and neg:
        print(f"\nscore means: positives {mean(r['score'] for r in pos):.3f} "
              f"vs negatives {mean(r['score'] for r in neg):.3f} "
              f"(hypothesis: positives LOWER)")
    jj = [r for r in recs if r["family"] == "johnson"]
    if jj:
        print(f"johnson check (item-6 signature): mean d_ate "
              f"{mean(r['d_ate'] for r in jj):+.3f}, mean d_clmm "
              f"{mean(r['d_clmm'] for r in jj):+.3f}, mean score "
              f"{mean(r['score'] for r in jj):.3f} vs all-family "
              f"{mean(r['score'] for r in recs):.3f}")
    print(f"\ndone in {time.time() - t_start:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
