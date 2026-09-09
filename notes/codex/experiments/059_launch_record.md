# 059-branched-path-screen: launch and retrieval

A053, retained-branch path, MM; six inputs, seed0, 60seconds. Each algorithm is evaluated separately on hyde06; only fresh
same-host timings are compared. Root owns transport under
`results/codex/059-launch`. One stage, one detached start, one retrieval;
no replacement run.

- Source snapshot: `ffa391885f99bccfc2babfb71ce27cdca21e7c16fd3b9160f1cbf14157182660`.
- Task manifest: `e2a326dfa41a3ac2ac75e5398fcfe0aa663d8c05e56761b967368cb272f8082f`.
- Protocol: `aeb31dfac71dbe17c440ef96d917495758ab87eecec7e2e5e3446abf1c43f767`.
- Transport input digest: `fa31ae5002e62dc94ee9d480b236cf2e06c4e530557fba2e150c8db60a51caa6`.
- Start Unix: 1788913331.5304763; outer bound 1920seconds.
- Controller 116926: finished Unix1788913441.3674023; 18/18 finalized.
- Terminal lock free, detached session absent, supervisor exit0.
- Retrieved files: 196; artifact digest
  `fca68e7319ad407a2da3a729f480845d017d55827add5a4691303ed01ca3f4af`.
- Archive: `results/codex/retrieved/hyde06/059-branched-path-screen`.

The common source freeze records the full working-tree bytes at d84ccd82,
subsequently committed in c51b4f53. Root checked copied source hashes, task
vectors and input/target bytes before transport. Shared changes are only three
algorithm descriptors; isolation, workers and original validators are unchanged.
Observation loss does not authorize a restart. Controller status counts are
operational observations; quality credit requires the independent saved analysis.
