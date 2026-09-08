# Track B002: joint insertion with a free extension frontier

2026-09-08. Hypothesis, pseudocode and critique saved before code. This replaces rejected B001 as Track B's one active candidate. B001 and its completed nine-input run remain unchanged.

B001 exhausted 20million adjacency scans before completing the three dense inputs. Its ER failure also exposed loss of earlier free-port reserves. Five sparse inputs succeeded but all lost ACL; subsequent frozen-neighbor sweeps saved only one qubit. A larger routing allowance does not address those mechanisms.

## One revised constructor

Keep one partial minor, but make insertion a **joint operation** on the new chain and any existing neighbors that need extension. Each placed chain that still has an unplaced logical neighbor must retain at least one free physical boundary site. This weak invariant preserves a possible extension direction; it does not reserve separate sites for every demand or certify eventual feasibility.

Before inserting v, if a required neighbor w has only one free port and needs another future neighbor after v, extend w through free sites until it has at least two ports. Use the extension opening the most free boundary sites. All changes are private until insertion completes; reject an impossible expansion. Do not allocate v into another chain's last required extension port. Reject any complete insertion that nevertheless consumes all such ports through a longer path.

Rank free roots by current neighbor contacts and source-frontier lookahead. For each unplaced logical vertex of degree at most the maximum target degree, compute the free sites simultaneously touching all its already placed neighbors. These are possible future singleton positions with the current chains frozen. Favor fewer empty/small domains through a lexicographic sorted domain-size vector; no graph-family information is used. Degree-ineligible vertices are omitted from this singleton-specific lookahead by a mathematical bound. The score is a heuristic: existing chains may later grow, and future unplaced edges impose additional constraints.

Evaluate at most four roots selected from 64 directly ranked boundary sites. From the new connected chain, run a multi-target shortest-path expansion to any unmet neighbor. Each free path may be split at any cut: its prefix extends the new chain and its suffix extends the reached old chain. Choose a cut that restores the most current contacts, preserves the extension frontier, and leaves better future singleton domains. Thus old neighbors can move their contact boundary during the same insertion. Reuse newly built chain pieces for remaining contacts. Prune safely removable sites of changed chains while preserving their existing contacts and extension frontier. Choose the completed insertion with least actual total Q, then better future domains, with deterministic seeded ties.

```text
partial = empty
while source vertices remain:
    v = most placed neighbors, then degree, then seeded tie
    stage necessary extensions of v's constrained existing neighbors
    rank at most 64 free roots using contacts and future source domains
    for the first four roots:
        start v at root in a private state
        repeatedly route from v to any unmet neighbor through free sites
        assign each path at a connected two-ended cut; preserve free frontiers
        prune changed chains; reject invalid or trapped private state
    commit the complete candidate minimizing actual Q then future-domain cost
    if none or interruption: report explicit failure and earlier partial minor
validate final minor and return; no separate global refinement sweeps
```

All setup, candidate branches and failures share the fixed 20million adjacency-scan cap and 60-second deadline. Bitset domain operations are separately time-bounded, not falsely counted as adjacency scans. Each shortest-path query stops at its first reached unmet contact, avoiding B001's full per-neighbor maps to64roots. Worst-case scans still depend on target size and source contacts; the explicit cap is a workload limit, not a performance guarantee. Memory is target adjacency/bitsets plus four private partial states, O(e+h²/word_size+Q) apart from heap storage. There is no MM, busclique, alternate constructor, saved starting embedding, family dispatch or portfolio.

## Self-critique and cheap falsifier

Connected path growth, congestion prices, endpoint assignment and limited lookahead are established routing ideas; no novelty is claimed. One free port is only a necessary extension opportunity. Two logical chains can compete for the same port, and a free corridor can lead nowhere useful. A short path may consume several ports together even when no individual site was initially unique. The proposal must reject the final trapped state rather than silently claim preservation. The four-root limit may miss the useful insertion. A future singleton-domain score ignores edges among unplaced vertices, and forcing old-chain extension may cost more Q than moving that chain. Strict immediate Q preference can sacrifice a better future layout. This whole-candidate screen will not isolate the contribution of each changed component.

The unchanged nine B001 development inputs, ideal Z12, seed0, candidate `frontier-tree` and fresh MM are fixed before implementation. Use the same 60seconds,20million scans, isolated fresh-process pairs on hyde02, and the existing validator/supervision. Keep all failures and times. Reject the revision if dense completion and sparse quality do not materially improve over B001; do not infer MM superiority from an incomplete or late comparator. A promising subset warrants mechanism-focused ablation, not a per-input constructor selector or broad claim. No larger cap or changed panel is part of B002.

## Implementation and pre-outcome freeze

New standalone module `packages/ember-qc/src/ember_qc/algorithms/factored/frontier_construction.py`, SHA-256 `cf884d8e86e33c5cb579686886d671cdb2b838ef7c249c462033c006810d6eae`. It copies only basic graph/budget/validity helpers from B001; there is no import or call to the B001 constructor, its path-union proposal, the geometric/native entrypoint or any external embedder. Candidate registry is `frontier-tree`, supplied by the shared pilot owner; pilot SHA-256 `9efb4444ef33b1e289a619c1e3e85329c9260087f132c6c1a5d06241dc2ea16f`.

Six focused guarded checks pass at `results/codex/track-b002-checks/attempt002`. They include a hand-built path allocation where the old endpoint must receive sites to preserve a future singleton domain, multi-qubit center growth during insertion, atomic failure of an impossible extension, valid tiny original-graph embeddings, deadline/work failure and insertion-order/metadata controls. `attempt001` also passed; the only subsequent source edit records scan counts if initialization is interrupted before the builder returns. The six-check repeat covers that accounting change. No exhaustive audit or corpus call preceded this freeze.

`staged_extension_sites` and `staged_pruned_sites` include discarded private work, not committed Q gains. Actual per-insertion Q changes and changed existing owners are recorded separately. Every completed candidate insertion is validated as a minor of the placed source subgraph, and its free-frontier invariant is checked. The complete output receives a final full original-graph validation inside the constructor and the unchanged independent pilot validation afterward. A partial/late output is not credited.

Frozen run `results/codex/track-b-frontier-002`:18calls, same nine graph and target bytes as B001, seed0,60seconds,20million scans. Manifest `a84d47561ef4de3e6c12cf384c682de714d95e4063eb637721fe3f0ff221be50`; source snapshot `ce146fbf4b25059f7cf98acddfc0ed5d80cbf08da9df0754652851f427930b11`. `results/codex/track-b002-checks/freeze.json` records the byte comparisons and full task order before outcomes. The four-root insertion evaluates a bounded set of local alternatives within one constructor; it does not run or select another embedding method.

Preparation used the existing pilot:

```sh
.venv/codex-native/bin/python -B scripts/codex/pilot.py init results/codex/track-b-frontier-002 --methods mm,frontier-tree --seeds 1 --timeout 60 --candidate-python /home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python --mm-python /home/dabh/ember-codex/envs/4e1fb892db12754e/mm/bin/python
.venv/bin/python scripts/codex/cluster.py --host hyde02 stage results/codex/track-b-frontier-002
```

Do not rerun `init` over this identity. New source/settings require a new identity; no reconnect causes a restart.
