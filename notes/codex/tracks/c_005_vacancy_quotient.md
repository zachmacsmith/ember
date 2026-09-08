# C005: constant-size region movement through unused target sites

**Hypothesis.** C004 retained sparse construction and reduced Q, but its immutable outer target boundary may obstruct harder source contacts. Keep its one compact allocation and total occupied-site budget. Add a joint move that places an unowned target site into a region and releases a safe site from that same region. This can move regions beyond the initial BFS domain without increasing Q, restarting construction or trying another subset size. The state remains one connected, disjoint region per source vertex; missing logical contacts are permitted during construction.

```text
create the single C004 compact allocation and source assignment
map its connected regions into the original full target
repeat a fixed three-visit cycle while original edges are missing:
    missing-contact-directed whole-region label exchange
    safe transfer of an owned boundary site between regions
    joint free-site addition and safe same-region site release
score the exact change in distinct represented original source edges
accept nonincreasing missing count, or the unchanged temperature-0.5 rule
update ownership, coupler counts, missing edges and connectivity caches
validate the first complete minor, delete unnecessary sites, validate again
```

For a free-site exchange into region u, the new site must neighbor its remaining chain. If u was a singleton, the new singleton is connected. Otherwise the released old site must be nonarticulating in the old chain; this is sufficient, though not necessary after adding the new site. The final site count is unchanged. Scoring subtracts old-site external couplers and adds new-site external couplers, but counts an original edge only when its physical contact crosses zero. Multiple couplers to one neighbor are not multiple represented source edges. No production call to earlier constructors or external embedders occurs.

C004's distance cache assumes a fixed connected occupied domain and is unsuitable once vacancies move. Instead, each site visit uses a BFS on the original target that stops after reaching its bounded set of nearest eligible frontier candidates. Owned transfers score at most sixteen sites; free exchanges score at most eight new sites and eight eligible releases per new site. All eligibility scans, BFS traversal, rejected scores, atomic commits and final copying share D. Swaps retain eight candidates. These bounds and the three-visit cycle are fixed before the screen; there is no runtime method selection. The input preparation, initial factor four, deadline reserve and final deletion policy remain C004's.

**Self-critique/prior art.** Region swaps/shifts and free-space movement overlap with PSSA/Bian and other local embedding searches; novelty is unresolved. Interior regions may initially have no free boundary site. Constant Q can still be too small, and moving through a vacancy can temporarily destroy useful contacts. The safe-release rule excludes some legal moves that reconnect an articulation through the new site. Truncated BFS can still examine most of the target on an unfavorable query. The changed site-query implementation is required by the moving domain and will be charged rather than presented as an isolated speed improvement. The alternative distinct-quotient-neighbor coarsening proposal remains separate; it is not bundled into C005.

**Cheap falsifier.** Before corpus calls, independently recount tiny joint-move contact deltas, connectivity and Q; test singleton movement, rejection of disconnected releases, crossing the old domain, interrupted scoring versus atomic committed work, and full-target final validation. Use the unchanged eight development inputs, ideal Z12, seed 0, 15 seconds and fresh paired MM on hyde04. Retain all four C004 successes and seek either one newly valid harder input or at least a 50% reduction of final missing edges on two of the four harder inputs. Otherwise this fixed move policy is rejected. No failure proves original Z12 infeasibility; no partial-state improvement is an MM quality win.
