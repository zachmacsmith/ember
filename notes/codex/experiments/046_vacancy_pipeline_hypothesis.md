# 046: bounded cumulative relocation in the inherited pipeline

Specified before implementation, 2026-09-08.

**Hypothesis.** The additional reach in 045 can produce useful cumulative ACL
reductions when applied to the current embedding after the inherited
constructor, contact refinement and final safe deletion. Vacancy found a first
contraction on 25/34 fixed entries, including eight missed by ordinary
reconstruction under that diagnostic's settings. All eight additional traces
(13 moves total) have now been independently replayed against original edges.
This motivates a pipeline test; it does not predict its final quality.

```text
run the unchanged inherited construction, contact refinement and safe deletion
measure elapsed pipeline time t before the new stage
set the relocation deadline to min(original deadline, now + min(1 second, 0.2*t))
share one 50,000-proposal allowance across at most 20 successful contractions
repeat:
    query the reviewed vacancy repair on the current valid embedding
    if a timely certified Q-minus-one proposal returns, adopt it privately
    otherwise stop and retain the last valid current embedding
perform the unchanged full original-graph final validation
apply the original whole-pipeline deadline and failure rules
```

Every unsuccessful query, repeated setup, certificate and materialization cost
is inside the stage allowance. The stage does not renew the pipeline deadline.
It runs only after the already supported safe-deletion configuration; the
default remains disabled. The input to each call is the preceding accepted
embedding, not a stored competitor or alternative algorithm output. Stage
interruptions preserve the last complete current embedding. Late complete
pipeline results remain failures even if their embedding is valid.

**Self-critique.** A first contraction may lead to a poor local minimum, and
restarting the deletion-seed order after each success can neglect other useful
moves. A one-second/20%-of-elapsed allowance may be too short on sparse graphs;
larger allowances might violate the runtime target. Repeated entry validation
can dominate useful search. The 20-contraction bound is an initial workload
limit, not a scaling or quality guarantee. These are heavily reused development
graphs, and a local mechanism's novelty is still unestablished.

**Cheap falsifier.** Use the audited full-pipeline pilot and original-label
validator on all 34 readiness structures, seed zero, Z12, 60 seconds per method,
fresh same-host hyde03 pairs. Control is the existing spectral/contact/final-
deletion configuration; treatment adds only bounded vacancy refinement. Retain
all failures, time, per-input Q/ACL and each accepted move trace. If no useful
aggregate reduction survives the runtime allowance, reject this integration
policy. Any success or quality regression requires explanation before promotion.
No MM superiority, seed-variance or fresh-instance claim follows from this
control comparison; a promising result requires a later fresh MM comparison.
