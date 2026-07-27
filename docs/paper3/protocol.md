# paper3 measurement constitution

Frozen at M0 (2026-07-26). Changing anything in this file requires a dated, justified
entry in `notes.md` — silent edits are a protocol breach.

## Why this file exists

Paper 1 (`new-algorithm` branch) died of unfair measurement: best-of-4 restarts compared
against single-shot minorminer (while the repo's own ceiling probe showed best-of-12
stock-MM seeds alone buys −4.8%..−10% ACL), a −1.8% polish applied to one arm only,
tuning on reported instances, and a variance claim that was the mechanical variance of a
min-of-4. Every rule below closes one of those holes. Paper 2 (`factored`, docs/paper2)
measured honestly; we inherit its discipline (paired one-flip probes, pre-registered
bars, source-verified claims about minorminer).

## The six rules

1. **Pairing.** Headline claims use the script route (`benchmark_one(..., seed=s)` with
   the SAME `s` for every arm → literal (instance, seed) pairs). The CLI route
   (`ember run`) salts the per-trial seed with the algorithm name
   (`benchmark.py::_derive_seed`) — CLI-derived tables are allowed for breadth sweeps and
   must carry the label "(instance, trial) pairing [CLI]". The two routes are never
   pooled in one statistic.

2. **No best-of-K vs single-shot, ever.** A multi-run/portfolio/selection scheme is
   measured at equal wall-clock on equal cores against minorminer given the identical
   multi-run privilege (best-of-K-parallel stock MM). Unconditional internal best-of-N is
   allowed only when the entire arm still fits inside ONE stock-MM run's budget (e.g.
   template assignment seeds, ~ms). `e0_ceiling` measures the best-of-K freebie once, as
   a standing deflator/control — it is never a proposed algorithm.

3. **Polish parity.** Every experiment logs both `acl` (raw) and `acl_spur`
   (spur-pruned, deadline-bounded) for EVERY arm including minorminer. A table uses
   exactly one of the two columns for all arms and names which.

4. **Dev/eval discipline.**
   - DEV instance seeds: **101–115** (E0 uses 101–103; dev-suite bars 101–105).
   - EVAL instance seeds: **901–915** (K=15). Never generated, run, or inspected before
     the M4 tuning freeze (freeze = a notes.md entry recording the tuned config shas).
   - Algorithm seeds: dev **0–4**; eval **10–14**. CLI master seed: dev 42, eval 4242.
   - Success rates are reported separately and unpaired. ΔACL is computed only on
     both-succeed pairs and labeled as such. No survivor filtering, ever.

5. **Budgets.** 60.0 s per attempt everywhere unless the experiment is explicitly a time
   sweep. Wall-clock comparisons are valid only within one batch (same host, same worker
   count, arms interleaved in one queue). Cross-batch or cross-host time comparisons are
   banned. Headline speed / time-matched-Pareto claims are re-measured at `--workers 1`
   on an idle machine (`who` / loadavg checked and recorded).

6. **Pre-registration.** Every experiment gets a `notes.md` §4.x entry committed BEFORE
   launch, using this template:

   ```
   ### 4.x <title> (<date>)
   PRE-REGISTERED <date>
   Question: ...
   Script/YAML: docs/paper3/data/<file> @ <git sha>
   Cells / arms / seeds / budget: ...
   Bars: <numeric criteria>
   Decision tree: bar met -> ...; not met -> ...
   --- results appended below; nothing above this line is edited after launch ---
   ```

## Registered-arm naming

CLI cannot pass kwargs → one registered name per hyperparameter point:
`p3-<family>[-<variant>]` (e.g. `p3-template`, `p3-clmm`, `p3-clmm-core`). Any internal
fallback-to-MM is OFF by default; a fallback variant gets an explicit `-fb` suffix.
Every arm passes `tests/algorithms/test_algorithm_contracts.py` before entering a batch.
mmfork arms in script-route experiments always pass `fallback=False`.

## Route choice

- Script route (`docs/paper3/data/*.py`, exemplar `docs/paper2/data/history_2x2.py`):
  paired headline claims, kwargs, exact (n,p) instances, watchdogged candidate arms.
- CLI route (`docs/paper3/experiments/*.yaml`): manifest-breadth sweeps (M5), multi-arm
  smoke, anything where per-arm seed identity is not load-bearing.
- Candidate (non-MM-family) arms in script runners are wrapped in a per-run subprocess
  with a hard kill at timeout+30 s (the harness has NO watchdog; a hang stalls a
  64-worker batch). MM-family arms are exempt (known cooperative).

## hyde06 (experiments host)

- EPYC 9575F: **64 physical cores / 128 SMT threads. Never exceed 64 workers.**
  Throughput-only sweeps ≤64; any run whose wall_time feeds a table ≤48 workers with
  `who`/loadavg logged; calibrate once (largest W with <15% MM wall-time inflation vs a
  16-worker slice). BLAS/OMP threads pinned to 1 in every launch.
- Everything under **/data/dabh/** ($HOME is ~96% full): repo at `/data/dabh/ember`;
  `env.sh` exports XDG_DATA_HOME/XDG_CACHE_HOME/UV_CACHE_DIR/UV_PYTHON_INSTALL_DIR
  under `/data/dabh/xdg/`.
- Deploy by rsync from the mac (no GitHub key on hyde06). Rebuild the fork per machine
  (`bash scripts/build_mm_fork.sh` must print parity OK). Version pins: python 3.10,
  networkx==3.4.2, numpy==2.2.6, scipy==1.15.3, minorminer==0.2.22,
  dwave-networkx==0.8.19. Cross-machine instance-hash check before first experiment.
- One batch at a time; `QUEUE.md` is the ledger and the lock. `nohup nice -n 5`,
  BatchMode-ssh polling, rsync results back, analysis stays local.

## Frozen dev suite (E0 §4.1 output 5, fixed rule; frozen 2026-07-27)

14 cells (ER instances from dev seeds 101–105 unless K_n):
- P16: (100, 0.2), (100, 0.3), (140, 0.12)†, (140, 0.2), (140, 1.0)=K140,
  (180, 1.0)=K180 [past-cliff], (160, 0.05) [sparse control]
- Z12: (100, 0.2), (100, 0.3), (140, 0.12)†, (140, 0.2), (140, 1.0)=K140,
  (179, 1.0)=K179 [past-cliff], (160, 0.05) [sparse control]
† baselined by the §4.1b extension run (done 2026-07-27: template loses at 0.12 on
both topologies → the straddle pair (0.12 below, 0.2 above) is confirmed).
Bars on this suite use the acl_spur column; per-cell baselines: E0 CSV + e0_ceiling.

## File layout

```
docs/paper3/
  protocol.md          # this file
  notes.md             # chronological lab record; one §4.x per experiment
  QUEUE.md             # hyde06 run ledger/lock
  survey.md            # literature synthesis
  proposals/<name>.md  # one spec per candidate algorithm
  data/*.py + *.csv    # script-route experiments + results
  experiments/*.yaml   # CLI-route experiments
```
