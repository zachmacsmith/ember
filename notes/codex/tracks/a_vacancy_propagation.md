# Track A: contact-directed relocation through free sites

Specified before implementation, 2026-09-08. This is a new repair mechanism
for the inherited prototype, tested initially on its fixed valid embeddings.

**Hypothesis.** Occupied-site exchange is too restrictive: both 043 and its
eightfold work-cap follow-up found the same three contractions, none absent
from ordinary reconstruction. Instead, after removing one site, propagate the
missing-contact defect by relocating an endpoint chain site to an unoccupied
target site. This admits free-space changes while preserving nonempty,
connected, disjoint chains and total Q-minus-one throughout the search.

For a missing source edge (u,v), choose either endpoint a. Let b be the other
endpoint. For each unoccupied target site q adjacent to b's current chain,
replace one site p in a's current chain by q. Retain only connected chains that
restore the chosen contact. Other incident contacts may become missing and
must be repaired later. The initially deleted site becomes available again;
the vacant site can move. This mechanism does not transfer occupied sites or
change the size of another chain. Each state modifies at most eight source
chains whose total original footprint is at most 64 sites.

```text
validate entry through the existing caller; keep it immutable
order nonsingleton chains by decreasing size, degree, then canonical label
for each chain and each site in canonical order:
    privately delete the site; reject empty/disconnected remainder
    form the exact set of missing original source contacts
    if none are missing, certify the contraction
    otherwise search at most eight relocation steps with a beam of sixteen:
        take the first missing source edge and enumerate its two endpoint moves
        retain connected, disjoint children that restore that edge
        rank by missing contacts, changed chains, changed sites, move descriptor
        deduplicate exact states and retain the best sixteen complete children
        certify any complete feasible child immediately
    return the first timely independently validated Q-minus-one output
```

One global five-second deadline includes graph/group preparation, search and
the existing final validation. Each deletion seed may examine at most 256
relocation proposals; the whole call may examine at most 50,000. These bounds
favor coverage across seeds. Interrupted nonfeasible child generation supplies
no replacement beam. A completed feasible child can be certified immediately;
there is no requirement to rank all remaining children first. All attempts,
caps, time and failed proposals remain recorded. No output combination or
family dispatch. No MM/busclique/global IP or competitor initialization.

**Self-critique.** Site relocation and defect repair are established local-search
ideas; this experiment does not establish novelty. Fixed chain sizes after
the first deletion exclude useful transfers, and the first-missing-edge rule,
beam truncation and seed cap can miss solutions. Choosing large chains first
may spend too much effort on difficult contractions. Missing-contact count is
only a search score. A local gain is neither a cumulative pipeline improvement
nor proof of acceptable end-to-end runtime.

**Cheap falsifier.** A tiny deletion-minimal five-cycle fixture must demonstrate
a contraction using a previously free site. Check failed/late searches leave
the entry unchanged and validate every returned tiny minor with the audited
validator. Then use all 34 existing Z12 entries and fresh ordinary paired
controls under the same five-second allowance. No relocation-only timely
contractions would reject this first mechanism for integration. Any such
contraction warrants inspecting its short move trace before a fixed pipeline
test; it is not a superiority claim.
