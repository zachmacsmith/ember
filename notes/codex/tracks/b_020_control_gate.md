# B020 control gate and panel preparation

The single-primary control resolves the same triangle overlap as B019, confirming that this tiny success does not require paired witness changes. One complete control call was made after the [pre-code specification](b_020_neighborhood_control.md); no B9 call or remote action occurred.

| Triangle→triangle, seed 0 | Q/O start→finish | Queries / combinations | Total / query units |
|---|---:|---:|---:|
| B019 paired, earlier saved gate | 4/1→3/0 | 6 / 96 | 8,715 / 8,440 |
| B020 single, this call | 4/1→3/0 | 6 / 24 | 1,979 / 1,734 |

The single control changed only witness `(1,2)` from `(2,0)` to `(2,1)`, leaving final chains `{0:[0],1:[2],2:[1]}`. All queries completed; no cap or deadline bound. The call took 2.364 ms, including 1.907 ms in queries; these tiny across-call timings are not an MM or panel speed claim. Independent original-graph validation, exact Q/O/energy, input nonmutation and nested work/deadline checks passed. No prohibited embedding import occurred. Full observations are in [the raw record](../../../results/codex/track-b020-contact-control/attempt003-case/triangle.json).

Two new checks establish AST equivalence to frozen B019 except scope/identity, and single-primary dispatch with no partner lookup and exact metering. An initial runner path-substitution mistake unnecessarily reran the nine inherited tiny checks; all passed, and no full paired constructor was called. That attempt is preserved. Corrected dispatch then ran only the two intended checks. This was a testing-workflow deviation, not a candidate or policy change.

The [27-call protocol](b_020_contact_screen_protocol.md) and [preparation manifest](../../../results/codex/track-b020-contact-control/prepared/manifest.json) bind the exact nine B011 source files, target, method order and candidate bytes. Preparation imports no solver and creates no controller. Registry and complete executable source freeze remain pending root review. Both policies will be judged on all final results; overlap reductions alone do not justify another refinement.

Stable source: paired `86d5b6dc…`, single `09a009c9…`. [Artifact manifest](../../../results/codex/track-b020-contact-control/artifact_manifest.json) binds full hashes and retained attempts. Repeat only the new targeted checks into a fresh directory:

```
.venv/codex-native/bin/python results/codex/track-b020-contact-control/run_checks.py /tmp/b020-control-review-001
```
