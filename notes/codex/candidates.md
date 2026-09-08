# Independent algorithm hypotheses

Date: 2026-09-07. This list was formulated and shown to the user before reading
existing handoff notes, paper drafts, or algorithm source. These are research
hypotheses, not claims of novelty or performance. Literature and repository audits
may reject or combine them. Every candidate receives an initial critique here
before any implementation. Later revisions must preserve this starting point.

All candidates construct disjoint connected branch sets representing every logical
vertex and realize every logical edge through a physical coupler. No candidate may
invoke MinorMiner, its forks, or busclique, including initialization, completion,
repair, polishing, cached embeddings, or hidden dispatch. An independently
implemented version of an established idea is not automatically novel.

## 1. Capacity-priced Steiner routing

Repeatedly construct a logical vertex's chain as an approximate node-weighted
Steiner tree touching neighboring chains. Update physical-qubit prices using both
congestion and marginal total chain length. Jointly update a few interacting trees
when single-chain steps stall.

**Hypothesis:** adaptive prices and coupled updates use scarce couplers more
efficiently across varied logical degree distributions.

**Self-critique:** weighted shortest-path chain construction is established prior
art, including CMR/MM. A new price schedule alone is a weak novelty claim. Feasible
embeddings may not emerge after overlap is penalized. Retain only if a distinct
coupled optimization step improves a simple independently built baseline.

**First discriminating experiment:** compare independent routing with and without
coupled updates on sparse and dense held-out development instances at equal time.

## 2. Negotiated congestion with joint chain updates

Allow temporary branch-set overlap during construction. Identify a conflict region,
remove its affected chains, and solve their routes together using historical
congestion costs. Only independently validated feasible incumbents are returned.

**Hypothesis:** grouped rerouting resolves bottlenecks that sequential chain updates
cannot escape, reducing success-conditioned ACL without reducing success rate.

**Self-critique:** this closely resembles negotiated routing in other fields and
MM's overlap minimization. Feasibility repair may erase apparent gains. The joint
update and its empirical benefit must distinguish the method from prior art.

**First experiment:** measure conflicts resolved per unit time, final valid ACL,
and success, not the chain length of overlapping intermediate states.

## 3. Multilevel embedding

Contract selected logical edges into a hierarchy, place the coarse graph, then
split connected physical regions while restoring fine-level edges. Refine the
placement and chains after each expansion.

**Hypothesis:** a global coarse layout avoids poor local minima and shortens
inter-region routes.

**Self-critique:** contraction can inflate effective degree and coarse chains may
not split into feasible fine chains. A coarse embedding need not be extendable on
the same finite target. Require an explicit expansion procedure with rollback and
compare edge contraction rules; do not infer feasibility from the coarse graph.

**First experiment:** diagnose coarse capacity, expansion failure, and resulting
ACL on clustered graphs versus expanders.

## 4. Separator-based embedding

Partition the logical graph using small vertex separators. Allocate physical
regions with explicit boundary capacity; embed pieces and optimize separator chains
and cross-region contacts jointly.

**Hypothesis:** structured sparse graphs benefit from short local chains and
limited global routing.

**Self-critique:** dense and expanding graphs have poor separators. Hard partition
boundaries can waste target capacity. This is likely one component of a general
method rather than a universal constructor; include a degradation detector.

**First experiment:** relate gains to measured separator size and compare against
unpartitioned placement without graph-family labels.

## 5. Zephyr-aware chain templates

Derive short connected chain shapes directly from the actual Zephyr graph. Optimize
their positions, orientations, lengths, and selected coupler contacts while allowing
local departures from the template where useful.

**Hypothesis:** exploiting repeated local structure lowers construction cost and
avoids needless chain growth.

**Self-critique:** restrictive shapes may impose an ACL floor well above optimum;
this must be distinguished from busclique and existing structured embedding
methods. Never import their constructors or cache output. Derive and validate
templates from the target graph, including removed nodes/edges when supported.

**First experiment:** compare template-only versus independent free-form local
repair, especially on graphs where ACL 1 is attainable.

## 6. Connected-region optimization

Represent chains as disjoint connected regions. Move or exchange boundary qubits,
contract redundant branches, and grow one chain while shortening a neighbor,
maintaining logical edge contacts.

**Hypothesis:** jointly changing contact locations gives improvements unavailable
to independent chain pruning.

**Self-critique:** valid local moves can be rare; maintaining connectivity and edge
witnesses may cost more than the improvement. Local optimality says nothing about
global embedding quality. Begin with rigorously checked small-region moves.

**First experiment:** compare deletion-only pruning, contact exchange, and grouped
boundary reoptimization on identical independent initial embeddings.

## 7. Edge-demand placement and routing

Place vertices with attention to incident edge demand and physical coupler supply.
Co-optimize representative locations, neighbor contacts, and connected chain growth;
share segments within a chain but never between different final chains.

**Hypothesis:** edge contacts convey more useful information than vertex distance
alone on hardware with structured coupler patterns.

**Self-critique:** independently optimizing edge routes can create disconnected
branch sets, collisions, or bad global bottlenecks. A placement surrogate can rank
embeddings incorrectly; evaluate actual chains and validation after routing.

**First experiment:** compare surrogate predictions to actual ACL and success;
reject surrogate changes that do not transfer to final embeddings.

## 8. Local exact repair

**Disposition after user prompt 4:** tiny diagnostic oracle or optional bounded
subroutine only. An IP-led constructor is excluded. The intended heuristic must
operate roughly within an order of magnitude of MM's runtime, not obtain low ACL
through effectively unrestricted exact optimization.

Select interacting chains and a bounded physical region. Freeze the remaining
embedding and solve assignment, connectivity, and required contact constraints
with an exact integer/constraint solver. Keep a valid incumbent if interrupted.

**Hypothesis:** exact local reoptimization breaks greedy plateaus while restricting
the otherwise large exact embedding problem.

**Self-critique:** an initial independent constructor is required; formulation size
and solver overhead may dominate. Optimality is only within the chosen region,
unless a global proof exists. Existing integer-programming embedding literature
must be checked. Include setup and solve cost in time comparisons.

**First experiment:** exhaustive small-graph agreement, then fixed-size repairs
with time limits and logged best bounds on real failing development instances.

## 9. Adaptive large-neighborhood search

Choose expensive chains or local bottlenecks, remove several branch sets, rebuild
them jointly, and adapt selection based on improvement per unit of compute.
Retain a separately stored valid incumbent throughout.

**Hypothesis:** occasionally revising multiple chains escapes representation and
contact constraints that defeat incremental shortening.

**Self-critique:** the method can plateau or spend most time reconstructing
feasibility. Operator adaptation may overfit instance identities. Use general
features, deterministic seeds, and held-out instances; an operator portfolio alone
is not an adequate novelty claim.

**First experiment:** compare fixed versus adaptive neighborhoods at matched total
time, with trajectories of best valid ACL and reconstruction success.

## 10. Tree-decomposition-guided embedding

Build a logical tree decomposition, allocate physical regions and interface states,
and combine partial embeddings through dynamic programming with bounded states or
beam search. Repair difficult interfaces using independent local routing.

**Hypothesis:** low-width regions admit globally coordinated short chains.

**Self-critique:** large treewidth makes state spaces explode, and a small logical
bag can have many physical realizations. Approximation weakens guarantees. Retain
as a structural component only if interface-state compression is effective.

**First experiment:** compare runtime and ACL as width grows; terminate the line if
even small-width cases cannot beat simpler placement within useful budgets.

## 11. Replica-exchange search over embeddings

Maintain multiple embedding states with different overlap and chain-length
penalties or exploration temperatures. Exchange states and use validated feasible
incumbents to track progress; supply explicit reversible or well-characterized
proposals if equilibrium claims are made.

**Hypothesis:** exchanges escape deep local minima and reduce run-to-run variation.

**Self-critique:** this can multiply compute without improving quality. Useful
chain moves are a prerequisite, and heuristic exchanges must not be described as
correct sampling without proof. Count all replicas' CPU time, memory, and cores.

**First experiment:** compare against the same number of independent restarts at
equal aggregate compute and equal wall time.

## 12. Feature-guided algorithm portfolio

**Disposition after user prompt 2: excluded.** Preserved only to document the
independent brainstorm. The user requires one non-portfolio algorithm. Do not
implement independent-algorithm selection, whether parallel or sequential. One
algorithm may construct and refine its own evolving embedding; this cannot disguise
an ensemble of independently competing embedding methods.

Use size, density, degree distribution, separator estimates, and measured progress
to allocate a shared budget among eligible independent constructors and improvers.
Select the best independently validated result.

**Hypothesis:** complementary methods can achieve strong class-wide performance
without requiring one mechanism to suit every structural regime.

**Self-critique:** selection is not itself a compelling standalone novelty claim.
Graph labels and instance identities invite leakage; training has a cost. The
portfolio must exclude MM, forks, busclique, and their cached outputs entirely.

**First experiment:** compare fixed, feature-selected, and all-method portfolios
on an untouched holdout; charge dispatch, all attempted methods, and selection.

The preceding proposed experiment is withdrawn by the user's clarification.

## Initial implementation discipline

Shortlist three to five mechanisms after code, benchmark, and literature audits.
Write an additional critique for every substantively new combination before coding.
Use small falsifying tests before broad cluster runs. A rejected method receives a
permanent failure note with budget, data hashes, evidence, and transferable lessons.
No finite experiment establishes universal superiority over all possible graphs;
the goal must be evaluated against a declared graph-family distribution and target.
For nonempty logical graphs ACL is at least 1, so a baseline at that bound cannot
be strictly improved; such ties must be reported honestly.
