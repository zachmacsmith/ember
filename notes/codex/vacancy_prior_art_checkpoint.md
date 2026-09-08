# Local relocation: focused prior-art checkpoint

2026-09-08. Read while 046 runs; no algorithm or experiment settings changed.

[Bian et al. (2014), section 2.2.5](https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2014.00056/full)
already searches disjoint connected chains with unfulfilled source edges.
Its objective includes missing-edge distances and squared chain sizes. Moves
include adding a free adjacent site, deleting or transferring a site while
retaining a connected chain, and exchanging sites between two chains. Thus
temporary missing contacts, local relocation, and a preference for short chains
are established embedding ideas. Section 2.2.4 describes neighbor-rooted
shortest-path chain reconstruction.

[PSSA and its improvements, sections 3–4](https://arxiv.org/html/2004.03819)
use whole-chain label swaps, adjacent leaf transfers and simulated annealing.
The described initialization and shift guidance use complete-graph embedding
patterns. The terminal phase removes unnecessary sites while preserving existing
contacts and connectivity, then joins missing contacts through free hardware
using BFS. These are relevant precedents for both vacancy refinement and C003's
movable-region constructor. Our candidates do not use those stored complete-
graph patterns or call that implementation.

**Inference from the current code and these sources:** 045/046 test a particular
bounded compound neighborhood: deliberately remove one site, preserve Q-minus-
one occupancy throughout contact-directed relocation, and commit only a fully
repaired minor. The code can temporarily lose other contacts while repairing a
chosen missing edge. Its beam, per-deletion cap and shared cumulative budget
are implementation/search-policy choices. This focused reading does not
establish that the compound neighborhood is new, and composing established
moves is insufficient evidence of novelty. Promising pipeline results would
justify a more precise comparison of reachable states and search cost; absent
such results, defer that work.

C003 likewise tests its target-coarsening initialization and globally movable
connected partition, with established swaps/transfers/annealing. No publication
claim is supported by this checkpoint.
