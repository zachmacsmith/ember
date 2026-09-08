# Final control-embedding deletion audit

2026-09-08. Prespecified read-only diagnostic, before inspecting deletion
outcomes. Scope: all 34 fixed control outputs from frozen experiment 039,
`native-search-joint1-contacts-spectral`, seed 0, ideal Z12. Retain every input,
including zero-removal cases. No new candidate trial, solver, converter, MM call,
production pruning function or cluster work is involved.

The trigger is a control-flow observation: native construction prunes before
contact refinement and then validates its final output; it does not perform a
final deletion pass. Generic `polish.py` has a different sequence and is not
evidence about this native path. Whether the retained control outputs actually
contain deletable qubits is unknown at the start of this diagnostic.

Read exact finalized control records and inverse label maps from the audited
039 archive. Bind them to the frozen manifest, normalized and original source
records, target, source snapshot and the independent audit's record identities.
Verify all file hashes available from those records. Reconstruct graph
adjacency using only the standard library and independently check each original
final embedding for exact logical-vertex coverage, nonempty connected chains,
target membership, disjointness and every original logical edge. An invalid or
identity-uncertain record remains an explicit audit failure, not an omission.

For each qubit q in each chain C_u of each valid final embedding, test its
individual deletion from that **unchanged** embedding. A safe deletion must
leave C_u nonempty and connected and leave a physical contact to every logical
neighbor of u. All other chains remain frozen. Enumerate each candidate once;
record the qubit, chain, chain size and contact/connectivity rejection reason.
Singletons are immediate rejections. Exact directed contact-support sets can
be precomputed by a full original-target-edge scan; deleting q preserves
contacts if no incident logical edge has support set exactly {q}. Connectivity
is independently checked by graph traversal after omitting q. Do not mutate
the saved mapping or chain lists.

Save additive stdlib code, exact input/output hashes, original validity, work
counts, elapsed diagnostic time and per-input removable-site counts in
`results/codex/final-deletion-audit`. Impose a generous diagnostic-only elapsed
cap of 180 seconds for deletion enumeration, and preserve completed records on interruption; unfinished inputs remain
missing, never zero. Report numbers of affected inputs/chains and individual
sites, together with every zero result. Do not compute a pruned candidate ACL
or select outputs by graph family.

Self-critique: deletion and witness bookkeeping are established techniques,
not a novelty claim. Two individually safe deletions may jointly disconnect a
chain or erase its final logical contact. The count of removable sites is not
a promised Q reduction and is not a deletion closure. These saved outputs may
depend on the historical seed, finite deadline and refinement trajectory; no
other seed, treatment or architecture is covered. An independent diagnostic's
runtime is not the incremental cost of an integrated pass. Positive evidence
would justify a separately specified, deadline-aware closure and fixed ablation;
negative evidence should stop that proposed change on these inputs. There is
no authorization here to integrate a new algorithm or alter old benchmark
results.
