"""High-level CHARME inference: load weights + run a single episode.

Two-phase architecture (mirrors the reference `charme_embed.py` shipped with
the retrained ep1800 checkpoint):

  Phase 1 — **Ordering**. Build the initial padded (ACTION_DIM=120) state once
  and run a greedy rollout: the GCN actor is queried N times, with `mask` and
  `mask_connected` updated between calls. The GNN state tensors themselves are
  NOT updated during the rollout (that matches the reference). Output: a
  permutation `order` of the logical nodes.

  Phase 2 — **Construction**. Replay the ordering through the ATOM binary.
  ATOM is seeded via `is_beginning=0`, then each remaining node is placed one
  at a time via `is_beginning=1` following the learned order.

Contract:
    {
        'embedding': dict[int, list[int]]   # logical → Chimera linear qubit indices
        'time':      float
        'success':   bool
        'status':    'SUCCESS' | 'FAILURE' | 'CRASH' | 'TIMEOUT'
        'method':    'CHARME'
    }
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional

import networkx as nx

logger = logging.getLogger(__name__)

# The shipped checkpoint was trained on Chimera(16,16,4) with action_dim=120 and
# a diverse graph corpus (BA, ER, WS, grid, bipartite, lattice, SBM, ...).
CHARME_TOPO_ROW = 16
CHARME_TOPO_COL = 16
CHARME_BIPART_CELL = 4
ACTION_DIM = 120          # upper bound on logical-graph size
HIDDEN_DIM = 64
IN_CHANNELS = 1


def _resolve_binary() -> Path:
    for var in ("EMBER_CHARME_BINARY", "CHARME_ATOM_BINARY"):
        val = os.environ.get(var)
        if val:
            return Path(val)
    from ember_qc._paths import get_user_binary_dir
    return get_user_binary_dir() / "charme" / "main"


def _linearise_chimera(embedding_tuples, n_cols: int, bipart_cell: int
                       ) -> Dict[int, list]:
    """Convert [(x,y,k,c), ...] → {c: [linear qubit indices]}."""
    per_cell = bipart_cell * 2
    out: Dict[int, list] = {}
    for (x, y, k, c) in embedding_tuples:
        out.setdefault(c, []).append(x * n_cols * per_cell + y * per_cell + k)
    return out


def _build_padded_state(source_graph: nx.Graph, target_graph: nx.Graph):
    """Build the initial state tensors, padded out to ACTION_DIM logical rows.

    Matches the reference's `_build_initial_state`: pads logical_attr and the
    emb_matrix to ACTION_DIM so the actor's softmax always spans 120 positions.
    """
    import torch
    from .utils import (
        analysing_logical,
        convert_embedding_to_tensor,
        get_hw_attr_synthetic,
        get_hw_edge_index,
        generate_Chimera,
    )

    n = source_graph.number_of_nodes()

    logical_edge_index, logical_attr = analysing_logical(source_graph)
    if logical_attr.shape[0] < ACTION_DIM:
        pad = torch.zeros(ACTION_DIM - logical_attr.shape[0], logical_attr.shape[1])
        logical_attr = torch.cat([logical_attr, pad], dim=0)

    # Rebuild target with 'mapping' indices if the caller didn't supply them.
    if any('mapping' not in target_graph.nodes[n_] for n_ in target_graph.nodes):
        hw = generate_Chimera(CHARME_TOPO_ROW, CHARME_TOPO_COL, CHARME_BIPART_CELL)
    else:
        hw = target_graph.copy()
    for i, node in enumerate(hw.nodes):
        hw.nodes[node]['mapping'] = i
        hw.nodes[node]['embedding'] = -1

    hw_edge_index = get_hw_edge_index(hw)
    hw_attr = get_hw_attr_synthetic(hw)

    emb_dense = convert_embedding_to_tensor([], hw, source_graph)
    if emb_dense.shape[0] < ACTION_DIM:
        pad = torch.zeros(ACTION_DIM - emb_dense.shape[0], emb_dense.shape[1])
        emb_dense = torch.cat([emb_dense, pad], dim=0)
    emb_matrix = emb_dense.to_sparse()

    return {
        'logical_attr':       logical_attr,
        'logical_edge_index': logical_edge_index,
        'hw_attr':            hw_attr,
        'hw_edge_index':      hw_edge_index,
        'emb_matrix':         emb_matrix,
    }, hw


def run_charme(source_graph: nx.Graph, target_graph: nx.Graph,
               weights_path: Path, *,
               timeout: float = 60.0, seed: int = 42,
               greedy: bool = True,
               num_samples: int = 1,
               binary_path: Optional[Path] = None,
               device: Optional[str] = None) -> dict:
    """Embed `source_graph` into `target_graph` via CHARME (two-phase).

    Args:
        num_samples: When >1, run multiple rollouts (with `greedy=False` and
            `seed, seed+1, ...`) and keep the best result (most chains placed,
            then shortest total time). When ==1 use the single greedy rollout.
    """
    if num_samples > 1:
        best: Optional[dict] = None
        deadline = time.monotonic() + timeout
        for i in range(num_samples):
            remaining = deadline - time.monotonic()
            if remaining <= 0: break
            r = run_charme(
                source_graph, target_graph, weights_path,
                timeout=remaining, seed=seed + i,
                greedy=False, num_samples=1,
                binary_path=binary_path, device=device,
            )
            r['sample_index'] = i
            if r.get('success'):
                return {**r, 'num_samples': num_samples, 'best_sample': i}
            # Keep the one with the most placed chains
            if best is None or len(r.get('embedding', {})) > len(best.get('embedding', {})):
                best = r
        out = best or {'embedding': {}, 'time': 0.0, 'success': False,
                       'status': 'FAILURE', 'error': 'no samples executed'}
        return {**out, 'num_samples': num_samples,
                'best_sample': out.get('sample_index', -1)}

    t0 = time.monotonic()

    # --- topology check ----------------------------------------------------
    gd = target_graph.graph
    if not (gd.get('rows') == CHARME_TOPO_ROW
            and gd.get('columns') == CHARME_TOPO_COL
            and gd.get('tile') == CHARME_BIPART_CELL):
        return {
            'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE',
            'error': (f"CHARME checkpoint is trained on chimera_"
                      f"{CHARME_TOPO_ROW}x{CHARME_TOPO_COL}x{CHARME_BIPART_CELL}; "
                      f"target has rows={gd.get('rows')}, columns={gd.get('columns')}, "
                      f"tile={gd.get('tile')}"),
        }

    # --- source-graph check (pad up to ACTION_DIM) -------------------------
    n = source_graph.number_of_nodes()
    if n == 0 or n > ACTION_DIM:
        return {
            'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE',
            'error': (f"CHARME supports source graphs with 1..{ACTION_DIM} nodes "
                      f"(got {n})."),
        }
    if source_graph.number_of_edges() == 0:
        return {
            'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE',
            'error': "CHARME requires the source graph to have ≥1 edge.",
        }

    # --- relabel to 0..n-1 -------------------------------------------------
    mapping = {node: i for i, node in enumerate(source_graph.nodes())}
    inv_mapping = {i: node for node, i in mapping.items()}
    relabelled = nx.relabel_nodes(source_graph, mapping, copy=True)

    # --- binary + weights --------------------------------------------------
    binary_path = Path(binary_path) if binary_path else _resolve_binary()
    if not binary_path.exists():
        return {
            'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE',
            'error': (f"CHARME binary not found at {binary_path}. "
                      f"Run: ember install-binary charme"),
        }
    weights_path = Path(weights_path)
    if not weights_path.exists():
        return {
            'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE',
            'error': f"CHARME weights not found at {weights_path}",
        }

    # --- deferred imports --------------------------------------------------
    try:
        import torch
    except ImportError as exc:
        return {
            'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE',
            'error': f"CHARME requires torch ({exc}); pip install torch",
        }
    try:
        import torch_geometric  # noqa: F401
    except ImportError as exc:
        return {
            'embedding': {}, 'time': 0.0, 'success': False, 'status': 'FAILURE',
            'error': f"CHARME requires torch_geometric ({exc}); pip install torch_geometric",
        }

    from .env_infer import CharmeAtomRunner
    from .models import ActorCritic

    torch.manual_seed(seed)
    dev = torch.device(device) if device else torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    model = ActorCritic(device=dev, logical_size=ACTION_DIM)
    try:
        state_dict = torch.load(str(weights_path), map_location=dev, weights_only=False)
        missing, unexpected = model.load_state_dict(state_dict, strict=False)
        unused_actor = [k for k in missing if k.startswith('actor.')]
        if unused_actor or unexpected:
            raise RuntimeError(
                f"CHARME checkpoint / model mismatch: "
                f"missing actor keys {unused_actor}, unexpected keys {unexpected}"
            )
    except Exception as exc:
        return {
            'embedding': {}, 'time': time.monotonic() - t0, 'success': False,
            'status': 'FAILURE', 'error': f"failed to load CHARME weights: {exc}",
        }
    model.eval()

    # --- Build padded state (used by the actor; embedding tensor is fixed
    # to all-empty, only mask/mask_connected change per step) -------------
    try:
        state, _hw = _build_padded_state(relabelled, target_graph)
    except Exception as exc:
        return {
            'embedding': {}, 'time': time.monotonic() - t0, 'success': False,
            'status': 'CRASH', 'error': f"CHARME state build failed: {exc}",
        }

    # --- Phase 0: ATOM init FIRST. The C++ binary picks 5 seed nodes via
    # P->get_seed_set; we need to know those before running the policy so
    # the action ordering forms a connected expansion from the seeds.
    # (Without this, mask_connected starts all-True, the actor falls
    # through to its NaN fallback, and produces an arbitrary ordering
    # disconnected from the seeds — making nearly every extend a no-op
    # because old_nodes is empty.)
    runner = CharmeAtomRunner(
        source_graph=relabelled,
        topo_row=CHARME_TOPO_ROW, topo_column=CHARME_TOPO_COL,
        bipart_cell=CHARME_BIPART_CELL,
        binary_path=binary_path, seed=seed,
        target_graph=target_graph,
    )
    try:
        seeded = set(runner.initialise())
    except Exception as exc:
        return {
            'embedding': {}, 'time': time.monotonic() - t0, 'success': False,
            'status': 'CRASH', 'error': f"CHARME atom seed failed: {exc}",
        }

    # --- Phase 1: action ordering, with mask/mask_connected initialised
    # from the actual seed set so the policy expands outward from there.
    # mask[i]=True → already embedded OR pad position.
    # mask_connected[i]=True → not yet on the frontier (blocked).
    mask = [False] * ACTION_DIM
    mask_connected = [True] * ACTION_DIM
    for i in range(n, ACTION_DIM):
        mask[i] = True
    for s in seeded:
        if s < ACTION_DIM:
            mask[s] = True  # seeded nodes are already placed
    for s in seeded:
        for nei in relabelled.neighbors(s):
            if nei < ACTION_DIM and not mask[nei]:
                mask_connected[nei] = False  # frontier of seeded set

    order: list[int] = []
    try:
        with torch.no_grad():
            for _ in range(n - len(seeded)):
                if time.monotonic() - t0 > timeout:
                    return {
                        'embedding': {}, 'time': time.monotonic() - t0,
                        'success': False, 'status': 'TIMEOUT',
                    }
                try:
                    chosen = model.act(state, mask, mask_connected, greedy=greedy)
                except Exception:
                    # Sampling can hit Categorical(all-zeros) → NaN when the
                    # masked distribution is empty (e.g. once the frontier
                    # is exhausted in a disconnected component). Fall back
                    # to the lowest-index frontier node, then to any
                    # remaining real node.
                    chosen = next((i for i in range(n)
                                   if not mask[i] and not mask_connected[i]), None)
                    if chosen is None:
                        chosen = next((i for i in range(n) if not mask[i]), None)
                    if chosen is None: break
                if chosen >= n or mask[chosen]:
                    chosen = next((i for i in range(n)
                                   if not mask[i] and not mask_connected[i]), None)
                    if chosen is None:
                        chosen = next((i for i in range(n) if not mask[i]), None)
                    if chosen is None:
                        break
                mask[chosen] = True
                for nei in relabelled.neighbors(chosen):
                    if nei < ACTION_DIM:
                        mask_connected[nei] = False
                order.append(chosen)
    except Exception as exc:
        return {
            'embedding': {}, 'time': time.monotonic() - t0, 'success': False,
            'status': 'CRASH', 'error': f"CHARME actor rollout failed: {exc}",
        }

    # Append any nodes missed (e.g. disconnected components)
    if len(order) < n - len(seeded):
        seen = set(order) | seeded
        order.extend(i for i in range(n) if i not in seen)

    placed = set(seeded)
    for node in order:
        if time.monotonic() - t0 > timeout:
            return {
                'embedding': {}, 'time': time.monotonic() - t0,
                'success': False, 'status': 'TIMEOUT',
            }
        if node in placed:
            continue
        try:
            hard_fail = runner.extend(node)
        except Exception as exc:
            return {
                'embedding': {}, 'time': time.monotonic() - t0, 'success': False,
                'status': 'CRASH', 'error': f"CHARME atom extend failed: {exc}",
            }
        if hard_fail:
            break
        placed.add(node)

    # --- Package result ----------------------------------------------------
    if not placed:
        return {
            'embedding': {}, 'time': time.monotonic() - t0, 'success': False,
            'status': 'FAILURE', 'error': "CHARME produced an empty embedding",
        }

    lin = _linearise_chimera(runner.embedding, n_cols=CHARME_TOPO_COL,
                             bipart_cell=CHARME_BIPART_CELL)
    embedding = {inv_mapping[c]: qubits for c, qubits in lin.items()
                 if c in inv_mapping}

    success = len(embedding) == n
    return {
        'embedding': embedding,
        'time': time.monotonic() - t0,
        'success': success,
        'status': 'SUCCESS' if success else 'FAILURE',
        'method': 'CHARME',
        **({} if success else {'error': f"CHARME placed {len(embedding)}/{n} nodes"}),
    }
