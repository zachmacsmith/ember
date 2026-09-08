# Cyclic deletion-seed continuation

Implemented the scheduling-only [048 hypothesis](experiments/048_cyclic_vacancy_hypothesis.md). `native_embed(vacancy_refinement='cyclic')` requires the existing supported final-deletion configuration. The explicit pilot method is `native-search-joint1-contacts-spectral-vacancy-cyclic`; its configuration differs from the bounded vacancy control only in this policy value. Existing `'off'` and `'bounded'` paths retain their diagnostic schema and behavior.

Native freezes the priority of **all** source owners once, by decreasing entry chain length, decreasing source degree, then canonical owner ID. Priority setup occurs inside the unchanged stage deadline and is reported as `priority_setup_wall`. Including every owner makes the order a complete structural ordering; eligibility is evaluated from the current chains on every query. One 50,000-proposal budget, the original fixed stage wall allowance, the 20-success ceiling, and the existing independent candidate/final validators remain.

The internal core accepts optional `owner_priority` and `cursor=(owner, site)` arguments. With these supplied, it builds the complete current eligible seed list in fixed owner/current-site order, selects the first strictly greater key than the cursor, and rotates once. A missing cursor site is handled by its position in that order. Newly acquired sites enter the current list; singleton chains and chains above the existing 64-site eligibility bound are excluded. No failed-state cache is introduced. The repair beam, missing-edge update, transfer neighborhood, ownership/site/depth/beam/proposal limits, certificates and first-success return are unchanged.

The native cursor advances only after a timely independently validated Q-minus-one candidate is committed. Failed, invalid or late candidates leave both the current valid embedding and cursor unchanged. Every query still stops at its first candidate or existing failure/work/deadline condition. The complete planned list is `seed_schedule`; `seeds` remains the actual inspected prefix. `rotation_index` and `wraps` describe the **planned schedule**, not proof that search reached the wrap before stopping. An interrupted list construction leaves `seed_schedule_complete=False` and publishes no partial schedule. Sorting, copying, setup and unsuccessful search consume elapsed time; proposal counts retain their earlier meaning.

**Targeted checks:** 33/33 PASS in 1.18 seconds, no prohibited imports, and all tested source hashes unchanged. This includes the existing 20 stage/deletion integration checks and 13 cyclic checks: absent and present cursors, wraparound, singleton cursor owner, new sites, 64-site eligibility, interruption before schedule publication, exact frozen-core/default replay, policy/config wiring, frozen priority after chain lengths change, shared-budget exhaustion, and late-gate cursor rollback.

The actual two-contraction fixture joins two copies of the previously reviewed five-cycle witness through their free sites. Neither initial center has a safe single deletion. The real core and stage independently validate Q=8 → 7 → 6; accepted cursors are `(0,10)` then `(3,20)`, and the third query has no eligible seeds. Inputs and every intermediate returned minor are checked independently. This is a supplied tiny physical graph, not a Zephyr benchmark or quality claim.

```sh
.venv/bin/python -I -B results/codex/cyclic-vacancy-checks/run_checks.py results/codex/cyclic-vacancy-checks/NEW_ATTEMPT
```

The runner refuses an existing attempt. Small reference files under `cyclic-vacancy-checks/reference` are byte-identical copies of frozen 047, with origin hashes in their manifest; they must be retained with the tests for fresh-checkout replay. No corpus, constructor, MM, remote, or exhaustive search was invoked by these checks.

Stable SHA256:

- Core: `ab3f7221c5ebd5af8800c8f7b80f8b9815200bb4a86a63274e4bf0a48627124f`.
- Native: `496b54221c2ea77710dc6979fc7f9a202af995c51d029134bdbe6b703764a225`.
- New tests: `19c1370343ac879709f5fa38ff5e18aa604531dadd1082c4cd0e2a3d01a3164d`.
- Pilot: `f560276b991792ad95af7a59bbbb7c1db2569f885c30dda83c487daacdf9e660` (also contains the separately tested B005 constructor registration).

**Limits:** This is conventional cyclic scheduling. Earlier failures may become productive after a repair; moving past them can worsen final quality. A full seed list costs O(Q) storage and traversal per query, plus the fixed priority setup, and that cost is inside the short wall allowance. Frozen priority can become less appropriate as chains shrink. These tests establish correctness of continuation and preservation of the existing control, not an improvement on the development inputs. The 048 paired experiment remains the falsifier.
