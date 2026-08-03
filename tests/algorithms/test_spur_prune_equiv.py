"""W1b gate: the clean-chain-skip spur_prune must be OUTPUT-IDENTICAL to the
stock implementation (deadline-free). Corpus: pre-prune template chains on
three Z12/P16 dev-suite instances + 20 MM-embedding fuzz cases + crafted
edge cases (unplaced neighbours, empty/singleton chains, star hubs).

``_spur_prune_reference`` below is a VERBATIM copy of the pre-W1b
implementation (factored/polish.py @ 0a317117). Any mismatch on any case
means W1b must be reverted entirely.
"""

import time

import networkx as nx
import dwave_networkx as dnx
import pytest

from ember_qc.embedding_backend import build_adjacency, chain_connected
from ember_qc.algorithms.factored.polish import spur_prune
from ember_qc.algorithms.paper3._template_core import (
    _sorted_nodes,
    assign_slots,
    get_target_state,
    ordered_template,
)


def _spur_prune_reference(chains, src_adj, adj, *, deadline=None):
    """Verbatim pre-W1b spur_prune (factored/polish.py @ 0a317117)."""
    work = {int(v): [int(q) for q in c] for v, c in chains.items()}

    changed = True
    while changed:
        if deadline is not None and time.perf_counter() > deadline:
            return work
        changed = False
        for v in sorted(work):
            if deadline is not None and time.perf_counter() > deadline:
                return work
            chain = work[v]
            if len(chain) <= 1:
                continue
            nbr_sets = {
                u: set(work[u]) for u in src_adj.get(v, []) if work.get(u)
            }
            for q in sorted(chain):  # sorted() snapshots the list
                if len(chain) <= 1:
                    break
                remainder = [x for x in chain if x != q]
                if not chain_connected(remainder, adj):
                    continue
                rem_set = set(remainder)
                covered = True
                for u in src_adj.get(v, []):
                    u_set = nbr_sets.get(u)
                    if not u_set:
                        covered = False  # neighbour unplaced: keep q (safety)
                        break
                    if not any(w in u_set for x in rem_set for w in adj.get(x, ())):
                        covered = False
                        break
                if covered:
                    chain.remove(q)
                    changed = True
    return work


def _assert_identical(chains, src_adj, adj):
    ref = _spur_prune_reference(chains, src_adj, adj)
    new = spur_prune(chains, src_adj, adj)
    assert ref == new, "clean-chain-skip diverged from stock spur_prune"
    return ref


def _template_case(target, n, p, inst_seed):
    """Pre-prune template state exactly as restrict_template builds it."""
    state = get_target_state(target)
    G = nx.gnp_random_graph(n, p, seed=inst_seed)
    chains, pos = ordered_template(state, n)
    verts = _sorted_nodes(G)
    slots, _ = assign_slots(G, verts, pos)
    vidx = {v: i for i, v in enumerate(verts)}
    emb = {i: list(chains[slots[i]]) for i in range(len(verts))}
    src_adj = {
        i: sorted(vidx[u] for u in G.neighbors(v) if u != v)
        for i, v in enumerate(verts)
    }
    return emb, src_adj, state.adj


# ── template-chain corpus: Z12/P16 dev instances (frozen dev-suite cells) ────

class TestTemplateCorpus:
    @pytest.mark.parametrize("topo,n,p,inst_seed", [
        ("Z12", 100, 0.3, 101),
        ("Z12", 140, 0.2, 102),
        ("P16", 100, 0.2, 101),
    ])
    def test_template_chains_identical(self, topo, n, p, inst_seed):
        target = (dnx.zephyr_graph(12) if topo == "Z12"
                  else dnx.pegasus_graph(16))
        emb, src_adj, adj = _template_case(target, n, p, inst_seed)
        pruned = _assert_identical(emb, src_adj, adj)
        # sanity: the prune actually did something on template chains
        assert sum(len(c) for c in pruned.values()) < sum(
            len(c) for c in emb.values())


# ── fuzz corpus: raw MM embeddings, 20 cases ─────────────────────────────────

class TestFuzzCorpus:
    def test_twenty_mm_embeddings_identical(self):
        import minorminer
        targets = [dnx.chimera_graph(4), dnx.pegasus_graph(4),
                   dnx.zephyr_graph(3)]
        cases = 0
        for i in range(30):          # over-generate; keep the first 20 hits
            tgt = targets[i % 3]
            n = 8 + (i * 3) % 25
            ps = (0.15, 0.3, 0.6)[i % 3]
            G = nx.gnp_random_graph(n, ps, seed=200 + i)
            raw = minorminer.find_embedding(
                G, list(tgt.edges()), timeout=5, random_seed=i, verbose=0)
            if not raw:
                continue
            adj = build_adjacency(tgt)
            src_adj = {int(v): sorted(int(u) for u in G.neighbors(v))
                       for v in G.nodes()}
            emb = {int(v): [int(q) for q in c] for v, c in raw.items()}
            _assert_identical(emb, src_adj, adj)
            cases += 1
            if cases == 20:
                break
        assert cases == 20, f"only {cases} fuzz cases embedded"


# ── crafted edge cases ───────────────────────────────────────────────────────

class TestEdgeCases:
    def _line_adj(self, k):
        return build_adjacency(nx.path_graph(k))

    def test_unplaced_neighbour_blocks_prune(self):
        adj = self._line_adj(6)
        # vertex 0 has neighbour 1 unplaced -> safety branch keeps everything
        chains = {0: [0, 1, 2]}
        src_adj = {0: [1], 1: [0]}
        _assert_identical(chains, src_adj, adj)

    def test_empty_and_singleton_chains(self):
        adj = self._line_adj(6)
        chains = {0: [2, 3], 1: [4], 2: []}
        src_adj = {0: [1, 2], 1: [0], 2: [0]}
        _assert_identical(chains, src_adj, adj)

    def test_star_hub_long_chain(self):
        tgt = dnx.chimera_graph(3)
        adj = build_adjacency(tgt)
        import minorminer
        G = nx.star_graph(8)
        raw = minorminer.find_embedding(
            G, list(tgt.edges()), timeout=5, random_seed=1, verbose=0)
        assert raw
        emb = {int(v): [int(q) for q in c] for v, c in raw.items()}
        src_adj = {int(v): sorted(int(u) for u in G.neighbors(v))
                   for v in G.nodes()}
        _assert_identical(emb, src_adj, adj)

    def test_isolated_vertices_and_no_src_adj_entry(self):
        adj = self._line_adj(8)
        chains = {0: [0, 1], 1: [3], 2: [5, 6, 7]}
        src_adj = {0: [], 1: []}       # 2 missing entirely
        _assert_identical(chains, src_adj, adj)
