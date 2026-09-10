# A066 diagnostic: neutral bridges exist, with narrow transfer

2026-09-10. **Exploration: continue to one complete-constructor test.** The exact
primitive finds useful neutral relocations on grid128 and fresh WS100. It finds
none on ER80, planar80, the singleton control or fresh SBM100. No constructor was
implemented or run for this diagnostic.

The [before-code contract](a_066_pair_diagnostic_contract.md) froze six existing
A065 final maps. All 259 eligible adjacent length-(2,1) pairs were exhausted;
there were no timeouts, unknown pairs, errors or prohibited import attempts.
Every exact one-owner singleton domain was empty.

| Input | Entry Q | Pairs | Neutral-first bridges requiring relocation | Pairs requiring joint release | Zero-donor strict-query obstructions | Process seconds |
|---|---:|---:|---:|---:|---:|---:|
| ER80 | 252 | 3 | 0 | 0 | 3 | 0.377 |
| Planar80 | 126 | 73 | 0 | 0 | 73 | 0.430 |
| Grid128 | 162 | 98 | 3 | 2 | 92 | 0.547 |
| Singleton control80 | 199 | 13 | 0 | 0 | 11 | 0.367 |
| Fresh WS100 | 244 | 43 | 1 | 0 | 29 | 0.424 |
| Fresh SBM100 | 251 | 29 | 0 | 0 | 19 | 0.363 |

All four neutral bridges have zero removable donor sites under unchanged A063
preparation. Thus the existing strict-Q query for each such two-site focus must
produce a singleton, but its exact fixed-neighbor singleton domain is empty.
Moving its adjacent singleton first preserves the complete minor at equal Q and
opens a strict shortening. This establishes an acceptance/neighborhood barrier
for those specific moves, rather than simply insufficient root computation.

Grid has five positive pairs involving four focus owners; two different joint
moves shorten the same focus. Some neutral-positive pairs also admit assignments
with no valid intermediate. The table's joint-release column counts only pairs
with no neutral-first assignment. **These savings are not additive.** No sequence
of the witnesses was executed. All saved moves individually save one qubit:
grid Q162→161; WS Q244→243. Within-chain variance decreases on grid but increases
on WS from 1.2464 to 1.2651. Across-seed variability remains unmeasured.

Eight canonical final maps and four neutral intermediate maps passed the
unchanged independent original-graph oracle. Assignment counts are exact domain
enumeration results; only the saved canonical maps receive independent witness
validation credit. All witness sites and owner IDs are retained in the bound
per-input output, never in candidate production code.

Six isolated native Python processes used the existing dependency guard, with
no MM/busclique dependencies, constructor calls, MM map reads or private witness
reads. The first execution of three focused check groups passed: brute-force
oracle comparison of direct/neutral/joint classification including occupied-site
and absent-contact exclusions; unchanged donor attribution; interrupted domain
and intermediate-validation behavior. There were no code corrections or retries.

The 30-second allowance was a maximum, not a quota. Total process wall was
2.508420 seconds across three concurrent local workers; total worker wall before
output was 2.120472 seconds. Exact domain enumeration consumed 0.035044 seconds.
Preparation, validation, input hashing/imports and output/process overhead remain
charged and separately recorded. These timings describe the diagnostic on this
host, not a paired constructor comparison against MM. All full process lifetimes
were below 0.55 seconds, so output accounting does not conceal a deadline overrun.

The frozen two-structure continuation criterion is met. A coordinated atomic
(2,1)→(1,1) operator can cover both observed witness types without neutral wandering.
It should be tested inside the evolving constructor immediately after proving
that the existing focus query cannot shorten. A pruning-only ablation can
separate saved futile computation from the additional move. Stop treating this
primitive as an explanation for the four fully negative structures; do not
silently widen the pair lengths or add repairs based on this result.

Evidence:
- Code: `scripts/codex/a066_pair_diagnostic.py`; checks: `scripts/codex/a066_pair_check.py`.
- Frozen packet: `results/codex/a066-pair-diagnostic/packet001/manifest.json`, SHA256
  `ec9ae8ece9a65e82bcc960d751f269a76eb514621fcb093a84dfcdeaa33eacd8`.
- First check/execution records: `check001/`, `execute001/`, `run001/` in that directory.
- Passive report first PASS: `report001/summary.json`, SHA256
  `ca13419b318c3b91b1b33be47bd6f0188c2ece7baead2043c1e7d55463b9d68c`;
  binds 16 results/control files plus all 13 frozen inputs/source references.

The remaining-transfer A065 screen was not altered. Its broader gains and
regressions remain separate complete-constructor evidence.
