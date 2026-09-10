# Transfer004 input preparation

2026-09-10. All eight planned generations succeeded once, followed by the new BA relabel. Preparation used 10.268 seconds of enclosing process time; the reused input review passed in 4.698 seconds. No embedder ran, and no failed input was replaced or reseeded.

| ID | Development input | Nodes | Edges |
|---|---|---:|---:|
| g0301 | ER, p=0.10 | 96 | 431 |
| g0302 | BA, m=4 | 96 | 368 |
| g0303 | Regular, d=8 | 96 | 384 |
| g0304 | WS, k=6, beta=0.2 | 96 | 288 |
| g0305 | SBM, four communities | 96 | 284 |
| g0306 | Random planar | 96 | 282 |
| g0307 | Singleton diagnostic control | 96 | 561 |
| g0308 | Branch diagnostic control | 96 | 391 |
| g0309 | Independent relabel of g0302 | 96 | 368 |

The reusable panel has 36 encodings / 33 structures, including 27 byte-identical Transfer003 copies. Original-label bijections, stripped metadata, copied identities and all three relabel parent identities pass. Original and relabeled control witnesses pass the unchanged independent oracle and stay in the evaluator-private sibling directory. Candidates receive graphs only.

The six new random structures have no match or unresolved comparison against the 526-record exposed index. The two new controls are independently generated and validated; they were not part of that isomorphism comparison. The BA relabel is intentionally the same structure as its parent. No global graph-novelty or confirmation claim follows.

Root read both thin adapters, compared the input reviewer with its predecessor, and verified all 605 saved review bindings. The [before-generation protocol](transfer_cycle_004_inputs.md) fixes seeds, sizes and generation limits. Evidence is in `results/codex/transfer004-preparation/` and `results/codex/transfer-cycle-004/`; panel SHA256 `b54a8ed0af8e35b3901630fddd2892e3735338ad29104913d3332df49eed250d`.

These inputs support small complete-constructor decisions on fresh structures and two seeds. They do not define a 36-input experiment or consume an untouched confirmation set. Freeze each track's exact subset, algorithm and allowance before execution.
