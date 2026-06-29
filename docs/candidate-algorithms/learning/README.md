# Learning-based minor-embedding — an honest bake-off vs PathFinder/minorminer

**Question (from the patent in scope):** can a neural network, trained on a cache of
randomized problem graphs labelled with *PathFinder-optimized* embeddings, predict
embeddings (or seeds for minorminer) that **match or beat PF/MM on average chain
length (ACL) and ACL-variance**?

**Short answer, after a thorough investigation:** *modestly, and only after fixing a
fundamental flaw.* A naive supervised model is **ill-posed and collapses to a constant**;
a **symmetry-invariant (Procrustes) objective** fixes it and yields a small but
**statistically significant** improvement over minorminer (~1%); a **decode-aware RL**
fine-tune does **not** exceed that — so a strong heuristic with restarts is hard to beat
with learned placement. An earlier "the VAE beats PathFinder-thorough" result was an
**artifact** of an unequal restart budget on top of a collapsed model, and is retracted
below.

## 1. The naive approach fails: ill-posed target → collapse

The first bake-off (gnn-seed, graph-VAE, objective-GNN, retrieval) appeared to show a
generative graph-VAE beating every baseline. On audit this was **not real**:

- **The supervised models collapse.** gnn-seed and the VAE regress each vertex's
  *absolute* hardware coordinate (its PF chain centroid). That target is **ill-posed**:
  a graph's embedding can be placed anywhere on the fabric (translation + the fabric's
  symmetries), so structure cannot predict absolute coordinates. The MSE-optimal
  predictor is the constant global mean, which the model finds in epoch 1 — the
  notorious "flat loss." Verified directly: the trained VAE outputs **one constant point
  for every vertex of every graph** (prediction std = 0); its MSE equals the
  "predict-the-mean" null model exactly. (Not underfitting, data, or model size.)
- **The VAE "win" was a budget artifact.** Because the layout is constant, the VAE's
  K=8 sampling is just **best-of-8 minorminer from a fixed central seed**. At equal
  budget it ties/loses to plain best-of-8 cold minorminer (2.097 vs 2.086 on a matched
  sample); its apparent edge over `pathfinder-thorough` was simply **8 restarts vs 4**.

## 2. The fix that works: a symmetry-invariant objective

The cure for the collapse is to make the loss **invariant to the placement symmetry**.
The **Procrustes loss** aligns the predicted layout to the target up to
rotation+reflection+scale+translation (closed-form, differentiable) *before* the MSE, so
the loss only sees the **relative** structure — which *is* determined by the graph. This
eliminates the collapse: the model learns a real, structure-aware layout (non-zero
spread; adjacent vertices placed closer than non-adjacent). Implemented as
`families/procrustes.py` (`learned-procrustes`, `learned-procrustes-k8`).

## 3. Fair, equal-budget results (held-out test set, 312 graphs)

The honest comparison gives every method the **same decode budget** (the earlier bake-off
did not). Single-shot = 1 minorminer decode; best-of-8 = 8 decodes.

| method | mean ACL | vs cold MM | Wilcoxon p vs cold |
|--------|---------:|-----------:|-------------------:|
| single cold minorminer | 2.072 | — | — |
| **`learned-procrustes`** (single) | **2.056** | **−0.8%** | 0.047 |
| `learned-procrustes` + RL (single) | **2.040** | **−1.5%** | 4.2e-4 |
| best-of-8 cold minorminer | 1.943 | — | — |
| **`learned-procrustes-k8`** | **1.925** | **−0.9%** | <1e-3 |
| `+RL`, best-of-8 | 1.927 | −0.8% | 1.3e-4 |

So the symmetry-fixed learned layout beats minorminer **significantly** at equal budget,
both single-shot and in best-of-8 — but the **magnitude is small (~1%)**. (Numbers are from
one matched 312-graph run; a light RL fine-tune, below, nudges single-shot to −1.5% but the
RL-vs-Procrustes gap is **not** significant, p=0.06.)

## 4. Decode-aware RL does not break the ceiling

To try to exceed the ~1% placement gain, we ran **REINFORCE with minorminer in the loop**
(policy = the Procrustes layout + exploration; reward = decoded ACL with a per-graph
baseline; small Procrustes anchor). Warm-started from the Procrustes model, the validation
gain does **not climb** and in fact **drifts down** (two independent runs: +1.1%→+0.9%→+0.2%
and +0.3%→+0.4%) — the noisy policy gradient cannot find placements better than the
supervised layout and slowly walks off it. The limit is the *placement action space*, not
the training objective: a 2-D layout only loosely maps to Pegasus hop-distance, and
minorminer's cold start + restarts is already a strong, well-tuned search.

## 5. Verdict

- **Learning helps, but only modestly and only after the symmetry fix.** The nontrivial
  contribution is the **diagnosis** (the supervised target is ill-posed → collapse) and
  the **fix** (a Procrustes/similarity-invariant objective), which turns a useless
  constant-predicting model into one that beats minorminer by ~1% (statistically
  significant) at equal budget.
- **It does not beat best-of-K minorminer by much**, and **decode-aware RL does not
  exceed the supervised layout** — the placement-prediction paradigm has a low ceiling
  here. The patent's premise is *partially* borne out: a learned model can give a small,
  real improvement, but it is not a substitute for a good heuristic with restarts.
- **The earlier "learned-vae beats PathFinder-thorough" claim is retracted** as a budget
  artifact.

Honest, validity is never at risk: all learned methods inherit minorminer's completeness
(the decoder always falls back to a cold minorminer call), so they are 100%-success in the
same sense minorminer is, and the learned layout only changes *quality*, never validity.

## Reproduce

```bash
# dataset (instance-disjoint splits, PF-thorough labels into P6+Z4)
python -m ember_qc_learn.datagen --out data/learn --scale cluster --workers 120
# the working method:
python scripts/train_family.py procrustes pegasus_6 ckpts/procrustes_pegasus_6.pt --device cuda
# fair equal-budget evaluation + significance: scripts under this directory / eval/.
```

`eval/` holds the committed CSVs; the collapse diagnosis, fair-budget control, and RL
scripts are in the project scratch and summarized above.
