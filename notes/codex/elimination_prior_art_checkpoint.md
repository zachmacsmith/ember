# Source elimination: limited prior-art check

2026-09-08, design stage. Two targeted searches for minor embedding with
low-degree vertex elimination/preprocessing did not locate a directly matching
algorithm in their returned primary sources. This is a limited search result,
not evidence of novelty or absence of prior work.

The [TEAQC author repository](https://github.com/merlresearch/TEAQC) and
[paper abstract](https://pubsonline.informs.org/doi/10.1287/ijoc.2021.1065)
describe integer-programming search over template minors of Chimera. That is
a different formulation and is not being adopted here. Other returned sources
concerned chain-energy robustness rather than this construction question.

The proposed A049 elimination order and clique fill are conventional graph
operations. Their usefulness here remains an experimental hypothesis. In
particular, an embedding of a reduced filled graph does not automatically
provide a valid embedding after reversing a subdivision or degree-three
elimination. Expansion must construct and independently validate the original
minor, including every eliminated vertex. No stronger literature claim is made.
