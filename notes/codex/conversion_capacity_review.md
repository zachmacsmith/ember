# Conversion capacity review — diagnostic 034

The suspected capacity-DP defect is **confirmed**. `_convert_line` can report a
complete parity assignment that violates its own lane capacities. Subsequent
seating preserves physical occupancy in the tested cases, but can miss an arm
even when all arms have a feasible placement. This was reproduced on an intact
ideal Zephyr Z12 line with the usual four lanes per parity.

Recommendation: correct the DP's expiration frontier in a separate, narrowly
scoped change, after the current 033 source snapshot is frozen. First verify the
corrected recurrence against an independent exhaustive oracle and measure its
state growth. Do not infer that the current raw-hull objective equals seated
qubits or final embedding quality. No implementation change or full embedding
run was performed for this review.

## Frozen evidence

The frozen source is
[`034-conversion-capacity-diagnostic/snapshot/field.py`](../../results/codex/034-conversion-capacity-diagnostic/snapshot/field.py),
SHA256 `6d717696317192ad0df4f0fb6f5a26bb1da0dc4f57408cfad7ac810bb1a1fbfd`.
The defect is in `_convert_line`, around lines 693–717; seating starts around 744.
The design was recorded before execution in
[`design.json`](../../results/codex/034-conversion-capacity-diagnostic/design.json).

The unmodified frozen module was loaded directly. A Python trace captured actual
DP state/history and final assignment; it did not replace the recurrence or
alter arguments. The independent physical oracle enumerated connected lane
segments and checked required contacts through target edges, then enumerated
disjoint lane assignments. Every tested returned chain was separately checked
for target membership, overlap, connectivity, and required contact coverage.

The interpreter was `.venv/codex-native/bin/python`, Python 3.10.19, NetworkX
3.4.2, dwave-networkx 0.8.19. The trace runner blocked MM/busclique imports and
recorded no attempts or loaded forbidden modules. No constructor, plane search,
completion, polishing, or external embedder was called. Creating the target
graph with `dwave_networkx.zephyr_graph` is hardware-input generation.

| Artifact | SHA256 |
| --- | --- |
| `diagnose.py` | `12c5ee6096f1e157834ad034dfc550489e4aea025fee93eab5284a7a3a55e132` |
| `observations.json` | `1029af1d7b2c0fe45700974b1a7859c192414ea25f4004c54ca9ba17486de199` |
| `actual_feasible.py` | `2516a8ae4db9d90bd289e1dab9d21c2dff2b5492648ff68be3e7ca9791aa95d8` |
| `actual_feasible.json` | `1679967068a2b52ea9d9b043e4458f2435f18fdd3df165eccb22fe707db6192b` |
| `verify_artifacts.py` | `c48e9cd630d4a52bdbd2a67c034f07a26ebb31de5b6b0092ebb33eed30ca9416` |

The ideal Z12 target has 4,800 vertices and 45,864 edges. Its coordinate-label
canonical nodes/edges SHA256 is
`fe833322b95294a242bcabf814b86d1420328c3df11ba3dfe47fdc5a8911607d`.
The hash encoding and an explicit feasible nine-arm placement are saved in
[`independent_verification.json`](../../results/codex/034-conversion-capacity-diagnostic/independent_verification.json).

## Why expiration is wrong

Arms are processed by their smaller possible start `min(lo0, lo1)`. The current
recurrence, however, expires *both* classes' previous intervals using the chosen
class's start `lo`. That start can be larger than the next arm's chosen start.
An expired occupied position can therefore become relevant again, after the DP
has forgotten its owner.

Consider three arms A, B, C, each targeting crossing 1, with one lane per parity.
Every arm has class-0 hull `[0,0]` or class-1 hull `[1,1]`. All costs are zero.
The captured winning history is:

| Decision | Retained active state | What was forgotten |
| --- | --- | --- |
| A chooses 0 | A0 | — |
| B chooses 1 | B1 | A0 expires because `0 < 1` |
| C chooses 0 | B1, C0 | A0 still occupies the only class-0 site |

Thus the DP accepts `(0,1,0)` although only two distinct physical sites exist.
Seating does not trust this as an occupancy certificate: it places two arms and
returns `(misses=1, flips=0)`. This first example refutes DP feasibility, but its
missing arm is unavoidable and does not by itself demonstrate lost quality.

## Feasible placements that seating misses

A deterministic bounded enumeration of two through four arms, using crossing
endpoints from 1 through 4, stopped after 578 cases when it found the first
feasible missed-seating and invalid-assignment witness. They were the same case.
This is an adversarial diagnostic search, not a benchmark success frequency.

With one lane per parity, let A target crossing 2 and B and C target crossing 3.
The required hulls are:

| Arm | Class 0 | Class 1 |
| --- | --- | --- |
| A | `[2,2]` | `[1,1]` |
| B | `[2,2]` | `[3,3]` |
| C | `[2,2]` | `[3,3]` |

A valid placement is A on odd position 1, B on even position 2, and C on odd
position 3. It uses three qubits and satisfies every actual required contact.
The old DP again chooses `(0,1,0)`. Seating first puts A at even position 2,
then tries C at that occupied site and moves it to odd position 3. B, processed
afterward, cannot be seated. The converter returns two occupied qubits and one
miss, despite a feasible three-arm placement. The smaller returned qubit count
is incomplete coverage, not an improvement in quality.

The same mechanism occurs with the standard Z12 capacities. Use horizontal
line 1, four arms targeting crossing 2, and five targeting crossing 3. A complete
nine-qubit placement exists: odd lanes at position 1 can serve the earlier
crossing and be reused at position 3 for the later crossing, alongside four even
sites at position 2. The oracle found 1,797,120 lane assignments, all with nine
qubits. A separate pass reconstructed one explicit assignment and verified its
disjoint chains and actual Zephyr couplers.

| Fixture | Oracle full placement | DP class-capacity result | Actual output |
| --- | --- | --- | --- |
| Two lanes, 3 identical crossing-1 arms | Impossible | Accepts; 2 arms at even position 0, capacity 1 | 2 seated, 1 miss |
| Z12, 9 identical crossing-1 arms | Impossible | Accepts; 8 arms at even position 0, capacity 4 | 8 seated, 1 miss |
| Two lanes, crossings 2, 3, 3 | 3 qubits | Accepts invalid `(0,1,0)` | 2 seated, 1 miss |
| Z12, four crossing-2 and five crossing-3 arms | 9 qubits | Accepts; 8 arms at even position 2, capacity 4 | 8 seated, 1 miss |

All occupied chains in these outputs were connected, disjoint, and covered their
assigned target crossings. The failures were missing arms. These converter
inputs are not proof that the current upstream plane packer emits this layout;
no production frequency or downstream ACL effect has been measured.

## Objective and returned qubits

The DP minimizes `sum(hi - lo)` for its selected required hulls, with deterministic
history tie-breaking. On an intact stride-2 lane with both endpoints present, a
fully represented hull uses `1 + (hi-lo)/2` qubits. Therefore

```
raw arm qubits = number of seated arms + sum(selected hull lengths)/2
```

requires that every arm is actually seated on its assigned full hull, with no
fallback change. The recurrence's complete assignment is currently insufficient
to establish those conditions. All four examples have DP hull cost zero, while
the missing arms make actual occupied qubits smaller than the naive full-arm
formula. Seating can also switch parity or use the wider fallback interval.
Completion may add qubits and later pruning may remove them. Neither the DP
cost nor raw arm mass is therefore a measured final ACL.

Source inspection identifies further limits to the broad “exact parity and lane”
wording: the DP sees lane counts, not per-lane missing-qubit or claimed-occupancy
patterns. Those are checked later in seating. `_lane_ok` checks the present
subsequence and internal stride gaps, without explicitly requiring both hull
endpoints to be present. Boundary, off-chip, and defective-lane behavior require
their own checks before an exact physical-conversion claim. They were not tested
or repaired in this capacity diagnostic; they are distinct from the reproduced
expiration defect on intact interior lanes.

## Proposed narrow correction and self-critique

Retain active intervals against one shared, nondecreasing sweep frontier,
`min(lo0, lo1)`, before considering either class. Do not discard the other class's
occupancy merely because the current alternative starts one position later.
Check the proposed class's capacity against its own interval start, and keep
the existing additive objective and tie-breaking. Forget a previous assignment
only once it cannot affect any later arm.

For valid interior parity-snapped crossing lists, each class's starts are
monotone in this sweep order, and the two possible starts differ by one. These
properties give the usual interval-start capacity argument. They must be tested
or made explicit in the recurrence's contract; arbitrary fallback or clipped
class intervals should not silently inherit that proof. Correcting expiration
alone does not solve heterogeneous lane feasibility or missing endpoints.

Before integration, compare full assignments and minimum cost against exhaustive
small positive-crossing interval cases, including ties and genuinely infeasible
lines. Independently check the actual seating, not just the reconstructed DP
history. Preserve the four fixtures above, then cover boundary and defective-lane
claims separately or narrow the documentation. No benchmark-selection logic,
different objective, or fallback embedder is needed for this correction.

Self-critique: the previous recurrence achieved some of its small state size by
forgetting necessary constraints. Retaining them may increase states and CPU
time; a fixed maximum number of active arms does not by itself imply a tiny
number of possible states. Record peak state count and converter wall time on
frozen inputs before making a speed claim. A feasible raw conversion can also
alter completion and later search, so a unit-level fix does not guarantee lower
final ACL. Keep 033 frozen and interpret a subsequent corrected-converter screen
as a separate revision, without rewriting earlier results.

Root reran the saved artifact verifier on2026-09-08 after independently reading
this review. Only its write-once output destination was redirected to
`root_verification.json`; all original artifacts were preserved. Saved hashes,
the regenerated coordinate-labelled Z12 target, and all nine disjoint physical
singleton arms with their actual required couplers passed. The subsequent035
specification strengthens the proposed capacity test to full interval overlap,
including nonmonotone class starts, before any full-pipeline experiment.
