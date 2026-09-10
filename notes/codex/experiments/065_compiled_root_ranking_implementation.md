# A065 implementation and query preparation

2026-09-09. Root approved implementation, focused checks and one paired six-query
packet after reviewing the [before-code policy](065_compiled_root_ranking_policy.md).
The frozen approval/policy is in `results/codex/a065-root-ranking/before_implementation.json`
and `approved_policy.md`. No complete constructor or registry edit is included.

Three new production files implement the exact cost change:

- `factored/compiled_boundary_roots.py`: one uncached, bounds-checked Numba BFS
  kernel; CSR target packed once per context; compact query masks/seeds; native
  pop/arc counters published together before clock checks; unchanged Python
  final root ordering. SHA `0cc7e0c93bf38c66e7873848ef466ea69119bd075f4bcc2ef78ace20862bb507`.
- `factored/compiled_boundary_reconstruction.py`: subclass only A063 `roots`,
  import the kernel lazily under the root clock, reuse unchanged A064 `_Search`
  and copy its operator lifecycle. SHA `e6b4e9d4945d92e6695e1998c97f8403dc3e36bf274b9b48af99134d82df96f8`.
- `factored/compiled_boundary_construction.py`: copied A064 wrapper with only
  operator/name/version metadata changed; one unchanged A061 base dispatch.
  SHA `f1fc242c55a7464af62f3ac0c490df4b4037f71e49bae6fef06e1657060a44fb`.

All old candidate and shared harness/validator sources remain unchanged. The
compiled score vectors are captured only by explicitly enabled tiny diagnostics;
normal candidate receipts retain scalar cost/count data, not those arrays.

Three new-risk groups passed first execution: score/root equivalence with an
independent tiny BFS specification, 1/2/256-pop chunk boundaries and integer/index
checks; interruption after dispatch/before publication; and complete finite
commit-trace equality on the existing tiny valid path fixture plus one stubbed
base dispatch. Full independent minor validation is reused. The suite took
0.857s, outer process 2.300s, with no prohibited imports. No development constructor
ran. Exact sources/tests were frozen before checks in `check_freeze001.json`.

Extraction attempt001 failed because the new extractor passed target node lists
and source edge lists to the unchanged oracle, which expects target adjacency
sets and a source edge set. Its traceback and exact failed extractor are retained
under `prepare001`. Only the extractor's adapter changed; attempt002 passed in
2.364s. Six independently valid A061 entry maps yielded their first rankable
owners deterministically, with degrees 3/37/10/3/99/20 and no bound exclusions.
Neither extraction attempted a root query or constructor. Hidden witnesses and
MM maps are absent. Packet data contain only original source/target adjacency,
candidate maps and the selected query identities/fingerprints.

Packet manifest `19369dc3b4b577ed7fd9d5ff10c50c44fead0efd75482f5625daa8a2e5709b25`
freezes six cases in order ER80, BA160, planar80, grid128, K100, singleton80;
separate cold arms run A064 then A065 on hyde06. Each receives a 60s packet
allowance and 90s outer watchdog, under the copied 240s detached supervisor.
All dependency versions are pinned and MM/busclique absent.

The copied transport's first preflight stopped before any launch because hyde06
has no GNU time executable. A read-only executable check confirmed timeout,
tmux and busctl are present. The documented second transport revision substitutes
a 29-line `Popen`/`os.wait4` observer for complete command wall/user/system CPU.
Its own startup/output are excluded explicitly; no RSS comparison is made.
One minimal child on hyde06 verified exit7, stdout/stderr preservation and the
measured busy-loop CPU/wall. Both transport revisions, failed preflight and child
check are preserved; the frozen packet bytes never changed. Root reviewed the
new production code and timing observer before the packet result.

Revised preflight, launch, status, quiescent inventory and fetch each succeeded
once. The only launch created `ember-codex-a065-packet001`, with live process IDs
recorded at launch. No observation timed out and no experiment restarted. See
[packet results](065_compiled_root_ranking_results.md) for the complete outcomes.
