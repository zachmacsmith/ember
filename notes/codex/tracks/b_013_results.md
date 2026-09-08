# B013: after-release frozen-port classification

2026-09-08. **Do not add this predicate to B012 on the present evidence.** The independent classifier completes every fixed test and all 21 saved ER release blocks, but rejects none of those blocks. It would add cost without avoiding the observed early routing query.

| Fixed classification | Rejected | Not rejected | Unknown / omitted |
|---|---:|---:|---:|
| Five prescribed tiny cases | 3 | 2 | 0 |
| All 21 B012 ER66 blocks | 0 | 21 | 0 |

All tiny outcomes match their hand-specified expectations: cross-owner protection and self-protection reject; a newly released alternative passes; demand solely for the new vertex is excluded while demand for a released owner remains pending. “Not rejected” does not establish connected insertion or eventual reconstruction.

The earliest surviving block remains index 0, releasing owner **53**. The recomputation matters: removing its physical site **1990** changes frozen required chain 72's free boundary from `{1991}` to `{1990,1991}`. Site 1991 is still protected by frozen owner 55, but site 1990 is unprotected. Therefore the required contact has an allowed site and this exact necessary obstruction is absent. The earlier B012 record's failed routing toward 1991 cannot justify discarding that alternative contact without further evidence.

The complete classification, including setup, hashes, decoding and the five tiny cases, uses **261,277 counted operations and 0.125 seconds**, below its fixed 500,000-operation/five-second limits. Setup accounts for 51,131 operations. Block 0 costs 10,065 operations and 0.00360 seconds. These independent set-iteration counts are not interchangeable with constructor scans or a measured integrated speed change. All records and exact certificates are preserved in [classification.json](../../../results/codex/track-b013-obstruction/attempt001/classification.json).

No reconstruction, constructor, MM, cluster or registry action occurred; B012 remains unchanged. This negative result is informative: after-release site availability invalidates the tempting pre-release obstruction. The unresolved question is whether the unprotected alternative belongs to a connected available region touching every required chain, or whether bounded routing misses such a region. That is a separate hypothesis, not an implemented extension of this predicate.

The [classifier](../../../results/codex/track-b013-obstruction/classify_blocks.py) uses only the standard library and the previously frozen source, target, failed entry and ordered block vector. Its full input/script/design hashes are in the result. Reproduce only if needed in a new additive output directory:

```sh
.venv/codex-native/bin/python -B results/codex/track-b013-obstruction/classify_blocks.py OUTPUT
```
