# C016 implementation and focused transition checks

2026-09-10 UTC. **Exploratory candidate, ready for the separately frozen eight-input complete screen.** C015 remains rejected at 0/8. The [before-code contract](c_016_constructor_contract.md) defines the hypothesis, pseudocode, self-critique and end-to-end falsifier; no policy or allowance changed during implementation or testing.

The new `zephyr_admissible_contact.py` exposes `admissible_contact_embed`, diagnostic policy `C016` and algorithm `admissible_contact_domain`. It aliases C015's unchanged placement, transaction, state, capacity and certification helpers. Its own `_run` differs from C015 by exactly one predicate: every available ordinary proposal goes directly to the existing publication certificate, including proposals that empty a pending singleton domain. Actual completed placement failure still invokes the unchanged coordinated transaction. The public driver is otherwise identical apart from its name and two diagnostic identity constants. An AST comparison established this scope before execution. C015/C014/C013 and all shared correctness infrastructure remain unchanged; no imported globals are mutated in production and no prior constructor is called.

The saved C015 causal projection was read and all ten input bindings verified before implementation. C016 adds no top-K, per-owner, work-count or time gate; it retains the global allocation, final reserve, complete-private recovery and final validity rules. It is one evolving embedding state, with no MM/busclique, portfolio or external embedding initialization.

Self-review before execution: C015's placement returns `None` only for completed failures, and propagates deadlines, so the new success branch cannot turn interrupted ordinary work into a transaction. The existing certificate and net-one test still precede publication. A quickly published feasible chain can nevertheless trap future placement or worsen ACL; the complete screen must decide whether the measured computation-allocation explanation transfers. Tiny transition checks establish none of those performance claims.

The **first and only focused execution passed all three groups**, with six actual fixture-loop calls and zero public complete-constructor calls:

1. A triangle prefix in a four-cycle publishes the exact first ordinary proposal even though the final owner's singleton domain becomes empty. No transaction is called; the subsequent two-site birth completes a valid minor.
2. A real contact-unreachable ordinary failure on a split prefix invokes coordinated reconstruction and publishes a valid net-one result. A separate capacity failure records obstruction while retaining the unchanged published prefix.
3. Controlled deadline interruption during ordinary placement, failed-birth rebuilding and publication certification preserves the prior published state. Interrupted placement receipts are censored, never completed failures; no partial result is published.

Eight saved state validations pass the unchanged independent oracle on the actual introduced source subgraph, and all existing quota checks pass. This includes repeated validation of one complete fixture and an empty obstructed prefix; it is **not eight independent graph experiments**. Test injection affects only isolated test modules or fixture budgets. No prohibited import is attempted or present. Test wall/CPU are 0.005052/0.005052 seconds; enclosing process wall is 0.338406 seconds. No failed test attempt or post-execution source correction occurred. The next action is the specified C016/A061/MM Z12 screen, not another routing diagnostic.

Evidence is under `results/codex/c016-constructor-checks/`: `before_implementation.json`, `source_freeze001.json`, `risk001/{invocation.json,stdout,stderr,status.json,output/summary.json}`, and `postcheck001.json`. The freeze binds eleven inputs; the post-check record rechecks those inputs and binds seventeen files including the execution records.

| Artifact | SHA256 |
|---|---|
| Production `zephyr_admissible_contact.py` | `d3b78ab971773f9bfe9698171cb5438282a32e6579ebf466de06defcfd19eec6` |
| `tests/test_codex_admissible_contact.py` | `ce8e51cb07630db628974b8b970a04a2403e29d82d86c6f66b798057f08a1dd0` |
| Source freeze | `862bc092086fdb8e7eae0a3b37521218a7d022bd128e100f5fbd37c16eb2f6ed` |
| Focused summary | `df1588582c9f1c54f59c140b0a565774a5d3469b86dc78f1a244c3b743af34c4` |
| Post-check record | `d52da455f689963b3329ff2483fe42798b303647fca20076eae30dadef5e2a12` |
| Unchanged inherited C015 | `b870572b5bffd79f31bb0ace89e41e79ea64361d1cc346d8356f455c0063c9fa` |
