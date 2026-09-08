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

The controller is newly launched; no terminal outcome or retrieval is reported yet.
