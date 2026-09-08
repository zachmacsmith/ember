# Induced-star singleton relocation: independent review

2026-09-08. Recommendation: permit a bounded development comparison after the
block selection, root order, and shared-work schedule are specified. The
restricted matching certificate is sound, and an actual Z12 witness establishes
useful coupling beyond strict one-chain shortening. Neither finding establishes
an advantage over our existing three-chain reconstruction or supports promoting
a new global policy. The matching reduction itself has close, explicit prior
art and should be attributed as conventional.

This review examines the [design](induced_star_relocation_spec.md), not an
implementation of the new operation. No candidate source was changed. The
mathematical diagnostic uses NetworkX matching and independently checks the
original source and target graphs. A later, separately authorized comparison
calls the existing generic local proposer once, using a frozen standalone copy.
Both diagnostics reject `minorminer`, `busclique`, and package-level `ember_qc`
imports. No constructor or complete embedding pipeline was run.

## Certificate and scope

For a valid incumbent, releasing the selected block and retaining the outside
chains reduces each selected vertex's external obligations to a domain of free
physical sites adjacent to every required frozen chain. With an induced source
star and fixed center site, its remaining constraints are center–leaf adjacency
and injectivity. A leaf-covering matching is therefore necessary and sufficient
for that center and those complete domains. Empty external obligations mean the
entire available target, as the design states.

The following details are conditions of the argument:

- Source and target are simple, undirected, and loopless, and the incumbent is
  valid. Check that every selected noncenter vertex is adjacent to the center
  and that no two selected leaves are adjacent.
- Domains include released qubits but exclude every frozen occupied qubit. All
  contact tests use actual target edges. The center cannot also serve a leaf.
- The matching graph must distinguish logical labels from physical labels;
  accidental label collisions must not merge its two partitions.
- Extra physical edges between leaves are allowed in a minor embedding. The
  source block is induced; the physical image need not be an induced star.
- Exhaustiveness applies only to the chosen block, singleton replacements, and
  examined roots. A truncated scan cannot certify absence of a move.

The degree exclusion is valid: each distinct logical neighbor needs at least
one distinct adjacent physical qubit when a chain is a singleton. Testing against
the target's maximum degree is a safe preliminary rejection; a proposed site's
actual degree may reject more. All accepted complete placements have selected
qubit count equal to the block size. If the old block uses more, qubits strictly
decrease even when contact redundancy falls. This guarantees immediate descent,
not the best later trajectory.

## A physical witness, checked exhaustively

The source is the five-vertex path `x–a–c–b–y`. Freeze `x` and `y`, select
`{a,c,b}`, and use `c` as the center. The table gives D-Wave Zephyr coordinates
`(u,w,k,j,z)` on the complete ideal Z12 target with tile parameter 4.

| Source vertex | Before: physical chain | After: physical chain |
| --- | --- | --- |
| x, frozen | `(0,0,0,0,0)` | unchanged |
| a | `(0,0,0,0,1), (0,0,0,0,2)` | `(1,1,0,0,0)` |
| c | `(1,5,0,0,0), (1,5,0,0,1)` | `(1,1,0,1,0)` |
| b | `(0,3,0,0,2), (0,3,0,0,1)` | `(1,1,0,0,1)` |
| y, frozen | `(0,3,0,0,0)` | unchanged |

Both complete embeddings pass independent checks for exact source coverage,
target membership, nonempty connected chains, disjoint ownership, and every
source edge. Total qubits fall from **8 to 5**, and ACL falls from **1.6 to 1.0**.
These are mathematical fixture results, not benchmark measurements.

For each of `a`, `b`, and `c`, the diagnostic substitutes every one of the 4,800
physical vertices while holding all other old chains fixed. None of the 14,400
substitutions is valid. Each selected old chain has length two, so this also
rules out every strict one-chain shortening of the incumbent. Equal-length
relocation, temporary growth, and multistep trajectories are not ruled out.

An independent joint enumeration uses only necessary endpoint constraints:
`a` must neighbor frozen `x`, `b` must neighbor frozen `y`, and `c` must neighbor
both proposed leaf sites. Checking every resulting triple against the complete
original source and target yields 32 valid assignments with 20 distinct center
sites. Separately, root-conditioned matching over all 4,798 sites available
after release identifies exactly those 20 centers. At the displayed center,
`a` has one eligible site and `b` has two; a covering matching exists.

This example demonstrates why moving adjacent chains together can help when
each chain's fixed neighbors prevent immediate shortening. The block has only
three vertices, so it remains within the existing generic operation's two-to-four
vertex bound. With only two leaves, the witness does not establish a computational
benefit from using matching instead of explicit assignment enumeration.

## One existing generic-proposer comparison

After the witness was frozen, the parent requested one local comparison on
that same incumbent and selected block. `generic_design.json` records the
settings before the call: group order `(c,a,b)` (center first, alphabetical
leaves), beam width 1, three alternatives, halo 2, region cap 512, 50,000
expansions, two reconstruction orders, 16 added boundary sites, greedy trees,
and objective `qubits_contacts`. These are the current fixed candidate's
per-group settings; the routine also tries the group's reversal. There was
no search over group orders, settings, or witnesses.

The existing operation **already improves the incumbent, from 8 Q to 7 Q**.
Both leaves become singletons at their old inner sites, while the center grows
from two qubits to three. The independently valid result has ACL 1.4 and gains
one redundant logical-edge coupler. It is less compact than the five-qubit
restricted optimum, but it refutes any claim that this fixture prevents generic
joint improvement.

| Diagnostic | Value |
| --- | ---: |
| Counted expansions | 321 / 50,000 |
| Tree attempts | 21 |
| Beam successors / pruned | 21 / 15 |
| Complete proposals / orders | 2 / 2 |
| Halo region / final region | 279 / 291 sites |
| Added boundary sites / boundary expansions | 12 / 14 |
| Stop reason | searched |
| Deadline overrun | 0 |

The displayed five-qubit witness's center is outside this region. However, 16
other valid all-singleton assignments, at 12 center sites, are wholly inside
it. Thus region exclusion alone cannot explain the missed optimum. The
bounded route alternatives, prefix ranking, and beam do not exhaust those
assignments, even though the overall expansion cap is not reached. The evidence
does not identify a single causal limit, nor show that other fixed generic
settings or later calls would miss the optimum.

The instrumented call took 0.02035 seconds including context creation and
wrapper overhead; the routine reported 0.01990 seconds. This one local diagnostic
is not a runtime benchmark or a timing comparison against a proposed matching
implementation. The exhaustive matching oracle is a correctness diagnostic,
not an integrated competing operator. All saved source, input, and result
hashes appear in the artifact manifest.

## Closest primary prior art

**Solnon's LAD filter is the closest mathematical mechanism.** Section 4,
Definition 1, on page 11 of the author preprint defines, for a pattern root
`u` and candidate target root `v`, the bipartite graph

```
vertices = adj(u) union adj(v)
edges = {(u',v') in adj(u) x adj(v) : v' belongs to D[u']}
```

A matching must cover `adj(u)`; its absence rejects `v` from the root domain.
This is the same root-conditioned neighborhood/domain graph proposed here.
Our inference is that independent leaves make the condition sufficient for
the entire selected block once frozen-chain obligations are encoded in domains;
for a general pattern, LAD is a necessary filtering test. Cite this directly,
rather than presenting a new matching reduction. The source is Christine Solnon,
*AllDifferent-based Filtering for Subgraph Isomorphism*, Artificial Intelligence
174, 850–864 (2010), [author preprint](https://liris.cnrs.fr/Documents/Liris-4568.pdf),
[published article](https://doi.org/10.1016/j.artint.2010.05.002).

The predecessor is Régin's matching-based treatment of distinct-value
constraints, including subgraph-isomorphism applications. It establishes the
domain/injectivity foundation used by LAD. See *A Filtering Algorithm for
Constraints of Difference in CSPs*, AAAI 1994,
[official proceedings PDF](https://cdn.aaai.org/AAAI/1994/AAAI94-055.pdf).
Solnon's [author software page](https://perso.liris.cnrs.fr/christine.solnon/LAD)
describes the C implementation and a CeCILL-B license; this review proposes no
source reuse or new dependency on that solver.

**Matching has also appeared in annealer minor embedding, with a different
role.** Lobe, Schürmann, and Stollenwerk formulate complete-graph embeddings on
broken Chimera by matching horizontal rows to vertical columns, subject to
additional compatibility conditions. Their variables choose cross-shaped
chains, rather than singleton leaves subject to frozen-chain domains. The paper
does not establish this local-refinement mechanism or its Zephyr performance,
but it precludes a broad claim that matching-based annealer embedding is new.
See Sections 1.3 and 3.1 of
[*Embedding of Complete Graphs in Broken Chimera Graphs*](https://link.springer.com/article/10.1007/s11128-021-03168-z)
(2021).

**Changing neighboring chain ownership is established local-search practice.**
CMR reconstructs chains from paths to neighboring models and allows portions
of paths to be reassigned to neighbors. See Sections 3 and 5 of
[*A practical heuristic for finding graph minors*](https://arxiv.org/html/1406.2741).
Bian et al. describe qubit removal, transfer, and two-chain exchanges within
partial-embedding optimization, as well as joint disjoint routing; see Sections
2.2.2 and 2.2.5 of
[*Discrete optimization using quantum annealing on sparse Ising models*](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full).
These are not the same whole-block singleton matching operation, but coupling,
movable contacts, and local embedding refinement alone are insufficient novelty
claims. The earlier [contact prior-art review](contact_prior_art.md) covers ATOM,
CHARME, and additional reconstruction precedents.

The bounded search found no verified source implementing this exact
frozen-boundary, strict-qubit-descent operation. That is an unresolved attribution
question, not evidence of absence of prior art. The prospective contribution is
a useful restricted minor-refinement neighborhood and its effective integration;
both usefulness and distinction still require evidence.

## Main practical risks and the next discriminating test

Root discovery and domain construction may dominate the small matching problem.
There can be 4,800 roots, while many blocks have no feasible root. Nonempty
individual leaf domains and a sufficiently large union are necessary but do
not replace a covering matching: subsets of leaves may still compete for too
few sites. The entire domain, ownership, adjacency, augmenting-path, and failure
cost must share the existing allowance. Rebuilding these structures for every
block can erase any gain from a polynomial assignment step.

Choosing one independent leaf subset is a material restriction. Adding leaves
can destroy feasibility, and a maximal subset can miss an improving smaller
block. Including only singleton leaves cannot save qubits unless the center
is longer; high-degree selected vertices cannot become singletons at all. No
family-specific remedy follows from these limitations.

A first covering matching gives strict qubit descent but chooses among many
equal-size outputs without optimizing their later contact opportunities. More
root or matching alternatives spend work and can displace ordinary groups,
as experiment 033 already showed for another promising local operation. The
unimplemented design currently leaves block selection, root order, size bounds,
and scheduling unspecified. These are concrete blockers to a reproducible
production comparison, rather than objections to the mathematical certificate.

After those policies are frozen, compare the new operation with ordinary joint
reconstruction on the same saved incumbents, chosen blocks, and shared work.
Include blocks larger than four when eligible: that tests the stated reason
to use matching beyond the current group bound. Report all zero-gain cases,
qubits saved, ordinary coverage displaced, and total refinement cost. A positive
isolated fixture does not justify an end-to-end candidate change, and neither
this witness nor a development ablation supports an Ember-wide claim.

## Reproducibility and archived evidence

Artifacts are in `results/codex/induced-star-witness/`. The frozen specification
predates the parent's appended initial prior-art paragraph. The diagnostic uses
Python 3.10.19, NetworkX 3.4.2, and dwave-networkx 0.8.19 in the isolated native
environment. Its output refuses overwrite. For a fresh replay, copy `check.py`
and `specification.md` to an empty directory and run the copied script with
`.venv/codex-native/bin/python`; it writes `witness.json` beside itself.

| Artifact | SHA-256 |
| --- | --- |
| Frozen specification | `3d1853a21b635192e630071b703ed0815f04dd87d251ac3b5e10312e90045b5a` |
| Diagnostic `check.py` | `1a8a67a7dec9a09f00fc59e96da88c97d9ef6fce41bee782f0d0e4acee16dabb` |
| `witness.json` | `d87f2425ac5f5cd2d84b60d037b887fa2e3ef975bebf282a0dbb1f20ed92e634` |
| Canonical full Z12 nodes/edges | `fe833322b95294a242bcabf814b86d1420328c3df11ba3dfe47fdc5a8911607d` |
| Solnon author PDF, 441,783 bytes | `2dcf030f09096d8f2d53e853b1bae02d3d21993eca525b61818cc5493f0517af` |

The primary PDF was downloaded directly from the author URL above; its local
name is `Solnon_LAD_author_preprint.pdf`. `pdftotext -layout` produced the archived
text. Section 4 begins on PDF page 10; Definition 1 is on PDF page 11, and the
matching implementation discussion follows on pages 12–13. `artifact_manifest.json`
records all saved-file hashes and the download/extraction provenance. These
artifacts preserve the precise source for attribution without relying on a
future web fetch.
