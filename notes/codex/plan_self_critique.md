# Two rounds of plan self-critique

Both rounds precede plan finalization and all algorithm implementation. This file
records substantive weaknesses and revisions, not a declaration that the plan is
certain to succeed. The independent candidate critiques are in `candidates.md` and
the combined shortlists have separate critiques in `PLAN_CODEX.md`.

## Round 1 — review of draft v0

Reviewed on 2026-09-07 after the source, benchmark, and literature audits.

1. **The success-conditioned primary mean can reward selective failure.** A family
   mean computed over different successful graphs is not a fair paired comparison.
   Revision: base the ACL contrast on identical graph/trial sets, show joint-success
   coverage explicitly, and require a separate reliability criterion on all trials.
   Add success-quality curves counting failures as not meeting any ACL threshold.
   Do not invent a finite ACL for failure or hide incomplete pairs.
2. **The scope language risks promising coverage the corpus cannot supply.**
   Sudoku has no Z12-eligible original instance; other necessary infeasibility
   checks go beyond vertex count. Revision: record an immutable full-corpus coverage
   table, distinguish proved impossible from unknown feasibility, and investigate
   clearly labeled smaller instances generated from the same family definition.
   Never replace or erase original infeasible instances to obtain an all-family claim.
3. **A generic local exact solver is too close to established work.** The draft
   lacks enough detail to evaluate novelty or implementation feasibility. Revision:
   specify the assignment/contact/connectivity subproblem and one shared construction
   and refinement operation; target flexible contact sets and adaptive region growth
   as hypotheses. Compare with the actual sequential repair and published IP methods.
4. **The shortlist risks becoming a disguised portfolio.** A, B and C are too easy
   to read as independently competing constructors run at inference. Revision: state
   explicitly that these are research revisions, and that the final implementation
   has one fixed path, one embedding state, one objective, and no output selection
   among independent algorithms. An internal local incumbent is not such a portfolio.
5. **A floating dependency environment makes reproduction weak.** The installed
   versions differ from the handoff and current metadata. Revision: capture existing
   versions for audit; build a fresh locked environment for new evidence. Record
   stock MM version and defaults and independently verify against official source.
6. **Quality-first budgets are under-specified.** Increasing MM's timeout may not
   increase its work when its own stopping rules end early. Revision: include stock
   defaults and a separately fixed, stronger stock-MM configuration, developed only
   on development data. Predeclare end-to-end quality budgets and distinguish fixed
   work from actual elapsed time. No favorable cross-machine time comparison.
7. **Persistence is a systems requirement, not an SSH option.** Keepalives cannot
   survive a network change by themselves. Revision: require detached/scheduler-owned
   workers, durable manifests, atomic results, reconnect discovery and a tested
   disconnect pilot. Existing cluster load and unavailable tools determine deployment.

Round-1 disposition: revise to v1, then challenge statistical validity, scalability,
and stopping rules again before finalization. No candidate code has been implemented.

## Round 2 — review of draft v1 and the concrete local model

Reviewed on 2026-09-07 after two independent agents challenged v1's implementation
and experimental design. The following are the primary agent's conclusions and
revisions, incorporating those challenges. No algorithm code was implemented.

1. **Common-success ACL plus equal success rates is still conditional.** The two
   algorithms can fail on different instances. Revision: show all four paired
   success/failure cells per graph and stratum, and restrict unconditional mean-ACL
   claims to complete common coverage. Else report conditional ACL with a clearly
   labeled all-trial success-quality endpoint; unresolved mean claims remain open.
   Predeclare a stringent reliability rule: no observed family-level regression
   and a one-sided confidence bound on excess failure below one percentage point.
   This margin is an uncertainty tolerance, not permission to trade failures for ACL.
2. **Original-corpus exposure is broader than personally inspected examples.**
   Prior full-library experiments can contaminate every original instance.
   Revision: treat the entire inherited corpus as development data. Generate fresh
   structure groups for confirmation and compare their topology against inherited
   and supplemental instances. Deterministic families with no fresh structures
   receive explicitly descriptive corpus evidence rather than a fictitious holdout.
3. **Repeated fresh holdouts do not alone prevent repeated-until-win inference.**
   Revision: record every frozen version subjected to confirmation and allocate
   alpha_k = 0.05 / (k(k+1)) to attempt k, with a predeclared familywise procedure
   and independent replication after a successful attempt. This summable policy
   makes continued research compatible with an honest significance claim. It does
   not guarantee statistical power or eventual discovery.
4. **The plan needs an operational outcome taxonomy.** Revision: freeze categories
   for supported improvement, certified optimal ties, unresolved eligible families,
   proved infeasible originals, and supplemental-only coverage. A few optimal
   instances cannot exempt a whole family. Above-bound ties and missing coverage
   cannot satisfy the project's broad objective.
5. **The local optimization is not yet a scalable constructor.** Revision: supply
   the flow/contact specification, explicit empty-state handling, model-size and
   region budgets, rollback, and status distinctions. Pilot acceptance requires
   useful construction without repeated whole-chip solves. Exactness is local;
   connectivity roots remain movable, and a timeout is not infeasibility.
6. **The final budget rule must be frozen, not adjusted to results.** Revision:
   use the pilot to choose one global budget or a prespecified size-only rule for
   both methods, fixed threads, warmup, watchdog and checkpoint boundaries. Name
   quality-first versus equal-time versus stronger-MM comparisons separately.
   Only a validated incumbent available by the deadline counts at that deadline.
7. **An import monkeypatch is not a complete no-MM argument.** Revision: use an
   isolated candidate environment without MM/forks/native modules/busclique/cached
   outputs, plus source/dependency and loaded-module audits. Ember's comparator
   environment can contain MM, but it communicates only graph inputs and independent
   outputs through the experiment controller. Exercise all failure paths.

Round-2 disposition: incorporate these revisions and finalize the plan. The
remaining uncertainty is scientific: construction scalability, region effectiveness,
novelty over prior IP/routing methods, and attainable per-family improvements. The
plan identifies experiments to resolve these uncertainties; it does not assert
that the objective has been achieved or is guaranteed achievable.

## User prompt 4 — runtime-focused revision, two further checks

The user rejected IP-led construction and clarified roughly MM-order runtime.
This supersedes the earlier interpretation of unrestricted quality-first search.
The lead mechanism is now bounded heuristic joint reconstruction; the exact model
is a small diagnostic oracle, not the runtime algorithm. Two additional checks
were completed before finalizing the revised plan:

1. **Scalability check:** replacing an IP solver with a beam does not automatically
   make the algorithm fast. Repeated tree searches, per-neighbor work, copying
   embeddings, expensive initial packing and large regions can dominate. Revision:
   cap and measure every work multiplier, use reversible local state, compare
   beam widths at equal total work/time, and require early end-to-end evidence
   roughly within 10x MM per family/size regime. Exact solves cannot rescue a
   runtime claim through excluded/off-budget work.
2. **Mechanism and claim check:** bounded beam reconstruction is not automatically
   novel or better than the existing sequential group rebuild; it may simply run
   more routing attempts. Revision: use identical constructors, regions and routing
   primitives in width-1 versus wider-beam and single-chain versus coupled ablations.
   Count improvements requiring one member to lengthen, and distinguish proof
   about that declared local move set from claims about all MM behavior. Freeze
   one constructor and one search process; no independent-method winner selection.

Both checks were informed by bounded agent critiques requested after prompt 4.
The new lead candidate receives its own pre-implementation critique in the plan
and `contact_search_spec.md`. No algorithm has been implemented during planning.
