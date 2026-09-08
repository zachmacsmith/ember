# 046 bounded vacancy pipeline launch

2026-09-08, hyde03, user dabh. One detached run of the predeclared
[hypothesis](046_vacancy_pipeline_hypothesis.md), with the reviewed stage in
[the implementation note](../vacancy_pipeline_implementation.md).

The unchanged 34 readiness structures (35 memberships), ideal Z12, seed zero,
60 seconds, control versus bounded vacancy: 68 tasks. Source, target and
corpus-selection bytes match 042 exactly. This compares two fixed configurations
separately; neither calls MM or selects among constructor outputs. No new
final-test graphs are involved.

Frozen snapshot `5dadefe9e1c9099282701cc45c060a810e355a92d4128dc537c443f7e50b9dd7`;
manifest `79bc699bd2da6de320d9b2499bd733420199585086c19afa7afb0ba8ea9e5936`;
transport `ec5c8b3826598391c3439274999b1b40a1b7018af00c53f9b7837d59a3b1c6b5`.
Preparation and lifecycle evidence are in `results/codex/046-preparation` and
`results/codex/046-launch`.

The standard audited cluster CLI staged once and started once. Supervision is
tmux plus the existing outer timeout of 6420 seconds. Session
`ember-codex-01e523d30a36afbe9766`; controller 179914 began at Unix
1788889764.1697977 (17:49:24 UTC). Initial observation has three finalized
SUCCESS records, a live controller/worker, busy lock and active session. This is
lifecycle evidence, not a quality result. The host's initial load is near zero.

The 20 focused checks passed before freezing. No shared validity predicate or
process supervision changed. Runtime includes the bounded stage and unchanged
final original-graph validator. All rejected/failed stage work remains recorded.
If observation is lost, inspect this run; never restart because SSH disconnected.

```sh
.venv/bin/python scripts/codex/cluster.py --host hyde03 status 046-vacancy-pipeline
.venv/bin/python scripts/codex/cluster.py --host hyde03 fetch 046-vacancy-pipeline results/codex/retrieved/hyde03/046-vacancy-pipeline
```

Fetch only after the audited remote inventory establishes quiescence. The
minimal result screen will validate complete outputs against original graphs,
retain all 68 statuses/times, and distinguish certified from committed moves.
