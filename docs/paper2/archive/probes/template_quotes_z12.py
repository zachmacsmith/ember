"""
docs/paper2/data/template_quotes_z12.py
=======================================
s3.74 audit purge: fabrics.md §4.4 cited four template constants with no
saved artifact (they were "one-liners against dnx", unsaved). This script
regenerates them the same way zephyr_triad.py part2 computed its quotes:

  - K162 clique template ACL (claimed 12.00 = 2 x turán's 6.00)
  - K184 (= K_max on Z12) clique template ACL (claimed 13.00)
  - K_{80,80} biclique template ACL (claimed 5.5; 16*5 = 80 sharpness)
  - K_{81,81} biclique template ACL (claimed exactly 6.0)

Run:  .venv/bin/python docs/paper2/data/template_quotes_z12.py \
        > docs/paper2/data/template_quotes_z12.log 2>&1
"""
import dwave_networkx as dnx
from minorminer import busclique


def acl(emb):
    return sum(len(c) for c in emb.values()) / len(emb)


def main():
    target = dnx.zephyr_graph(12, 4)
    bc = busclique.busgraph_cache(target)
    big = bc.largest_clique()
    print(f"Z12 K_max = {len(big)} (ACL {acl(big):.2f})", flush=True)
    for k in (162, 184):
        emb = bc.find_clique_embedding(k)
        print(f"K{k} template ACL = {acl(emb):.2f}" if emb
              else f"K{k}: no template", flush=True)
    for a in (80, 81):
        emb = bc.find_biclique_embedding(a, a)
        if emb:
            print(f"K_{{{a},{a}}} template ACL = {acl(emb):.2f}",
                  flush=True)
        else:
            print(f"K_{{{a},{a}}}: no template", flush=True)


if __name__ == "__main__":
    main()
