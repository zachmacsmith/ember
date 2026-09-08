# B018: the fixed small contact gate passes

2026-09-08. The standalone movable-contact primitive passes its three prespecified calls with unchanged pools, seed and 5-second/100,000-unit limits. **Stop for root review; no constructor or panel has run.** The source implements no initialization, adaptive prices, sweep schedule or registry entry.

| Fixed case | Result | Work units | Complete combinations | Call wall |
| --- | --- | ---: | ---: | ---: |
| Path contact relocation | Valid Q 5→3 | 1,464 | 16 | 1.161 ms |
| Optimal star | No improving proposal; valid Q4 entry retained | 1,652 | 16 | 0.982 ms |
| Triangle on a physical path | No proposal; overlapping entry remains invalid | 2,016 | 16 | 1.225 ms |

The path winner changes witness 01 from physical `(0,1)` to `(2,3)`, retaining witness 12=`(3,4)`. It returns chains `{0:[2],1:[3],2:[4]}`, with Q=3 and overlap=0. Moving the contact and both adjoining trees removes the fixed-witness obstruction. The winning proposal changes **only one witness**: this result does not establish a need for simultaneous changes to two logical edges, nor an advantage over existing generic joint reconstruction or MM.

For the star, three center obligations share physical site 0, counted once toward Q. The retained center tree still supports the unchanged third logical edge. No strictly smaller valid proposal exists below the four-vertex lower bound, and none is returned. For the triangle, the original-graph validator rejects the initial overlap; every inspected combination remains non-embeddable. No private contact/tree certificate is mistaken for a full minor certificate.

All 48 complete combinations receive independent checks of original-edge witnesses, connected chains, actual union Q/overlap, and agreement between zero overlap and the reused full original-graph validator. Every input remains unchanged; no work or deadline cap binds. Millisecond times describe these tiny calls only and imply nothing about Z12 throughput.

[Seven targeted checks](../../../results/codex/track-b018-contacts/attempt001-checks/summary.json) pass, covering duplicate obligations and pruning, exact energy, preserved contacts, route-interruption rollback, expired entry and final-publication deadline rejection, outside list order and malformed graphs. No prohibited embedding import loads. No failed test attempt or source correction after observation occurred.

The [pre-code addendum](b_018_contact_primitive.md), [frozen initial states](../../../results/codex/track-b018-contacts/inputs.json), [all three observations](../../../results/codex/track-b018-contacts/attempt002-cases/summary.json), and [artifact manifest](../../../results/codex/track-b018-contacts/artifact_manifest.json) preserve the exact policy and evidence. Source SHA-256: `5f6cc2c7546c7e71d203b606dae033f4127b125b2d28b67169f1c346b10611b5`. The query returns `(proposal_or_none, info)`; a proposal from an overlapping entry must still be independently checked before any embedding credit. This narrow positive gate supports considering a construction experiment, without establishing its initialization quality, conflict convergence, runtime or novelty.
