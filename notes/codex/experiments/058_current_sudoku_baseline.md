# 058: current A053/MM baseline on corrected Sudoku inputs

Pre-observation protocol, 2026-09-08. Use the unchanged audited027 supplement
(box orders2/3,16/81vertices), ideal Z12, fixed A053 and stock MM, seeds0–1,
60s each: eight serial calls on hyde02 in its existing isolated environments.
No graph generation, source replacement, candidate refinement or portfolio.
All method pairs share one host; original03 Sudoku timings stay historical.

Purpose: fill the current-policy evidence gap left by the oversized inherited
Sudoku entries, while preserving the supplement's separate provenance. Verify
source/target bytes equal029, reuse audited supplement semantics and validators,
and independently validate every claimed minor. No repeated exhaustive generator
check is needed because input bytes are identical. Keep all status, timeout,
late-valid and failure costs; successful and common-seed mean/sample variance
have explicit denominators. Two seeds and two fixed graphs are development
observations, with no population or unseen-structure claim. Orders4/5 stay reserved.

A lower mean on one box order cannot hide regression on the other. Allow an
ACL1 tie as optimal; a higher-ACL tie needs an independent lower bound to call
optimal. The old24-qubit order2 witness remains relevant and prevents calling
an order2 Q25 tie optimal. Candidates receive no embedding or family metadata.
The original017/012 missing-family records remain unchanged.
