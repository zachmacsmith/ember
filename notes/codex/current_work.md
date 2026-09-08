# Current research checkpoint

Updated 2026-09-08 22:42 UTC. Branch `codex`, goal active and unmet.
One general non-portfolio algorithm, no MM/busclique calls, ideal Z12,
competitive per-class mean ACL and roughly MM-scale cost. Optimal ACL-one
ties are explicitly acceptable. No new final-test sources have been exposed.

The [mechanism workflow](tracks/workflow.md) now requires a representation /
move-neighborhood / acceptance / cost diagnosis and a distinguishing observation
before further refinement. Full-constructor outcomes determine continuation;
partial progress alone does not. The [class gap analysis](mm_gap_by_class.md)
separates current A053 historical quality, fresh047 timing and older032 seed
variance. Current A053 versus frozen MM047 has11 wins,18 losses,3 optimal ties
and2 MM timeouts. Current-policy variance remains unmeasured pending056.

- **A / literature:** Retain A053. Both054 and055 are reviewed and not promoted.
  [055](experiments/055_results_screen.md) completes18/18 valid/timely calls:
  four wins,three losses,two ties, Q3494→3503 while macro ACL2.742192→2.737235
  slightly improves; solver47.055→46.783s. Preserve this metric disagreement.
  Stop reduction eligibility/order tuning. Next bounded design review targets
  compact embeddings versus inherited constructor/search reach, without code
  or calls yet. A currently handles the combined B/C registry update and one
  passive diagnostic-map logging field before returning to that review.
- **B / algorithm_audit:** [B019](tracks/b_019_results.md) passes four small
  complete-constructor gates, including actual triangle overlap resolution.
  [B020](tracks/b_020_control_gate.md) resolves the same triangle with a single
  witness change, so paired-neighborhood benefit is unproved. Root reads the
  full constructor and minimal control diff/checks; all34/50bindings pass.
  [27-call B9 protocol](tracks/b_020_contact_screen_protocol.md) is approved:
  paired contacts,single-primary control,freshMM,seed0/60s on02. No control
  output is selected as a fallback. Registry/freeze/launch are pending.
- **C / benchmark_audit:** [Elementary variable occupancy](tracks/c_variable_occupancy_constructor_results.md)
  fails triangle→cycle6 at24visits withM1/Q3, despite ample remaining time.
  A saved valid Q6 completion has elementary energy increments+.25,+.25,−.75.
  The approved [atomic-growth discriminator](tracks/c_atomic_growth_constructor_proposal.md)
  passes all four tiny gates: same initialization/visits0–1, then one path with
  ΔM−1,ΔQ+3,ΔE−.25 completes the cycle. This supports larger growth proposals
  under unchanged energy; it does not prove broad constructor quality.
  Atomic/elementary/MM C8screen,24calls,seed0/15s on04 is approved pending
  stable preparation/registry/freeze. No temperature/cap/schedule adjustment.

055 is terminal/retrieved:192files,digest4b3fcda430a34aaec72d670b26960cc2666b1bfa2589fa1a4155b761b29b4952,
controller203360 finished1788906802.8006332,lockfree/tmuxoff/supervisor0.
One saved analysis passes; root reads report/checkers and all23finalbindings.
No candidate rerun. Root owns remote transport for all tracks.

**056 baseline replication is detached/running on06** (within track A, not a
fourth algorithm):272calls,34structures,seeds0–3,A053 versusMM,60s each.
New isolated Python3.11.2 environments3c7aa36653394e61 prepared once. Source
snapshot0d5b77e35a196734c7b5a3526c2247ae7a6da5e230d2fb6b81b01f2b961ca9a4.
Controller55147, tmux ember-codex-160f709fe24a52ef3cdf, start1788906940.7068093,
outer24780s. Status001:4/272SUCCESS,lockbusy/tmuxalive. Observe existing handle;
never restart because SSH disconnected. [Protocol](experiments/056_current_policy_seed_replication.md).
Do not pool06times with03/04/02. Sudoku has only older029 supplement evidence;
no current A053 observation yet. Preserve its separate provenance in follow-up.

Latest commits:cc2a7b2e (A055 plus user prompt/workflow/gap analysis),ad541c7a
(B019 and C elementary/certificate/atomic proposal,056protocol). The root gap
analysis script uses saved audited outputs only; no new oracle or solver.
All claims remain exploratory. No source-generalization, novelty, current
seed-variance or across-class MM superiority claim is justified.
