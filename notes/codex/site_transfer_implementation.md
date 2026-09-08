# A053 implementation and fixed reach gate

The isolated implementation passes its eight focused correctness groups and
all eight prescribed fresh-process reach calls. **Coverage passes; quality is
mixed, so broader use awaits root review.** The wheel regression is retained.
No pilot registration, 34-input run, cache, original-only requirement change,
or additional constructor comparison was performed.

`site_transfer_construction.py:reduced_core_embed(source,target,*,seed=0,
timeout=60.,deadline=None)` copies fixed A050 and adds only the proposed
pre-insertion query. `site_transfer.py:transfer_site(engine,v,entry)` consumes
the live engine whose source is the privately staged R after removing the
current row's created fill. The helper returns a private candidate/receipt;
the caller owns inherited cleanup and atomic R/mapping adoption. Original and
older synthetic requirements remain active. Ordinary insertion and blocked
repair are unchanged when no transfer returns and work/time remain.

Candidate order and limits are exactly the approved policy: donor size,
source rank, site rank; first 64 ordered sites; first certified proposal;
50k/query and 1M/constructor inside the original 20M budget and deadline.
Owner/free-boundary setup is repeated per query. Donor traversal checks its
connectivity, contacts and future port; the new singleton must touch every
required placed neighbor and retain a port if needed. The existing partial
validator and full future guard certify the first locally admissible mapping.
Every raw transfer has unchanged occupied sites/Q and freezes other chains.
Inherited endpoint cleanup can subsequently change Q and is recorded
separately. All new setup, pool comparisons, site/adjacency traversals and
certificate work are charged; inherited routine loop/allocation costs also
remain in elapsed time. These scan units are not CPU-instruction counts.

The focused checks cover two valid filled-entry witnesses, original versus
older-fill contact retention, articulation and both donor/new-vertex future
guards, exact first-candidate and 64-site truncation, local/cumulative/global
limits, late publication, immutable entry, no-transfer A050 equivalence,
actual reduction-to-core wiring with a controlled core result, and cleanup
interruption retaining the preceding R. Hand-supplied path/star step witnesses
test the primitive; their source alone can protect its center as an anchor,
so they are not claimed as full-constructor trajectories. No prohibited
imports occurred.

| Fixed input | n / m / max degree | Q050 | Q053 | Transfers | Transfer scans | Solver s050 / s053 | Total scans050 / scans053 |
|---|---|---:|---:|---:|---:|---:|---:|
| Star | 128 / 127 / 127 | 138 | 138 | 0 | 351,397 | 1.354 / 1.685 | 1,559,996 / 1,911,393 |
| Wheel | 128 / 254 / 127 | 189 | 191 | 12 | 458,934 | 5.647 / 5.603 | 6,375,877 / 5,964,868 |
| Subdivided K5 | 15 / 20 / 4 | 17 | 17 | 1 | 4,001 | 1.751 / 1.472 | 236,592 / 237,379 |
| Exposed cycle | 126 / 126 / 2 | 155 | 148 | 18 | 116,876 | 3.178 / 2.707 | 3,793,990 / 3,008,706 |

Every output is independently original-valid; no failure, deadline, process
timeout or internal error occurred. Each input/arm used its own process,
seed0 and 20-second constructor allowance. Only subdivided K5 invoked native
on a core, once per arm. All other calls used the inherited edgeless base case.
No limits or ordering changed after outcomes.

Across A053's four calls, 1,750 sites were inspected, 31 transfers certified
and committed, all raw ΔQ=0; post-transfer cleanup removed zero additional
sites in these calls. Transfer work totalled 931,208 scans and 0.714 s,
overlapping global/expansion totals. Maximum query work was 14,942, maximum
constructor transfer work 458,934; neither transfer allowance bound the reach
calls. Rejections counted 969 missing new contacts, 475 disconnected donors,
272 lost donor contacts and three missing new-vertex ports. Wheel required
three blocked repairs/819,840 repair scans versus none for A050; cycle avoided
A050's one repair/80,381 scans. Thus 31 local constant-Q steps yielded only
five fewer final qubits in aggregate (499→494), with a two-qubit wheel loss.

Total solver time was 11.929→11.466 s (CPU11.695→11.454), process time
14.997→14.620 s and global scans11,966,455→11,122,346. This small local sample
does not establish a runtime advantage. In particular, star paid 351,397
additional scans without a transfer or quality change. Whole-input quality
can worsen after a valid constant-Q step; fixed filled-core excess also remains.

All first-attempt source bytes, inputs, plan, eight observations, process
records and checks are in `results/codex/a053-site-transfer/attempt001`.
After that completed run, static review found one receipt-only boundary:
a deadline crossing inside the local-cap exception handler could leave the
query's status as `started`, although timeout/rollback were correct. The
final helper annotates that deadline before re-raising. Old helper/test bytes
and a targeted synthetic check are preserved in `receipt_correction`; that
one check passed. No reach calls were repeated. The constructor/ranking/
nonbinding search behavior is unchanged by this correction.

Evidence and final hashes are bound by
`results/codex/a053-site-transfer/manifest.json`; exact source delta is
`constructor_delta.diff`. The original eight-call command was:

```sh
.venv/codex-native/bin/python -I -B results/codex/a053-site-transfer/run_checks.py results/codex/a053-site-transfer/attempt001
```

This records the completed invocation, not authorization to repeat it.
The only subsequent execution was the synthetic
`receipt_correction/check.py`. Files are stable for independent review;
registration and a broader experiment remain unapproved.
