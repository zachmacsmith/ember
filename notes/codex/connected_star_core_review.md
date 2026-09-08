# Independent connected-center core review

2026-09-08. **No correctness blocker found under the declared internal contract.**
The frozen core passed the independent matching, original-graph, interruption,
cache and Z12 mechanism checks below. This clears the local core for a separately
reviewed integration; it does not establish heuristic completeness, cumulative
ACL improvement, MM-scale runtime or novelty.

The reviewed [implementation specification](connected_star_implementation_spec.md)
has SHA-256 `41e7b0bc31d7fa44a8c2f326d0a143315b6e5f178a5e7164cc530a32919f1e99`.
The author declared the core stable before this reviewer executed it. The
independent [audit plan](../../results/codex/connected-star-independent-review/audit_plan.json)
was saved first. No production files, author tests, scheduler or pilot were
edited. No constructor, saved embedding input, MM call or corpus benchmark was
used.

## Contract and static findings

The core requires original simple undirected loopless graphs, a valid incumbent,
fixed context and immutable incumbent mappings/chain lists. It returns only a
proposed selected replacement. The caller must independently check its commit
deadline, commit atomically, and refresh ownership before another proposal.
Identity checking alone cannot detect an unauthorized in-place incumbent edit.

The selected vertices are rechecked to induce exactly one star in
[`_Problem`](../../packages/ember-qc/src/ember_qc/algorithms/factored/connected_star_relocation.py#L115).
Grouping leaves by equal frozen-neighbor sets preserves singleton eligibility;
each site retains capacity one. The eligibility memo publishes only completed
boolean decisions. Compact successor copies do not share mutable speculative
sets, assignments or counts with their parent state.

[`_maximum_assignment`](../../packages/ember-qc/src/ember_qc/algorithms/factored/connected_star_relocation.py#L291)
starts every underfilled demand class and allows filled classes to exchange
sites. A completed unsuccessful search includes the full neighborhood of the
reachable classes, including their owned sites. Demand counts class multiplicity.
No interrupted matching is marked maximum. Consuming an assigned center site
decrements its old class before matching is repaired; assignment size need not
increase during growth.

[`_bounds`](../../packages/ember-qc/src/ember_qc/algorithms/factored/connected_star_relocation.py#L372)
uses the unfiltered distinct available boundary, separately from physical edge
boundary. For connected one-site growth, the removed boundary site and at most
Delta-minus-one newly exposed sites justify the stated necessary bound. It is
conditional on retaining the footprint and does not prove global infeasibility.

[`_certify`](../../packages/ember-qc/src/ember_qc/algorithms/factored/connected_star_relocation.py#L560)
expands individual leaves and checks actual target membership, nonempty connected
center, disjoint ownership, every original selected-incident source edge, and
strict selected Q reduction. It recounts actual couplers for old and new chains.
A strict Q improvement may lower redundancy and may grow the center. Final
budget/deadline checks precede returning the certified proposal.

[`ConnectedStarSearch`](../../packages/ember-qc/src/ember_qc/algorithms/factored/connected_star_relocation.py#L755)
charges lazy setup, selection, query and refresh through the supplied live visit
and shared auxiliary allowance exactly once. Refresh removes all old selected
owners before adding new ones. Interruption disables the partially updated cache
without changing the externally committed valid embedding. The imported
singleton module supplies budget/cache primitives; its proposal is never called.

## Independent evidence

The [standalone verifier](../../results/codex/connected-star-independent-review/verify.py)
loads only frozen core/dependency bytes. It recreates the small context directly,
blocks all other Ember/MM/busclique imports, and never imports the author's tests
or validators. It expands classes into individual leaves and exhaustively
enumerates partial injective assignments. Original-edge validity and Q/R checks
use separate adjacency code.

| Check | Observed result |
|---|---|
| Capacitated assignment | 4,608 inputs; 32,404 maximum-cardinality comparisons, including varied valid partial assignments and consumed/re-exposed owned or free sites; zero differences |
| Original-graph fixtures | 32 generated valid minors plus 3 adversarial/steering fixtures; 419 connected footprints, 121 full strict-Q certificates; exact agreement with expanded domains and original physical constraints |
| Frozen obligations | Generated cases use 3–4 independent leaves, center obligations, 3 outside vertices including a two-qubit frozen chain, outside logical edges, and 2–4 demand classes |
| Conditional bounds | 99 rejected footprints had no feasible connected superset within the ceiling in the exhaustive small-footprint oracle |
| Query interruption | 1,407 prefixes over successful, failing and bridge-steering queries; work-prefix and budget-check deadline injection, including final checks |
| Shared work and refresh | 858 setup/query/auxiliary prefixes and 50 refresh prefixes; exact accounting, no invalid returned proposal, unchanged input, disabled partial caches and stale-identity rejection |
| Actual ideal Z12 | Independently reconstructed source degree 22 exceeds target Delta 20; selected Q 25→24, center size 3→2, redundancy 2→1, 1,808 charged units |

The original-graph fixtures returned 34 certified queries. Their constructed
incumbents are deliberately small correctness cases, so this rate is not a
coverage or quality estimate. Twenty-two strict-Q query certificates reduced
redundancy; the independent score checks accepted that intended behavior.
The separate positive-member-growth and zero-gain bridge cases also passed.

The documented seven-site root failure was reproduced: root 1 has no solution
within its ceiling, but exhaustive enumeration finds the better center `{2,3}`.
The query returns `heuristic_no_proposal`; it is not misreported as exhaustive
infeasibility. The same example confirms matching size can decrease 1→0 after
center growth. Full unsuccessful evidence remains in `attempt001/graphs.json`
and `attempt001/bounds.json` alongside successful cases.

These finite checks do not prove all inputs safe. They exercise stronger
starting-state variation than replaying the author's suite, but still use tiny
domains and prescribed graph constructions. The Z12 witness proves only that
an above-Delta center can be refined within this local allowance. The measured
2.740-second audit duration is not a candidate runtime comparison. A single
query can consume the whole auxiliary share; heterogeneous domains, root choice
and displaced ordinary work remain material cumulative-performance risks.

## Frozen identities and reproduction

Artifacts are under `results/codex/connected-star-independent-review/`.

| File / record | SHA-256 |
|---|---|
| Frozen core | `d58b16bdee4024e5f40d066165c17fec1e7a5193c97d31a63fa871d0b80d9473` |
| Shared budget/cache dependency | `785a1ab9f88d8ec6454029fe648b5d62213063f17d4933bdadbef336602c965a` |
| Author test bytes, retained but not executed here | `67763d5a9822c5f6d3bcd61cebae35a647602a7c0ae32bb2f65d42a5bb6f28a8` |
| `source_manifest.json` | `f40b666df7dd7ffd2ddd74cb843ff550221462add0185f90dbd6d370e96fc2ae` |
| `verify.py` | `88586761635434d68bd03fb4ad9f9517d7f2dab459d06d4c75185f1c38e13790` |
| `attempt001/summary.json` | `e71bfd1ee626bf604489153266adbe59fe16c070bde07e2f29513caa37a5f7f8` |
| `attempt001/z12.json` | `a4d23d02a2e8cebc6d01ed7002e1af79c580f40cecc47a23bb0e1985a20ee9eb` |

The live core and dependency still matched these frozen hashes after the audit.
The target is the original 037 ideal-Z12 record, SHA-256
`c683ae784e2ee9a1d14f0760368deaa5cfeee2c47a6c2eade683e5412e61177c`.
An additive rerun, from the repository root and with a fresh output directory:

```sh
.venv/codex-native/bin/python results/codex/connected-star-independent-review/verify.py results/codex/connected-star-independent-review/root_repeat
```

The verifier preserves inputs, full observations and any failure context, refuses
existing output directories, checks source hashes before import, and reports its
own hash. No scheduler integration is included in this review.
