# B016 static gate: complete-block capacity changes both release vectors

2026-09-08. All six tiny checks and all **31 release blocks** across the two fixed failed states complete within the shared diagnostic limits. The capacity-priority policy has informative effects on both states, but **no reconstruction or constructor has been called**. Surviving capacity checks are not feasibility certificates.

| Saved B011 blocked state | Blocks rejected / inspected | First capacity-priority survivor | Original index |
|---|---:|---|---:|
| ER, next vertex 66 | 1 / 21 | `[72]` | 4 |
| Complete 40, next vertex 9 | 9 / 10 | `[0,12]` | 5 |

ER's baseline constrained required owner is 72; its protecting owners are 53 and 55. Release `[31]` is correctly rejected: frozen chain 72 needs contacts to both selected vertices 31 and 66, but only site 2002 is usable. Boundary site 1991 remains reserved for outside owners' genuine future demand. The complete new vector places `[72]` and then its pairs first, followed by protecting-owner releases and other blocks. Releases `[53]` and `[55]` pass this capacity test but remain subject to B015's independently justified first-insertion component rejection; this new test does not replace it.

The K40 identity and eligibility were frozen **before** release classification: task `3c184a0c753d01220a467856`, `FAILURE/construction_blocked`, 24 placed chains using 137 qubits, next vertex 9. Its baseline constrained owners are 0, 7 and 34. The unchanged capped pool is `[0,27,12,21]`, omitting constrained owners 7 and 34; that limitation is preserved. Only release `[0,12]` passes all complete-block capacity rows. Passing does not prove it can be connected or greedily rebuilt under the ordinary root and work limits.

The tiny checks distinguish two selected contacts competing for one usable site, the effect of adding a second site, released-member demand counted in `d` rather than future `p`, and a shared free site satisfying two remaining frontier guards without inventing two distinct free-site reservations. The existing occupied-endpoint witness also passes its capacity check. All expected outcomes match.

Total cost is **403,429 counted operations and 0.186 seconds** of diagnostic wall, under five seconds/two million operations. Initial target setup uses 50,672 operations; ER assessment uses 245,656 operations/0.0875 seconds and K40 uses 106,880/0.0461 seconds. All block assessments complete with no unknown or omitted assessment. Omitted *owners* from the capped pool are explicitly separate. These set-iteration counts and local timings are not integrated constructor work or a speed claim.

[Input freeze](../../../results/codex/track-b016-capacity/input_freeze.json), [complete rows and reordered vectors](../../../results/codex/track-b016-capacity/attempt001/classification.json), and the [stdlib classifier](../../../results/codex/track-b016-capacity/classify_capacity.py) retain identities, every certificate, costs and test evidence. No candidate module or local helper is imported. No B016 constructor implementation, MM call, registry edit or cluster action occurred.

This gate supports considering an isolated policy implementation: it removes a demonstrated restoration impossibility and identifies a different bounded neighborhood on a second failed input. It does not support a broad benchmark run yet. Actual reconstruction may still exhaust its allowance on the newly prioritized survivor, and the unchanged pool can omit useful owners. No cap, block size or pool was enlarged in response to these outcomes.
