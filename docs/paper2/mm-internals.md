# minorminer internals — what the shipped program actually does

Source-verified reference for minorminer **0.2.22**, the version installed from pip
and the base of our fork. Chronological findings live in `notes.md` (§3.8, §3.14,
§3.15, §3.17); this file is the organized state. The 2014 CMR paper
(arXiv:1406.2741) is a *sketch* of this program, not a specification — several
load-bearing mechanisms below appear nowhere in it (§"paper-vs-program" table).

**House rule: verify every claim about minorminer against this source, never the
paper.**

## 1. Provenance & how to verify

- `external/minorminer-fork` — git clone of `dwavesystems/minorminer` (Apache-2.0),
  checked out at tag **0.2.22** (`git describe --tags` → `0.2.22`), the same release
  as the installed pip package. The algorithm is header-only C++ in
  `include/find_embedding/*.hpp`.
- The working tree carries **our fork patch applied on top** (`scripts/mm_fork.patch`:
  the `var_order=` and `history_alpha=` switches, plus — since paper3 P4/P6,
  2026-07-26 — `short_audit=`/`audit_budget=`/`dirty_skip=` and
  `chain_tree=`/`root_boltzmann=`; ~450 inserted lines in `embedding.hpp`,
  `embedding_problem.hpp`, `pathfinder.hpp`, `util.hpp`, and the Cython bindings).
  Every switch is parity-guarded: defaults are byte-identical to stock (same
  embeddings, same RNG stream), enforced by the build self-test,
  `tests/algorithms/test_mmfork_history.py`, and `tests/algorithms/test_p3_fork.py`.
  Line numbers cited below refer to the patched working tree; in patched files they
  may sit noticeably off from pristine 0.2.22 (pathfinder.hpp grew ~250 lines).
- To re-verify a claim: `grep -n <symbol> external/minorminer-fork/include/find_embedding/*.hpp`.

## 2. Program structure

`find_embedding` drives a pathfinder object whose `heuristicEmbedding()`
(`pathfinder.hpp:623`) runs up to `tries` restarts of a pass loop built from four
pass types:

| pass | where | job |
|---|---|---|
| `initialization_pass` | `pathfinder.hpp:233` | build all chains once, overlaps allowed |
| `improve_overfill_pass` | `pathfinder.hpp:247` | reroute to reduce max qubit overfill |
| `pushdown_overfill_pass` | `pathfinder.hpp:262` | squeeze overfill with `target_chainsize=0` rebuilds |
| `improve_chainlength_pass` | `pathfinder.hpp:301` | post-legality chain shortening |

Facts that repeatedly surprised us:

- **`tries` are feasibility restarts that stop at the first success** — they do not
  re-roll for quality. Paper 1's fork probe measured `tries` ∈ 1..10: identical ACL
  and wall-clock on instances that legalize first try (notes §3.6 correction).
- Every rebuild funnels through two sites: `find_chain`
  (`pathfinder.hpp:199` dispatching to `:357`) during legalization, and
  `find_short_chain` (`pathfinder.hpp:388`) during shortening.

## 3. Search primitives — the Dijkstra question, resolved

Recurring confusion ("does minorminer ever run Dijkstra like the paper says?").
The precise answer has two halves:

1. **Legalization: yes, vanilla node-weighted Dijkstra.** The per-neighbour
   root-distance searches are an explicit priority-queue Dijkstra over qubit weights
   (`pathfinder.hpp:496-525`; the code comment at `:507` calls it "a vanilla
   implementation of node-weight dijkstra"). The header comment at `:43` claims
   Dijkstra is "responsible for 99% of our runtime" — **that claim is stale**: §3.15
   measured the legalization phase at ~5–15% of wall-clock on benchmark workloads.
2. **Shortening — where 85–95% of the time actually goes: no.** `find_short_chain`
   (`pathfinder.hpp:388-450`) expands one search per neighbour chain **through free
   qubits only at unit weight** (`d += 1` per hop, `:433`) — synchronized
   ("lockstep") BFS balls despite using a distance queue. Every free qubit reached
   by all k balls is a candidate root, visited in increasing radius; at **every**
   candidate it constructs the full Steiner chain, measures the *actual* length, and
   tears it out unless strictly better (the "exhaustive audition", notes §3.17). It
   early-exits only on strict improvement and abandons at radius > current chain
   length. The audit exists because the legalization-phase estimate (sum of root
   distances) misranks Steiner trees (trunk sharing).

So: weighted Dijkstra lives in the phase that legalizes; localized unit-weight
search + Steiner construction dominates the phase that costs. A native shortener
should therefore use plain BFS, not a heap.

**Chain construction** (`embedding.hpp`):

- `construct_chain_steiner` (`embedding.hpp:198`) is the **only** constructor ever
  called (`pathfinder.hpp:377` in `find_chain`; `:422` in `find_short_chain`).
  Nearest-attach Steiner build: first neighbour's path grows from the root; each
  subsequent neighbour attaches at the nearest node of the current chain, with
  attach candidates restricted to root/branch nodes (`refcount > 1`) — a mild
  variant of Takahashi–Matsuyama SPH.
- `construct_chain` (`embedding.hpp:180`) — the union-of-independent-shortest-paths
  build that the 2014 paper describes — is **dead code**: defined, documented, never
  invoked. Its successor's own comment (`:197`): the Steiner build "has an
  opportunity to make shorter chains than `construct_chain`".
- The group-Steiner→Steiner contraction (connect to a *chain*, not a vertex) is
  implemented in the Dijkstra seeding: every qubit of a neighbour's chain is seeded
  at distance 0 with `parent = -1` (`pathfinder.hpp:459` region), and `link_path`
  (`chain.hpp:333`) walks parents until it lands inside the neighbour's chain.

## 4. Cost machinery

- Qubit prices come from a **precomputed exponential weight table** with exponent
  capped at 63 and an `exponent_margin` overflow-scaling mechanism
  (`embedding_problem.hpp:222, 244-265, 288-310`): scaled prices saturate at
  `max_distance / exponent_margin`, keeping path sums overflow-free in int64.
- The base is **not** `diam(G)`: `max_beta` defaults to "effectively infinite"
  (`util.hpp:134`: `numeric_limits<double>::max()`, realized via the capped table).
  Consequence: **overlap is priced lexicographically-hard** — any occupancy level
  dominates any path length — rather than at the paper's `D`-per-level exchange
  rate. (Why our replica's `beta = D̂` corner is *not* the shipped program; and why
  a multiplicative history factor `(1+h)` can only reorder qubits *within* an
  occupancy class, notes §3.13.)
- All pricing flows through one site: `compute_qubit_weights`
  (`pathfinder.hpp:527-537`) — which is where the fork's `history_alpha` multiplies
  in `(1 + h_q)`, and where any future cost experiment should plug in.

## 5. Randomization channels (none of these are in the paper)

- **Vertex order is re-shuffled every pass**: `var_order()`
  (`embedding_problem.hpp:366-408`) shuffles then optionally re-orders by one of
  five strategies (SHUFFLE, DFS, BFS, PFS, RPFS). The paper randomizes once per
  restart. (The fork's `var_order=` switch supplies a fixed order via
  `params.fixed_var_order`, `:374`.)
- **Neighbour-visit order inside searches is randomized**: `shuffle_first` /
  `rndswap_first` tags (`embedding_problem.hpp:202-203`, used at `:317-324`) —
  randomized tie-breaking at the path level.
- **Root choice is uniform among the exact-minimum tie set**: `collectMinima`
  (`pathfinder.hpp:372`) then a `randint` pick. The paper proposes (but nobody
  shipped) a Boltzmann-weighted root choice.
- Restarts (`tries`, default 10) complete the diversity stack.

Why it matters: this randomness does **feasibility** work, not just quality work —
our deterministic replica with none of it deadlocks on instances stock solves in
milliseconds, and history-as-memory only partially substitutes (§3.6, §3.9, §3.10).
Randomness and cross-pass memory are substitutes; MM has the former, so adding the
latter is inert inside real MM (§3.13, the history 2×2).

## 6. Measured economics (notes §3.15–§3.17)

- **85–95% of wall-clock is the post-legality shortening phase**
  (`improve_chainlength_pass` / `find_short_chain`), which earns a consistent
  ~30–38% ACL reduction. Legalization is cheap and scales mildly. MM's economy:
  legalize fast and dumb, then spend 10× that budget polishing.
- **Legal-stage ACL carries no information about polished ACL** (§3.16, r ≈ 0
  pooled): the grind washes out the starting basin (measured on ER; untested on
  structured sources).
- **`threads` is a no-op at benchmark scales**: the parallel pathfinder covers only
  the legalization-phase root-distance computation.
- The expensive part of the shortener is the audition, not the search: cost peaks
  exactly when no improvement exists (~10 failing full sweeps before
  `chainlength_patience` expires). Candidate fork switch: `short_audit` —
  estimate-only or budgeted audition (§3.17), aimed at the 90% slice.

## 7. Paper-vs-program deltas (the running list)

| 2014 paper says | shipped 0.2.22 does | where |
|---|---|---|
| union of independent shortest paths | nearest-attach Steiner tree; union constructor is dead code | `embedding.hpp:180,198` |
| weight `diam(G)^occ` | capped exponential table, `max_beta` effectively infinite (lexicographic overlap) | `embedding_problem.hpp:254-265`, `util.hpp:134` |
| random vertex order per restart | re-shuffle every pass + five order strategies | `embedding_problem.hpp:366` |
| root = argmin (Boltzmann variant proposed) | uniform among exact-minimum ties | `pathfinder.hpp:372` |
| (no shortening phase described) | shortening = 85–95% of runtime, lockstep BFS + exhaustive audition | `pathfinder.hpp:388` |
| Dijkstra as the engine | true in legalization; the dominant phase is unit-weight BFS | `pathfinder.hpp:507` vs `:433` |
| `tries` as quality restarts (common reading) | feasibility restarts, stop at first success | `pathfinder.hpp:623` region |

## 8. Fork hooks (for future switches)

- Pricing: `compute_qubit_weights` (`pathfinder.hpp:527`) — single site; history
  `(1+h_q)` multiplies here.
- History update: end of each pass type, where occupancy is globally consistent;
  `h` lives on the pathfinder object (persists across passes *and* tries; reset per
  `find_embedding` call).
- Order: `params.fixed_var_order` (`embedding_problem.hpp:374`).
- Tree ablation arm: revive `construct_chain` behind a switch (the *dumber* union
  build — "what does MM's Steiner trick buy?", §3.14). **Built** (paper3 P6):
  `chain_tree=` 1 = union, 2 = pure SPH (attach filter dropped), dispatched at both
  construct sites; plus `root_boltzmann=` (the 2014 paper's unshipped root rule).
- Shortener economics: audition policy in `find_short_chain` (`short_audit`, §3.17).
  **Built** (paper3 P4): `short_audit=` 1 estimate-only / 2 budgeted (`audit_budget=`),
  and `dirty_skip=` (fingerprint-tracked negative cache in the chainlength phase).
  As-built details: `docs/paper3/proposals/{shortener,anatomy}.md`.
