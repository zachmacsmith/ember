# First transfer panel after strategic review — before generation

2026-09-09 UTC. This is development, not confirmation. Generate each declared
attempt once; preserve errors/time and do not replace failed attempts. No
candidate/MM outcome is used to select this panel. Frozen generator code and
parameters precede generation; independent original-graph validation precedes
embedding credit. The common target is the already audited idealZ12 record.

Twenty intended structures plus two nested relabelings:

- Twelve fresh generation attempts: at n80 and160, ER p0.10, BA m4,
  regular d8, Watts–Strogatz k6/beta0.2, four-block SBM p_in0.20/p_out0.02,
  and the repository's full greedy nonuniform-planar generator. These generators
  are imported from pinned `generate_graphs2.py`, never its save/CLI routines.
  Planar generation must finish its entire pair scan;300s/attempt is a generation
  watchdog, not permission to publish a partial graph. Other generators use30s.
- Three exposed diagnostic anchors from A061: grid1584, honey32367 andwheel2429.
  Fresh BA and planar inputs provide their respective structural contrasts.
- One exposed dense sentinel: B's complete100, unchanged. Its past failures stay
  failures; this panel cannot establish an all-class result.
- Four evaluator-hidden known-feasible controls: n80/n160 connected induced
  singleton subgraphs ofZ12, and n80/n160 quotients of disjoint connected target
  branch sets of sizes1,2,3 in cyclic order. Singleton controls certifyACL1;
  branch controls certify only a feasibleQ upper bound. Grow using actual target
  adjacency and one fixed seeded traversal, without solving any embedding.
- One additional independent relabeling of anchor grid1584 and fresh BA n80.
  They share their parent structure and are never counted as independent graphs.

All base inputs are sanitized and independently permuted into consecutive source
labels, with empty metadata/attributes. Seed namespace is SHA256 of
`ember-codex-transfer001/{generation|label|order}/{case}` truncated to64bits.
Generator seeds use the generation namespace; relabelings use distinct label
namespaces. Solver seeds are separate and will be frozen in screen protocols.
No source-family identifier, target coordinate, witness or generation parameter
is passed as graph data. Neutral gNNNN keys identify tasks.

Build singleton controls by a randomized breadth-first traversal of actual
target adjacency, taking exactly n vertices and retaining every induced edge.
Build quotient controls one connected branch at a time, rooting the next branch
at a free neighbor of already occupied sites, then extending within free target
adjacency. A failed root/extension ends that generation attempt; no reseeding or
retry. Include every original-source edge supported by distinct branch owners.
The witness is validated by the existing independent oracle, separately from
the generator. Original sources, relabeling maps and witness maps live only in
`/Users/dabh/ember-evaluator-private/transfer-cycle-001`, outside remote candidate
filesystems and omitted from every transport. Candidate source imports neither
the generator nor any evaluator artifact.

Preserve the complete attempt ledger, generator/protocol/target hashes, actual
n/m, wall/CPU, label bijections and graph hashes. Check exact labeled-topology
matches against exposed012/017 and recent raw inputs where available. Such an
index is not an isomorphism proof; unresolved global identity stays explicit.
Different seeds or labels are not evidence of a fresh structure. Use exact
isomorphism checks only against plausible same-n/m development matches, with
bounded time and unresolved outcomes retained; do not regenerate matches.

The audited pilot worker, supervision and embedding validators are reused.
A preparation adapter may supply these graph objects to the existing initializer
instead of its built-in B9 provider, recording its source and checking every
frozen graph/task hash afterward. Runtime worker code remains unchanged except
three explicit constructor registry entries. Private evaluator files are never
copied into the initialized run. Any schema/provenance limitation is reported,
not hidden by relabeling these inputs as inherited corpus data.

Self-critique: target-derived controls are biased diagnostics, only six generated
families are covered, and one graph at each size cannot estimate a family mean.
The panel tests mechanisms and transfer promptly. It does not replace the full
retained-class table, repeated seeds or a separate untouched confirmation set.
