# 056 launch record

Run `056-current-policy-seed-replication` on hyde06, frozen before execution. Root owns transport;
all invocations and failures are recorded under `results/codex/056-launch`.
There was one successful stage and one actual detached start, with no restart.

- Source snapshot: `0d5b77e35a196734c7b5a3526c2247ae7a6da5e230d2fb6b81b01f2b961ca9a4`.
- Task manifest: `f70792c06c6a9bfbb83e0edf7d0839f45c0cfcf44c960cca87783c1c2bc8ed47`.
- Protocol: `e619f6bcef0124f2887e28e8d97c2e3c947279b2d0b7daae035d5ada2f59ffe8`.
- Transport input digest: `3e6e524ef07f8f646452fe52b21f67241df038c0aa6c6cb55edefedf8aecb0e7`.
- Tasks / structures: 272 / 34.
- Supervision start Unix: 1788906940.7068093.
- Outer bound: 24780 seconds.
- Detached session: `ember-codex-160f709fe24a52ef3cdf`.

The frozen input/target/selection bytes match042. Different host times are not
pooled. Observe this existing handle after a network interruption; loss of
observation never authorizes a replacement run.

Terminal: controller55147 finished at Unix1788910452.9278667,272/272
finalized, lock free, tmux absent, supervisor exit0. Retrieval verifies1487
files, digest`7b68106f54322afffc09566d7c0a22863e330709c5cbfeebc7cf12c0147a7d56`.
One saved analysis passes all current/historical gates; root reads the report
and verifies18 final bindings. A053 succeeds134/136 versusMM120/136, with
40 lower-Q,65 higher-Q and13 ties on118 common successes. Both candidate
failures and all16 MM timeouts remain in the accounting. All34 seed-zero
candidate quality/status outcomes replay old053; historical times are not
pooled. See [results](../../../results/codex/056-results-review/RESULTS.md)
and [current class gaps](../mm_gap_current_replications.md).
