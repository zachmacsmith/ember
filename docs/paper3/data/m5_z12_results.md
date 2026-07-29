# M5 Zephyr Z12 — full-library results (main batch, §4.11)

30,221 eligible graphs × {minorminer, p3-template, p3-ate, p3-clmm, p3-mmpolish},
60 s/attempt, seed 4242, arms v1.1 (guards active). Pairing: (instance, trial) [CLI]
— per-arm derived seeds differ; the measured seed-noise floor on success rates is
sd 1.57 pt / max 4.55 pt per family (notes §4.11-Z12, passthrough null).
Cells: median paired ΔACL% vs minorminer on both-succeed pairs (win-rate), · success%.
**Bold** = category win (median < −0.5%, win-rate ≥ 55%). Raw DB: hyde06
results/m5full_z12/ (700 MB, not in git); verdicts: m5_analyze.py output.

| category | n | MM succ% | p3-ate | p3-mmpolish | p3-clmm | p3-template |
|---|---|---|---|---|---|---|
| watts_strogatz | 11988 | 66.5 | +0.0% (47%W) · 67%s | **-3.2% (65%W)** · 67%s | +0.0% (43%W) · 67%s | +25.0% (17%W) · 67%s |
| barabasi_albert | 3416 | 66.3 | +0.0% (45%W) · 67%s | **-1.6% (56%W)** · 66%s | +0.0% (37%W) · 67%s | +12.0% (25%W) · 67%s |
| regular | 3375 | 57.8 | -1.0% (53%W) · 58%s | **-2.9% (64%W)** · 58%s | +0.0% (48%W) · 58%s | +16.0% (29%W) · 59%s |
| random_er | 3024 | 72.1 | +0.0% (43%W) · 74%s | +0.0% (46%W) · 72%s | +0.0% (39%W) · 74%s | +3.6% (28%W) · 74%s |
| planted_solution | 2616 | 91.2 | +0.0% (44%W) · 91%s | -0.2% (50%W) · 91%s | +0.0% (44%W) · 91%s | +33.9% (13%W) · 92%s |
| sbm | 1125 | 76.9 | +0.0% (48%W) · 77%s | **-2.1% (57%W)** · 77%s | +0.0% (41%W) · 77%s | +26.9% (19%W) · 78%s |
| generalized_petersen | 755 | 91.7 | +0.0% (43%W) · 91%s | +0.0% (47%W) · 92%s | +0.0% (45%W) · 92%s | +22.4% (13%W) · 92%s |
| turan | 607 | 83.2 | **-5.6% (60%W)** · 88%s | **-2.4% (57%W)** · 83%s | **-4.5% (59%W)** · 87%s | +0.0% (49%W) · 88%s |
| spin_glass | 598 | 69.2 | **-3.5% (62%W)** · 74%s | **-2.6% (61%W)** · 69%s | +0.0% (49%W) · 74%s | +6.6% (43%W) · 74%s |
| weak_strong_cluster | 444 | 54.5 | +0.0% (50%W) · 56%s | **-4.3% (83%W)** · 55%s | +0.0% (45%W) · 57%s | +15.3% (13%W) · 60%s |
| circulant | 337 | 86.9 | +0.0% (43%W) · 88%s | -0.7% (53%W) · 88%s | +0.0% (46%W) · 87%s | +25.0% (11%W) · 87%s |
| random_planar | 216 | 88.9 | +0.0% (42%W) · 89%s | **-2.1% (58%W)** · 89%s | +1.8% (35%W) · 89%s | +43.0% (2%W) · 89%s |
| bipartite | 208 | 81.2 | **-12.3% (66%W)** · 83%s | +0.0% (38%W) · 80%s | **-12.0% (64%W)** · 82%s | **-12.3% (62%W)** · 85%s |
| triangular_lattice | 182 | 90.1 | +0.0% (42%W) · 90%s | **-2.4% (59%W)** · 90%s | +0.0% (46%W) · 90%s | +28.2% (9%W) · 88%s |
| honeycomb | 151 | 72.8 | +0.7% (40%W) · 74%s | +0.0% (43%W) · 73%s | +0.0% (47%W) · 74%s | +10.1% (20%W) · 72%s |
| grid | 143 | 82.5 | +0.0% (38%W) · 84%s | +0.0% (48%W) · 84%s | +0.0% (46%W) · 83%s | +17.2% (6%W) · 85%s |
| kagome | 130 | 71.5 | +1.1% (45%W) · 74%s | **-1.5% (55%W)** · 72%s | +0.0% (49%W) · 73%s | +17.3% (18%W) · 71%s |
| johnson | 74 | 43.2 | **-6.4% (81%W)** · 43%s | **-4.1% (84%W)** · 43%s | +4.5% (31%W) · 43%s | **-3.6% (62%W)** · 43%s |
| cubic_lattice | 74 | 56.8 | +0.0% (40%W) · 55%s | +0.0% (45%W) · 55%s | +0.4% (34%W) · 55%s | +9.0% (20%W) · 57%s |
| king_graph | 70 | 72.9 | +0.8% (37%W) · 71%s | **-5.2% (65%W)** · 73%s | -1.0% (52%W) · 71%s | +30.0% (10%W) · 73%s |
| frustrated_square | 70 | 74.3 | +0.6% (40%W) · 71%s | **-5.7% (70%W)** · 73%s | +0.2% (45%W) · 70%s | +29.9% (14%W) · 73%s |
| shastry_sutherland | 66 | 100.0 | +1.1% (36%W) · 100%s | **-2.8% (62%W)** · 100%s | +0.0% (45%W) · 100%s | +14.9% (17%W) · 100%s |
| cycle | 63 | 96.8 | +0.0% (22%W) · 95%s | +0.0% (21%W) · 97%s | +0.0% (25%W) · 97%s | +0.1% (10%W) · 94%s |
| star | 63 | 71.4 | +0.0% (38%W) · 73%s | +0.0% (29%W) · 73%s | +0.0% (24%W) · 73%s | +0.0% (40%W) · 95%s |
| path | 63 | 95.2 | +0.0% (0%W) · 95%s | +0.0% (0%W) · 97%s | +0.0% (0%W) · 95%s | +0.2% (0%W) · 95%s |
| wheel | 62 | 93.5 | +0.0% (40%W) · 94%s | +0.0% (45%W) · 92%s | +0.0% (36%W) · 95%s | +35.0% (7%W) · 92%s |
| lfr_benchmark | 61 | 68.9 | -0.1% (50%W) · 69%s | **-5.0% (71%W)** · 69%s | **-2.8% (60%W)** · 69%s | +4.9% (36%W) · 69%s |
| complete | 56 | 78.6 | **-9.6% (66%W)** · 86%s | -0.8% (52%W) · 79%s | **-5.1% (61%W)** · 86%s | **-8.1% (59%W)** · 86%s |
| kneser | 41 | 56.1 | **-9.5% (87%W)** · 66%s | **-1.4% (65%W)** · 61%s | **-2.5% (65%W)** · 66%s | **-8.9% (61%W)** · 66%s |
| hardware_native | 41 | 48.8 | **-14.2% (74%W)** · 51%s | +5.9% (42%W) · 49%s | **-3.0% (63%W)** · 51%s | +34.1% (25%W) · 51%s |
| tree | 26 | 92.3 | +0.0% (21%W) · 92%s | +0.0% (33%W) · 92%s | +0.0% (29%W) · 92%s | +6.5% (21%W) · 92%s |
| bcc_lattice | 22 | 63.6 | +1.7% (38%W) · 59%s | **-2.1% (57%W)** · 64%s | +6.2% (46%W) · 59%s | +20.9% (15%W) · 59%s |
| named_special | 12 | 100.0 | +0.0% (8%W) · 100%s | +0.0% (0%W) · 100%s | +0.0% (8%W) · 100%s | +27.1% (0%W) · 100%s |
| hypercube | 11 | 63.6 | +3.7% (0%W) · 64%s | +0.0% (14%W) · 64%s | +0.0% (14%W) · 64%s | +50.0% (0%W) · 64%s |
| binary_tree | 11 | 81.8 | +0.0% (11%W) · 91%s | +0.0% (11%W) · 82%s | +0.0% (11%W) · 82%s | +6.7% (11%W) · 91%s |

## Reading guide

- **p3-mmpolish**: wins or ties 34/35 categories (sole loss hardware_native, 41 graphs) — a
  strict-improvement wrapper on MM; the consistency arm.
- **p3-ate**: the margin arm — dense-structured wins to −14.2% and (per E0/M4) −9..−33% on
  dense-random cells; ties (≡ MM at another seed) below the crossover. Its ~+0.6..1.7%
  nominal losses on small lattices are the template-attempt tax (see improvement-notes).
- **p3-clmm**: dense-structured/mid-band wins; passthrough elsewhere; johnson/random_planar
  are its documented boundaries (ate covers both).
- **p3-template**: constructive specialist; standalone it loses everywhere sparse by design —
  it ships inside p3-ate.
- Library category means are regime mixtures: the dense-random headline lives at the
  (n ≥ 80, p ≥ 0.2) cells of the crossover map, a thin slice of the library's ER graphs.
