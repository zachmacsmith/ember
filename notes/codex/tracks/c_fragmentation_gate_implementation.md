# Fragmentation gate: implementation and execution freeze

This implements the [approved single-query policy](c_fragmentation_saved_state_discriminator.md) unchanged. The policy SHA256 is `dd115bfdb35c8ce92b814187dfd98a39dec6cba24940b26b51976a8673be8fa0`. No constructor, registry, MM call or evolving repair sequence is included.

The standalone [gate](../../../results/codex/track-c-fragmentation-gate/gate.py) builds physical cross-owner coupler counts once. Moving q from donor d to recipient u changes only couplers incident to q; their old/new multiplicities determine exact lost and gained original contacts. Donor-minus-q components are cached across recipients because that set is identical. Candidate eligibility/sampling uses this local accounting; complete certificates independently scan original target edges and use the previously reviewed chain oracle. The source record hash in sampling is SHA256 of its exact normalized JSON bytes. Original label maps are verified against those edges before decoding the fixed starts.

All eight atomic final maps are retained in source order, including the two complete/no-query starts. Each private query retains transfer/reconnection/final maps when reached, contact and M/C/Q changes, its path, every attempted deletion, timing/work and interruption status. Reconnection uses the unchanged free-path primitive with sorted target adjacency. The deletion helper receives the realized original-contact subgraph after reconnection. It is never asked to certify missing source edges. A valid subgraph assignment becomes a full original minor only when the independently recounted missing set is empty.

One absolute 15-second deadline begins before graph construction. Each query's one-second deadline is clipped to it. Forensic copies after interruption remain charged and cannot restore witness credit. Graph decoding/hash checking and result-file writing are evaluator overhead; graph setup, sorting, private copies, component/contact work and final certification are inside the diagnostic allowance. This is diagnostic timing, with no solver speed comparison.

The five specified check groups pass: articulation/connected classification and local deltas in both directions; lost-contact rejection; reconnection with and without Q compensation; private-state rollback; and late valid-certificate rejection. The final pass also checks the supplied absolute deadline. `checks001` preserves the earlier pass before that driver-deadline clarification; `checks002` is the final 5/5 pass, 0.0027 seconds, with no prohibited imports. No broader enumeration or constructor fixture was run.

Final executable identities before the eight-state call:

| File | SHA256 |
|---|---|
| gate.py | `a6606fb7854f38002b2c37f5a65553ca5af3c18df87dda4cf6be9ce55b25beab` |
| checks.py | `a677fb4461d17aff377f72bbf2f526726966cb1439d2583779d58f49e069fc4a` |
| run.py | `611ac53f5e33f43a33e7ee4f25df3c57c8e2788908ee664e748c1f5987c639f5` |
| prepare.py | `37a9a7f4c247a8d1c2cd01637b06acb26fad0b7d4e76e87faabf1d68bc2038fa` |

The [input manifest](../../../results/codex/track-c-fragmentation-gate/input_manifest.json), SHA256 `3b6acb763128c489b8c0ebea1a23090a854619e5734a4ad3d7cd40e033258886`, binds nine copied input files and 44 original references. `pre-execution.json` binds this note, the policy, code, helper/validator, final check evidence and all inputs before the one authorized gate. Any later interpretation belongs in a separate result note; these bytes remain frozen.
