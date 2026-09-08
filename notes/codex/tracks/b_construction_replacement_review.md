# Replacing B's sequential construction

2026-09-08. **Select a small movable-contact experiment next; design only.** No source change, solver, corpus replay or cluster action was performed. B017 and its failed local gates remain unchanged.

[B009](b_009_results.md) exposes a quality problem as well as failed insertion. Its 846 matching queries all completed; stronger singleton feasibility did not prevent three failed inputs or excess qubits on four completed inputs. [B011](b_011_results.md) preserved all six complete qubit totals. These are individual exposed seed-0 inputs, not graph-family means or ACL-variance estimates.

| B009 outcome | Candidate Q | Contemporary MM Q |
| --- | ---: | ---: |
| Bipartite / regular | 330 / 110 | 180 / 90 |
| Watts–Strogatz / king | 133 / 128 | 94 / 90 |
| Grid / honeycomb | 64 / 70 | 70 / 71 |
| K40 / K100 / ER | Failed | 194 / late / 211 |

The four completed losses use 22–83% more qubits. Their measured runtime ratios are 5.76–18.76× MM, with the documented host-load qualification. The evidence therefore supports reconsidering placement and chain allocation, not just extending repair reach. It does **not** identify a uniquely causal initial placement error.

Two alternatives are worth distinguishing. **Movable physical contacts** make a logical edge's hardware coupler a joint decision for both endpoint trees; every source vertex remains revisable. **Simultaneous connected-chain domains** would retain several branch-set choices per vertex and coordinate contact/occupancy constraints through messages. The latter avoids irreversible singleton promotion, but dynamic domain generation and approximate message convergence add substantial unresolved cost. Select the first: its new reachable move has a much cheaper falsifier.

## Selected hypothesis and bounded update

Hypothesis: repeatedly revising contact locations and both adjoining trees can shorten chains and resolve congestion before a valid partial-minor commitment becomes permanent. This replaces B's state and construction trajectory; it does not add another blocked-state release rule.

State: one oriented physical coupler witness per logical edge, and one nonempty physical tree per source vertex containing all its incident witness endpoints. Repeated terminals for the **same** owner consume one qubit. Different owners sharing a site create a conflict. With owner multiplicity k(q), retain exact totals Q=sum_v |C_v| and O=sum_q max(0,k(q)-1). Connectivity and all logical contacts hold throughout; only O=0 states may be credited as embeddings, after independent validation.

Provisional initialization on connected hardware: make seeded degree-tied BFS orders of the source forest and target; pair source vertices injectively with the first target sites. Use the target BFS tree path between each logical edge's provisional sites; choose its middle physical edge as witness and give each half-path to its logical endpoint. Per-owner half-path unions are connected. Prune nonterminal leaves, retaining the provisional site for an isolate. These sites impose no subsequent anchor constraint. This inexpensive initialization uses all source edges, but its BFS geometry may be poor; disconnected hardware needs an explicit later policy and is outside this first ideal-Z12 hypothesis.

```text
initialize all trees, witnesses, multiplicities; set congestion prices lambda=1
for at most 8 sweeps, under one 20M-work / 60-second allowance:
    move any conflicted isolate to the first free site, if available
    visit logical edges in fixed seeded order
    pair each edge with its highest-conflict incident edge, if one exists
    privately remove those witnesses; trim newly dispensable tree leaves
    retain old couplers plus 3 ranked alternatives per changed edge
    inspect at most 16 joint coupler combinations (at most 3 changed trees)
    reconnect new terminals to retained trees by weighted shortest paths
    prune, then evaluate actual resulting tree unions, Q and O
    atomically adopt the best strictly improving complete proposal
    after a complete infeasible sweep, increase lambda(q) by max(0,k(q)-1)
```

For a patch, alternative couplers come from the induced subgraph on the closed one-hop neighborhood of its old trees, including both orientations. Rank by the sum of weighted endpoint-attachment estimates, then seeded physical rank; keep the old coupler explicitly. Empty retained trees start at their new terminal; a shared owner connects multiple new terminals in fixed source-edge order. Other witness endpoints remain compulsory. Routing may cross other owners, with priced occupancy; it cannot silently forget a logical contact. Isolate relocation and its site scans share the same allowance. No target partition or independent constructor supplies the state.

Before feasibility, compare the exact candidate energy Q+sum_q lambda(q)max(0,k(q)-1), with prices fixed throughout a sweep. Once O=0, preserve feasibility and accept only strict Q reductions. A failed or interrupted private proposal leaves the current state intact; a deadline-expired return gets no timely credit. Count initialization paths, adjacency/site scans, terminal copying, candidate generation, routing and scoring against the shared work allowance; all sorting and administration remain in wall time. At most 8|E(G)| patches are visited. Repeated searches can still exhaust this allowance early: the bound is a cost ceiling, not evidence of MM-scale speed.

## Self-critique and cheap falsifier

This can fail through correlated contact choices, poor initial geometry, oscillating congestion pressure, or the small coupler pool. Attaching each terminal greedily can miss a cheaper shared Steiner branch. Equal-Q relocation may be needed after feasibility but is excluded initially. Temporary overlap is established CMR/routing prior art; explicit edge witnesses and reference-counted link trimming also predate this proposal. The possible contribution is the particular bounded **joint contact update within a full-source trajectory**, still unestablished—not witnesses, Steiner trees or prices themselves. See the already checked [CMR](https://arxiv.org/html/1406.2741), [Bian routing discussion](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full), and [Bernal witness formulation](https://arxiv.org/html/1912.08314); the [endpoint prior-art note](../endpoint_support_prior_art.md) records the additional MM link/trim overlap. No implementation is to be copied or called.

First test only a contact-update primitive on three fixed small cases. For source path u–v–w and target path a–b–c–d–e, witnesses (a,b),(d,e) force the valid deletion-minimal trees {a},{b,c,d},{e}, Q=5. Fixed witnesses cannot reduce Q; jointly moving contacts to (a,b),(b,c) permits {a},{b},{c}, Q=3. This tests moving contact obligations, not superiority to generic joint reconstruction or MM. A source star on the same-sized physical star tests shared same-owner terminals at optimal Q=n. A triangle on a physical path is the negative case: it must never receive feasible credit. These fixtures are independent of ER66/K40.

If the prescribed bounded update misses the positive move or mishandles the negative case, stop before a constructor. If it passes, seek approval for one fixed constructor on the same exposed nine-input panel, retaining every failure and cost. No additional completions **and** no reduction on any of the four existing nonoptimal successes would falsify its immediate practical value; favorable toy reach alone warrants no larger search allowance or publication claim.
