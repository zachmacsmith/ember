# Check the scope of worker peak RSS

2026-09-09, before a single synthetic measurement probe on hyde03.

C014's completed archive reports identical multi-gigabyte worker peaks on many
later, unrelated candidate and MM calls. The frozen pilot records
`getrusage(RUSAGE_SELF).ru_maxrss` in each worker before writing its JSON, while
the controller retains the preceding parsed result when it spawns the next
worker with `Popen(..., pass_fds=...)`. This is a concrete measurement-scope
concern; validity, Q and separate wall/CPU fields are not thereby invalidated.

Hypothesis: pre-exec memory inherited from the parent can raise the worker's
reported lifetime high-water mark even when the executed child uses little
memory. Pseudocode: in one fresh native Python parent, launch a minimal child
using the pilot's relevant Popen/pass_fds pattern; retain and touch192MiB in the
parent, launch the identical child; release that buffer and launch it once
more. Record each child's ru_maxrss and current/high-water RSS from /proc,
parent memory observations, exact code/environment and all process costs.
No embedder, shared harness edit, benchmark rerun or MM dependency is used.

Cheap falsifier: unchanged child lifetime peaks despite the live parent buffer
would refute this proposed explanation under the measured spawn path. Increased
ru_maxrss with unchanged current child RSS would support the scope concern.
Self-critique: one Python/kernel/spawn environment cannot establish all-platform
semantics or reconstruct historical algorithm memory peaks. Preserve the raw
benchmark values and report unresolved attribution; do not subtract a guessed
parent contribution or change frozen runs.


The first probe passed on hyde03's pinned native Python3.10.12. All three
children exited0 with empty stderr; total remote wall0.176s, parent CPU0.122s.
Before allocation, child ru_maxrss was11,008KiB and /proc VmHWM9,296KiB. With the
parent retaining192MiB, child ru_maxrss was207,616KiB while its executed image's
VmHWM was9,032KiB. After releasing the buffer, child ru_maxrss remained207,616KiB
while VmHWM was9,340KiB and parent current RSS had returned to11,224KiB.

This directly supports inherited lifetime-peak contamination under the actual
Linux/Python spawn pattern, including after the large buffer was released.
Existing `peak_rss_bytes` values cannot establish algorithm-specific memory
requirements or compare algorithms without additional measurement. This
supersedes unqualified per-algorithm RSS interpretations in prior result notes,
including A064/B028; all original fields and files remain unchanged. The probe
does not reconstruct or subtract historical memory, and its /proc observations
are specific to this measured environment. The worker reads ru_maxrss before
JSON writing, so that field also omits any later serialization peak in that
worker. Solver wall/CPU, process wall, original embedding validity and Q use
separate measurements and are not invalidated by this finding.

Evidence: `results/codex/rss-scope-diagnostic001/attempt001`, first invocation,
stdout, stderr and status; probe SHA256
`7ad5c175278bfcfc22367e09e411a256a090fd055bfabccba12e7dfc4b442d3e`.
No shared harness was changed and no benchmark was rerun. Future memory work
needs an explicit executed-image metric plus a focused spawn-scope check.
