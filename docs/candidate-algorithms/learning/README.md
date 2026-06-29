# Learning-based minor-embedding — a bake-off vs PathFinder/minorminer

**Question (from the patent in scope):** can a neural network, trained on a cache of
randomized problem graphs labelled with *PathFinder-optimized* embeddings, predict
embeddings (or seeds for minorminer) that **match or beat PF/MM on average chain
length (ACL) and ACL-variance**? The patent's architecture is: a cache of
(problem-graph, embedding) pairs → a deep network predicts a *candidate embedding*
→ a minor-embedding algorithm refines it (predict-then-refine), with graph
encodings via feature-extraction or a Graph-VAE, and optimized results fed back
into the cache.

This directory reports a fair, end-to-end bake-off built in `packages/ember-qc-learn`
and evaluated through Ember's own `benchmark_one` harness.

## Approach — a "learned layout", then decode

Every learned family predicts, for each logical vertex, a **coordinate in the
target's normalized hardware frame** (a learned *layout*). From that layout we
decode to a valid embedding two ways, both reusing Ember's repair backend so no
validity logic is reinvented:

- **seed → MM** (the patent's predict-then-refine): snap each vertex to a distinct
  nearest qubit (Hungarian) → `minorminer.find_embedding(initial_chains=…)`.
- **direct → repair**: proximity soft-assignment → `round_assignment` →
  `grow_to_connected` → `resolve_overlaps`.

An *oracle* check (feed the true PF-chain centroids as the layout) confirmed the
decoder recovers PF quality — **seed→MM 1.03× ACL, 100% valid** — so the learning
problem is exactly "predict a good layout".

### The four families (the bake-off)

| family | what it learns | path | patent tie-in |
|---|---|---|---|
| `learned-gnn-seed` | GNN → layout, **supervised** (MSE to PF chain centroids) | seed→MM | FIG 3/4 |
| `learned-vae` | Graph-VAE → layout; **generative**, samples K=8 layouts and keeps the best | seed→MM | FIG 7 |
| `learned-obj` | GNN → layout, **label-free** (minimizes an embedding objective: edge-stretch + anti-collapse) | seed→MM | FIG 3 |
| `learned-retrieve` | **non-neural** embeddings-cache: nearest training graph → remap its PF chains | seed→MM | FIG 2/5/6 (prior art) |

`learned-gnn-seed-direct` is the same model decoded via the direct→repair path.
`retrieve` is the strong, cheap baseline that learning must beat to justify itself.

## Pipeline (`packages/ember-qc-learn`)

- `features.py` — source structural features (degree, clustering, triangles, core,
  Laplacian PE) + target 2-D hardware geometry (dwave_networkx layouts).
- `decode.py` — layout → valid embedding (both paths), reusing `ember_qc.embedding_backend`.
- `datagen.py` — randomized graphs (ER / d-regular / BA / kNN-geometric over a
  size×density grid) labelled with `pathfinder-thorough` into P6/Z4; **instance-disjoint**
  train/val/test (a graph never crosses splits); parallel via `benchmark_one`.
- `dataset.py` / `models/` / `train.py` — PyG models predicting layout coords; models
  are **selected on the real downstream metric** (val ACL ratio after seed→MM), not on MSE.
- `families/` — the VAE / objective / retrieval modules (self-registering `learned-*`).
- `algorithms.py` — registry adapters so every family runs through `benchmark_one`.
- `evaluate.py` / `make_learn_figures.py` — the held-out test bake-off + figures.

## Data & compute

- **Dataset:** 1560 train / 312 val / 312 test problem graphs, each labelled with
  PathFinder-thorough into **Pegasus P6 (680 qubits)** and **Zephyr Z4 (576 qubits)**
  → 3120 / 624 / 624 valid (graph, target, PF-embedding) examples. Instance-disjoint.
- **Training:** on a 4-GPU cluster (2× RTX A6000 + 2× A4000); torch + torch_geometric.
  Each neural family trained per target; retrieval builds an index (CPU).

### Training (validation) results — val ACL ratio vs PathFinder-thorough (100% valid)

| family | Pegasus P6 | Zephyr Z4 |
|---|---|---|
| gnn-seed | 1.025× | 1.013× |
| graph-VAE (K=8) | 1.024× | 1.015× |
| objective-GNN | 1.027× | 1.013× |

All neural families land within ~1.5–2.7% of PathFinder-thorough on held-out
*validation*. The decisive numbers are the held-out **test** set below.

## Results (held-out test set)

312 test graphs (instance-disjoint from training), 3 seeds each, through Ember's
`benchmark_one`. All methods 100% valid. `figures/acl_and_variance.png` and
`figures/acl_ratio_by_family.png` visualize these.

**Pegasus P6** (mean ACL — lower better; ACL std over seeds = run-to-run variance):

| algorithm | mean ACL | ACL std/seed | time (s) |
|---|---|---|---|
| minorminer | 2.075 | 0.072 | 0.39 |
| minorminer-layout | 2.101 | 0.078 | 0.48 |
| pathfinder | 2.044 | 0.068 | 0.52 |
| pathfinder-thorough | 1.955 | 0.037 | 2.17 |
| **learned-vae** | **1.947** | **0.031** | 3.74 |
| learned-obj | 2.057 | 0.066 | 0.51 |
| learned-gnn-seed | 2.075 | 0.066 | 0.50 |
| learned-retrieve | 2.072 | 0.066 | 0.40 |

**Zephyr Z4** (same protocol):

| algorithm | mean ACL | ACL std/seed |
|---|---|---|
| **learned-vae** | **1.675** | **0.025** |
| pathfinder-thorough | 1.687 | 0.029 |
| learned-obj | 1.765 | 0.055 |
| minorminer | 1.777 | 0.057 |
| minorminer-layout | 1.787 | 0.058 |

**Per-family P6 mean ACL** (vs the two strongest references):

| family | minorminer | pathfinder-thorough | learned-vae | learned-obj |
|---|---|---|---|---|
| BA  | 1.621 | 1.540 | **1.515** | 1.610 |
| ER  | 2.858 | **2.690** | 2.698 | 2.846 |
| GEO | 2.135 | **1.994** | 1.996 | 2.115 |
| REG | 1.425 | 1.353 | **1.330** | 1.394 |

## Verdict

**Yes — learning helps, and the win is on the metric that matters most (variance),
plus a tie-or-better on quality.**

- **`learned-vae` (generative Graph-VAE) is the best method overall on both P6 and
  Z4**, on *both* mean ACL and run-to-run variance. It edges the strongest heuristic
  (PathFinder-thorough) on mean ACL (P6 1.947 vs 1.955; Z4 1.675 vs 1.687) and beats
  it on **variance** (P6 0.031 vs 0.037; Z4 0.025 vs 0.029), while beating
  `minorminer` and `minorminer-layout` decisively on every source family. Per-family
  it beats PF-thorough on BA + REG and ties (±0.3%) on ER + GEO. The mechanism: the
  seed→MM decoder is near-lossless (oracle 1.03×), so the task reduces to predicting
  a good layout; sampling **K=8** layouts and keeping the best both lowers ACL and —
  by being insensitive to any single MM seed — **cuts variance**, which is exactly
  PathFinder's headline advantage, now improved on by a learned model.
- **`learned-obj` (label-free objective-GNN) beats `minorminer` and `minorminer-layout`
  on every family at minorminer-like speed (~0.5 s)** — learning a layout *objective*
  (no PF labels at all) already improves on the standard baselines.
- **`learned-gnn-seed` and `learned-retrieve` match `minorminer`** within noise at
  ~0.4–0.5 s; the non-neural retrieval cache is the cheapest learned method and ties MM.

**Cost & caveats (honest).** The VAE's quality/variance win costs wall-clock: 3.7 s
(K=8 layouts × MM decode) vs MM's 0.4 s and PF-thorough's 2.2 s; the single-shot
learned methods are MM-speed. The mean-ACL margin over PF-thorough is small (~0.4%
P6 / ~0.7% Z4) and family-dependent — the *robust, decisive* learned wins are (a)
over MM / MM-layout on quality everywhere and (b) on **variance** versus all methods.
Test sources are ≤50 nodes; larger graphs, broken-hardware robustness, and end-to-end
(decode-in-the-loop) training are the natural next steps. (`minorminer-layout` was
marginally *worse* than plain `minorminer` on this grid — p-norm layout did not help here.)

## Reproduce

```bash
# 1. dataset (cluster CPUs)
python -m ember_qc_learn.datagen --out data/learn --scale cluster --workers 120
# 2. train each family (per target); e.g. on a GPU node:
python scripts/train_family.py gnn-seed pegasus_6 ckpts/gnn-seed_pegasus_6.pt --device cuda
python scripts/train_family.py vae      pegasus_6 ckpts/vae_pegasus_6.pt      --device cuda
python scripts/train_family.py obj      pegasus_6 ckpts/obj_pegasus_6.pt      --device cuda
python -m ember_qc_learn.families.retrieve --data data/learn --out ckpts
# 3. evaluate on the held-out test set + figures
EMBER_LEARN_CKPT_DIR=ckpts python -m ember_qc_learn.evaluate --data data/learn --out data/learn/eval --seeds 3
python -m ember_qc_learn.make_learn_figures --eval data/learn/eval --out docs/candidate-algorithms/learning
```
Cluster env: `scripts/cluster_bootstrap.sh` (uv-based torch cu121 + torch_geometric).
