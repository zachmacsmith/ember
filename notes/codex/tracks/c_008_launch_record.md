# track-c-008-compound-transfer: launch and retrieval

Atomic regions, compound regions, MM; eight inputs, seed0, 15seconds. Each algorithm is evaluated separately on hyde03; only fresh
same-host timings are compared. Root owns transport under
`results/codex/track-c008-launch`. One stage, one detached start, one retrieval;
no replacement run.

- Source snapshot: `ffa391885f99bccfc2babfb71ce27cdca21e7c16fd3b9160f1cbf14157182660`.
- Task manifest: `1ef39c68edb2e74b521b44b07bf24255582f83af60aecbc00aaa82758824bf58`.
- Protocol: `96b2c5105aedf6fc9dcc32147868bee15c7904ba579c17034f86f2823441180a`.
- Transport input digest: `05f0fcbd5731d8341ecea2a687d1490c5c20364d4feab34dc2da086a28f111da`.
- Start Unix: 1788913055.6443007; outer bound 1380seconds.
- Controller 211788: finished Unix1788913295.3217294; 24/24 finalized.
- Terminal lock free, detached session absent, supervisor exit0.
- Retrieved files: 228; artifact digest
  `aab7f43e3c9e69446386abc5bef605a05d4a5a6ea91df21dcc5ce796afb3945c`.
- Archive: `results/codex/retrieved/hyde03/track-c-008-compound-transfer`.

The common source freeze records the full working-tree bytes at d84ccd82,
subsequently committed in c51b4f53. Root checked copied source hashes, task
vectors and input/target bytes before transport. Shared changes are only three
algorithm descriptors; isolation, workers and original validators are unchanged.
Observation loss does not authorize a restart. Controller status counts are
operational observations; quality credit requires the independent saved analysis.
