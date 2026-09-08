# Experiment 011: contact refinement after geometric order search

Date: 2026-09-07. Development data only. Source is frozen before launch in
`results/codex/011-search-contact-ablation`; its manifest records the exact
source revision, file hashes, input hashes, settings and seeds.

## Rationale and critique before running

Experiment 009 found that the native search configuration substantially improves
on packed construction for sparse inputs. Packed construction is therefore not
the lead general configuration. Preserve its dense results and negative sparse
results; do not introduce family-based switching. Native search remains the one
constructor for every candidate in this ablation.

The implemented contact primitive is unchanged. Expose its existing group-size
and expansion bounds through the native entry point so single-chain and joint
moves can be compared. The five fixed configurations are MM, native search
without contact refinement, search plus singleton reconstruction, search plus
width-one joint reconstruction, and search plus width-four joint reconstruction.
They are independent experimental rows, with no per-instance best-result choice.

Self-critique of these configurations: singleton reconstruction may account for
most easy reductions; wider beams can spend budget on alternatives that never
complete. Group selection may revisit overlapping regions and fail to cover the
whole source. A fixed number of attempts is not equal work, so report actual BFS
expansions, accepted moves, CPU and wall time. A wider beam can produce a worse
final trajectory under fixed work bounds. Width-one already examines both pair
orders; a growing member is not evidence specific to width four. Strict qubit
descent can still stop above a useful local plateau. None of these mechanisms
alone establishes novelty (see `../contact_prior_art.md`).

Prediction: reconstruction will shorten some valid search embeddings, especially
where the geometric representation retains unnecessary chain segments. Dense
embeddings may have little room left. The immediate falsifier is no material
quality gain beyond singleton/width-one controls at a plausible runtime cost.
Do not fit graph-specific group counts or roots in response to individual rows.

## Frozen protocol

Reuse all nine development inputs from 009, two solver seeds (0,1). Sixty-second
solver allowance for every method, correcting 009's short K100 MM time allowance
without relabeling its recorded timeout as a success. Native search permits 1000
order-search proposals. Refinement uses four passes, a total 512 group cap,
500000 popped-vertex cap,
and the existing per-group/region/root bounds. Singleton groups are `[1]`;
both joint configurations allow `[1,2,3,4]`, with width 1 or 4 respectively.

The global limits are identical across input classes. All methods use sequential
randomized method order, fresh processes, empty per-task JIT caches and one thread.
Candidate environment contains no MM/busclique. Validation and deadline accounting
are identical to corrected experiment 009. A developer-machine run was initially
contemplated; the launch uses shared hyde03 as recorded below, with separate
solver and whole-process values. Two seeds provide only a very
weak variance estimate, not a class-level precision claim or confirmation.

## Results

Pending at launch. Compare quality on paired timely valid trials and report
coverage/status separately. Preserve optimal ACL 1 ties as ties. More scales,
seeds and actual Ember corpus coverage are required before deciding on a general
improvement, and fresh confirmation data are still untouched.

## Actual cluster launch

Frozen at 2026-09-08 01:37:22 UTC (September 7 in America/Chicago), parent source
revision `904be3ecbf9baa5039b431585301fb906feda02e`. Snapshot hash:
`73cca55965158b69bdbf94340cd36d701acd8fa426be191f457c4945284baeae`.
Target hash: `38cde794d3c1461054a45b5a660d157737b019c19cb9a7b38e2027730e3d5938`.
Transport input digest:
`c0c3b7ad995d94ff406b482d8b5109d5c4e9badbd63fb0c406225fc0ae13f2f0`.

The 90 tasks were staged without changing inputs and started on hyde03 in
`/home/dabh/ember-codex/runs/011-search-contact-ablation`. Native and MM Python
paths are the separate pinned 3.10.12 environments under
`/home/dabh/ember-codex/envs/4e1fb892db12754e/`. Preparation, hardware/load data,
and the successful detached SSH probe are in experiment 010.

The initial start response verified a live tmux supervisor and held controller
lock. The project tmux session is `ember-codex-000c7479c47969c292dc`, on the
`ember-codex` socket. The outer supervisor permits 8400 seconds for the whole
queue; each solver still has its own 60-second credited allowance. This is one
sequential worker queue; CPU timings must be compared within this host and
must not be pooled with 009's laptop measurements.

A separate fresh-SSH audit observed progress from 9 to 10 finalized successes,
with controller PID 113328 and an active child. All inspected records matched
their tasks, had valid embeddings and zero deadline overrun. All eight candidate
records used the isolated native interpreter and frozen candidate source, with
no installed MM, no prohibited import attempts, and no loaded embedding library.
Both K40 seeds completed for all five methods; the remaining inputs were still
running. These checks establish execution/provenance, not an overall outcome.

Resume/status and eventual verified retrieval commands:

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde03 status 011-search-contact-ablation
.venv/bin/python scripts/codex/cluster.py --host hyde03 start 011-search-contact-ablation
.venv/bin/python scripts/codex/cluster.py --host hyde03 fetch 011-search-contact-ablation results/codex/retrieved/hyde03/011-search-contact-ablation
```

`start` is idempotent while live or finished. Use `fetch` only when the run is
quiescent. A wifi change does not require restarting the job. Preserve all
failures and interrupted attempts; do not rerun them as invisible new samples.
