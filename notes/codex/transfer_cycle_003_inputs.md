# Transfer003 development inputs — before generation

2026-09-09. Prepare three fresh development structures for the next complete
constructor screens: Watts–Strogatz n=100, k=6, beta=0.2; SBM n=100 with four
communities, p_in=0.20, p_out=0.02; and random planar n=100. Use the unchanged
pinned Ember generator and NetworkX 3.4.2. Generate each once; record failures
without replacement. Generation watchdogs are 30 seconds for WS/SBM and
300 seconds for planar, as in Transfer001. These are generation limits, not
candidate work limits.

Seed each generation with the first 64 bits of
SHA256(`ember-codex-transfer003/generation/{case}`); independently permute source
labels using the corresponding `label` namespace. Assign neutral identifiers
g0201/g0202/g0203. Candidates receive only the sanitized graph, never family
labels, parameters, private originals, witness maps or this protocol.

The reusable input panel also copies all 22 Transfer001 encodings and the two
Transfer002 fresh encodings byte for byte. Preserve the two nested relabelings
and their parent identities; do not count them as independent structures.
Copied originals and witnesses remain evaluator-private. The intended panel
has 27 encodings, including 25 structures; this is not a 27-input experiment.
Each candidate's exact subset, source and time allocation will be frozen
separately after its mechanism evidence supports a complete screen.

Reuse the existing generation/sanitization/oracle helpers and original-to-solver
identity checks. Extend the exposed-index comparison to include Transfer002;
preserve possible isomorphism matches and unresolved comparisons. Verify
every copied byte binding and every original-label bijection before any
constructor sees an input. No embedding algorithm runs during generation or
input review.

These new intermediate-size instances test transfer for A's cost mechanism and
C's construction mechanism. Three structures cannot establish class means or
generality. All become development data; no untouched confirmation set is
created or consumed. This preparation does not revive a failed policy or
authorize a constructor screen without its separate decision.
