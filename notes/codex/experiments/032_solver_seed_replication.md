# Experiment 032: repeated solver seeds for the fixed spectral candidate

This development experiment compares the single spectral/contact candidate with
MM on all 34 original readiness structures from 017. It fixes solver seeds
`0, 1, 2, 3`, ideal Z12 and a 60-second solver deadline: 272 calls. Seed zero
provides a quality replay check after the semantics-preserving 028 optimization;
the three additional seeds expose initialization/search variability. There is
no selection of the best seed, embedding, initializer or algorithm within a
candidate call. Every trial and failure stays in the analysis.

The candidate is `native-search-joint1-contacts-spectral` with the same explicit
configuration as 026: spectral initialization, 1000 placement evaluations,
four contact passes, 512 total groups, group sizes 1–4, width one, 16 extra
boundary sites, round-robin coverage and the qubit/contact-redundancy objective.
Default shared contact work is 500000, with 50000 per group and a 512-qubit
region cap. The source includes the 028 removal of unused neighbor preparation.
It does not include the proposed direct singleton relocation or physical
checkpoint selection. MM is an isolated comparator with one call per task.

The run uses the existing isolated native and MM environments on hyde03 and the
existing disconnect-resistant tmux supervisor. Calls are sequential on this
shared host, in the runner's frozen order. Each has a fresh process and JIT
cache. Full solver wall includes first-call compilation; process wall is reported
separately. Stage the immutable source, target, inputs and trial plan before
launch. Start only after the completed 029 controller is quiescent and its archive
has been retrieved and checked. Later source edits cannot affect this snapshot.

Report per-source attempted/timely-valid counts, ACL means and sample variance
across timely successful solver seeds, all paired seed differences, and solver
and process times. Also report the count and values of failed/late/invalid trials.
An ACL mean conditioned on success is not an unconditional success-adjusted
measure. If either method fails, show the complete-case comparison separately
from each method's success-only summary. Never silently substitute a late valid
embedding. Compare seed-zero physical chain sets with 026 as a separate quality
replay check; no old timing observation enters the new paired timing analysis.

Count the shared king/frustrated-square input once in aggregates and retain its
two family memberships in the ledger. These inherited inputs remain development
data. Repeating solver seeds does not supply new source structures or independent
family samples. Sudoku stays in its separately identified supplementary study.
Four solver seeds give only a preliminary variance estimate and cannot establish
family-wide mean superiority, statistical equivalence or a stable runtime ratio.
This experiment does not consume a protected final set or alter the success
criterion for optimal ACL-one ties, which remains awaiting user clarification.

The purpose is to test repeatability and obtain contemporaneous MM timing while
the next general refinement is developed independently. No result from 032 will
trigger per-family settings or a seed-selection policy.

```sh
.venv/bin/python scripts/codex/pilot.py init results/codex/032-solver-seed-replication \
  --corpus-selection results/codex/017-corpus-readiness/selection.json \
  --methods mm,native-search-joint1-contacts-spectral --seeds 4 --timeout 60 \
  --candidate-python /home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python \
  --mm-python /home/dabh/ember-codex/envs/4e1fb892db12754e/mm/bin/python
.venv/bin/python scripts/codex/cluster.py --host hyde03 stage results/codex/032-solver-seed-replication
```

This note freezes the protocol before any 032 solver outcome. Record actual
source/transport identities and verified launch in an additive section.
