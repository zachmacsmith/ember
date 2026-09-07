# EXPERIMENTS — how experiments are run and how to compare against the baseline

Everything below was verified against the working tree on 2026-09-07
(branch `factored`, HEAD `39cffd06`). Commands are given relative to the
repository root.

One caveat on provenance: the baseline files in section 6 were recorded
by the engine at HEAD `39cffd06`; on the same day the working tree
gained an uncommitted change to `plane.units` (one question per distinct
neighbourhood — see `CODE_MAP.md`), and a `step6` fingerprint of that
change was in progress when this page was written. When you compare,
say which engine (commit, or the diff) produced each side.

---

## 1. Environment

**What this project was measured with** (the `.venv` on the lead's
machine, read back with `python -c "import …; print(__version__)"`):

| component | version |
|---|---|
| Python | 3.11.2 |
| numba | 0.67.0 (JIT for the packer kernels; `pyproject` requires `>= 0.67`) |
| dwave-networkx | 0.8.19 (prints a deprecation warning about Ocean 10 / `dwave-graphs`; harmless) |
| minorminer | 0.2.22 |
| networkx | 3.6.1 |
| numpy | 2.4.6 |
| pytest / pytest-timeout | 9.1.1 / 2.4.0 (`pytest.ini` passes `--timeout=120`, so the plugin is required) |
| ember-qc | 1.4.2, installed editable from `packages/ember-qc` |

**Install.** `packages/ember-qc/pyproject.toml` declares the runtime
dependencies (numpy, pandas, networkx, tqdm, minorminer, dwave-networkx,
platformdirs, pyyaml, numba) and the extras `dev` (pytest,
pytest-timeout), `analysis` (the companion `ember-qc-analysis` package;
not needed for anything on this page) and `charme` (torch; not needed).

```bash
git clone https://github.com/zachmacsmith/ember.git && cd ember
git checkout factored
python3.11 -m venv .venv
.venv/bin/pip install -e "packages/ember-qc[dev]"
.venv/bin/python -m pytest tests/algorithms -q        # 505 tests, ~2 min
```

`docs/getting-started.md` says `pip install ember-qc` (PyPI); for this
branch use the editable install above so that the `factored` package on
disk is what runs. Pin the versions in the table if you want to
reproduce the stored numbers bit for bit; `tail="none"` results that
stop by `"fixpoint"` or `"asks"` are deterministic given the same numpy
and numba (the kernels are exact integer/float arithmetic ported
op-for-op, and `TestPackLinesFeasibilityEquivalence` pins them to the
Python original).

**The `.venv` convention.** All commands in this repo are written as
`.venv/bin/python …` from the repository root — nothing is activated,
nothing depends on `PATH`. The tests do not need the package installed
(`pytest.ini` puts `packages/ember-qc/src` on `pythonpath`); the harness
scripts under `docs/paper2/data/` do (`from ember_qc.… import …`), hence
the editable install.

---

## 2. Graph loading

`ember_qc.load_graphs.load_graph(gid) -> nx.Graph` resolves an integer
graph id through three layers (from its docstring):

1. **local cache** `~/.local/share/ember-qc/graphs/{id}_{name}.json`,
   SHA-256-prefix-verified against the bundled `manifest.json` (a stale
   file is deleted and lookup continues);
2. **bundled files** shipped inside the package
   (`ember_qc/graphs/library/` — only 37 small graphs, ids 1–60 and
   100–199 of `test_graphs/REGISTRY.md`);
3. **remote download** from the HuggingFace dataset
   `zachmacsmith/ember-graphs`, verified and cached, so the second call
   hits layer 1.

`KeyError` for an id not in the manifest, `RuntimeError` for a corrupt
file or a failed download. Structural duplicates are redirected to their
canonical (lower) id. `test_graphs/REGISTRY.md` documents the selection
syntax (`"1-10, 51-60"`, presets `quick`/`diverse`) used by `ember run`;
the harnesses below call `load_graph` directly.

**None of the seven board graphs is bundled**: on a fresh laptop the
first run of any harness downloads them (seven small JSON files) into
the cache; do that once while online.

### The standard 10-cell board

Every harness loads the cells the same way
(`nx.convert_node_labels_to_integers(load_graph(gid))` for the library
graphs):

| cell | source graph | n | m | loader |
|---|---|---|---|---|
| `K100` | complete graph | 100 | 4950 | `nx.complete_graph(100)` |
| `K140` | complete graph | 140 | 9730 | `nx.complete_graph(140)` |
| `ER100_d10` | Erdős–Rényi, mean degree 10 | 100 | ≈500 | `nx.gnp_random_graph(100, 10/99, seed=12345)` |
| `turan_n162` | Turán graph, 2 parts (`turan_n162_r2`) | 162 | 6561 | gid **2647** |
| `spin_glass_n163` | `spin_glass_n163_d0.30_bimodal_s0` | 163 | 3915 | gid **37309** |
| `regular_n316` | 4-regular (`regular_n316_d4_s1`) | 316 | 632 | gid **13096** |
| `ws_n486` | Watts–Strogatz k=4, β=0.3 (`ws_n486_k4_b0.30_s0`) | 486 | 972 | gid **17188** |
| `grid_200` | `grid_10x20` | 200 | 370 | gid **1590** |
| `honeycomb_200` | `honeycomb_10x10_periodic` | 200 | 300 | gid **32393** |
| `king_graph_196` | `king_14x14` | 196 | 702 | gid **32622** |

Cell classes used when reporting deltas: **dense** (K100, K140,
spin_glass, turán), **ER** (ER100_d10), **sparse lattices** (grid,
honeycomb, king), **small-world & regular** (ws, regular).

**Targets.** The board target is `Z12 = dnx.zephyr_graph(12, 4)`
(course-resolved `TileGrid`: 25 × 25 lines, 8 wires per interior line,
stride 2). The tests and the small fingerprints use
`Z3 = dnx.zephyr_graph(3, 4)`.

---

## 3. The three live harnesses (`docs/paper2/data/`)

All three share the same shape: a `BOARD`/`CELLS` list, a `BUDGET` dict,
a `_run(job)` worker that calls `attract_embed` (workers `os.nice(10)`
themselves), a `ProcessPoolExecutor`, one result line printed per job as
it finishes, a results file written next to the script, and a final
**sentinel line** printed to stdout. Each script's module docstring is
its manual.

### 3.1 `plane_fingerprint.py` — the acceptance fingerprints

The acceptance test of any engine change (also quoted in `CLAUDE.md`).
`tail="none"`, work budgets:

| cell | target | seeds | `max_asks` | `timeout` (safety net) |
|---|---|---|---|---|
| K8 | Z3 | 0 | 2000 | 120 |
| K10 | Z3 | 0 | 2000 | 120 |
| path60 (`nx.path_graph(60)`) | Z12 | 0 | 3000 | 300 |
| K100 | Z12 | 0 | 10000 | 900 |
| turan_n162 | Z12 | 0–9 | 15000 | 900 |
| grid_200 | Z12 | 0 | 8000 | 900 |

```bash
nohup .venv/bin/python docs/paper2/data/plane_fingerprint.py mytag \
    > docs/paper2/data/plane_fingerprint_mytag.log 2>&1 &
# … later:
grep -c done-fingerprint docs/paper2/data/plane_fingerprint_mytag.log   # 1 when finished
```

`argv[1]` is a free **tag** (default: a timestamp; the lead's runs are
tagged `step0` … `step6`); the output is
`docs/paper2/data/plane_fingerprint_<tag>.json` (a list of per-job
dicts: `cell, seed, acl, max_chain, certified, mm_skipped, extensions,
asks, bookmark_asks, stopped_by, pen, stair, error, wall`). An optional
`engine=<name>` argument is forwarded to `attract_embed` as a kwarg; the
current engine ignores it (it existed to select variants of the old
engine), as it ignores the `init_mode="random"` the script always
passes. 16 workers. The script also prints `turán crystal hits: k/10`
(the count of `acl == 6.0 and max_chain == 6`). Sentinel:
`done-fingerprint`.

### 3.2 `rewrite_board.py` — the paired board

Arms (the `ARMS` tuple is `("new", "new+mm", "mm")`; `old` is extra):

| arm | what runs |
|---|---|
| `new` | the rewrite, `tail="none"`, `max_asks=BUDGET[cell]`, `timeout=1800` (safety net): **the engine's own answer at a work budget** |
| `new+mm` | the rewrite, `tail="mm"`, `timeout=60`: the shipped shape at a 60 s wall |
| `mm` | stock `minorminer.find_embedding(src, edges, random_seed=seed, timeout=60)` |
| `old` | the archived default engine (`attract_embed(src, tgt, timeout=60, seed=seed)` with *its* defaults, tail included), run from the archived source tree |

Seeds: `(0, 1, 2)` per cell; `DEEP_CELLS = (turan_n162, ws_n486,
regular_n316, ER100_d10)` get `range(10)`. 58 jobs per arm. 24 workers.

```bash
# the three live arms (default when no arm is named):
nohup .venv/bin/python docs/paper2/data/rewrite_board.py new new+mm mm \
    > docs/paper2/data/rewrite_board.log 2>&1 &
# or one arm at a time — this is how the stored files were made:
nohup .venv/bin/python docs/paper2/data/rewrite_board.py new new+mm > docs/paper2/data/rewrite_board_new2.log 2>&1 &
nohup .venv/bin/python docs/paper2/data/rewrite_board.py mm         > docs/paper2/data/rewrite_board_mm.log  2>&1 &

# the archived engine: the same script, the archived package first on PYTHONPATH
PYTHONPATH=/data/max/ember-archive/packages/ember-qc/src \
  nohup .venv/bin/python docs/paper2/data/rewrite_board.py old \
    > docs/paper2/data/rewrite_board_old.log 2>&1 &

# merge every rewrite_board_*.csv in the directory into one table:
.venv/bin/python docs/paper2/data/rewrite_board.py summary
```

Output: `docs/paper2/data/rewrite_board_<tag>.csv` where `<tag>` is the
arm names joined by `-` with `+` removed (`new`, `new+mm` →
`rewrite_board_new-newmm.csv`; `old` → `rewrite_board_old.csv`). Columns:
`cell, arm, seed, acl, max_chain, legal_acl, stopped_by, asks,
bookmark_asks, pen, certified, mm_skipped, error, wall`. The script
prints the summary at the end and the sentinel `done-board`.

`summary` globs **all** `rewrite_board_*.csv` in the directory and
averages per `(cell, arm)`; if you re-run an arm under a different tag
without moving the old file, both files' rows are averaged together.
Keep one CSV per arm, or run in a copy of the directory.

**The `old` arm** needs the archived engine, which is git commit
`ea5d1cf2` (2026-09-04) checked out as a worktree at
`/data/max/ember-archive` on the lead's machine (`git worktree list`).
On another machine:

```bash
git worktree add ../ember-archive ea5d1cf2
PYTHONPATH=../ember-archive/packages/ember-qc/src nohup .venv/bin/python docs/paper2/data/rewrite_board.py old > docs/paper2/data/rewrite_board_old.log 2>&1 &
```

The archived `attract_embed` ignores unknown kwargs too, so the same
script works; its own default init and tail apply.

### 3.3 `invariance_probe.py` — order and init invariance

Two groups per cell, `tail="none"`, `max_asks=BUDGET[cell]`,
`timeout=1800`:

- **`order`**: `seed=0`, `sched_seed=draw` — the same init, different
  question orders;
- **`init`**: `seed=draw`, `sched_seed=0` — different inits, the same
  bag order.

`draw` runs `1..K` (`draws=K`, default 5). 24 workers.

```bash
nohup .venv/bin/python docs/paper2/data/invariance_probe.py \
    > docs/paper2/data/invariance_probe.log 2>&1 &          # the 10-cell board, 100 jobs
nohup .venv/bin/python docs/paper2/data/invariance_probe.py smoke draws=3 \
    > docs/paper2/data/invariance_probe_smoke.log 2>&1 &    # grid_200, ws_n486, turan_n162 only
```

Output: `invariance_probe_board.csv` or `invariance_probe_smoke.csv`
(columns `cell, group, draw, seed, sched_seed, legal_acl,
legal_max_chain, asks, bookmark_asks, stopped_by, pen, stair, bars,
certified, mm_skipped, error, wall`), then a `MAP` block per cell (mean,
sd, range of `legal_acl` and mean `legal_max_chain` per group, the
`stopped_by` histogram) with the flag `SENSITIVE` when
`range > tol = max(0.3, 0.05 · mean)`, a `sensitive:` list, and the
sentinel `done-probe`.

### 3.4 The `nohup` pattern, and why

```bash
nohup .venv/bin/python <script> [args] > <log> 2>&1 &
```

Long jobs (anything beyond ~15 minutes) are started detached with
`nohup … &`, their stdout and stderr redirected to a log next to the
results, so that they survive the end of the shell or AI-assistant
session that launched them. Every harness prints one line per finished
job and a **sentinel** as its last line (`done-fingerprint`,
`done-board`, `done-probe`); `grep -c done-board <log>` or `tail -1`
tells you whether a run finished without having to watch it, and a log
without its sentinel is an interrupted run, not a result. The stored
logs in `docs/paper2/data/` end with those sentinels (the board's
merged summary logs end with `done-all`/`done-all2`, a shell wrapper's
own sentinel).

---

## 4. Conventions for a measurement

**Work budgets, per cell** (`BUDGET` in both `rewrite_board.py` and
`invariance_probe.py`; the fingerprint's are in section 3.1):

| cell | `max_asks` |
|---|---|
| K100 | 10 000 |
| K140 | 12 000 |
| ER100_d10 | 8 000 |
| turan_n162 | 15 000 |
| spin_glass_n163 | 12 000 |
| regular_n316 | 10 000 |
| ws_n486 | 15 000 |
| grid_200, honeycomb_200, king_graph_196 | 8 000 |

**Why asks, not seconds.** One ask is one `align_reinsert` evaluation
(the interleaver DP). Counting the budget in asks makes a result a
function of `(instance, seed, sched_seed, max_asks)` and of nothing
about the machine: the same run on a laptop or on a box at load 120
gives the same answer and the same `stopped_by`. The old engine's wall
budget was itself a parameter of its answer (turán needed a third pass
that a slow box never reached); that was one of the audited defects
(`notes.md` s3.127). `timeout` remains as a safety net and is set large
(1800 s on the board, 900 s in the fingerprint) so that it never fires;
if `stopped_by == "deadline"` appears in a result row, that row is not a
budgeted measurement.

**`tail="none"` vs `tail="mm"`.** `tail="none"` is the engine's own
answer: arrange → exact conversion → completion → (certificate or
minorminer legalization) → spur prune, and nothing after. `tail="mm"`
adds minorminer's warm-started grind and the ball pass, both bounded by
the remaining wall — it is the shipped default and the arm to compare
against stock minorminer at equal wall, but it re-introduces the clock.
The arm-name suffix **`-nt`** ("no tail") in the archived probes and
in `notes.md` means the same arm run with `tail="none"`; in the live
board that twin is simply called `new` (versus `new+mm`).

**`legal_acl`** = the mean chain length of the legal embedding *before
the tail* (after legalization and spur pruning). It is the number to
read for the engine itself; the `acl` column is the finished embedding
(identical to `legal_acl` when `tail="none"`).

**Paired by (instance, seed).** Every arm runs the same cells with the
same seed list, and the summary reports `d = arm − mm` averaged over
the seeds both arms have (`rewrite_board.py::summary`). A comparison
between two engine versions is likewise per `(cell, seed)`: same cells,
same seeds, same budgets, and only then averaged.

**Tolerance.** A difference in mean pre-tail ACL smaller than
`tol = max(0.3, 0.05 · control)` is within the engine's own spread and
is not a result — this is the invariance probe's flag rule
(`invariance_probe.py` line 123) and the rule to apply to "better /
worse" per cell.

---

## 5. Expected runtimes

Measured per job, `new` arm (`tail="none"`, the budgets above), on the
lead's box: 128 cores at a load average of ~115–125 while the boards
ran (`nproc`, `uptime`), 24 concurrent workers, from
`rewrite_board_new2.log`, `invariance_probe.log` and
`plane_fingerprint_step5.log` (all 2026-09-07 code):

| cell | wall per run | stops by |
|---|---|---|
| K8 / K10 on Z3 (2000 asks) | 2–3 s | fixpoint (71 / 108 asks) |
| path60 (3000 asks) | ~6 s | fixpoint (2100 asks) |
| K100 (10 000 asks) | 12–24 s | fixpoint (~1.4k–2.2k asks) |
| K140 (12 000) | 30–40 s | fixpoint |
| ER100_d10 (8 000) | 12–43 s | fixpoint |
| spin_glass_n163 (12 000) | 28–64 s | fixpoint |
| turan_n162 (15 000) | 200–290 s (**≈ 4 min**) | asks |
| regular_n316 (10 000) | 135–150 s | asks |
| ws_n486 (15 000) | 320–370 s (**≈ 6 min**; up to ~8 under heavier load) | asks |
| grid_200 (8 000) | 57–80 s | asks |
| honeycomb_200 (8 000) | 53–67 s | asks (occasionally fixpoint) |
| king_graph_196 (8 000) | 60–74 s | asks |

The wall-bounded arms are fixed by construction: `mm` and `new+mm` take
~60 s per job (plus a few seconds of setup), except that stock
minorminer returns early on the sparse cells (0.5–10 s).

Totals (serial CPU time): `new` arm ≈ 2.3 h for the 58 jobs (ws and
turán are two thirds of it); `mm` and `new+mm` ≈ 1 h each; the
fingerprint ≈ 40 min (10 turán jobs × ~4 min); the invariance board
(100 jobs) ≈ 2.8 h; `smoke` at `draws=5` ≈ 1.7 h. Divide by the number
of cores you can give it.

**Note for a laptop.** The scripts hard-code `max_workers = min(16 or 24,
jobs)`. On a 4–8-core laptop that oversubscribes the CPU: the answers do
not change (asks are asks), but per-job wall inflates by the
oversubscription factor and a turán or ws job can then run into the
`timeout` safety net (900 s in the fingerprint) and be cut off as
`"deadline"`. Either edit `max_workers` in a copy of the script to your
core count, or raise `timeout`/`TIMEOUT` in the copy. The numba kernels
compile once per environment (a couple of seconds, cached in
`__pycache__`).

**Laptop-scale variants** (all in `docs/paper2/data/` or a copy):

- **Smoke**: `invariance_probe.py smoke draws=2` (grid, ws, turán; 12
  jobs; ≈ 40 CPU-min) and, for the board, edit `BOARD` in a copy down to
  the same three cells with `SEEDS = (0, 1, 2)`.
- **The fingerprints** (`plane_fingerprint.py`) are already the small
  set; drop turán to seeds `(0, 1, 2)` in a copy for a 10-minute run.
- **Smaller Z**: `dnx.zephyr_graph(6, 4)` (1248 qubits, 13 × 13 lines,
  8 wires per interior line) holds the ≤ 200-vertex sparse cells (grid,
  honeycomb, king) with room to spare; it does not hold the dense cells
  (the Zephyr clique template grows with `m`). Numbers on Z6 are not
  comparable to the Z12 baseline, but engine-vs-engine deltas on the
  same target are.
- **Fewer seeds**: 3 instead of 10 on the deep cells; report the range,
  not only the mean.
- **The unit tests** (`tests/algorithms`, 2–4 min) plus the K10/Z3
  fingerprint (`legal_acl 1.8, max_chain 2, certified, fixpoint`) are
  the five-minute check that the environment reproduces the lead's.

---

## 6. Where results live, and how to compare a new run

**Records**: `docs/paper2/data/` holds every result file of the rewrite
era next to the scripts that made it:

- `plane_fingerprint_step0-old.json` (the old engine from a random init),
  `…step2-plane2.json`, `…step4-plane2.json` (checkpoints during the
  build), **`plane_fingerprint_step5-default.json`** (the current
  engine) and their `.log`s;
- **`rewrite_board_new-newmm.csv`**, **`rewrite_board_mm.csv`**,
  **`rewrite_board_old.csv`** and the logs `rewrite_board_new2.log`,
  `rewrite_board_old.log`, `rewrite_board_summary2.log` (the merged
  table). `rewrite_board_new.log` / `rewrite_board_summary.log`
  (2026-09-04) are from an earlier state of the engine and are superseded;
- **`invariance_probe_board.csv`** and `invariance_probe.log`;
- the many other `*_probe.csv/.log` files are records of the old
  engine's probes (their scripts are archived; see below).

**The frozen baseline**: `docs/handoff/baseline/` holds copies of the
files in bold above plus `invariance_summary.log`,
`plane_fingerprint_step0-old.json`, and `RESULTS.md` (the tables, the
commands, and the rule for judging a change); `docs/handoff/
compare_baseline.py` re-runs the fingerprints (and, with `board`, the
new engine's board arm) and prints better / same / worse per cell and
per cell class. The stored numbers
(from `rewrite_board_summary2.log`, mean ACL over successes / mean max
chain; `d` = arm − mm on shared seeds):

| cell | mm (60 s) | old (+tail, 60 s) | new (`tail="none"`, work budget) | new+mm (60 s) |
|---|---|---|---|---|
| K100 | 10.467 / 15.0 | 7.26 / 8.0 | 7.26 / 8.0 | 7.26 / 8.0 |
| K140 | 20.286 / 40.5 (2/3 succeed) | 9.757 / 10.0 | 9.766 / 10.667 | 9.766 / 10.667 |
| ER100_d10 | 4.818 / 8.8 | 4.652 / 7.8 | 4.599 / 8.1 | 4.452 / 7.5 |
| turan_n162 | 11.304 / 18.9 | 9.457 / 12.5 | 6.0 / 6.0 | 6.0 / 6.0 |
| spin_glass_n163 | 20.564 / 35.333 | 11.041 / 12.667 | 10.849 / 12.333 | 10.842 / 12.0 |
| regular_n316 | 3.59 / 9.6 | 2.783 / 6.5 | 4.747 / 13.6 | 3.612 / 9.3 |
| ws_n486 | 3.144 / 11.7 | 2.557 / 8.0 | 4.401 / 27.4 | 3.336 / 12.1 |
| grid_200 | 1.082 / 2.0 | 1.265 / 3.0 | 1.59 / 5.667 | 1.29 / 2.667 |
| honeycomb_200 | 1.16 / 2.333 | 1.332 / 2.667 | 1.89 / 6.0 | 1.235 / 2.667 |
| king_graph_196 | 1.76 / 3.667 | 1.832 / 4.0 | 2.561 / 7.667 | 2.111 / 4.667 |

Fingerprints (`plane_fingerprint_step5-default.json`): K8 1.5, K10 1.8,
path60 1.067, K100 7.26 (fixpoint at 1555 asks), turán 6.000 / max 6 on
10/10 seeds (all `"asks"`), grid_200 1.605 — all certified,
`mm_skipped`, `extensions == 0`. Invariance (`invariance_summary.log`):
order- and init-free on K100, K140, ER, turán, spin_glass, grid,
honeycomb; `SENSITIVE` on regular (order range 0.54), ws (order 0.39,
init 1.01) and king (init 0.32).

**Comparing a new run** — the procedure the paired rule implies:

1. Run the same harness with the same cells, the same seed lists and
   the same `BUDGET` (the defaults), writing into a fresh directory or
   under a new tag; never overwrite a baseline CSV.
2. For the engine itself compare the **`new` arm** (`tail="none"`) on
   `legal_acl` and `max_chain`, joined to the baseline by
   `(cell, seed)`; take the per-cell mean of the differences and the
   per-cell range. Check `stopped_by` first: a row that stopped by
   `"deadline"` is not comparable.
3. Report the deltas **per cell class** — dense (K100, K140,
   spin_glass, turán), ER, sparse lattices (grid, honeycomb, king),
   small-world & regular (ws, regular) — calling a cell better or worse
   only beyond `max(0.3, 0.05 · baseline)`, and always alongside
   `bookmark_asks`/`asks` (work-to-answer) and the fixpoint/asks split.
4. Only then the `new+mm` arm against `mm` at equal wall, remembering
   that both depend on the machine.
5. Any change to the engine must also keep the fingerprints:
   K8/K10 certified at the template, K100 = 7.26 at a fixpoint, turán
   6.000 from every random init, path60 ≈ 1.02–1.07, grid_200 pre-tail
   ≤ 1.76 (`CLAUDE.md`).

`rewrite_board.py summary` gives the per-arm means; the join by seed is
a few lines of pandas over the two CSVs (`cell, arm, seed` keys).

---

## 7. The archived probes

`docs/paper2/archive/probes/` holds the 110 probe scripts of the old
engine (plus a `README.md` and `rewrite_board_strip_new-newmm-mm.csv`,
the pre-fix sparse rows mentioned in `notes.md` s3.127). They import
modules that no longer exist in this tree (`orders`, `seat`, `loop`,
`coarsen`, `costs`, `AttractConfig`) and **do not run** against it; they
are records of what was tried, readable with their result files in
`docs/paper2/data/`, and runnable only from the `ea5d1cf2` worktree. The
verdicts they produced are summarised in `docs/paper2/attraction.md`
and the chronicle `docs/paper2/notes.md`.
