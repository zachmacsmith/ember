# B030 implementation and focused check

2026-09-10. The isolated implementation is ready for root's source review.
No complete constructor, development instance, remote worker or registry change
was executed for this work. The [exact contract](b_030_exact_contract.md) remains
the policy; the earlier contact-only draft stays explicitly withdrawn.

- `disconnected_ownership_construction.py`: the new state, fair schedule,
  patch/label/merge proposals, exact Q/M/D/P energy, acceptance, deadlines and
  incumbent handling. SHA256
  `23ab3ee3cbff777ff9752c5ed56d4660246701a3265023d98cec97024cfe7990`.
- `disconnected_ownership_arrays.py`: actual-adjacency translation filtering,
  proposal sampling and exact hardware-distance fields keyed by immutable site
  sets within one target/call. SHA256
  `84649f438258bfcbf7a3b24a1c692e0d95eed93afb89893aad1e796a899ae793`.
- `scripts/codex/b030_risk_check.py`: the approved rail fixture and its
  cache/MST/ablation/rollback checks. SHA256
  `85aa7c29d33d06d3fd0da0b13bc82bdc8bd967679413c0a9ad57a7d3174d4978`.

The candidate reuses only the existing B028 meter/adjacency reader and unchanged
`validation.py`. It does not call B028's constructor or router. NumPy/SciPy
imports, sparse-target packing and lazy unweighted distance searches occur inside
the call clock. The distance cache has no work/entry cap and belongs to one
target; memory and discarded computation remain costs. Labels and immutable
owner sets are reconciled before publication. The incumbent has its own original
graph certificate; the existing external audit still owns benchmark credit.

One pre-check clarification stops immediately at a certified Q=n incumbent,
the exact lower bound for nonempty disjoint owners. It is not an empirical work
limit. Heavy operations check the deadline before and after completion; an
overrun cannot supply a credited map. Slots preserve scalar before/proposed/after
energy and time, including interrupted work. Detailed changed-site traces contain
only the first sixteen and last; they are not complete site-level trajectories.
Every valid incumbent admission is retained. Whole-call CPU and per-slot CPU
are recorded; phase CPU is not separately imputed from phase wall.

**First focused execution: PASS**, three check groups, no errors, retries,
source changes or prohibited import attempts. The cold check process took
1.158517 s; its recorded program wall/CPU were 0.994162/0.783596 s. This is
correctness-check cost on the local host, not a constructor or MM comparison.

The actual rail patch moves two labels onto an image overlapping its origin.
It preserves the source contact at Q3 but fragments U, giving P(U)=1; the
unchanged independent oracle rejects it. The actual free target graph has one
least-cost bridge in this fixture. The kernel's cost and rank-selected path
match that independently enumerated bridge, restoring validity at Q4. The
test does not assume that the named b site is the only possible bridge in
general. A third-component extension checks the MST against all three component
spanning trees; direct BFS fields verify old/new cache identity. The connected
ablation and interruption immediately before publication preserve the entry.
These checks establish accounting, not successful compaction: this fixture
deliberately exhibits the expensive-reconnection risk.

Evidence: `results/codex/b030-constructor/check001/`. Its before-execution manifest
binds eleven source/contract/original-oracle/public-target inputs, SHA256
`769dd566b0f35f45a8b2d396a028f5fe6a3d706bcec4f88f38d6e3f27fd07ad3`.
`invocation.json`, `completion.json`, `stdout.txt`, `stderr.txt` and `summary.json`
preserve the one execution. No private known-embedding witness or MM map was read.

Remaining: root reviews source, registers the two entrypoints `ownership_embed`
and `connected_embed`, freezes the six-encoding/two-seed/four-arm experiment and
owns the cluster launch. No additional local performance gate or solver campaign
is proposed. The 48 complete calls must decide whether temporary fragmentation
and patch transport produce timely, low-Q complete minors, rather than only
more contacts or lower geometric debt.
