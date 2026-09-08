# Root review of the isolated ownership-exchange prototype

2026-09-08. The isolated implementation passes its bounded correctness review.
This accepts a proposal generator for the next reach/cost experiment, not a
change to the native algorithm or evidence of better Zephyr embeddings.

Root read the complete module, accepted specification, author implementation
note, independent 191-line oracle, complete independent verifier, fixture
definitions and final independent review. No unresolved implementation defect
was identified. The source is
`015781019833ee5a3f49dcec5a189161104003224b1327b44cedda6e084532bb`;
the author tests are
`6654d95dd6cf6ef561c5d901b6088f41a3072b5553700e77814ada1c17516b03`.

The author reports 38 passing checks. The independent final run is **attempt003**,
with ten passing groups, 10,476 exact public-result comparisons on valid tiny
minors, 5,424 exhaustive-domain complete-generation checks, a twelve-child
global-ranking example, nine larger fixtures, 618 work allowances, 630 clock
prefixes and 250 direct generation/rollback prefixes. The independent certificate
and trace checks use original graph edges. These counts describe different,
partly overlapping checks and must not be summed into a claim of independent
instances. The tiny exhaustive positive results all have depth one; the separate
two-swap fixture supplies deeper physical evidence.

Root verified every one of the 28 author-manifest and 64 independent-manifest
file records, including retained failed review attempts. The manifests have
SHA-256 `1b4c1952a37e910aca75aff0ecb311a5681f70833d8457dfe8851f7ab17c09bf`
and `ffd5d63ee1bfd7abea8797e034e6210a1667e5a843364451b9043e45347295f6`.
The readback is saved at
`results/codex/ownership-exchange-root-review/artifact_readback.json`.
The independent suite was not repeated after its passing final run: source
reading and artifact verification raised no new concern requiring another run.

The API shares one immutable entry validation across a finite ordered group
batch, preserves input and parent state under interruption, fully generates and
ranks children before search, and publishes only a complete timely certificate
of exactly one fewer qubit. Linear contact accumulation avoids the repeated
long-chain-per-logical-neighbor scan identified in experiment 042. Simple,
undirected, stable target adjacency remains a caller precondition; untouched
target rows are not independently certified by this module.

The remaining risks are scientific and computational: occupied-site-only moves
exclude useful free-space reconstructions; top-four/depth/state/patch bounds
restrict reach; frozen-boundary scans, private copying and complete generation
can dominate runtime; and a local contraction need not improve an evolving
pipeline's final ACL. Ownership transfers and swaps have substantial prior art.
No novelty, global infeasibility, MM superiority or generalization is claimed.

Next, freeze one general group rule and common wall allowance, calibrate finite
implementation work bounds on existing synthetic fixtures, and compare first
contractions against unchanged ordinary reconstruction sharing its own entry
setup. Use all 34 audited, deletion-closed 042 development incumbents. Keep both
methods separate as experimental controls; do not combine their outputs into a
portfolio. Any promising mechanism still needs a full-pipeline experiment and
fresh-instance validation.
