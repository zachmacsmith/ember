# Offline comparison of temporary constraints and saved good embeddings

Strategic review only, 2026-09-09. No constructor, MM call, graph generation,
embedding optimization or candidate initialization is performed.

Use the already audited A061 seed0 branch-control and MM outputs for grid1584,
honeycomb32367, BA10662, wheel2429, LFR31357 and planted34404. These deliberately
target known persistent gaps. Add planar31536, where this retained output beats
MM, as a contrast. This selection is diagnostic, not a population estimate.

Reconstruct the inherited elimination journal from each unchanged source graph.
Check recorded neighbors and newly created fill edges, then identify the final
core and its original versus auxiliary edges. Independently validate both saved
final embeddings using the existing oracle. For each, count which temporary
core contacts its final physical chains realize, and the Q on core versus
eliminated vertices. Infer the initial core Q only from the previously audited
base-Q and committed net-Q receipts; its physical map was not saved.

The question is whether MM's good final arrangement satisfies the candidate's
temporary construction constraints with the same physical chains. A missing
auxiliary contact establishes incompatibility of that particular arrangement,
not an unavoidable Q penalty or global minor infeasibility. Candidate final
chains may also lose auxiliary contacts after those constraints are released.
Report both sides, and retain cases with no auxiliary edges. Coupled with the
independent chain/contact-profile and pinned-source reviews, this can locate
where a coherent constructor redesign should act. It does not justify another
fill threshold, label-based dispatch or local repair sequence by itself.
