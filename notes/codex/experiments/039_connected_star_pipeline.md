# Connected-center rule in the complete embedding pipeline

Draft protocol, 2026-09-08. No 039 source/input freeze or launch yet. The core
is committed as `6044e200` and has passed its 43 focused checks, including root's
repeat; independent core review and scheduler integration checks remain pending.
This protocol fixes the intended comparison before seeing its corpus outcomes.

The hypothesis is that one connected center with exactly assigned singleton
leaves can shorten source blocks unavailable to a singleton-center operation,
including centers above the target maximum degree. This changes one local
proposal rule within the existing constructor/refinement pipeline. Neither arm
calls MM or busclique, consumes competitor output, chooses among constructors,
or dispatches by graph family. No pair of resulting embeddings is combined.

Use the same 34 original development inputs and exact ideal Z12 target as 037.
Retain all 35 family memberships, the linked king/frustrated-square structure,
and the explicit absence of the malformed original Sudoku inputs. Do not
substitute supplemental Sudoku or drop a graph based on degree, expected
eligibility, previous losses or the new rule's measured cost. Source labels and
every target/source edge must match the original selection. These inputs are
development structures; this run cannot support a claim about unseen graphs.

The control is the current globally fixed spectral constructor with corrected
physical conversion and legacy singleton/contact refinement:
`native-search-joint1-contacts-spectral`. The treatment uses that exact
configuration with only `polish_star_policy='connected'`. The treatment invokes
the connected core in the existing failed-ordinary-visit schedule, once per
center per pass. It uses one root, the fixed greedy independent leaf subset,
demand classes, at most four successor trials (stopping on the first zero
deficit) and the specified BFS. It does not invoke
the singleton-center proposer as well. Both arms retain four contact passes,
512 total ordinary groups, group sizes 1–4, 500,000 shared work units and the
existing per-visit work limit. Treatment auxiliary setup/query/refresh uses
at most 25,000 of those shared units and has no separate 2,048-unit query cap.
The proposed additional auxiliary allowance in the allocation note is excluded.

Run one recorded seed, zero, per input and arm: 68 calls total, each with the
same 60-second solver deadline. Use the pinned native environment on hyde03,
one worker at a time, fresh process/cache per call, fixed single-thread settings,
adjacent within-input control/treatment pairs and a deterministically shuffled
input/arm order saved before launch. The input list is formed by
`random.Random('ember-codex-039-input-order').shuffle(sorted(graph_keys))` and
passed explicitly through the pilot's `--graphs` argument; the pilot itself
does not shuffle inputs. Within each input/seed, retain its existing
`random.Random(f'{name}:{seed}').shuffle(methods)` rule, starting with control
then `native-search-joint1-contacts-spectral-connected-star`. The predeclared
list and rules are saved in `results/codex/039-protocol/graph_order.json`, SHA
`8be5feff3102f38801ab32abf4efc17c9967aa22cc11b63e3969b955d01151fc`. Freeze and verify that order with the task matrix.
No pilot reruns, unrecorded warmups, preferred
seed selection or retry after a timeout. Preserve late/partial embeddings and
failure details. Use the existing detached cluster supervisor, inherited task
locks, process watchdog and quiescent hash-verified retrieval. Final output
uniqueness is enforced by the controller/claim policy: the existing atomic JSON
writer uses replacement, so it is not itself a non-overwriting primitive.

Before launch, freeze the integrated git revision, complete source map,
normalized graphs, target, environments, task matrix, configuration and this
protocol. The pilot bundle supplies normalized graphs and both selection
ledgers; it does not itself copy raw originals or label-map files. Separately
freeze/hash-check the original graphs and label maps as evaluator-only inputs,
using the independently audited 038 original records and checking their exact
agreement with the new task matrix. The workers never consume these extra
evaluation files or prior embeddings. Verify the off-policy path retains its prior behavior and the
new mode invokes exactly one connected search object. Independent review must
check the original-edge/Q/R/member-growth certificate, deadline before commit,
refresh failure handling and the shared budget accounting. Current core-only
checks do not satisfy the integration requirement. Only root launches the run.

The primary table contains every input's status, original-graph validity, Q,
ACL, maximum chain length and solver/process wall for both arms. Report paired
lower/equal/higher ACL and total Q, plus the arithmetic mean of per-input ACL
over an explicitly stated common-success population. Preserve unmatched
failures separately; do not treat them as numerical ACL values. Identify
proved degree-bound optima among ties. Family tables preserve duplicate
membership without counting the linked structure twice in the aggregate.
One seed supplies no across-seed ACL variance estimate. Same-host timing is
descriptive under observed load; historical local/remote runs are not timing
controls, and this experiment contains no MM arm.

The mechanism audit must reconcile constructed Q, pruned Q, ordinary savings,
connected-rule savings and final Q. Check actual signed R and member-growth
counts, covering assignments versus returned certificates versus committed
moves, selection/stop reasons, root/growth/BFS behavior and distinct demand-class
counts. Setup + query + refresh must equal auxiliary work, and ordinary +
auxiliary must equal each visit's total and the global total. Include work spent
on disabled or unsuccessful attempts. Record queries that exhaust the entire
allowance; that outcome must not be called an exhaustive block-infeasibility
proof. Unsaved intermediate embeddings cannot be independently reconstructed
from scalar trajectory summaries and must remain an explicit audit limit.

Self-critique: a larger local search can consume the shared budget early,
displace productive ordinary moves, or change later trajectories even after
locally useful commits. The one-root rule remains incomplete. Group selection
can be ineligible in dense graphs and still cost work. The full pipeline may
therefore worsen despite strict improvement in every committed connected move.
Report those regressions; do not justify promotion from local savings or the
best graph alone. If the whole-pipeline result is weak or adverse, preserve the
mechanistic lesson before changing a general rule in a separate experiment.
Any useful result still needs solver-seed replication, new graph instances and
a fresh same-host MM comparison before an across-family research claim.
