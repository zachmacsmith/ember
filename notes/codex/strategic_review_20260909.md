# Research decision after inspecting MM and the retained embeddings

2026-09-09 UTC. **Keep A061 as the single retained algorithm. Redirect research
toward coordinated physical contact placement and reconstruction.** The recent
fixed refinements do not advance the class-level objective. This review finishes
the two previously launched runs; it launches no replacement constructor or
guarded-connector diagnostic. All evidence below is exposed development.

The [retained per-class table](mm_gap_retained_a061.md) is the progress baseline:
34/34 valid A061 outputs versus MM29/34 in the breadth cohort; on 29 common
successes, eight lower-Q results, seventeen higher-Q results and four optimal
ACL-one ties. The five MM timeouts have no finite ACL comparison. This is one
seed, so across-seed ACL variance is unknown in this cohort. Separate replications
retain planted/wheel/hypercube failures and variance results; neither constructor
versions nor hosts are pooled. Sudoku remains explicitly unmeasured for A061.

| Persistent deficit examples | A061 ACL / MM ACL | What the saved map reveals |
|---|---:|---|
| Grid | 1.273 / 1.047 | 22 of29 excess sites belong to degree-four owners; most excess is on core owners. |
| Honeycomb | 1.268 / 1.032 | 40 of45 excess sites belong to degree-three owners; no individual site can be deleted. |
| Wheel | 1.472 / 1.157 | 37 of40 excess sites lie on the degree-three rim, rather than the hub. |
| LFR | 1.700 / 1.600 | Lifted owners use13 extra sites while core owners use3 fewer; no individual deletion starts. |
| BA | 3.475 / 3.361 | No elimination occurs; MM has more branching yet fewer sites. |
| Planted | 1.188 / 1.023 | More long low-degree chains; no individual deletion starts. |
| Planar contrast | 1.711 / 1.849 | A061 wins despite necessary contactless connectors and higher maximum chain length. |

The complete class table retains cubic+71Q, hardware-native+61Q,
king/frustrated+56Q, Kneser+44Q and every other loss. These were not all given
the seven-pair structural diagnosis. Dense wins cannot cancel their deficits.

**What we now understand about MM.** The [exact stock source review](stock_mm_capabilities_review.md)
verifies minorminer0.2.22 against official distributions and both comparator
hosts. MM removes and reconstructs a whole chain against all neighboring chains,
shares connecting branches, can move contact-bearing pendant segments between
owners, and continues restructuring after feasibility. Its quality search
evaluates actual reconstructed chain sizes. The public wrapper's effective
chainlength patience is ten, not the C++ fallback of two. We inspected stock
code and saved outputs offline; no MM map enters candidate initialization.

The [saved profiles](tracks/c_a061_static_map_results.md) show that MM packs
several original-neighbor contacts onto more singleton sites in grid/honeycomb
and wheel. The [fill projection](strategic_fill_diagnosis_results.md) locates
deficits in both core and lifted owners. MM's arrangements often do not satisfy
A's temporary fill contacts, but this proves only incompatibility of those
particular arrangements. BA loses without fill, and planar wins without fill.
Consequently neither another fill threshold nor removal of branches is a
sufficient general explanation. Whole-chain and contact-boundary mobility is
a supported capability to investigate, **not a proved cause or new invention**.

**Resolved experiments and stop decisions.**

- [B025](tracks/b_025_results.md) rejects nonincreasing current-price acceptance:
  2/9 valid versus B0236/9 and MM8/9, with worse Q on both common B successes.
  It rejected2312 complete moves, none a scored zero-defect proposal. All seven
  failures reach the search deadline below the work cap; these are not the early
  pass stops of previous B policies. The added comparison costs0.258s; changed
  trajectories double routing cost. Stop this
  fixed policy and numerical acceptance tuning without a new mechanism question.
- [C011](tracks/c_011_results.md) resolves the unused-wall explanation for the
  fixed clone policy: both arms2/8 versus MM6/8. Raising useful search exposure
  from0.333–0.659s to14.502–14.515s adds no success. Stop clone splitting/local
  revision in this form; no further cap increase follows from partial placements.
- A062's ready ordering remains rejected, including its recovered failures,
  new planted failure and grid/wheel regressions. The held three-site connector
  draft remains untested. Stop the sequence of lifting-only numerical repairs.
  A061's branch stage remains retained because modest improvements survived
  complete-output checks, not because of intermediate contraction counts.

**Allocation decision.** The [cross-track cap audit](strategic_allocation_review.md)
finds no empirical calibration for a universal20M work allowance or three-times
MM gate. A local1M repair can end a constructor at4–6s of60s; B's eight-pass
schedule can end sparse attempts at4–11s of20s. B also hard-clamps its own deadline
to20s. Those restrictions leave specific alternatives unobserved. C011, in
contrast, actually tests an allocation change and remains negative.

Future experiments use wall/CPU and complete outcomes to judge allocation;
counters remain diagnostics unless an active backstop has measured justification.
Freeze each experiment's wall, search restrictions and reporting before outcomes.
Document later changes under a new identity. A cap-limited failure may receive
one bounded follow-up when it discriminates a stated question; previous failure
and regression rows remain. Do not silently retry with larger limits. Use a
common60s outer envelope for the next small complete screens, already used for
the retained baseline, with measured internal deadlines and all-attempt timing.
This is an exploration envelope, **not** permission to call a60s candidate
competitive with subsecond MM. Report per-input solver and process ratios and
time-to-first-valid/quality progress where recorded. There is no universal3×
promotion cutoff. Any active internal work cap must first be calibrated in
small target-process trials including unsuccessful work and certification.

Three independent tracks continue, with the following design questions. These
are strategic candidate cards; their exact operator contracts and experimental
parameters must be written before implementation. No independent outputs are
combined, and no source-family labels, IDs or canned embeddings are inputs.

| Track | Hypothesis and pseudocode | Self-critique and cheap disproof |
|---|---|---|
| A: retained constructor, original-contact reconstruction | The valid inherited map is trapped by fixed contact locations. Run the unchanged constructor once; visit owners under original constraints; privately release a whole chain and eligible neighboring contact-only suffixes; jointly reconnect required contacts, redistribute boundaries, certify and accept smaller actualQ. Use one valid evolving map. | This cannot recover an incomplete core/lifting call and adds time to an already slow base. Strict improvement can block neutral sequences. First test the elementary boundary-transfer risk, then a small complete-constructor comparison containing sparse deficits, BA and planar plus fresh controls. No completed lower-Q reconstructions on varied inputs rejects this neighborhood; censored queries implicate cost instead. Do not claim A/B independently establish different mechanisms. |
| B: fresh whole-chain construction | Joint all-neighbor reconstruction with movable contact boundaries can reach compact minors without A's filled core. Initialize its own state; rebuild selected owner trees with shared paths and movable neighboring stems; allow explicitly defined temporary defects during feasibility; preserve a valid incumbent once reached and continue actual-Q restructuring within the same trajectory. | This overlaps established MM capabilities; a transcription is not a publication contribution. B025 shows that mandatory weighted-energy nonincrease is not an established feasibility rule. Routing each neighbor overZ12 may dominate time. Tiny shared-path/stem cases precede a complete diverse screen. Record exercised boundary moves, complete validity/Q and time, not merely defect decrease. Compare frozen-boundary and mobile-boundary variants only if the full operator is promising or attribution remains decisive. |
| C: fresh Zephyr frontier construction | Introduce source vertices and realize contacts together near a moving physical frontier, letting compact low-degree chains close early. Choose one structural ordering and sweep; keep unfinished chains connected to the frontier; place births using exact rail/coupler contacts; jointly revise movable terminal suffixes when blocked; advance the frontier and close fulfilled owners. No whole-tree rip-up or independent restart. | Wide source frontiers may force long chains on dense graphs or expanders, and fixed windows may exclude good embeddings. Geometry indexing alone is not the mechanism. Tiny full path/tree/grid and coordinated-contact cases precede a complete screen with dense and sparse inputs plus hidden feasible controls. Attribute extraQ to contact creation versus frontier carrying. Retire if carrying/ordering restrictions dominate without complete cross-structure benefit. Window/suffix limits require explicit reach and cost tests before becoming active defaults. |

For every track, distinguish: a representation exclusion (a supplied diagnostic
state/witness cannot be expressed); a neighborhood exclusion (a valid better
arrangement exists outside allowed revisions); an acceptance exclusion (an
actually generated admissible proposal is rejected); and a cost stop (the
relevant search is not completed). Failure to find a proposal alone proves none
of the first three. Bounded exact neighborhood solves are optional instruments
for that distinction, never constructors. One coherent redesign may change
complementary representation, move and scheduling mechanisms together; use
controlled ablations for a specific causal question, not as a prohibition on
coherent design.

**Transfer starts with the next complete screen.** Repeated examples remain
diagnostic anchors; they cannot be the sole development panel. Before calls,
freeze fresh generation attempts spanning sparse/local, community, hub and
dense structures at two sizes, plus at least one relabeling on both an old and
a fresh structure. Use the [proposed generator and exposure controls](tracks/c_strategic_evaluation_controls.md)
to make the exact small manifest. Select without candidate/MM outcomes, retain
generation failures and deduplicate or label unresolved structural identity.
Start with a small subset, then the full proposed two-size panel only if useful.
Require fresh structure evidence in the first continuation decision, not after
another long refinement sequence. Relabelings and solver seeds are nested
replicates, never fresh graph counts or output selectors.

Include four known-feasible controls: two singleton target subgraphs and two
connected-branch quotients. Hide witnesses and target-derived labels from the
candidate runtime filesystem; only the evaluator holds the maps. Singleton
witnesses certifyACL1, other witnesses only an achievableQ bound. They diagnose
search failure, not representative class performance. No such control has been
generated in this review. A separate confirmation set remains untouched by
creating/sealing it under an independent evaluator after candidate and analysis
freeze; current inherited/diagnosed inputs are exposed. Uncertain identity is
not called clean. Opened confirmation outcomes become development thereafter.

Continue using isolated dependencies, existing independent original validators
and failure/time accounting. Add checks for new ownership-transfer, frontier or
deadline risks only. Use02/03/06 for independent tracks and available spare
workers for separate instances/seeds; run paired methods on the same host,
retain load and environment identities, and supervise detached jobs through01.
Do not count cross-host time differences as algorithmic gains.

**Exploration versus promotion.** A completed negative policy stays rejected.
A mechanism follow-up needs a specific explanation supported by its completed
data and a bounded discriminator. A promising diagnostic moves promptly to a
complete screen. Advancement requires an original-valid quality/success benefit
on more than repeatedly used examples, transparent costs and every regression
still visible. It does not erase a regressing class or promote that version over
the retained algorithm. Replacement of A061 requires broader per-class evidence
that resolves regressions and repeat-seed uncertainty; final superiority needs
the separate confirmation evaluation. Optimal ACL-one ties are acceptable.
Mean ACL, variability, success and runtime remain separate columns, never a
dense-weighted aggregate score.

Plan self-critique1: the first synthesis nearly treated A/B as distinct novel
mechanisms and proposed vague geometry acceleration forC. Revision: separate
A's valid-state quality question from B's fresh construction question, acknowledge
their common mechanism, and defineC's distinct frontier/contact schedule and
its likely dense-graph failure. Novelty remains unestablished.

Plan self-critique2: diagnosis-selected examples and lifted-vertex repairs could
again consume the cycle without transfer or complete construction. Revision:
retain the full class table, require fresh inputs immediately, preserve BA and
planar counterexamples, charge upstream core cost, and stop a direction without
complete-output benefit. The60s envelope is a frozen research allocation, not
an empirical speed claim; actual costs determine subsequent allocations.

All previously running calls are terminal. B025/C011 final reports and saved
analyses are preserved; root checked27/31 final bindings. Root additionally
checked39 cap-review,19 map-review and23 stock-source bindings, and all seven
held-draft hashes. No new candidate implementation or execution followed the
strategic-review request. The research goal remains active and unmet.
