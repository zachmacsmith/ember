# Guiding minorminer's *search* — ordering & rip-up heuristics (deterministic + learned)

**Question.** Every prior Ember effort tuned an embedder's *initialization* (Reweave's
warm start; the learned-placement bake-off, which plateaued at ~1%). The untried lever is
the **search itself**: the **vertex/construction order** and the **rip-up (tear-and-reroute)
policy**. Does guiding those — deterministically or with a learned model — beat stock
minorminer (MM) and Reweave on **ACL and/or run-to-run variance**?

**Short answer.** *Ordering helps; rip-up selection does not.*
- **Rip-up selection is a dead lever** (for quality): on the embeddings Reweave's LNS
  reaches, *which* chain you tear up first changes nothing — every policy, even a contrarian
  one, lands on the same local optimum.
- **Vertex ordering is a real lever on minorminer's full search.** We forked minorminer to
  inject a custom order into `find_embedding` (parity-exact without it) and found that a
  **bandwidth/locality order (Cuthill–McKee) lowers mean ACL ~1.6–2.2% and cuts run-to-run
  variance ~25%**, deterministically. A **per-instance portfolio** of good orders reaches
  **−5.3% ACL vs MM and −3.1% vs Reweave at roughly half MM's variance** — the best method in
  the study — at ~6× wall-clock. **Learning does not beat the best deterministic order**: a
  cheap order-selector only ties Cuthill–McKee, and a learned generated order is no better than
  the fixed heuristics — so a GPU GNN was not warranted.

Everything inherits minorminer's completeness (the fork is stock MM when no order is given),
so these are quality/variance changes, never validity changes.

---

## 1. The four levers and where they live

Minor embedding via MM-style search has four control points
(see `docs/candidate-algorithms/search-guidance` and `CLAUDE.md`):

1. **construction / vertex order** — the order chains are first built / revisited;
2. **rip-up selection** — which chain to tear out and reroute next;
3. congestion schedule; 4. routing kernel.

The user named #1 and #2 as the focus; #3–#4 were largely settled in the optimization pass.
We tested #1 and #2 in three vehicles: **Reweave** (our open Python MM-style engine), a
**fork of real minorminer**, and minorminer's own **`quickpass`** greedy primitive.

## 2. Honesty gate — is there any headroom? (ceiling probe)

`ceiling_probe.py` samples the search-control choices randomly and reads the ACL spread —
the most a perfect order/policy could buy:

| signal | best-of-12 vs random-mean |
|--------|--------------------------:|
| MM stochastic (random seeds) | **+7.1%** |
| construction order, raw cold start | +10.5% |
| construction order, after LNS | +16.7% |

So ordering has real headroom (~7–17%); worth pursuing. (The cold-start signals are from the
small cells where the negotiated cold start stays valid under the time budget.)

## 3. Rip-up selection — a measured **negative**

`rw_ripup.py` adds five rip-up *selection* policies to Reweave's dirty-set LNS (longest,
boundary-churn, contention, inflation, shortest), changing **only** which chain is attacked
next (move operator + accept rule held byte-for-byte). On the dense grid (6 LNS-active cells
× 3 seeds):

| policy | ACL | vs Reweave |
|--------|----:|-----------:|
| reweave (baseline) | 4.908 | — |
| inflation | 4.906 | −0.0% |
| longest (≡ baseline) | 4.908 | +0.0% |
| shortest (contrarian) | 4.909 | +0.0% |
| boundary | 4.910 | +0.0% |
| contention | 4.910 | +0.0% |

All within 0.004 ACL. The dirty-set improver converges to essentially the same local optimum
regardless of rip-up order — so the FPGA "which net to rip" idea (RL-Ripper) has **no quality
headroom here**, and a learned rip-up policy was not pursued. (`reweave-ripup-longest`
reproducing `reweave` exactly is also the parity check on the refactored loop.)

## 4. Vertex ordering — the live lever

### 4a. On minorminer's `quickpass` primitive (cheap, real MM internals)
`minorminer_guided.py` drives MM's own `quickpass` greedy pass with a chosen order (no fork).
Ordering clearly matters — `cuthill`/`minfill` beat MM's native `rpfs` order by ~4% on
identical machinery — but `quickpass` is MM's *weak* primitive: even the best-ordered
quickpass (~5.34) loses to the full `find_embedding` (~5.09). So the decisive test needs the
order injected into the **full** search.

### 4b. On minorminer's full `find_embedding` (the fork) — the headline
We forked minorminer 0.2.22 (`external/minorminer-fork`, reproduced by
`scripts/build_mm_fork.sh` from `scripts/mm_fork.patch`): a ~90-line patch adds a
`var_order=` parameter that injects a user order into every pass of `heuristicEmbedding`.
**Without `var_order` the fork is byte-identical to stock minorminer** (parity-tested over
seeds; `mmfork` ≡ `minorminer` in the leaderboard). Exposed as `mmfork-<order>` algorithms.

Dense grid (6 cells × 4 seeds, `tries=10`), ACL vs the default (random RPFS) order:

| order | ACL | vs default | std(seed) | wins |
|-------|----:|-----------:|----------:|-----:|
| default (stock MM) | 4.865 | — | 0.133 | 0/6 |
| **cuthill** | **4.760** | **−2.2%** | **0.101** | 5/6 |
| bfs | 4.755 | −1.7% | 0.139 | 3/6 |
| spectral | 4.785 | −1.3% | 0.139 | 4/6 |
| minfill | 4.829 | −0.8% | 0.179 | 2/6 |
| mcs | 4.841 | −0.4% | 0.118 | 5/6 |
| degeneracy | 4.905 | +0.5% | 0.197 | 2/6 |
| community | 4.948 | +1.4% | 0.178 | 3/6 |

A bandwidth/locality order (Cuthill–McKee) wins on ACL **and** variance. Because these
instances embed on the first try, `tries=10`≈`tries=1`: MM's variance here is *order*-driven,
which is exactly why fixing a good order cuts it.

Standard grid (7 cells × 3 seeds; size/density/topology mix), vs stock minorminer (3.641,
std 0.115):

| method | ACL | std | vs MM | vs Reweave | time |
|--------|----:|----:|------:|-----------:|-----:|
| **mmfork-portfolio** | **3.456** | **0.059** | **−5.3%** | **−3.1%** | 2.9s |
| reweave | 3.553 | 0.102 | −2.3% | — | 0.7s |
| mmfork-cuthill | 3.592 | 0.105 | −1.6% | +0.8% | 0.5s |
| mmfork-mcs | 3.612 | 0.103 | −0.8% | +1.6% | 0.5s |
| minorminer ≡ mmfork | 3.641 | 0.115 | 0.0% | +2.4% | 0.5s |

**`mmfork-portfolio`** (run the 5 good orders, keep the best) is the study's best method:
−5.3% ACL vs MM, **−3.1% vs Reweave**, at **half MM's variance** — at ~6× the wall-clock,
since it runs every order. That cost is exactly what the learned arm tries to remove.

## 5. Learned ordering (`learn_order.py`) — *preliminary*

Two cheap, local learned approaches (ceiling-probe discipline — if a linear model can't beat
the best fixed order, a heavy GNN almost certainly won't):

- **(A) order selector** — graph-level features → which fixed order to run (1× cost).
- **(B) per-vertex linear score** — features → order, weights hill-climbed with the forked MM
  in the loop (decode-aware).

Held-out test set (47 instances, instance-disjoint from the 72 train), mean ACL:

| method | ACL | vs MM |
|--------|----:|------:|
| stock minorminer | 3.963 | — |
| best fixed order (cuthill) | 3.893 | −1.8% |
| **oracle / portfolio** (per-instance best) | **3.780** | **−4.6%** |
| (A) learned selector | 3.889 | −1.9% |
| (B) learned per-vertex score | 3.956 | −0.2% |

The verdict is **negative for learning** on this lever: the selector (−1.9%) only **ties the
best fixed order** (−1.8%) and comes nowhere near the oracle portfolio (−4.6%) — i.e. graph-level
features don't reliably predict which order wins, so it amounts to "just use Cuthill–McKee". The
learned per-vertex score (−0.2%) **does not beat the fixed heuristics** at all — its hill-climbed
weights collapse to a degeneracy-like prior (degree+core up, eccentricity down). Because this
cheap, decode-aware test shows no headroom above the best deterministic order, **a GNN on the GPU
cluster was not warranted** — the same ceiling the learned-placement bake-off hit.

## 5b. Do they stack with Reweave? Are they drop-in safe?

**Stacking — yes.** Reweave warm-starts from any registered base embedder (`base_method`) and
then improves it, so the ordered variants compose with it directly. Seeding Reweave from
`mmfork-portfolio` instead of stock MM stacks the two orthogonal gains (better-ordered base +
negotiated improver) and gives the lowest ACL of all:

| cell | minorminer | reweave | mmfork-portfolio | **reweave+mmfork** |
|------|-----------:|--------:|-----------------:|-------------------:|
| n40 d0.5 | 4.57 | 4.45 | 4.38 | **4.32** |
| n60 d0.5 | 7.71 | 7.30 | 6.89 | **6.62** |

**Drop-in safety — yes, ≥ minorminer.** Unlike a constructive embedder (ATOM) that can fail
outright, every `mmfork` output is a genuine minorminer embedding. `mmfork` ≡ stock MM;
`mmfork-portfolio` always includes a stock-MM config; and each single-order `mmfork-<order>`
**falls back to one stock-MM call if its ordered attempt fails** → success ≥ MM by construction.
Empirically, forced into MM's partial-success regime (8 s budget, dense cells), a fixed Cuthill
order *matches or exceeds* MM's success rate — dramatically on the hardest cell:

| cell | minorminer | mmfork-cuthill (no fb) | mmfork-cuthill |
|------|-----------:|-----------------------:|---------------:|
| n63 d0.5 | 8/8 | 8/8 | 8/8 |
| n64 d0.5 | 7/8 | 8/8 | 8/8 |
| n65 d0.5 | **2/8** | **8/8** | **8/8** |

A good order *expands MM's feasibility frontier* (embeds instances MM's random order misses in
the same budget), as well as shortening chains — so the fallback is a guarantee, not a crutch.

## 6. Verdict (so far)

- **Rip-up selection: no quality headroom** — a clean negative; Reweave's gains come from its
  move operator + negotiated routing, not the rip-up order.
- **Vertex ordering on MM's full search: a real, deterministic win** — Cuthill–McKee −1.6/−2.2%
  ACL and ~25% lower variance; a per-instance **portfolio −5.3% vs MM / −3.1% vs Reweave at
  half the variance**, the best method here. It **stacks with Reweave** (`reweave+mmfork` is best
  overall) and is **as reliable as minorminer** (≥ MM success by construction; more reliable near
  the boundary).
- **Learning does not beat the best deterministic order** on this lever — the order-selector
  only ties Cuthill–McKee (and never approaches the per-instance oracle), and a learned generated
  order is no better than the fixed heuristics. Consistent with the placement bake-off: strong
  hand-built structure is hard to beat with a learned model here, and the gap the oracle shows
  (−4.6%) is real but not predictable from features — so the open opportunity is a *cheaper*
  portfolio, not a learned order.

## Reproduce

```bash
# build the parity-exact minorminer fork (var_order patch)
bash scripts/build_mm_fork.sh
# honesty gate, rip-up negative, ordering on the full search, learned arm:
.venv/bin/python docs/candidate-algorithms/data/ceiling_probe.py
.venv/bin/python docs/candidate-algorithms/data/leaderboard.py --dense reweave-ripup-{longest,boundary,contention,inflation,shortest}
.venv/bin/python docs/candidate-algorithms/data/mmfork_order_probe.py
.venv/bin/python docs/candidate-algorithms/data/leaderboard.py mmfork mmfork-cuthill mmfork-portfolio ...
.venv/bin/python docs/candidate-algorithms/data/learn_order.py
```

New algorithms: `mmfork`, `mmfork-<order>`, `mmfork-portfolio`, `mmfork-learned`
(`minorminer_forked.py`); `mm-guided-<order>`, `mm-strategy-<s>` (`minorminer_guided.py`);
`reweave-cold-<order>` (`rw_order.py`); `reweave-ripup-<policy>` (`rw_ripup.py`).
Orderings in `search_orders.py`; learned order in `learned_order.py`.
