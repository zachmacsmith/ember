# Saved-state orientation gate implementation

The only executable changes are reviewer-owned `gate.py`/`checks.py` under
`results/codex/packed-orientation-gate`. No production source or registry changed
for this gate. The frozen pre-code proposal is `precode.md` (ee76ad8a…), and
`plan.json` binds the six exact040 capture/source/original-label records, the
frozen040 geometry and helper sources, and all limits before implementation.

The extractor adds one read-only callback after both existing `_arm` returns;
removing that AST statement reproduces the original function AST exactly. It
retains the legacy return, both orders/costs and identity cost. Each counterfactual
starts from a private saved-picture copy. Complete axis readouts and the final
judge require a timely check before the picture is returned; partial results
stay diagnostic. No new state feeds a later question. Only the first on-chip,
feasible packed-score reversal per input can consume the two physical evaluations.
Constructed and pruned chains are validated with040's unchanged original-edge
oracle, including inverse original labels, and retained even on failure.

Each fresh worker gets a separate empty Numba cache, single-thread numerical
settings and a5s clock starting in its parent before launch. Imports, source/input
checks, decoding, grid setup, two unscored setup readouts, question work and
validation consume that allowance. The setup readouts discard their output and
separate first compilation from the warm query ratio. Extra and legacy readouts
alternate measurement order across question indices. DP includes the small
observer materialization cost; this is not a deployment speed claim. Physical
oracle/serialization/administration are included in complete observed wall and
reported separately from the query ratio. CPU measures the worker function,
including numerical imports, but excludes earlier Python/stdlib startup.

The reused supervised20s watchdog terminates/reaps a stuck worker, with a fixed1s
TERM grace. The controller also checks actual outer return against5s, so late
publication cannot produce a complete gate. Raw worker status remains visible.
No result is retried. Missing/error/late outcomes remain explicit; incomplete
coverage cannot become a mechanism-negative conclusion. Candidate entrypoints,
full geometry search and contact refinement are actively blocked in the worker;
MM/busclique import guards are inherited from040.

Only the requested checks ran. The first extraction check failed before any
numerical call because Python3.10's `ast.unparse` inserts tuple parentheses.
Its raw error and pre-correction runner are preserved in `checks/attempt001`.
Matching the exact assignment AST fixes that instrumentation lookup without any
numerical or policy change. `attempt002` passes eight legacy-output comparisons
(five accepting, three declining) and both interruption boundaries (after first
pack and after final judge). There were no constructor, corpus or remote calls.

Frozen runner SHA256: `a22719e499258c5b17b4cbed6b6cdcdd1c864cf7f7b7c678a7577b6857fd070e`.
Checks SHA256: `e69dc413bca4d36759c9f8b8340767f0b7caeee44b6709745d52232de78322e4`.
The execution manifest includes these identities. The approved next action is one
six-state gate invocation, followed by a results/limitations record; neither a
candidate registration nor a complete-constructor screen is yet authorized.
