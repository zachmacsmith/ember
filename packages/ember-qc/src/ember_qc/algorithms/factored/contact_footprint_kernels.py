"""Contact-supported interleaving pricing; no physical embedding solver."""
from typing import Dict, List, Optional, Tuple
import numpy as np
from ember_qc.algorithms.factored.field import rank_scale

def align_reinsert(order: List[int], cluster,
                   src_adj: Dict[int, List[int]],
                   values, anchors, *, axis: int,
                   other: Dict[int, float], contacts,
                   slot_costs: bool = False, bar: float = 0.0
                   ) -> Tuple[Optional[List[int]], bool]:
    """Exact interleaving cost for contact-supported arms.

    The lattice minimization/backtrack is inherited from field.align_reinsert.
    X uses frozen horizontal supports. Y recomputes activity from the prefix:
    an unplaced owner's vertical arm crosses the next gap exactly when some,
    but not all, neighbors are placed. A sole active arm excludes the owner.
    Only moved-axis spans receive the inherited slot-rank tie-break.
    """
    n = len(order)
    _declined = None if slot_costs else (None, False)
    if n < 3:
        return _declined
    if anchors is not None:
        lo_fix = np.asarray(anchors[0], dtype=float)
        hi_fix = np.asarray(anchors[1], dtype=float)
        if (lo_fix < np.inf).any() or (hi_fix > -np.inf).any():
            return _declined
    cset = set(cluster)
    S = [v for v in order if v in cset]
    if len(S) < 1 or len(S) >= n:
        return _declined
    if slot_costs and len(S) != 1:
        return _declined
    R = [v for v in order if v not in cset]
    p, m = len(R), len(S)
    val = np.asarray(values, dtype=float) * rank_scale(n) + np.arange(n)
    bar = float(bar) * rank_scale(n)   # the bar lives in true units too
    gapv = np.zeros(n)
    gapv[1:] = val[1:] - val[:-1]
    BIG = n + 1  # +inf proxy for index minima

    # ---- shared setup (s3.100b): one O(E) pass, numpy throughout;
    # both orientation arms derive from these structures (the reversed
    # arm's Q-side indices are m-1-q, so its sorted views are pure
    # slices of the forward arm's — nothing is rebuilt from src_adj) ----
    slot_of = {v: t for t, v in enumerate(order)}
    inS = np.zeros(n, dtype=bool)
    for t, v in enumerate(order):
        inS[t] = v in cset
    rpos = np.cumsum(~inS) - 1          # side-index, valid at R slots
    qpos = np.cumsum(inS) - 1           # side-index, valid at S slots
    r_slots = np.flatnonzero(~inS)      # slot of R[i]
    q_slots = np.flatnonzero(inS)       # slot of S[j] (forward)
    # the other axis's values feed the h-spans on axis 1: same scale as
    # the gaps, so every true-cost term outweighs the rank tiebreak
    xs_slot = (np.array([float(other[v]) for v in order]) * rank_scale(n)
               if axis == 1 else None)

    # Only vertical reinsertion re-derives contacts from source neighbors.
    # Horizontal reinsertion uses frozen contact nets below, so these views
    # and minima are unused there. Keep vertical preparation unchanged.
    if axis == 1:
        heads: List[int] = []
        tails: List[int] = []
        for t, v in enumerate(order):
            for u in src_adj.get(v, []):
                if u != v and u in slot_of:
                    heads.append(t)
                    tails.append(slot_of[u])
        ha = np.asarray(heads, dtype=np.int64)
        ta = np.asarray(tails, dtype=np.int64)
        if ha.size:
            srt = np.argsort(ha, kind="stable")
            ta_s = ta[srt]
            bnd = np.searchsorted(ha[srt], np.arange(n + 1))
        else:
            ta_s = ta
            bnd = np.zeros(n + 1, dtype=np.int64)

        nRi: List[np.ndarray] = [None] * n  # R-side nbr indices, sorted
        nQi: List[np.ndarray] = [None] * n  # Q-side nbr indices (fwd), sorted
        xRn: List[Optional[np.ndarray]] = [None] * n  # x aligned with nRi
        xQn: List[Optional[np.ndarray]] = [None] * n  # x aligned with nQi
        for t in range(n):
            nb = ta_s[bnd[t]:bnd[t + 1]]
            mq = inS[nb]
            rn_t = rpos[nb[~mq]]
            qn_t = qpos[nb[mq]]
            ro = np.argsort(rn_t, kind="stable")
            qo = np.argsort(qn_t, kind="stable")
            nRi[t] = rn_t[ro]
            nQi[t] = qn_t[qo]
            xRn[t] = xs_slot[nb[~mq]][ro]
            xQn[t] = xs_slot[nb[mq]][qo]
        minRv = np.array([int(a[0]) if a.size else BIG for a in nRi])
        maxRv = np.array([int(a[-1]) if a.size else -1 for a in nRi])
        minQf = np.array([int(a[0]) if a.size else BIG for a in nQi])
        maxQf = np.array([int(a[-1]) if a.size else -1 for a in nQi])

    net_stats = None
    if axis == 0:
        # The owner belongs to its horizontal support only at a real bend.
        net_stats = []
        for t, w in enumerate(order):
            mem = [t] if contacts[w][0] and contacts[w][1] else []
            for u in contacts[w][0]:
                tu = slot_of.get(u)
                if tu is not None and tu != t:
                    mem.append(tu)
            if len(mem) < 2:
                continue
            sl = np.asarray(mem, dtype=np.int64)
            mq = inS[sl]
            rs = rpos[sl[~mq]]
            qs = qpos[sl[mq]]
            net_stats.append((int(rs.min()) if rs.size else BIG,
                              int(rs.max()) if rs.size else -1,
                              int(qs.min()) if qs.size else BIG,
                              int(qs.max()) if qs.size else -1))

    # stepQ's R-side extrema rows are arm-independent: per S slot, the
    # extrema of static x over R-neighbours with index >= i, all i
    rrow_max: List[Optional[np.ndarray]] = [None] * n
    rrow_min: List[Optional[np.ndarray]] = [None] * n
    if axis == 1:
        ii_all = np.arange(p + 1)
        for t in q_slots:
            ra, xr = nRi[t], xRn[t]
            if ra.size:
                smaxs = np.concatenate(
                    [np.maximum.accumulate(xr[::-1])[::-1], [-np.inf]])
                smins = np.concatenate(
                    [np.minimum.accumulate(xr[::-1])[::-1], [np.inf]])
                pos = np.searchsorted(ra, ii_all)
                rrow_max[t] = smaxs[pos]
                rrow_min[t] = smins[pos]

    def _arm(arm_flip, path_of=None, slot_mode=False):
        """One orientation arm (``arm_flip`` reverses S). Returns
        (best_cost, best_order[, e_path]) where e_path is the DP path
        cost of ``path_of`` (a merge of R and forward S) if given.
        ``slot_mode`` (m == 1 only): return the per-slot cost vector
        instead — see the ``slot_costs`` contract above."""
        Q = S[::-1] if arm_flip else S
        qsl = q_slots[::-1] if arm_flip else q_slots  # slot of Q[j]
        if axis == 1:
            minQv = (m - 1 - maxQf) if arm_flip else minQf
            maxQv = (m - 1 - minQf) if arm_flip else maxQf

            def _qview(t):
                # Q-side indices sorted ascending in THIS arm, x aligned
                if arm_flip:
                    return ((m - 1 - nQi[t])[::-1], xQn[t][::-1])
                return nQi[t], xQn[t]

        # point-cost arrays: stepR[i, j] = cost of placing R[i-1] into
        # cell (i, j) (from (i-1, j)); stepQ[i, j] likewise for Q[j-1]
        # (from (i, j-1)). Zero on axis=0 (all cost lives in the gaps).
        stepR = np.zeros((p + 1, m + 1))
        stepQ = np.zeros((p + 1, m + 1))
        if axis == 1:
            jj_all = np.arange(m + 1)
            for i in range(1, p + 1):
                t = r_slots[i - 1]
                ra, xr = nRi[t], xRn[t]
                pos = int(np.searchsorted(ra, i))
                smax = float(xr[pos:].max()) if pos < ra.size else -np.inf
                smin = float(xr[pos:].min()) if pos < ra.size else np.inf
                qa, xq = _qview(t)
                if qa.size:
                    sufmax = np.concatenate(
                        [np.maximum.accumulate(xq[::-1])[::-1],
                         [-np.inf]])
                    sufmin = np.concatenate(
                        [np.minimum.accumulate(xq[::-1])[::-1],
                         [np.inf]])
                    posj = np.searchsorted(qa, jj_all)
                    hi = np.maximum(sufmax[posj], smax)
                    lo = np.minimum(sufmin[posj], smin)
                else:
                    hi = np.full(m + 1, smax)
                    lo = np.full(m + 1, smin)
                lower = np.logical_or(minRv[t] < i - 1, minQv[t] < jj_all)
                upper = np.isfinite(hi)
                # Avoid inf-inf even for an isolate or an upper-empty suffix.
                hi = np.where(upper, hi, 0.0)
                lo = np.where(upper, lo, 0.0)
                bend = lower & upper
                hi = np.where(bend, np.maximum(hi, xs_slot[t]), hi)
                lo = np.where(bend, np.minimum(lo, xs_slot[t]), lo)
                stepR[i, :] = hi - lo + bar * (lower.astype(int) + upper.astype(int))
            for j in range(1, m + 1):
                t = qsl[j - 1]
                qa, xq = _qview(t)
                pos = int(np.searchsorted(qa, j))
                smax = float(xq[pos:].max()) if pos < qa.size else -np.inf
                smin = float(xq[pos:].min()) if pos < qa.size else np.inf
                if rrow_max[t] is not None:
                    hi = np.maximum(rrow_max[t], smax)
                    lo = np.minimum(rrow_min[t], smin)
                else:
                    hi = np.full(p + 1, smax)
                    lo = np.full(p + 1, smin)
                lower = np.logical_or(minRv[t] < ii_all, minQv[t] < j - 1)
                upper = np.isfinite(hi)
                hi = np.where(upper, hi, 0.0)
                lo = np.where(upper, lo, 0.0)
                bend = lower & upper
                hi = np.where(bend, np.maximum(hi, xs_slot[t]), hi)
                lo = np.where(bend, np.minimum(lo, xs_slot[t]), lo)
                stepQ[:, j] = hi - lo + bar * (lower.astype(int) + upper.astype(int))

        # count grid CG[i, j]: #arms (axis=1) / #open nets (axis=0)
        # crossing the next slot gap at cell (i, j) — a pure function of
        # the placed set, built by rectangle scatter + 2-D prefix sum.
        diff = np.zeros((p + 2, m + 2))

        def _rect(i0, i1, j0, j1, w):
            i0 = max(i0, 0)
            j0 = max(j0, 0)
            i1 = min(i1, p)
            j1 = min(j1, m)
            if i1 < i0 or j1 < j0:
                return
            diff[i0, j0] += w
            diff[i1 + 1, j0] -= w
            diff[i0, j1 + 1] -= w
            diff[i1 + 1, j1 + 1] += w

        if axis == 1:
            # For an unplaced owner, some-but-not-all neighbors placed
            # means either a dual arm reaches its future corner or a sole
            # vertical arm still has a future contact. All-neighbors-placed
            # must be subtracted: its sole vertical support already ended.
            for t in range(n):
                if not nRi[t].size and not nQi[t].size:
                    continue
                mr, mq_ = int(minRv[t]), int(minQv[t])
                xr_, xq_ = int(maxRv[t]), int(maxQv[t])
                if not inS[t]:
                    r = int(rpos[t])
                    _rect(0, r, 0, m, +1.0)
                    _rect(0, min(r, mr), 0, mq_, -1.0)
                    _rect(xr_ + 1, r, xq_ + 1, m, -1.0)
                else:
                    q = int(m - 1 - qpos[t]) if arm_flip else int(qpos[t])
                    _rect(0, p, 0, q, +1.0)
                    _rect(0, mr, 0, min(q, mq_), -1.0)
                    _rect(xr_ + 1, p, xq_ + 1, q, -1.0)
        else:
            # h-net of w crosses the gap iff some member is placed and
            # some is not: 1 - [none placed] - [all placed]
            for (mnR, mxR, mnQ, mxQ) in net_stats:
                if arm_flip:
                    mnQ, mxQ = m - 1 - mxQ, m - 1 - mnQ
                _rect(0, p, 0, m, +1.0)
                _rect(0, mnR, 0, mnQ, -1.0)
                _rect(mxR + 1, p, mxQ + 1, m, -1.0)
        CG = np.cumsum(np.cumsum(diff, axis=0), axis=1)[:p + 1, :m + 1]

        # the DP. Full transition-cost matrices first: a[i, j] = cost of
        # the R-step into (i, j), b[i, j] = the Q-step's. Then the
        # right/down grid recurrence collapses per line: any path to
        # (i, j) enters row i by one R-step at some column k and
        # Q-steps from k to j, so T[i] = B[i] + running-min of
        # (T[i-1] + a[i] - B[i]) with B the row prefix-sum of b — one
        # minimum.accumulate per line, sweeping the SHORTER dimension.
        K = np.arange(p + 1)[:, None] + np.arange(m + 1)[None, :]
        gapM = gapv[np.maximum(K - 1, 0)]
        a = np.full((p + 1, m + 1), np.inf)
        a[1:, :] = stepR[1:, :] + gapM[1:, :] * CG[:-1, :]
        b = np.full((p + 1, m + 1), np.inf)
        b[:, 1:] = stepQ[:, 1:] + gapM[:, 1:] * CG[:, :-1]
        if slot_mode:
            # m == 1 closed form: the path inserting the S-member after
            # k rest-steps costs prefix(a[:,0])[k] + b[k,1] +
            # suffix(a[:,1])[k]; C[j0] equals the identity e_path by
            # the same accumulation (pinned in tests).
            aR0 = a[1:, 0]
            aR1 = a[1:, 1]
            pre = np.concatenate(([0.0], np.cumsum(aR0)))
            suf = np.concatenate((np.cumsum(aR1[::-1])[::-1], [0.0]))
            return pre + b[:, 1] + suf
        T = np.empty((p + 1, m + 1))
        if p <= m:
            B = np.zeros((p + 1, m + 1))
            B[:, 1:] = np.cumsum(b[:, 1:], axis=1)
            T[0, :] = B[0, :]
            for i in range(1, p + 1):
                T[i, :] = B[i, :] + np.minimum.accumulate(
                    T[i - 1, :] + a[i, :] - B[i, :])
        else:
            Bc = np.zeros((p + 1, m + 1))
            Bc[1:, :] = np.cumsum(a[1:, :], axis=0)
            T[:, 0] = Bc[:, 0]
            for j in range(1, m + 1):
                T[:, j] = Bc[:, j] + np.minimum.accumulate(
                    T[:, j - 1] + b[:, j] - Bc[:, j])
        # backtrack choices recovered vectorized from T + the cost
        # matrices; ties prefer the rest-step (deterministic merge)
        candR = np.full((p + 1, m + 1), np.inf)
        candR[1:, :] = T[:-1, :] + a[1:, :]
        candQ = np.full((p + 1, m + 1), np.inf)
        candQ[:, 1:] = T[:, :-1] + b[:, 1:]
        CH = (candR <= candQ + 1e-9).astype(np.int8)  # 1 = R-step

        i, j = p, m
        merged: List[int] = []
        while i + j > 0:
            if CH[i, j] == 1:
                merged.append(R[i - 1])
                i -= 1
            else:
                merged.append(Q[j - 1])
                j -= 1
        merged.reverse()

        e_path = None
        if path_of is not None:
            ci = cj = 0
            e_path = 0.0
            for v in path_of:
                g = gapv[ci + cj]
                if v not in cset:
                    e_path += stepR[ci + 1, cj] + g * CG[ci, cj]
                    ci += 1
                else:
                    e_path += stepQ[ci, cj + 1] + g * CG[ci, cj]
                    cj += 1
        return float(T[p, m]), merged, e_path

    if slot_costs:
        return _arm(False, slot_mode=True)
    bf, of, e0 = _arm(False, path_of=order)
    bb, ob, _ = _arm(True)
    if bb < bf - 1e-12:
        best, border, flip = bb, ob, True
    else:
        best, border, flip = bf, of, False
    if best < e0 - 1e-9 and border != order:
        return border, flip
    return None, False

