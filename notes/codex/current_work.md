# Current research checkpoint

Updated 2026-09-08 UTC. Branch `codex`; full research goal remains active and
unmet. Preserve the original scope: one general non-portfolio algorithm, no MM
or busclique inside it, ideal Z12, quality and success retained, roughly MM's
runtime range. The pending user question about optimal ACL-1 ties has no answer;
do not interpret silence as a change in the success criterion.

## Running experiment

`026-corpus-spectral-initialization` is running on hyde03, after completed 025 was
retrieved. It compares random versus one bounded spectral initialization in the
same contact-rearrangement pipeline, 34 inputs and 68 trials, one seed, 60 seconds.
Frozen commit `f93f889f428baa26d1722382c77de385d4b4822f`; source hash
`91824466fdd3880940df0cc6d3569a461a617c3d1ae883e50425ee368952a765`.
Initial live check found controller 122275 and worker 122287, held lock and live
tmux supervisor. The benchmark auditor monitors this exact run. Do not restart
it after a transient connection failure. Retrieve and analyze after quiescence.

## Most recent complete evidence

019: both candidates have 34 timely valid results; MM has 31 plus three timeouts.
On the common 31 inputs, candidates win eight and lose 23 on ACL. The lower
aggregate mean hides broad sparse quality deficits and runtime problems.

025: all 68 results timely and valid. Contact rearrangements save 65 qubits versus
the fixed strict candidate, with 17 improvements, 10 regressions, seven ties.
The strict arm reproduces all 34 strict-019 embeddings exactly. Contact policy
still wins eight and loses 23 against historical MM quality. Ordinary and
independent artifact checks pass; no new MM timing comparison is available.

026 local smoke: all three predeclared spectral calls valid, with MM absent and
no prohibited imports. This is correctness evidence only. The integration suite
passed 160 focused tests, then the full 14-test integration file passed after
adding the approximate-success boundary test.

027: Sudoku q2/q3 records are frozen separately, with new IDs 1000002/1000003,
16/81 vertices and 56/810 edges. Root reran all 34 tests and verified the bundle.
Original entries remain unchanged; q4/q5 are reserved and ungenerated. No solver
has used these new inputs, so embeddability remains unproved.

## Parallel work and ownership

- `benchmark_audit`: 025 review and 026 launch notes are complete and reviewed;
  now monitor and independently audit 026. Root reran ordinary 025 analysis.
- `algorithm_audit`: 028 performance change is complete and independently reviewed;
  55 proposal tests plus 38 root integration tests pass. All 12 outputs and
  trajectories match exactly, with small observed speed gains and timing caveats.
  Now specify and diagnose physical-qubit checkpoint selection in one unchanged
  placement trajectory. Own `physical_checkpoint_spec.md` and additive diagnostic
  artifacts under `results/codex/030-physical-checkpoint-diagnostic`; no production
  plane/native callback, new pilot configuration or repeated contact repair yet.
- `literature`: add explicit `--input-supplement` loading to pilot/cluster/analyzer
  and `test_codex_pilot_supplement.py`, preserving every old path. Freeze the full
  supplement and loader source; carry provenance outside solver metadata.
  `029_sudoku_comparison_protocol.md` predeclares both sources, MM/contacts/spectral
  contacts, seed 0, 60 seconds, six trials. Do not launch until reviewed and tested.

Review agent-owned edits before committing. The current cluster run uses its
frozen source and is unaffected by these working-tree edits. Root owns README,
session log and this checkpoint; avoid touching files while their agent edits.
Preserve unrelated `.claude/` and graph-library `.verified.json` files.

## Next actions

1. Review and commit stable 025/026 notes, then preserve 026 all-input results and
   failures before deciding whether spectral initialization merits further study.
2. Preserve the completed 028 evidence. Review 030's physical-score mismatch and
   cost evidence before choosing a bounded integration experiment. Neither the
   small speed gain nor better checkpoint scores prove an all-class improvement.
3. Review the supplement adapter's identity, source isolation, transport and
   corruption checks. Freeze and run the declared six-trial comparison after
   appropriate host sequencing, without altering earlier corpus experiments.
4. Continue general revisions from observed failure mechanisms. No source-family
   dispatcher, per-input best-of result, hidden fallback, broad superiority claim,
   or paper-success claim is justified by present evidence.

The user was told the backend goal reports `active`; `/goal resume` is currently
unnecessary. No UI internals or goal scheduler state were modified.
