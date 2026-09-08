# 049 failures: contact reach exists, but future ports conflict

Read-only diagnosis of the two saved failed entries, before A050 implementation.
This separates free-space contact reach from the constructor's future-demand
condition. No constructor, MM call or new source input was used.

In both states, one connected component of unused Z12 sites touches every
required neighbor of the failed insertion. Therefore a connected free branch
set realizing its current contacts exists with endpoints fixed. This statement
does not guarantee preservation of other vertices' future access or a short
chain. On the wheel, unused site517 alone touches all three required chains
(0,124,126). On the cycle, the two endpoint frontiers intersect the same giant
free component but have no shared singleton site.

Reconstructing trial requirements from the saved journal reveals contention:

| Failed insertion | Required access | Competing pending chain |
|---|---|---|
| wheel125 | singleton517 touches all required neighbors | vertex12 has only free neighbor517 |
| cycle114 | required endpoint113 has only free neighbor686 | vertex68 also has only free neighbor686 |

Neither new vertex has a pending neighbor after this insertion. The obstruction
is another placed chain's pending demand. In the cycle, every free insertion
with endpoints fixed consumes686 and removes vertex68's last extension site.
The wheel's shared singleton has the analogous defect; other routes are not
ruled out. These facts do not prove that a chosen local repair will succeed.

A050 should test movement of required endpoints or the chain whose remaining
port conflicts with insertion. A required-neighbor-only neighborhood can miss
the actual competitor. Merely increasing shortest-path effort does not resolve
the cycle's fixed-ownership conflict with future-port preservation.

Evidence: [component reach](../../../results/codex/049-results-review/failure_free_components.json)
and [pending-port recount](../../../results/codex/049-results-review/failure_pending_ports.json).
The first component invocation encountered a null top-level partial field;
the corrected read uses the already audited `diag.partial_embedding`. No
artifact or search ran in that failed invocation. The component pass, including
reading all saved result records, took approximately 0.156 seconds; its raw exact
wall is saved. These are diagnostic observations, not full-pipeline evidence.
