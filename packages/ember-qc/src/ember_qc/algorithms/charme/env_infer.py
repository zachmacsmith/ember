"""Inference-time CHARME helper: ATOM binary wrapper + hardware-state tracker.

This is a thin wrapper around the C++ `atom_system` helper. Unlike the training
env it does *not* maintain GNN state tensors — at inference time the policy is
called once up front (with the initial padded state) to produce a node ordering,
then ATOM is replayed over that ordering here with no further model queries.

Responsibilities:
  - spawn the binary per step via subprocess.run (per-call scratch tempfile so
    concurrent workers don't collide)
  - track (embedding, chimera_graph, curr_row, curr_column) across steps so the
    binary can be fed the running state on each call
"""
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import networkx as nx

from .utils import generate_Chimera

logger = logging.getLogger(__name__)


class CharmeAtomRunner:
    """Stateful driver around the CHARME `atom_system` binary."""

    def __init__(self, source_graph: nx.Graph,
                 topo_row: int, topo_column: int, bipart_cell: int,
                 binary_path: Path, seed: int = 42,
                 target_graph: Optional[nx.Graph] = None,
                 max_extend_retries: int = 3,
                 retry_time_budget_s: float = 30.0):
        self.topo_row = topo_row
        self.topo_column = topo_column
        self.bipart_cell = bipart_cell
        self.seed = seed
        self.binary_path = Path(binary_path)
        # Target graph used for adjacency validation after each extend. The
        # C++ binary may report success even when expanding_chain leaves a
        # gap to one of `old_nodes` (no Lemma-2 recovery in per-step mode);
        # we detect it Python-side and retry with a bumped virtual grid.
        self.target_graph = target_graph
        self.max_extend_retries = max_extend_retries
        # Per-run total time budget spent in retry loops. Prevents dense
        # / infeasible graphs from running for hours via cascading retries
        # (seen: 2600+s single calls on hard-suite SBMs).
        self.retry_time_budget_s = retry_time_budget_s
        self._retry_time_spent_s: float = 0.0

        self.logical_graph = source_graph.copy()
        # Snapshot the ORIGINAL source-graph edges before any per-extend
        # removal mutates `logical_graph`. Used by _validate_extend to check
        # all placed-pair adjacencies (not just the new action's neighbors),
        # since the C++ binary re-routes existing chains on every call.
        self._src_edges: List[Tuple[int, int]] = list(source_graph.edges())
        self.chimera_graph = generate_Chimera(topo_row, topo_column, bipart_cell)
        for node in self.chimera_graph.nodes:
            self.chimera_graph.nodes[node]['embedding'] = -1

        self.embedding: List[Tuple[int, int, int, int]] = []
        self.curr_row: int = -1
        self.curr_column: int = -1

    # --------------------------------------------------------------------- seed
    def initialise(self) -> List[int]:
        """Run binary with is_beginning=0 to pick the seed set. Returns the
        list of logical node ids that were seeded."""
        emb, rr, cc, _ = self._call_atom(
            self.logical_graph, self.topo_row, self.topo_column,
            self.seed, is_beginning=0,
        )
        self._update_hw([], emb)
        self.embedding = emb
        self.curr_row = rr
        self.curr_column = cc
        return [e[3] for e in emb]

    # --------------------------------------------------------------------- step
    def extend(self, action: int) -> bool:
        """Extend embedding by one logical node. Returns True on hard failure.

        Retry strategy (Lemma-2 style): if the binary's placement does not
        actually achieve adjacency between chain[action] and every embedded
        neighbor in `old_nodes`, bump the virtual grid by 2 rows + 2 cols
        and perturb the seed, then retry. Up to `max_extend_retries` tries.
        Only commit (mutate logical_graph / chimera_graph / embedding) on a
        validated success — the binary is otherwise stateless across calls.
        """
        curr_emb = list(self.embedding)
        snapshot_row, snapshot_col = self.curr_row, self.curr_column

        last_err: Optional[Exception] = None
        import time as _time
        for attempt in range(self.max_extend_retries + 1):
            # Cut retries short once the aggregate budget is exhausted; on
            # dense / near-infeasible graphs a single extend can otherwise
            # burn minutes of subprocess time before giving up.
            if attempt > 0 and self._retry_time_spent_s >= self.retry_time_budget_s:
                logger.debug("CHARME extend(%d) retry-budget exhausted (%.1fs)",
                             action, self._retry_time_spent_s)
                break
            topo_r = snapshot_row + 2 * attempt
            topo_c = snapshot_col + 2 * attempt
            seed = self.seed + attempt * 1009  # cheap pseudo-perturb

            _t0 = _time.monotonic()
            new_emb, rr, cc, old_nodes = self._call_atom(
                self.logical_graph, topo_r, topo_c, seed,
                is_beginning=1, curr_node=action, embedding=curr_emb,
            )
            if attempt > 0:
                self._retry_time_spent_s += _time.monotonic() - _t0

            if not self._validate_extend(new_emb, action, old_nodes):
                # Don't commit anything; loop and retry on a bigger grid.
                logger.debug(
                    "CHARME extend(%d) attempt %d failed adjacency check "
                    "(old=%s); retrying with topo=(%d,%d) seed=%d",
                    action, attempt, old_nodes, topo_r + 2, topo_c + 2,
                    seed + 1009,
                )
                continue

            # --- commit ---
            # NOTE: do NOT strip edges from logical_graph. The C++ binary's
            # expanding_horizontal/vertical decides whether to insert a
            # "bridge" qubit between two existing chains based on whether
            # `P->has_edge(prev_co, next_co)` returns true. If we strip
            # already-satisfied edges, later expansions silently break the
            # adjacency between previously-good chain pairs (gap of one
            # cell across the inserted column/row). C++ does its own
            # per-call degree reduction internally, which is what the
            # bridge heuristic actually needs.
            self.curr_row = rr
            self.curr_column = cc
            try:
                self._update_hw(curr_emb, new_emb)
            except Exception as exc:
                logger.debug("CHARME _update_hw failed: %s", exc)
                last_err = exc
                # Roll back curr_row/col so the snapshot stays consistent.
                self.curr_row, self.curr_column = snapshot_row, snapshot_col
                return True
            self.embedding = new_emb
            return False

        # Exhausted retries — hard fail so the wrapper aborts cleanly
        # (better than silently shipping a broken embedding).
        logger.debug("CHARME extend(%d) hard-failed after %d retries (last_err=%s)",
                     action, self.max_extend_retries + 1, last_err)
        return True

    # --------------------------------------------------------------------- validation
    def _validate_extend(self, new_emb, action: int, old_nodes: List[int]) -> bool:
        """Check chain[action] is adjacent in target_graph to chain[nb]
        for every nb in old_nodes. Returns True if all adjacencies hold.

        If no target_graph was supplied, falls back to the per-cell Chimera
        adjacency rule encoded by (x, y, k) tuples — sufficient for the
        16x16x4 case the inference layer uses today.
        """
        # Group qubits by chain id from new_emb
        chains: dict = {}
        for (x, y, k, c) in new_emb:
            chains.setdefault(c, []).append((x, y, k))
        chain_a = chains.get(action, [])
        if not chain_a:
            return False  # action chain wasn't placed at all

        if self.target_graph is not None:
            # Use the supplied target graph (linearised qubit indices).
            # Important: the binary may re-route OTHER chains on each extend,
            # so we must validate every placed source-edge, not just `action`'s
            # adjacencies to old_nodes. Otherwise step N can silently break
            # an adjacency that was good after step M<N.
            n_cols = self.topo_column
            per_cell = self.bipart_cell * 2

            def lin(x, y, k):
                return x * n_cols * per_cell + y * per_cell + k

            tgt = self.target_graph
            chain_lin = {}
            for c, qs in chains.items():
                s = {lin(x, y, k) for (x, y, k) in qs if lin(x, y, k) in tgt.nodes}
                if s:
                    chain_lin[c] = s

            if action not in chain_lin:
                return False

            for (u, v) in self._src_edges:
                if u not in chain_lin or v not in chain_lin:
                    continue
                cu, cv = chain_lin[u], chain_lin[v]
                ok = any(b in cv for a in cu for b in tgt.neighbors(a))
                if not ok:
                    return False
            # And specifically the new action's old_nodes must hold (already
            # covered above, but keep as belt-and-suspenders for old_nodes
            # whose edge was removed from logical_graph in a prior commit).
            for nb in old_nodes:
                if nb not in chain_lin:
                    return False
                ok = any(b in chain_lin[nb] for a in chain_lin[action]
                         for b in tgt.neighbors(a))
                if not ok:
                    return False
            return True

        # Fallback: tuple-based Chimera adjacency
        def tuple_adj(a, b):
            ax, ay, ak = a
            bx, by, bk = b
            if ax == bx and ay == by:
                # intra-cell: k in [0, bipart_cell) connects to [bipart_cell, 2*bipart_cell)
                bc = self.bipart_cell
                return (ak < bc) != (bk < bc)
            if ak != bk:
                return False
            # inter-cell: k < bipart_cell varies one axis, k >= varies the other.
            # Conservative: accept if (|dx|+|dy|)==1.
            return abs(ax - bx) + abs(ay - by) == 1

        for nb in old_nodes:
            nb_qubits = chains.get(nb, [])
            if not nb_qubits:
                return False
            ok = any(tuple_adj(a, b) for a in chain_a for b in nb_qubits)
            if not ok:
                return False
        return True

    # --------------------------------------------------------------------- helpers
    def _update_hw(self, curr_emb, new_emb):
        for e in curr_emb:
            self.chimera_graph.nodes[(e[0], e[1], e[2])]['embedding'] = -1
        for e in new_emb:
            self.chimera_graph.nodes[(e[0], e[1], e[2])]['embedding'] = e[3]

    def _call_atom(self, P: nx.Graph, topo_row: int, topo_column: int,
                   seed: int, is_beginning: int,
                   curr_node: Optional[int] = None,
                   embedding: Optional[List[Tuple[int, int, int, int]]] = None,
                   ) -> Tuple[List[Tuple[int, int, int, int]], int, int, List[int]]:
        if not self.binary_path.exists():
            raise FileNotFoundError(
                f"CHARME binary not found at {self.binary_path}. "
                f"Run: ember install-binary charme"
            )

        n = len(P.nodes)
        m = len(P.edges)
        args: List[str] = [str(self.binary_path), str(n), str(m)]
        for u, v in P.edges:
            args += [str(u), str(v)]
        args += [str(topo_row), str(topo_column), str(seed), str(is_beginning)]

        old_nodes: List[int] = []
        if is_beginning == 1:
            assert curr_node is not None and embedding is not None
            args.append(str(curr_node))
            check = [False] * n
            for e in embedding:
                if e[3] < n:
                    check[e[3]] = True
            for nei in P.neighbors(curr_node):
                if nei < n and check[nei]:
                    old_nodes.append(nei)
            args.append(str(len(old_nodes)))
            args += [str(x) for x in old_nodes]
            args.append(str(len(embedding)))
            for e in embedding:
                args += [str(e[0]), str(e[1]), str(e[2]), str(e[3])]

        log_dir = self.binary_path.parent / "atom_log"
        log_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix="PPO_", suffix=".txt", dir=log_dir)
        os.close(fd)
        args.append(tmp_path)

        try:
            # Hard backstop: even with the C++ extend-loop time cap in place,
            # cap subprocess wall-clock to avoid the binary ever wedging.
            subprocess.run(args, cwd=self.binary_path.parent, check=True,
                           capture_output=True, timeout=5.0)
            return self._parse_atom_output(tmp_path) + (old_nodes,)
        except subprocess.TimeoutExpired:
            logger.debug("CHARME extend subprocess timed out (>5s); soft-fail")
            # Return the input embedding unchanged so the wrapper detects Δ+0.
            return (list(embedding) if embedding is not None else [],
                    topo_row, topo_column, old_nodes)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    @staticmethod
    def _parse_atom_output(path: str) -> Tuple[List[Tuple[int, int, int, int]], int, int]:
        new_embedding: List[Tuple[int, int, int, int]] = []
        rr, cc = -1, -1
        with open(path, "r") as f:
            while True:
                line = f.readline()
                if not line:
                    break
                parts = line.rstrip("\n").split(" ")
                if len(parts) == 4:
                    new_embedding.append((int(parts[0]), int(parts[1]),
                                          int(parts[2]), int(parts[3])))
                elif len(parts) == 2:
                    rr, cc = int(parts[0]), int(parts[1])
                    break
        return new_embedding, rr, cc
