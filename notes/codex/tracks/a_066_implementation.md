# A066 implementation ready for a complete-constructor screen

2026-09-10. **Four focused check groups passed on their first execution.** No
complete development constructor was run and no cluster action was taken here.
This implements the root-reviewed [contract](a_066_constructor_contract.md),
following the positive but narrow [saved-state diagnostic](a_066_pair_diagnostic_results.md).

New isolated files:
- `paired_boundary_reconstruction.py` adds exact obstruction pruning and atomic
  adjacent (2,1)→(1,1) replacement inside the A065 search.
- `paired_boundary_construction.py` exports `paired_boundary_embed` and the
  constant `pruned_boundary_embed` ablation. Both have one unchanged A061 base
  call and the original A065 deadline/reserve/final-validation behavior.

A two-site owner is eligible only when unchanged preparation removed no donor
sites. The new proof explicitly checks that each prepared donor has exactly its
incumbent site set. Old reconstruction changes only the focus tree, and old
commit installs all prepared donors unchanged; therefore a strict improvement
requires a singleton. An empty exact singleton domain closes that original query
for the epoch. The full policy first tests every eligible adjacent singleton
until it finds a physical coupler between the exact released domains, then
certifies and publishes both owners together. The ablation only closes the
proven obstruction. Neither operator reads graph IDs, diagnostic witnesses or
MM outputs, and there are no new production work caps.

Pair publication happens before a normal query cache exists. Explicit pair
receipts identify both owners/sites, complete changed chains, Q−1, and whether a
neutral intermediate would be possible. They distinguish relocation from donor
trimming. The original publication sequence certifies, rebuilds the bundle,
prepares receipts, checks the deadline, then atomically changes the incumbent and
invalidates every cached query and closed-owner mark. The round resumes at the
next slot. Normal A065 visits retain the existing implementation.

Root and C-track static review found one diagnostic edge: cache disposal may
notice the deadline after a valid admission. Nested pair status is now set to
`committed` before disposal. This correction preceded the frozen check execution;
it was not a failed-test repair. The interruption group explicitly covers it.

The four first-pass groups cover:
1. Exact domains under nontrivial source/target relabeling, actual old-root
   reconstructions under a proved obstruction, and rejection of a changed donor
   set despite a zero-removal declaration.
2. Pair admission with a real preexisting A064 cache and prior closed owner,
   including global invalidation, round-slot continuation and independent map
   validation.
3. Five interruptions before publication (domain, certificate, bundle, receipt,
   final publication preparation) preserving the incumbent; interruption during
   disposal after publication preserving the complete valid new map.
4. The constant pruning-only branch, isolated-owner boundary handling, and two
   tiny stubbed-base wrapper calls through the unchanged final validation gate.

Process wall was 2.157480 seconds; test body wall was 0.819042 seconds. There were
zero errors, failures, forbidden dependency attempts or changed frozen bindings.
MM, `_minorminer` and busclique were absent. These are correctness checks, not
constructor quality or runtime evidence. No exhaustive routing test suite was
added or rerun.

`results/codex/a066-implementation/` preserves the before-code proof/approval,
14-file check freeze, first execution/log/output and a passive wrapper AST
comparison. The wrapper body matches A065 except for the new operator, identity
and constant pair-policy argument; the two explicit exports select that constant.
The original A063/A064/A065 sources remained unchanged.

SHA256 identities:
- Core: `e9280652f080218caef4bc8b149177217cf0b18e1250f30865c70511242bbae6`.
- Wrapper: `d00793c59d62571b172e42cdcf256318a85c977ee34b500972e91de4aa1c8c9e`.
- Frozen checks: `cdc6cdf71b54b5988c8fcdfb4cbe5fc0cf5e21212e57d8ce5e705ee9f830d3e0`.
- Check output: `1223894297f35744d6810567f295d91ea83184b9c0ce86a488ead9662e208ac7`.

Proceed to the frozen complete-constructor comparison once root registers these
exports and reviews the final source identities. Local pair gains remain
non-additive, four diagnostic structures remain negative, and A066 has no
end-to-end development evidence yet.
