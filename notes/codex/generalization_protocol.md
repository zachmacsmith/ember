# Protocol for fresh-structure generalization and final confirmation

Date: 2026-09-08 UTC. Proposed protocol only. No graph was generated or modified,
no input was downloaded, and no embedding experiment ran for this note.
Generalization has not been demonstrated.

All inherited graph files, historical experiments, 012, 017, and current pilot
graphs are development data. A new graph ID, RNG seed, weight assignment, vertex
label, or serialization order does not by itself create a new structural problem.
An eventual paper should distinguish:

1. Performance of the frozen algorithm on the explicitly enumerated inherited
   corpus. This can provide descriptive per-family evidence despite prior tuning.
2. Confirmation on genuinely new structures from declared comparable generator
   distributions or previously unseen parameter regimes.
3. Finite families for which the allowed original catalogue has already been
   exhausted. These cannot acquire an unseen-structure holdout by repeating seeds.

The original all-family research objective stays open when a family loses or is
unresolved. Missing fresh structures are a limitation of a generalization claim,
not permission to relabel an observed loss or an optimal tie as improvement.

## Repository evidence and generator problems to resolve first

Source abbreviations used below:

- **G1**: [generate_graphs.py](../../scripts/generated_graphs/New_Generation/generate_graphs.py).
- **G2**: [generate_graphs2.py](../../scripts/generated_graphs/New_Generation/generate_graphs2.py).
- **CSV**: [generate_graph_library_csv.py](../../scripts/generated_graphs/New_Generation/generate_graph_library_csv.py).
- **Manifest**: [manifest.json](../../packages/ember-qc/src/ember_qc/graphs/manifest.json).
- **NX Sudoku**: installed NetworkX 3.4.2,
  `.venv/lib/python3.10/site-packages/networkx/generators/sudoku.py:51`.

These sources define the repository's generator behavior; they do not prove which
source revision or dependency version produced every inherited file. Preserve raw
hashes as authoritative instance identity. Before generating confirmation data,
freeze a reviewed generator module, dependency versions, actual output schema,
and semantic property checks. Do not run the legacy bulk CLI: G2:64 points its
output directory at a previous developer's absolute Dropbox path.

Material findings:

- **Sudoku parameter mismatch.** CSV:395–396 labels board side lengths 9 and 16
  with expected 81 and 256 cells. G1:1215–1216 and G2:1239–1240 pass that `size`
  directly as the NetworkX **box order**, producing 9^4 and 16^4 vertices. G1:243–247
  correctly documents ordinary 9×9 Sudoku as order 3. This explains the oversized
  original entries; it is not evidence that ordinary Sudoku graphs exceed Z12.
- **BCC periodicity does nothing.** G2:576–604 uses `periodic` only in the name and
  metadata. Both values create the same open graph with `(m+1)^3 + m^3` vertices
  and `8m^3` edges. The 012 exact duplicates agree with this source finding.
- **King and frustrated-square are one unweighted structure family with two
  labels.** G2:522–528 literally calls `gen_king_graph`. Shared structures must stay
  in the same split and carry one independent structural observation.
- **LFR has two different generation policies.** G1:603–622 makes one call with
  fixed community bounds. G2:611–646 changes `min_community` on successive failures,
  potentially changing the population being sampled. Use fixed explicit community
  bounds for confirmation; generation failures remain records, not an excuse to
  change parameters until a graph appears.
- **“Planted solution” is induced hardware sampling here.** G2:739–774 samples
  vertices from a hardware graph. CSV clique-size/background-density parameters
  are metadata only in G1:1219–1229. They cannot count as new structural parameters
  or establish a planted optimization solution. Disconnected components and
  isolates are legitimate outputs and must be preserved.
- **The Shastry–Sutherland name needs scientific review.** G2:544–573 claims
  orthogonal dimers, but its explicit loop adds northeast diagonals from every
  even-parity grid site. An interior even-parity site can receive a southwest
  diagonal as well as emit a northeast one; this is not a one-dimer-per-site
  matching. CSV:289–296 also estimates `4m^2` vertices while the constructor loops
  over `m*n` sites. Preserve this as the *repository-defined* family until an
  independently specified physical lattice is reviewed; any corrected generator
  needs a separately identified supplement.
- **Random planar is not uniform planar sampling.** G2:427–444 shuffles all
  candidate edges and greedily retains those preserving planarity. Preserve that
  procedure for a comparable distribution; an early prefix is a different graph
  distribution. CSV:226–231 already notes its high generation cost above 660 nodes.
- **Hardware feasibility is target-specific.** G2:777–824 generates full C/P/Z
  source graphs. Their identity embeddings on their own coordinate topologies do
  not establish identity embeddings on the experiment's Z12 target. For a smaller
  Zephyr source, any coordinate mapping into Z12 must be checked against the
  actual target adjacency, not assumed from integer labels.

## Split construction and protection from adaptation

Freeze a split-generation protocol before producing new validation or test
outcomes. The following concrete starting design is suitable for development
planning; graph counts must still be increased to satisfy the precision and
reliability requirements below.

- New development sizes for stochastic generators: `N = {64, 128, 256}`.
- Validation sizes: `N = {80, 160, 320}`.
- Final-test sizes: `N = {96, 192, 384}`.
- A separately reported size-extension set can use `{640, 896, 1280}` for sparse
  generators, after its budgets are calibrated on development sizes and frozen.
  It is not pooled into the smaller-size comparison or silently required of every
  dense family.

These disjoint sizes test unseen-size behavior relative to the *new* development
series; they do not prove novelty relative to the full inherited corpus. Every
candidate structure must still pass the identity checks below. For deterministic
families use the parameter pools in the table, then partition verified new
structure groups by a salted hash into development/validation/test proportions
40/20/40 within the predeclared node-size strata. Treat the immutable inherited
corpus as development regardless of its hash partition.

Use independent namespaces for graph-generator seed, solver seed, source
relabeling seed, and method execution order. A concrete generator-seed scheme is
the first 32 bits of SHA-256 of `(protocol version, split, family, full canonical
parameters, replicate index, split salt)`, with collisions detected and resolved
by a recorded counter. NetworkX generators differ in their accepted RNG objects;
freeze an explicit integer-seed interface and dependency version. Disjoint seed
namespaces alone never substitute for structural checks.

For planning, schedule 10 graph-generator replicates per stochastic parameter/size
cell for new development and validation. Choose final graph counts from validation
precision estimates before exposing final data, with a floor of 30 distinct
structures per family where the family actually supplies that many. Schedule 10
solver-seed replicates per graph initially. These are starting counts, not a claim
of adequate power; the one-percentage-point reliability requirement can need far
more independent graph observations.

Final inputs should be generated by a separate evaluator after the algorithm,
configuration, budget rule, dependency hashes, inference code, and accepted
generator definitions are frozen. Commit a final-salt hash and publish the salt
with the results. Keep final graph files, failures, per-instance outcomes, and
diagnostics inaccessible to algorithm development until that frozen attempt is
complete. Validation results may guide development; any exposed final structures
become development for subsequent revisions. Do not peek at selected final
families, revise the algorithm, and resume the same claimed test.

## Concrete generator/parameter proposals for all 36 families

`N` means the split-specific actual vertex count above. All candidate pools are
subject to actual simple-graph checks, `n <= 4800`, `m <= 45864`, and structural
novelty verification. Passing these bounds does not certify embeddability. Primary
parameters below stay close to the repository generator; any expansion beyond
the inherited parameter range must be labeled an unseen-parameter distribution,
not represented as a random sample from the old manifest.

| Family | Proposed source generation / parameters | Source and freshness limits |
| --- | --- | --- |
| random_er | `gnp_random_graph(N,p)`, `p={.02,.10,.30}` | G2:375; new generator seeds and verified new structures. Retain isolates. |
| barabasi_albert | `barabasi_albert_graph(N,m)`, `m={2,4,8}` | G2:383; same generator definition, new seeds/sizes. |
| regular | `random_regular_graph(d,N)`, `d={3,8,20}` | G2:391; all proposed N are even, with N>d. |
| watts_strogatz | `watts_strogatz_graph(N,k,beta)`, `k={4,12,20}`, `beta={.1,.5,1}` | G2:401; report beta=0 separately as a deterministic circulant, not many seed-independent graphs. |
| sbm | Four equal blocks, `(p_in,p_out)={(.2,.02),(.5,.05),(.2,.10)}` | G2:409; all N divisible by four. Keep block labels out of solver input. |
| lfr_benchmark | `tau1=2.5,tau2=1.5,mu={.1,.3,.5},average_degree=5`, `min_community=max(3,min(20,N//10))`, `max_community=N//3`, fixed `max_iters=500` | Freeze a direct NetworkX call matching G1:608, not G2's parameter-changing retries. Remove self-loops as a declared transformation, retain failure/parameter records. |
| random_planar | G2's full shuffled-edge greedy planar construction at the proposed N | G2:427; predeclare a generation cap, initially 1800 s per graph. Timeout yields GENERATION_TIMEOUT, not a partially generated replacement. |
| spin_glass | `gen_spin_glass(N,p,'bimodal',seed)`, `p={.1,.2,.3}`; separate p=1 panel where count bounds permit | G2:663; sparse adjacency is ER. Weights and p=1 RNG draws do not create new embedding structures. Link complete and ER duplicates across families. |
| weak_strong_cluster | `cluster_size={8,16}`, `n_clusters=N/cluster_size`, `inter_edges_per_cluster=1` | G2:690; values divide all proposed N. An optional inter-edge `{2,4}` panel is an explicit parameter extension. Duplicate random inter-edges may reduce actual edge count. |
| planted_solution | `gen_planted_solution(N, topology, seed)`, topology in `{chimera,pegasus,zephyr}` with G2's exact parent-size formulas | G2:739; report parent topology/size and the sampled vertex set privately to the evaluator. This concerns source graph generation; every embedding target remains ideal Z12. |
| complete | Enumerate `K_N` for integer N=33…303; stratify by actual size after removing all inherited equivalent structures | G2:135; dense spin-glass copies are the same source. N=304 violates the Z12 edge bound. No random graph seeds. |
| bipartite | `K_(a,ra)`, a=8…80, r in `{1,2,3}` | G2:139 and CSV:85–94; normalize part swap, link balanced r=1 cases with Turan r=2. |
| cycle | `cycle_graph(N)`, all integer N=64…512 | G2:150; unseen lengths only, after cross-family identity checks. |
| path | `path_graph(N)`, all integer N=64…512 | G2:154; an ordering or label shuffle is a robustness replicate, not a new path. |
| star | `gen_star(N-1)`, integer actual N=64…512 | G2:158 takes leaf count, not total vertices. |
| wheel | `gen_wheel(N-1)`, integer actual N=64…512 | G2:163 takes rim count. Keep the N versus N−1 conversion explicit. |
| grid | m=4…24, n in `{m,m+1,2m,3m}`, open boundary for the primary comparable panel, actual vertices<=512 | G2:144; remove transpose equivalence. A periodic panel is separately labeled if absent from the inherited grid distribution. |
| circulant | N=17…512 and offset sets `{(1,2),(1,3),(2,4),(1,2,3),(1,3,5),(2,4,6),(1,2,3,4)}`, with N>2max(offsets) | G2:198, CSV:123–130; offset sets can produce isomorphic or disconnected graphs. Do not condition on connectedness. |
| generalized_petersen | outer-ring size a=8…256, k=1…min(10,floor((a−1)/2)); actual N=2a | G2:239; remove k↔a−k and other detected isomorphisms, including named graphs. |
| turan | `turan_graph(N,r)`, N=33…256, r=2…8 | G2:192; require N>r; link bipartite r=2 and other exact duplicates. |
| hypercube | Enumerate Q2…Q12 as the original finite census | G2:181; all are inherited already. Q13 exceeds the vertex bound. No nontrivial unseen structure remains in this original eligible range. |
| binary_tree | Balanced binary depths 1…11 as the original finite census | G2:169; all are inherited. Depth12 exceeds the vertex bound; new random trees are a different family. |
| tree | Balanced `(branching,height)` with branching 2…20, height 2…5, then count bounds; separate the new branching>=6 panel | G2:175, CSV:146–151; inherited range uses branching2…5. Binary cases share structures with binary_tree. A random Prüfer tree is not this family's generator. |
| johnson | Enumerate J(a,k), a=5…24, k=2…floor(a/2), checking `C(a,k)` vertices and `C(a,k)*k*(a−k)/2` edges | G2:207; complement parameters k and a−k are isomorphic. Examples worth checking for novelty include J(12,6), J(13,6); no assertion they are fresh or embeddable. |
| kneser | Enumerate KG(a,k), a=5…24, k=2…floor(a/2), checking `C(a,k)` vertices and `C(a,k)*C(a−k,k)/2` edges | G2:223; k>=5 extends the old CSV range. KG(2k,k) is a matching, so many labels/parameters provide little independent difficulty. |
| triangular_lattice | m=3…12, n in `{6,8,…,24}`, periodic false/true, actual vertices<=512 | G2:471; count actual NetworkX boundary vertices. Do not use the CSV approximate mn count. |
| honeycomb | m=3…12, even n in `{4,6,…,24}`, periodic false/true, actual vertices<=512 | G2:481; periodic requires even n>1,m>1. Boundary and transpose equivalences need audit. |
| kagome | Line graph of the preceding honeycomb parameter grid, actual vertices<=512 | G2:532; source vertices are honeycomb edges. Preserve the construction definition and strip coordinate hints. |
| king_graph | m=8…20, n in `{m,m+1}`, periodic false/true | G2:503; rectangular n=m+1 is an explicit unseen-parameter extension. |
| frustrated_square | The identical king-graph panel with a second family membership | G2:522; never split matching instances or count them as independent family evidence. |
| shastry_sutherland | If retained as a repository-defined family: m=6…20, n in `{m,m+2}`, periodic false/true, actual vertices<=512 | G2:544; freeze the actual edge rule and flag the physical-name mismatch above. A corrected orthogonal-dimer graph requires a separately reviewed supplement. |
| cubic_lattice | Open/periodic `(x,y,z)` with x=3…8, y in `{x,x+1}`, z in `{x,x+2,2x}`, actual vertices<=512 | G2:491; normalize axis permutations. This introduces explicit rectangular aspect ratios beyond the old cube/ratiometric subset. |
| bcc_lattice | Original open cubes m=2…12 are a finite inherited census; periodic labels add no new structure | G2:576. Correct periodic BCC or rectangular boxes would be separately labeled supplements, after correcting and testing the edge definition. |
| hardware_native | Census of all original C1…C16, P2…P14 and Z1…Z12 passing Z12 count bounds | G2:777 and manifest; those eligible scales are inherited. A randomized induced graph belongs to the planted-source supplement, not a fresh full hardware-native instance. |
| named_special | Census of the original 12 named structures with exact hashes | CSV:388–393. Extra registered names may define an explicitly extended catalogue, but some are generalized-Petersen/circulant aliases; do not replace this finite family with random regular graphs. |
| sudoku | Corrected supplement with explicit NetworkX order q in `{2,3,4,5}` | G2:251 / NX Sudoku:51; reserve q=2,3 for development of the supplement, q=4 for a frozen confirmation opportunity, and q=5 for separate size extension. Four fixed graphs do not provide a stochastic graph population. |

These parameter pools specify what to generate, not which instances to keep based
on either embedding algorithm's performance. Within new deterministic pools,
actual count bounds, duplicate membership and hash partitioning select the split;
there is no search for inputs where the candidate already looks favorable.

## Sudoku: corrected sizes, scope, and feasibility

For box order q, the cell graph has `q^4` vertices and degree
`3q^2−2q−1`: row and column contacts contribute `2(q^2−1)`, and the additional
same-box contacts contribute `(q−1)^2`. Thus:

| Order q | Board side | Vertices | Edges | Count-bound status |
| --- | ---: | ---: | ---: | --- |
| 2 | 4 | 16 | 56 | passes |
| 3 | 9 | 81 | 810 | passes |
| 4 | 16 | 256 | 4992 | passes |
| 5 | 25 | 625 | 20000 | passes |
| 6 | 36 | 1296 | 61560 | exceeds Z12 edge count |

The CSV's 5440 edges for the 16×16 board is also inconsistent with this definition.
Do not modify original Sudoku IDs 37900/37901. Give corrected instances new
supplement IDs, `box_order`, `board_side`, generator version and actual graph hashes.

Orders 2 and 3 are the sensible small feasibility checks; their count-bound pass
is not itself a proof of an embedding. Obtain a separately validated witness or
mathematical construction before describing an order as Z12-feasible. Preserve
all predeclared order outcomes, including failures at 4 or 5; do not select a
Sudoku claim by whichever order succeeds. A supplied witness is evaluator-only,
never initialization or an input hint for either compared algorithm. Changing
Sudoku clues does not change this fixed cell-conflict graph, so different puzzles
are not independent structures here. A one-hot QUBO encoding would be a different
source family and must not be substituted silently.

## Structural novelty checks and failure ledger

Before labeling a structure clean, check it against **all inherited sources**,
including 167 legacy `test_graphs/` files, the 31,149-entry manifest, archived custom
pilot inputs, all new development/validation inputs, and every previously exposed
confirmation set. The current 012 normalized-hash index covers only its verified
subset, so it cannot certify absence from that universe.

Use full unweighted source hashes, exact deterministic relabeling, and known
analytic equivalences first. Bucket possible remaining matches by actual n/m,
degree multiset, component-size multiset and similar cheap invariants. A correctly
computed WL invariant can rule out matches when values differ; equal values do
not prove isomorphism. Perform exact isomorphism/canonical-label checks within
unresolved buckets, with
certificates and tool/version records. Large symmetric families may need analytic
canonical parameter rules. A timed-out isomorphism comparison is unresolved,
not a new independent source. Keep duplicates together across **family labels**.

A complete inherited identity index is not currently available. Some original
files are missing. Use source acquisition/regeneration audits as a prerequisite
for clean confirmation, not a reason to silently assume no collision. When an
unavailable source could match a proposed test graph, its novelty remains
unresolved unless a structural argument excludes the match. This note does not
authorize downloading or regenerating the corpus now.

For each predeclared generator attempt record parameters, generator seed,
generator/dependency hashes, actual counts, canonicalization state and one of:
READY_NEW, DUPLICATE_INHERITED, DUPLICATE_SAME_SPLIT, CROSS_SPLIT_DUPLICATE,
GENERATION_ERROR, GENERATION_TIMEOUT, INVALID_GENERATOR_OUTPUT,
COUNT_BOUND_EXCLUDED, or NOVELTY_UNRESOLVED. Save attempted and usable counts per
family/size/parameter cell. Decide any fixed reserve-seed schedule before generation;
do not tune a generator on final-set failures or silently refill until a favorable
sample appears. A conditional-on-generation-success distribution needs that exact
label and a reported generation-success rate. Input failures are separate from
embedding failures and cannot disappear from coverage.

## Freeze the algorithm and the statistical claim

One global algorithm implementation/configuration must serve every family. The
solver receives only sanitized source adjacency, the exact Z12 target and its
declared random seed/time budget. Family, ID, generator parameters, coordinates,
file paths, split identity and known embeddings are evaluator-side metadata.
Audit dispatch conditions, imported/native dependencies and external file reads.
Generic structural decisions such as degree-dependent moves can be legitimate;
a family recognizer, graph hash table or best-of-method dispatch violates the
single-algorithm design. Source permutation/metadata controls should be fixed
before confirmation and repeated on unseen examples.

Freeze one global budget or explicit input-size-only budget function calibrated
solely on development, including cold/warm policy, construction, repair, all
unsuccessful search, and overall timeouts. Do not assign a graph's candidate budget
after observing its test-time MM runtime. Pair runs on the same machine, interleave
method order independently of outcome, limit threads, and record contention.
Report stock MM, equal-time curves, and the separately declared stronger MM
configuration; they answer different comparisons.

Follow PLAN_CODEX's success/quality requirements. All scheduled solver trials
remain in the denominator. Record both-success, candidate-only, MM-only, neither,
invalid, crash and timeout outcomes. Common-success ACL is conditional; unqualified
mean-ACL improvement requires complete common coverage of the declared comparison
set. Mean ACL, solver-seed variance, within-chain variance and all-trial
success-quality curves are separate quantities. ACL=1 ties are certified optimal
ties, never strict wins. A tie on one graph does not settle its family.

Inference uses independent source structures as the sampling units, with solver
seeds nested within source and machine blocks preserved. Shared structures carry
one observation across family memberships; do not use 36 independent-family
assumptions. Predeclare per-family size/parameter weights. A pooled advantage is
not an all-family result; missing, inconclusive and losing cells remain explicit.

The plan requires no observed family success regression and a one-sided bound on
candidate excess failure below one percentage point. The nominal 30-graph/10-seed
starting design is unlikely to establish that tight bound. For illustration, even
an optimistic IID zero-event calculation for the sufficient event “candidate
fails while MM succeeds” needs **793 independent graph draws per family** to put
its probability below 1% at a Bonferroni level `(0.025/2)/36`. This is an exact
zero-event binomial calculation, not a power analysis for the actual hierarchical
experiment; correlated solver seeds do not supply that many independent graphs.
For a completely enumerated finite catalogue, one may instead estimate algorithm
randomness conditional on that fixed catalogue, explicitly limiting the claim.

Keep the plan's confirmation-attempt spending
`alpha_k = 0.05 / (k*(k+1))`. Within an attempt preallocate error to quality and
reliability endpoints and use a declared simultaneous procedure for separately
advertised family claims. Distinguish an intersection/conjunction claim from many
separate discoveries. Fresh test graphs do not eliminate repeated-until-significant
selection. Choose sample sizes using validation only, complete the frozen attempt,
and independently replicate a successful frozen version before a broad claim.

## Self-critique and decision limits

1. **Some original finite families have no useful unseen structure.** Hypercubes,
   binary trees, original BCC cubes, hardware-native scales, and named graphs
   require descriptive censuses or explicitly expanded families. A universal
   clean-holdout claim across all 36 original catalogues is therefore unavailable
   simply by choosing fresh seeds. This does not excuse losing on those catalogues.
2. **Generator defects can undermine a scientific family label.** Reproducing a
   repository graph faithfully is different from validating a physical model.
   Sudoku needs a corrected supplement; Shastry–Sutherland needs an edge-rule
   decision; BCC periodicity needs correction before that parameter means anything.
3. **Near-128 readiness graphs are not a final population.** The proposed split
   grid broadens sizes and structural parameters but remains a declared restricted
   distribution. Near-capacity regimes need separate adequate sampling and budgets.
4. **Novelty indexing is real work.** Exact hashes alone miss isomorphisms, and
   missing inherited files prevent a blanket clean-data claim. Identity-unresolved
   cases must stay unresolved rather than becoming convenient new test samples.
5. **Reliability, multiplicity and selective failure are likely sample-size
   bottlenecks.** A visually consistent ACL advantage on a small screen can still
   fail the confirmation criteria. Do not weaken those criteria after seeing
   final results; revise a future protocol openly and preserve the previous attempt.

Current next step: continue development on 012/017, review/freeze the generator
definitions independently, and build the inherited structure-identity ledger.
Only then generate a protected final set for one frozen algorithm. No part of
this proposal establishes that the present algorithm generalizes or beats MM.
