# Bounded vacancy-repair correctness review

2026-09-08. **No correctness blocker remains for the exploratory caller.**
Reviewed source SHA256:
`6f990653299e418e878188466f61d4e2ddb0490262c6406075f9c50c2c595093`.
No production code was edited by this reviewer and no corpus or remote call
was made. This is a targeted review, not an exhaustive neighborhood proof.

For simple undirected source/target graphs, replacing a site of chain `a`
changes only logical contacts incident to `a`. Removing those incident edges
from the old missing set, then recomputing all of them against the updated
physical ownership, is exact. The code checks that the chosen missing edge is
restored. Selecting a currently free new site preserves disjointness; testing
the entire replacement preserves connectivity and nonemptiness. The first
deletion reduces Q by one and every later replacement preserves that Q.

The selected-owner history grows monotonically. Every proposed added owner
passes the eight-owner and 64-original-site tests before relocation. Initial
seed chains also obey the site bound. Keeping owners in this history even after
their chain returns to its entry state can exclude moves; it does not admit an
oversized original footprint. Outside chain lists are copied unchanged and all
returned lists are private. The entry mapping and adjacency are read-only.

Four fixed synthetic fixtures passed independent missing-contact, ownership,
connectivity and Q checks at **2,697 generated states and 29 connected deletion
states**. They exercise the published free-site five-cycle witness, a cycle
with leaf sites that reaches six separate 256-proposal seed caps, a nine-owner
cycle that reaches exactly eight selected owners, and a 65-site cycle that
reaches exactly 64 selected original sites. The returned witness passes the
accepted 042 original-edge validator. A separate three-proposal global cap
interrupts without changing the input. No broad graph enumeration was used.

The original final rejection clock preceded later wall/overrun observations.
Root corrected that narrow boundary to derive all final timings and rejection
from one last observation. The reviewer injected a crossing on exactly that
last (35th) clock call: the already certified candidate was withheld,
`candidate_returned=False`, `stopped_reason='deadline'`, wall=2 and overrun=1.
The prior certificate remains diagnostic evidence. The caller still owns its
independent original-graph validation and actual outer return deadline.

Important limits for 045 interpretation:

- Work counts attempted relocation proposals. Setup, adjacency scans, copying,
  hashing and sorting consume wall time but are not additional proposal units.
  This counter cannot be compared to 043 elementary units or routing pops.
- The supplied group vector is ignored by vacancy search; it remains an input
  to the ordinary control. `groups_inspected` stays zero here. Use deletion-seed
  attempts and proposal counts to describe this method's actual coverage.
- The visited set records generated states before beam selection. A state
  discarded by the beam can therefore suppress a later occurrence. This is a
  heuristic completeness limitation. No feasible-output validity relies on it.
- Ranking uses the complete move trace as the deterministic final tie-break.
  Early feasible children are certified immediately; capped/interrupted
  nonfeasible generation does not publish a replacement beam.

Evidence: `results/codex/vacancy-independent-review/checks.py` and
`summary.json`. The source hash is checked before and after the diagnostic.
The reused structural oracle hash is
`2fb76ee1ca2b3f2f6d736736948b23075c7b54a8462460740375632a9c140b9c`.
These observations support running the specified falsifier; they establish no
quality, runtime or novelty advantage.
