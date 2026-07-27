"""
ember_qc/algorithms/paper3/race.py
===================================
P3 — the wall-clock-budgeted successive-halving racer (spec:
``docs/paper3/proposals/portfolio.md``; gate PASSED, notes.md §4.2: selection
on early-POLISH ACL works, per-instance ρ@q4 median +0.885).

Two public entry points plus one registered arm:

``race(source, target, total_budget_s, seed, arms_spec, ...)``
    The core library. Heterogeneous arms (stock MM seeds, mmfork-cuthill,
    p3-clmm variants, the deterministic p3 template slot) share ONE wall-clock
    budget. The template runs first and is kept aside as a floor (never
    halved, never polished past its own internal shorten). Every other arm is
    legalized once (MM arms: ``chainlength_patience=0``), then successive
    halving on current best-so-far ACL: each surviving arm polishes for one
    quantum via the §4.2-verified warm-restart pattern
    (``initial_chains`` + ``skip_initialization=True`` + large
    ``chainlength_patience`` + ``timeout=quantum``), the worst half is dropped
    each round, and the last survivor polishes on the remaining budget. The
    best-ever valid embedding wins; rich metadata records every trajectory,
    the survivor sets, and the budget accounting.

    * ``n_workers=1`` (default) is strictly sequential and wall-clock honest:
      total elapsed ≤ ``total_budget_s`` + the cooperative-timeout overshoot
      of the single last minorminer call (~1 s at benchmark scales). This is
      the "same wall-clock, one core" product configuration.
    * ``n_workers>1`` runs each phase's stages in a ``fork``-context
      ``ProcessPoolExecutor``. Its wall-clock claim is PER CORE COUNT: the
      budget is wall time on ``n_workers`` cores, and per protocol rule 2 it
      may only be compared against a baseline given the same core count
      (best-of-K-parallel stock MM). Not reentrant (module-level shared
      state feeds the fork snapshot).

``race_baseline_bestofk(source, target, total_budget_s, seed, K)``
    THE protocol-rule-2 baseline, kept next to the racer so no experiment can
    "forget" it: best-of-K stock minorminer under the identical wall-clock
    accounting — K sequential runs of ``total_budget_s / K`` each, lowest raw
    ACL wins. It is a control, NOT a registered algorithm; the M3 comparison
    is p3-race8 vs this at the same total budget (never race vs single MM).

``p3-race8`` (registered arm)
    Single-process sequential race, K=8: template + mm×4 + cuthill×1 +
    clmm×1 + clmm-core×1, quantum = timeout/16. Contract-clean: never raises,
    plain int chains, no stdout, deterministic per seed at contract scale,
    and with ``timeout ≤ 2 s`` it degrades to template + one stock-MM shot.

Determinism. Per-arm seeds are ``seed*1000 + arm_index`` (mod 2^31-1);
polish-quantum seeds are derived from those, so the whole schedule is a pure
function of ``(seed, arms_spec)``. Stage RESULTS are bit-deterministic
whenever every minorminer call ends on its own stopping rule (patience)
rather than the wall clock — always true at contract scale (K4-ish sources
finish each quantum in ≪ the slice). At experiment scale the wall clock
truncates polish quanta and, exactly as for stock minorminer with a binding
``timeout``, results are deterministic only up to CPU-speed jitter in where
the clock falls.

``polish_patience`` defaults to 2000 rather than the probe's 10**6: at
experiment scale (n ≥ 100 on P16) 2000 consecutive no-improvement shortening
sweeps cannot fit inside any quantum ≤ ~60 s (a failing sweep there costs
≥ tens of ms), so behavior is identical to the verified plumbing (quanta end
on timeout); on tiny instances patience trips in well under a second
(measured: K6/C4 ≈ 0.30 s), which is what makes the registered arm
deterministic and fast under the contract suite. A polish call that returns well before its
slice (< half of it) is patience-terminated ⇒ that arm is CONVERGED and is
never polished again (it still competes on its best-so-far ACL).

Arm kinds (``arms_spec`` = list of ``(kind, params)``):

* ``"template"`` — the deterministic P1 template path (``ate._template_arm``).
  Runs first, bounded to ~one quantum, kept as a floor. ``params`` unused.
* ``"mm"``       — stock minorminer. Legalize = ``chainlength_patience=0``
  (first valid embedding, no grind), then generic warm-restart polish.
* ``"cuthill"``  — mmfork-cuthill construction via ``forked_find_embedding``
  (``fallback=False``; SKIPPED silently when the fork .so is not built).
  Polish quanta use stock MM warm restart — the fork's contribution is the
  construction order, the polish machinery is shared. ``params`` may carry
  ``{"tries": int}``.
* ``"clmm"`` / ``"clmm-core"`` — the P2 arms (``clmm._clmm_embed``): template
  seeding + single-shot MM legalization as construction, then shared polish.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import networkx as nx

from ember_qc.registry import EmbeddingAlgorithm, register_algorithm
from ember_qc.embedding_backend import build_adjacency, is_valid_embedding

logger = logging.getLogger(__name__)

Embedding = Dict[object, List[int]]
ArmsSpec = Sequence[Tuple[str, Dict]]

# ── design constants ─────────────────────────────────────────────────────────
DEFAULT_QUANTUM_FRAC = 1.0 / 16.0
POLISH_PATIENCE = 2000       # "large": trips only when a quantum truly converges
LEGALIZE_PATIENCE = 0        # mm arms: first valid embedding, no grind (§4.2)
_MIN_SLICE_S = 0.05          # never start a stage with less than this left
_CONVERGED_FRAC = 0.5        # stage used < this fraction of its slice ⇒ patience
_TINY_TIMEOUT_S = 2.0        # registered arm: at/below this, template + 1 mm shot
_SEED_MOD = 2 ** 31 - 1
_EPS = 1e-9

#: p3-race8's arm roster (index order is seed-derivation order; template first).
RACE8_SPEC: ArmsSpec = (
    ("template", {}),
    ("mm", {}), ("mm", {}), ("mm", {}), ("mm", {}),
    ("cuthill", {}),
    ("clmm", {}),
    ("clmm-core", {}),
)

_VERSION = "1.0.0"


def _arm_seed(seed: int, index: int) -> int:
    """Per-arm seed: ``seed*1000 + arm_index`` (spec), clamped to int32."""
    return (int(seed) * 1000 + int(index)) % _SEED_MOD


def _quantum_seed(arm_seed: int, q: int) -> int:
    """Per-quantum polish seed, collision-free across (arm, quantum)."""
    return (int(arm_seed) + 7919 * int(q)) % _SEED_MOD


def _acl(embedding: Embedding) -> float:
    return sum(len(c) for c in embedding.values()) / max(1, len(embedding))


def _normalize(raw: Dict) -> Embedding:
    return {v: [int(q) for q in c] for v, c in raw.items()}


# ──────────────────────────────────────────────────────────────────────────────
# Stage functions
#
# Each takes only small picklable args and reads the big objects (source
# graph, target edge list) from _SHARED, which the parent fills before doing
# any work (and before creating the worker pool, so fork children inherit it).
# Each returns {"embedding": {v: [int qubits]} or {}, "used": float,
# "err": str} and never raises.
# ──────────────────────────────────────────────────────────────────────────────

_SHARED: Dict = {}


def _set_shared(source: nx.Graph, target: nx.Graph) -> None:
    _SHARED["source"] = source
    _SHARED["target"] = target
    _SHARED["edges"] = list(target.edges())


def _stage_mm_legalize(args: Dict) -> Dict:
    t0 = time.perf_counter()
    try:
        import minorminer
        emb = minorminer.find_embedding(
            _SHARED["source"], _SHARED["edges"],
            random_seed=int(args["seed"]),
            timeout=float(args["slice_s"]),
            chainlength_patience=int(args.get("patience", LEGALIZE_PATIENCE)),
            verbose=0,
        )
        used = time.perf_counter() - t0
        if not emb:
            return {"embedding": {}, "used": used, "err": "mm legalize empty"}
        return {"embedding": _normalize(emb), "used": used, "err": ""}
    except Exception as e:  # pragma: no cover — defensive
        return {"embedding": {}, "used": time.perf_counter() - t0,
                "err": f"mm legalize: {type(e).__name__}: {e}"}


def _stage_cuthill(args: Dict) -> Dict:
    t0 = time.perf_counter()
    try:
        from ember_qc.algorithms.minorminer_forked import forked_find_embedding
        r = forked_find_embedding(
            _SHARED["source"], _SHARED["target"],
            order=args["order"],
            seed=int(args["seed"]),
            timeout=float(args["slice_s"]),
            tries=int(args.get("tries", 10)),
            fallback=False,
        )
        used = time.perf_counter() - t0
        emb = r.get("embedding") or {}
        if not emb:
            return {"embedding": {}, "used": used,
                    "err": r.get("error", "cuthill construction empty")}
        return {"embedding": _normalize(emb), "used": used, "err": ""}
    except Exception as e:  # pragma: no cover — defensive
        return {"embedding": {}, "used": time.perf_counter() - t0,
                "err": f"cuthill: {type(e).__name__}: {e}"}


def _stage_clmm(args: Dict) -> Dict:
    t0 = time.perf_counter()
    try:
        from ember_qc.algorithms.paper3.clmm import _clmm_embed
        r = _clmm_embed(_SHARED["source"], _SHARED["target"],
                        timeout=float(args["slice_s"]),
                        seed=int(args["seed"]),
                        core_seeding=bool(args["core"]))
        used = time.perf_counter() - t0
        emb = r.get("embedding") or {}
        if not emb:
            return {"embedding": {}, "used": used,
                    "err": r.get("error", "clmm construction empty")}
        return {"embedding": _normalize(emb), "used": used, "err": ""}
    except Exception as e:  # pragma: no cover — defensive
        return {"embedding": {}, "used": time.perf_counter() - t0,
                "err": f"clmm: {type(e).__name__}: {e}"}


def _stage_polish(args: Dict) -> Dict:
    """One warm-restart polish quantum (§4.2-verified plumbing)."""
    t0 = time.perf_counter()
    try:
        import minorminer
        emb = minorminer.find_embedding(
            _SHARED["source"], _SHARED["edges"],
            initial_chains=args["chains"],
            skip_initialization=True,
            timeout=float(args["slice_s"]),
            random_seed=int(args["seed"]),
            chainlength_patience=int(args["patience"]),
            verbose=0,
        )
        used = time.perf_counter() - t0
        if not emb:
            return {"embedding": {}, "used": used, "err": "polish empty"}
        return {"embedding": _normalize(emb), "used": used, "err": ""}
    except Exception as e:  # pragma: no cover — defensive
        return {"embedding": {}, "used": time.perf_counter() - t0,
                "err": f"polish: {type(e).__name__}: {e}"}


_STAGE_FNS = {
    "mm": _stage_mm_legalize,
    "cuthill": _stage_cuthill,
    "clmm": _stage_clmm,
    "clmm-core": _stage_clmm,
}


# ──────────────────────────────────────────────────────────────────────────────
# The race
# ──────────────────────────────────────────────────────────────────────────────

class _Arm:
    """Mutable per-arm race state (metadata view is built at the end)."""

    __slots__ = ("index", "kind", "params", "seed", "status", "chains",
                 "acl_best", "converged", "trajectory", "err", "n_quanta")

    def __init__(self, index: int, kind: str, params: Dict, seed: int):
        self.index = index
        self.kind = kind
        self.params = dict(params or {})
        self.seed = seed
        self.status = "pending"
        self.chains: Optional[Embedding] = None   # current (chain-forwarded)
        self.acl_best: Optional[float] = None
        self.converged = False
        self.trajectory: List[Dict] = []
        self.err = ""
        self.n_quanta = 0                          # polish quanta consumed

    def record(self, stage: str, acl: Optional[float], t_race: float) -> None:
        if acl is not None and (self.acl_best is None or acl < self.acl_best):
            self.acl_best = acl
        self.trajectory.append({
            "stage": stage,
            "acl": None if acl is None else round(acl, 4),
            "acl_best": None if self.acl_best is None else round(self.acl_best, 4),
            "t": round(t_race, 3),
        })

    def view(self) -> Dict:
        return {
            "index": self.index, "kind": self.kind, "seed": self.seed,
            "status": self.status,
            "acl_best": None if self.acl_best is None else round(self.acl_best, 4),
            "converged": self.converged,
            "err": self.err,
            "trajectory": list(self.trajectory),
        }


def _run_batch(tasks: List[Tuple[Callable, Dict]], pool) -> List[Dict]:
    """Run ``[(fn, args), ...]``; inline when ``pool`` is None, else on the
    pool. Results come back in task order either way."""
    if pool is None:
        return [fn(args) for fn, args in tasks]
    futures = [pool.submit(fn, args) for fn, args in tasks]
    out = []
    for fut in futures:
        try:
            out.append(fut.result())
        except Exception as e:  # a worker died — treat as a failed stage
            out.append({"embedding": {}, "used": 0.0,
                        "err": f"worker: {type(e).__name__}: {e}"})
    return out


def _run_template(source: nx.Graph, target: nx.Graph, deadline: float,
                  seed: int) -> Dict:
    """The deterministic template slot (P1 path). Returns the stage-result
    shape plus 'meta' from the template arm. Never raises."""
    t0 = time.perf_counter()
    try:
        from ember_qc.algorithms.paper3.ate import _template_arm
        from ember_qc.algorithms.paper3._template_core import get_target_state
        state = get_target_state(target)
        if state is None:
            return {"embedding": {}, "used": time.perf_counter() - t0,
                    "err": "target not supported by busclique", "meta": {}}
        r = _template_arm(source, target, state, deadline, seed)
        used = time.perf_counter() - t0
        if r["embedding"] is None:
            return {"embedding": {}, "used": used, "err": r["err"],
                    "meta": r.get("metadata", {})}
        return {"embedding": r["embedding"], "used": used, "err": "",
                "meta": r.get("metadata", {})}
    except Exception as e:  # pragma: no cover — defensive
        return {"embedding": {}, "used": time.perf_counter() - t0,
                "err": f"template: {type(e).__name__}: {e}", "meta": {}}


def race(source_graph: nx.Graph, target_graph: nx.Graph,
         total_budget_s: float, seed: int, arms_spec: ArmsSpec,
         n_workers: int = 1, quantum_frac: float = DEFAULT_QUANTUM_FRAC,
         *, polish_patience: int = POLISH_PATIENCE,
         validate: bool = True,
         on_event: Optional[Callable[[str], None]] = None) -> Dict:
    """Race ``arms_spec`` under one wall-clock budget; return the best-ever
    valid embedding plus rich metadata. See the module docstring for the
    mechanism, budget semantics, and determinism contract.

    Returns a dict with keys: ``embedding`` (possibly ``{}``), ``success``,
    ``acl``, ``winner`` (``{"index", "kind", "stage"}`` or None),
    ``final_survivor``, ``arms`` (per-arm views incl. trajectories),
    ``rounds`` (survivor sets per halving round), ``template``,
    ``budget`` (accounting), ``elapsed_s``, ``quantum_s``, ``n_workers``.
    """
    t0 = time.perf_counter()
    total_budget_s = float(total_budget_s)
    deadline = t0 + total_budget_s
    quantum = max(_MIN_SLICE_S, total_budget_s * float(quantum_frac))
    say = on_event if on_event is not None else (lambda s: None)

    _set_shared(source_graph, target_graph)
    try:
        adj = build_adjacency(target_graph) if validate else None
    except Exception:
        adj = None

    arms = [_Arm(i, kind, params, _arm_seed(seed, i))
            for i, (kind, params) in enumerate(arms_spec)]

    best: Dict = {"emb": None, "acl": math.inf, "index": None,
                  "kind": None, "stage": None}

    def now() -> float:
        return time.perf_counter() - t0

    def remaining() -> float:
        return deadline - time.perf_counter()

    def ok(emb: Embedding) -> bool:
        if not emb:
            return False
        if not validate:
            return True
        try:
            return is_valid_embedding(emb, source_graph, target_graph, adj=adj)
        except Exception:
            return False

    def consider(emb: Embedding, arm: Optional[_Arm], stage: str) -> Optional[float]:
        """Validate; on strict improvement adopt as global best. Returns the
        ACL if valid else None. Strict '<' keeps the earliest achiever on
        ties (the template runs first, so it wins exact ties)."""
        if not ok(emb):
            return None
        a = _acl(emb)
        if a < best["acl"] - _EPS:
            best.update(emb=emb, acl=a,
                        index=None if arm is None else arm.index,
                        kind=None if arm is None else arm.kind, stage=stage)
        return a

    acct = {"template_s": 0.0, "legalize_s": 0.0, "rounds_s": 0.0,
            "final_s": 0.0}

    # ── phase 0: template slot(s) — deterministic floor, never raced ────────
    template_view: Optional[Dict] = None
    for arm in [a for a in arms if a.kind == "template"]:
        rem = remaining()
        if rem < _MIN_SLICE_S:
            arm.status = "skipped:no-budget"
            continue
        slice_s = min(rem, max(2.0, quantum))
        r = _run_template(source_graph, target_graph,
                          time.perf_counter() + slice_s, arm.seed)
        acct["template_s"] += r["used"]
        a = consider(r["embedding"], arm, "template")
        arm.record("template", a, now())
        arm.err = r["err"]
        arm.status = "floor" if a is not None else "template-failed"
        view = {"index": arm.index, "acl": None if a is None else round(a, 4),
                "used_s": round(r["used"], 3), "err": r["err"]}
        view.update({k: v for k, v in r.get("meta", {}).items()
                     if isinstance(v, (int, float, str, bool, type(None)))})
        if template_view is None or a is not None:
            template_view = view
        say(f"template: acl={a if a is None else round(a, 3)} "
            f"({r['used']:.2f}s) {r['err']}")

    racing = [a for a in arms if a.kind != "template"]

    # cuthill preflight: skip silently (no budget spent) when the fork is absent
    try:
        from ember_qc.algorithms.minorminer_forked import _find_so
        fork_available = _find_so() is not None
    except Exception:
        fork_available = False
    cuthill_order: Optional[List] = None
    if any(a.kind == "cuthill" for a in racing) and fork_available:
        try:
            from ember_qc.algorithms.search_orders import ORDERINGS
            cuthill_order = ORDERINGS["cuthill"](source_graph)
        except Exception as e:
            logger.debug("cuthill order failed: %s", e)
            fork_available = False
    for arm in racing:
        if arm.kind == "cuthill" and not fork_available:
            arm.status = "skipped:fork-unavailable"
    live = [a for a in racing if not a.status.startswith("skipped")]

    # worker pool (created after the template phase so fork children inherit
    # warm busclique caches along with _SHARED)
    pool = None
    if n_workers and n_workers > 1 and live:
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        ctx = multiprocessing.get_context("fork")
        pool = ProcessPoolExecutor(max_workers=int(n_workers), mp_context=ctx)

    try:
        # ── phase 1: legalize every racing arm once ─────────────────────────
        t_phase = time.perf_counter()
        if pool is None:   # sequential: size each slice against the deadline
            for arm in live:
                rem = remaining()
                if rem < _MIN_SLICE_S:
                    arm.status = "skipped:no-budget"
                    continue
                args = _legalize_args(arm, min(quantum, rem), cuthill_order)
                if args is None:
                    continue
                _fold_legalize(arm, _STAGE_FNS[arm.kind](args), consider, now)
        else:              # parallel: one common slice, arms run concurrently
            rem = remaining()
            tasks: List[Tuple[Callable, Dict]] = []
            tarms: List[_Arm] = []
            if rem >= _MIN_SLICE_S:
                slice_s = min(quantum, rem)
                for arm in live:
                    args = _legalize_args(arm, slice_s, cuthill_order)
                    if args is not None:
                        tasks.append((_STAGE_FNS[arm.kind], args))
                        tarms.append(arm)
            else:
                for arm in live:
                    arm.status = "skipped:no-budget"
            for arm, r in zip(tarms, _run_batch(tasks, pool)):
                _fold_legalize(arm, r, consider, now)
        acct["legalize_s"] = time.perf_counter() - t_phase

        survivors = sorted(
            [a for a in live if a.status == "racing"],
            key=lambda a: (a.acl_best if a.acl_best is not None else math.inf,
                           a.index))
        say(f"legalized: {[(a.index, a.acl_best) for a in survivors]} "
            f"({now():.1f}s)")

        # ── phase 2: successive-halving polish rounds ───────────────────────
        rounds: List[Dict] = []
        t_phase = time.perf_counter()
        rnd = 0
        while len(survivors) > 1 and remaining() >= _MIN_SLICE_S:
            rnd += 1
            info = {"round": rnd, "survivors_in": [a.index for a in survivors],
                    "quantum_s": round(min(quantum, max(0.0, remaining())), 3)}
            active = [a for a in survivors if not a.converged]
            _polish_arms(active, quantum, remaining, pool, polish_patience,
                         consider, now)
            # drop the worst half (keep k - k//2, deterministic tie-break)
            survivors.sort(key=lambda a: (a.acl_best, a.index))
            keep = len(survivors) - len(survivors) // 2
            dropped = survivors[keep:]
            for a in dropped:
                a.status = f"dropped:r{rnd}"
            survivors = survivors[:keep]
            info["dropped"] = [a.index for a in dropped]
            info["survivors_out"] = [a.index for a in survivors]
            info["acl_best"] = {a.index: round(a.acl_best, 4) for a in survivors}
            rounds.append(info)
            say(f"round {rnd}: keep {info['survivors_out']} "
                f"drop {info['dropped']} ({now():.1f}s)")
            if all(a.converged for a in survivors):
                break
        acct["rounds_s"] = time.perf_counter() - t_phase

        # ── phase 3: the last survivor gets the remaining budget ────────────
        t_phase = time.perf_counter()
        final_survivor = None
        if survivors:
            survivors.sort(key=lambda a: (a.acl_best, a.index))
            winner_arm = survivors[0]
            final_survivor = winner_arm.index
            for a in survivors:
                a.status = "survivor"
            winner_arm.status = "final"
            fq = 0
            while (not winner_arm.converged and winner_arm.chains
                   and remaining() >= _MIN_SLICE_S):
                fq += 1
                _polish_one(winner_arm, min(quantum, remaining()),
                            polish_patience, consider, now,
                            stage=f"final{fq}")
        acct["final_s"] = time.perf_counter() - t_phase
    finally:
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)

    elapsed = now()
    success = best["emb"] is not None
    result = {
        "embedding": best["emb"] if success else {},
        "success": success,
        "acl": round(best["acl"], 4) if success else None,
        "winner": ({"index": best["index"], "kind": best["kind"],
                    "stage": best["stage"]} if success else None),
        "final_survivor": final_survivor if survivors else None,
        "arms": [a.view() for a in arms],
        "rounds": rounds,
        "template": template_view,
        "budget": {"total_s": round(total_budget_s, 3),
                   "elapsed_s": round(elapsed, 3),
                   **{k: round(v, 3) for k, v in acct.items()}},
        "elapsed_s": round(elapsed, 3),
        "quantum_s": round(quantum, 3),
        "n_workers": int(n_workers),
    }
    say(f"race done: acl={result['acl']} winner={result['winner']} "
        f"({elapsed:.1f}s of {total_budget_s:g}s)")
    return result


def _legalize_args(arm: _Arm, slice_s: float,
                   cuthill_order: Optional[List]) -> Optional[Dict]:
    """Build the phase-1 stage args for one arm; None (with the arm's status
    set) when the kind is unknown."""
    args: Dict = {"seed": arm.seed, "slice_s": slice_s}
    if arm.kind == "cuthill":
        args["order"] = cuthill_order
        if "tries" in arm.params:
            args["tries"] = arm.params["tries"]
    elif arm.kind in ("clmm", "clmm-core"):
        args["core"] = (arm.kind == "clmm-core")
    elif arm.kind == "mm":
        args["patience"] = arm.params.get("legalize_patience",
                                          LEGALIZE_PATIENCE)
    else:
        arm.status = f"skipped:unknown-kind:{arm.kind}"
        return None
    return args


def _fold_legalize(arm: _Arm, r: Dict, consider, now) -> None:
    """Fold one legalize/construction stage result into arm state."""
    a = consider(r["embedding"], arm, "legalize")
    arm.record("legalize", a, now())
    if a is None:
        arm.status = "legalize-failed"
        arm.err = r["err"] or "invalid/empty construction"
    else:
        arm.chains = r["embedding"]
        arm.status = "racing"


def _polish_one(arm: _Arm, slice_s: float, patience: int,
                consider, now, stage: str) -> None:
    """One warm-restart quantum for one arm (inline). Chain-forwards the RAW
    result (best-or-not, §4.2 plumbing); flags convergence when the call ends
    on patience well before the slice."""
    arm.n_quanta += 1
    args = {"chains": arm.chains, "slice_s": slice_s, "patience": patience,
            "seed": _quantum_seed(arm.seed, arm.n_quanta)}
    _fold_polish(arm, _stage_polish(args), slice_s, consider, now, stage)


def _fold_polish(arm: _Arm, r: Dict, slice_s: float, consider, now,
                 stage: str) -> None:
    if r["embedding"]:
        a = consider(r["embedding"], arm, stage)
        arm.record(stage, a, now())
        arm.chains = r["embedding"]           # chain-forward raw result
    else:
        arm.record(stage, None, now())
    if r["used"] < _CONVERGED_FRAC * slice_s:
        arm.converged = True


def _polish_arms(active: List[_Arm], quantum: float, remaining, pool,
                 patience: int, consider, now) -> None:
    """Polish each non-converged arm for one quantum. Sequential mode sizes
    each slice against the live deadline; parallel mode gives every arm the
    same slice and runs them concurrently."""
    if pool is None:
        for arm in active:
            rem = remaining()
            if rem < _MIN_SLICE_S:
                return
            _polish_one(arm, min(quantum, rem), patience, consider, now,
                        stage=f"q{arm.n_quanta + 1}")
        return
    rem = remaining()
    if rem < _MIN_SLICE_S:
        return
    slice_s = min(quantum, rem)
    tasks, tarms = [], []
    for arm in active:
        arm.n_quanta += 1
        tasks.append((_stage_polish,
                      {"chains": arm.chains, "slice_s": slice_s,
                       "patience": patience,
                       "seed": _quantum_seed(arm.seed, arm.n_quanta)}))
        tarms.append(arm)
    for arm, r in zip(tarms, _run_batch(tasks, pool)):
        _fold_polish(arm, r, slice_s, consider, now, stage=f"q{arm.n_quanta}")


# ──────────────────────────────────────────────────────────────────────────────
# Protocol rule 2 baseline — a control, NOT a registered algorithm
# ──────────────────────────────────────────────────────────────────────────────

def race_baseline_bestofk(source_graph: nx.Graph, target_graph: nx.Graph,
                          total_budget_s: float, seed: int, K: int,
                          *, validate: bool = True,
                          on_event: Optional[Callable[[str], None]] = None
                          ) -> Dict:
    """Best-of-K stock minorminer under the racer's wall-clock accounting:
    K sequential full-default MM runs of ``total_budget_s / K`` each (each
    slice clamped to the live deadline), lowest raw ACL among valid results
    wins. Per-run seeds are ``seed*1000 + i`` — the same derivation as
    ``race`` — so baseline and race are paired on the master seed.

    This is THE baseline required by protocol rule 2 for any multi-run
    scheme: minorminer given the identical multi-run privilege. It lives in
    this module so it cannot drift from the racer's accounting; it is
    deliberately NOT registered as an arm (it is a control, not an
    algorithm). The M3 comparison is p3-race8 vs this at equal total budget.
    """
    import minorminer

    t0 = time.perf_counter()
    total_budget_s = float(total_budget_s)
    deadline = t0 + total_budget_s
    per = total_budget_s / max(1, int(K))
    say = on_event if on_event is not None else (lambda s: None)
    try:
        adj = build_adjacency(target_graph) if validate else None
    except Exception:
        adj = None
    edges = list(target_graph.edges())

    best_emb, best_acl, best_run = None, math.inf, None
    runs: List[Dict] = []
    for i in range(int(K)):
        rem = deadline - time.perf_counter()
        if rem < _MIN_SLICE_S:
            runs.append({"run": i, "seed": _arm_seed(seed, i), "acl": None,
                         "used_s": 0.0, "status": "skipped:no-budget"})
            continue
        slice_s = min(per, rem)
        rs = _arm_seed(seed, i)
        t = time.perf_counter()
        try:
            emb = minorminer.find_embedding(
                source_graph, edges, timeout=slice_s, random_seed=rs,
                verbose=0)
        except Exception as e:
            emb = {}
            logger.debug("baseline mm run %d raised: %s", i, e)
        used = time.perf_counter() - t
        rec = {"run": i, "seed": rs, "acl": None,
               "used_s": round(used, 3), "status": "failed"}
        if emb:
            emb = _normalize(emb)
            valid = True
            if validate:
                try:
                    valid = is_valid_embedding(emb, source_graph, target_graph,
                                               adj=adj)
                except Exception:
                    valid = False
            if valid:
                a = _acl(emb)
                rec["acl"] = round(a, 4)
                rec["status"] = "ok"
                if a < best_acl - _EPS:
                    best_emb, best_acl, best_run = emb, a, i
        runs.append(rec)
        say(f"baseline run {i}: acl={rec['acl']} ({used:.1f}s)")

    elapsed = time.perf_counter() - t0
    success = best_emb is not None
    return {
        "embedding": best_emb if success else {},
        "success": success,
        "acl": round(best_acl, 4) if success else None,
        "best_run": best_run,
        "runs": runs,
        "K": int(K),
        "budget": {"total_s": round(total_budget_s, 3),
                   "elapsed_s": round(elapsed, 3),
                   "per_run_s": round(per, 3)},
        "elapsed_s": round(elapsed, 3),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Registered arm
# ──────────────────────────────────────────────────────────────────────────────

def _tiny_embed(source: nx.Graph, target: nx.Graph, timeout: float,
                seed: int) -> Dict:
    """timeout ≤ 2 s degradation: template + one stock-MM shot, better one
    wins (template on exact ties). Internal shape mirrors race()'s result."""
    t0 = time.perf_counter()
    deadline = t0 + timeout
    best_emb, best_acl, winner = None, math.inf, None

    r = _run_template(source, target,
                      min(deadline, t0 + max(0.5 * timeout, 0.25)),
                      _arm_seed(seed, 0))
    tmpl_acl = None
    if r["embedding"] and is_valid_embedding(r["embedding"], source, target):
        tmpl_acl = _acl(r["embedding"])
        best_emb, best_acl, winner = r["embedding"], tmpl_acl, "template"

    mm_acl = None
    rem = deadline - time.perf_counter()
    if rem >= _MIN_SLICE_S:
        try:
            import minorminer
            emb = minorminer.find_embedding(
                source, list(target.edges()), timeout=rem,
                random_seed=_arm_seed(seed, 1), verbose=0)
        except Exception:
            emb = {}
        if emb:
            emb = _normalize(emb)
            if is_valid_embedding(emb, source, target):
                mm_acl = _acl(emb)
                if mm_acl < best_acl - _EPS:
                    best_emb, best_acl, winner = emb, mm_acl, "mm"

    return {
        "embedding": best_emb if best_emb is not None else {},
        "success": best_emb is not None,
        "acl": None if best_emb is None else round(best_acl, 4),
        "winner": None if winner is None else {"kind": winner},
        "mode": "tiny",
        "acl_template": None if tmpl_acl is None else round(tmpl_acl, 4),
        "acl_mm": None if mm_acl is None else round(mm_acl, 4),
        "elapsed_s": round(time.perf_counter() - t0, 3),
    }


@register_algorithm("p3-race8")
class P3Race8(EmbeddingAlgorithm):
    """P3 racer, product configuration: single-process sequential successive
    halving over 8 arms (template + 4 stock-MM seeds + mmfork-cuthill +
    p3-clmm + p3-clmm-core) inside ONE wall-clock timeout; quantum =
    timeout/16; selection on early-polish best-so-far ACL (gate: notes §4.2).
    Protocol rule 2: measured only against best-of-K-parallel stock MM
    (``race_baseline_bestofk``), never against single-shot MM."""

    supported_counters: List[str] = []
    _uses_subprocess = False

    @property
    def version(self) -> str:
        return _VERSION

    def embed(self, source_graph, target_graph, timeout=60.0, **kwargs):
        t0 = time.perf_counter()
        try:
            timeout = max(0.01, float(timeout))
            seed = kwargs.get("seed", 42)
            seed = 42 if seed is None else int(seed)

            if timeout <= _TINY_TIMEOUT_S:
                r = _tiny_embed(source_graph, target_graph, timeout, seed)
                meta = {k: r[k] for k in ("mode", "winner", "acl_template",
                                          "acl_mm", "elapsed_s")}
            else:
                r = race(source_graph, target_graph, timeout, seed,
                         RACE8_SPEC, n_workers=1,
                         quantum_frac=DEFAULT_QUANTUM_FRAC)
                meta = {
                    "mode": "race",
                    "winner": r["winner"],
                    "final_survivor": r["final_survivor"],
                    "acl": r["acl"],
                    "quantum_s": r["quantum_s"],
                    "budget": r["budget"],
                    "rounds": r["rounds"],
                    "template": r["template"],
                    "arms": [{k: v.get(k) for k in
                              ("index", "kind", "status", "acl_best",
                               "converged")}
                             for v in r["arms"]],
                    "trajectories": {str(v["index"]): v["trajectory"]
                                     for v in r["arms"]},
                }
            if not r["success"]:
                status = ("TIMEOUT" if time.perf_counter() - t0 >= timeout - 0.05
                          else "FAILURE")
                return {"embedding": {}, "time": time.perf_counter() - t0,
                        "success": False, "status": status,
                        "error": "race: no arm produced a valid embedding",
                        "metadata": meta}
            return {"embedding": r["embedding"],
                    "time": time.perf_counter() - t0,
                    "metadata": meta}
        except Exception as e:  # contract: never raise
            logger.error("p3-race8 error: %s", e)
            return {"embedding": {}, "time": time.perf_counter() - t0,
                    "success": False, "status": "FAILURE",
                    "error": f"race: {type(e).__name__}: {e}"}
