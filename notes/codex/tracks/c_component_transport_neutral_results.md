# Neutral component transport repairs seven additional queried edges

The [equality-admission amendment](c_component_transport_neutral.md) certifies seven additional edges on the same supplied states and limits: ten of 25 queries, versus three under strict descent. Every new certificate needs two donor exchanges. All whole-source outputs remain incomplete because each query starts independently from its supplied entry and preserves only the already realized original contacts plus its requested edge. No query outputs were combined.

| Input | Queries | Certified, strict → neutral | Attempts | Neutral admissions | Diagnostic wall |
|---|---:|---:|---:|---:|---:|
| ER 6450 | 8 | 1 → 4 | 88 | 83 | 3.542 s |
| Regular 14334 | 8 | 0 → 0 | 517 | 499 | 24.916 s |
| Complete 1041 | 1 | 0 → 1 | 65 | 64 | 1.572 s |
| SBM 30736 | 8 | 2 → 5 | 80 | 72 | 3.080 s |

The complete query `(8,63)` first relocates donor 43 from site 1542 to 1178, then donor 93 from 1541 to 3513. The first move opens an isolated pocket at unchanged separation two; the second connects the endpoint-accessible regions. Its seven-site unused path increases Q from 3556 to 3563. This certifies the formerly sealed contact while the other two initially missing contacts remain unproved by that certificate. It does not establish sequential completion or final ACL after cleanup.

The new ER edges are `(1,21)`, `(5,29)` and `(5,117)`; SBM adds `(1,15)`, `(1,42)` and `(1,113)`. The three earlier repaired edges remain repaired, with exactly the strict diagnostic's saved witnesses. Across 750 attempted replacements, 718 equal-separation states were admitted, ten moves led to certificates, ten proposals resealed an endpoint and twelve repeated an already seen state. Admissions can subsequently be pruned by the beam; they are not all expanded. Regular reached depth four without a certificate and consumed most of its 30-second allowance. Complete retained its 64-proposal first-state cap, then certified on the first attempted child proposal. No input timed out or exhausted a query's 512-proposal allowance.

The diagnostic took 33.789 s, versus 8.043 s for strict descent; independent saved-state review added 25.576 s. Component reconstruction examined 48.003 million adjacency entries, ranking searches 9.448 million and separation searches 33.063 million. Those costs, failed domains, capped prefixes and every edge-selection outcome remain recorded. A preserved metadata preparation failure stopped before reading inputs or calling the diagnostic; there was only one actual supplied-state execution.

Four focused test groups passed, including strict rejection versus neutral two-move success on the modified pocket fixture. The older five-site fixture remains rejected because its required first donor is outside the unchanged release boundary. Independent replay verified 775 query-scoped private-state records against original labels and edges, conserved Q, endpoint/outside ownership, exact post-exchange regions and non-increasing separation. These counts identify replay records, not globally distinct embeddings.

This result supports testing one evolving incumbent next, preserving every contact realized at each commit. That test must be specified separately: the current independent certificates cannot be assembled into a complete minor by assumption. No constructor, MM, cleanup or remote call occurred. See the [full summary](../../../results/codex/track-c-component-transport-neutral/summary.json), [25-query table](../../../results/codex/track-c-component-transport-neutral/queries.csv), [478-edge ledger](../../../results/codex/track-c-component-transport-neutral/all_missing_edges.csv) and [frozen manifest](../../../results/codex/track-c-component-transport-neutral/review_manifest.json).
