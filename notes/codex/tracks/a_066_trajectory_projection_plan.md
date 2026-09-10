# A066 initial-screen incumbent trajectories: bounded passive projection

2026-09-10. Prepare a projection of the completed first screen only. No running
broader results, candidate imports, constructors or validators are used.

For A066, pruning-only and A065, retain every saved admission's elapsed wrapper
and operator time, Q and ACL. The wrapper has one successful A061 handoff before
the added stage. Its observation lies between the recorded base interval and
the added-stage meter's start, derived consistently from each saved admission's
two elapsed times. This is a bound for the wrapper's first reported valid-base
handoff; the earlier discovery time inside A061 is unrecorded. Intermediate maps
are not independently revalidated by this projection.

A strict-Q admission sequence permits identification of when the eventual final
Q first appears. Report that timestamp and the remaining observed operator time
afterwards. Keep full solver/process wall as separate headline costs: this is
not an early-stop rerun or evidence that the same result would be returned by a
new shorter-budget policy. No time cap or algorithm change follows automatically
from a flat saved trajectory.

Use all 27 native calls on the same nine encodings (eight structures), seed 0.
Existing common audit owns success, final Q/ACL and all-call timing; the corrected
mechanism audit owns admission chronology and disjoint phase accounting. Read
only their frozen completed outputs and create scalar JSON/CSV artifacts. Charge
all projection work; allow at most 30 seconds with an outer 45-second lifetime.
No iterative rescan, new sample selection or interpolation of unrecorded first
validity. Freeze source/input hashes and review before execution.
