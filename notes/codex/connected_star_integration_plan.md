# Integrating one connected-center refinement rule

This is an implementation plan following the reviewed connected-center policy,
not an additional candidate or a benchmark result. Core correctness review is
still required before these production edits. The policy retains one evolving
embedding, one constructor and one refinement call. It never selects the best
of separate embedding algorithms.

Expose `polish_star_policy='connected'` as an experimental alternative in native
configuration, with the corresponding `star_policy` in contact refinement. A
call selects exactly one of off, singleton-center matching, or connected-center
growth. Connected mode requires the existing legacy singleton setting and the
same simple, undirected, loopless graph preconditions. It constructs only
`ConnectedStarSearch`; it does not call `StarSearch.propose` or the separate
direct-singleton proposer. The default configuration remains unchanged while
the complete-pipeline effect is tested.

The existing failed-visit schedule is reused. An ordinary accepted move,
including an equal-Q contact improvement, suppresses the auxiliary attempt.
Otherwise the first logical vertex in that visit is considered once per pass,
and the connected core selects its fixed induced star. Setup, selection,
proposal and refresh consume the same live remaining visit and global work.
The auxiliary allowance remains `global_work // 20`, including maintenance;
there is no separate 2,048-unit query limit. The distinct future proposal to
add extra auxiliary work is not part of this integration.

The core returns a replacement for the selected block only. The scheduler
forms one trial mapping, checks the shared deadline, then commits the certified
strict Q reduction atomically. Refresh follows publication of the valid new
incumbent. Interrupted refresh disables future auxiliary work and retains that
incumbent. No saved alternative is promoted after expiry. Outside chains remain
the same immutable objects.

The old singleton-center commit path adds only accepted count, Q savings and
contact-redundancy change because its member growth is always zero. Connected
mode must also add the **actual member-growth count** from the certificate to
the move, aggregate and trajectory; its center can grow while the whole block
shrinks. A strict Q improvement may reduce contact redundancy, so retain the
signed value. Keep a clear distinction among a completed covering assignment,
a returned original-edge certificate and a scheduler commit. Record the
connected operator and search policy explicitly. Work-return fields describe
already charged work and must not be charged a second time.

Focused integration checks should establish: one allowed constructor/proposer;
suppression after ordinary acceptance; once-per-center scheduling; no extra
ordinary groups; correct Q/R/growth aggregates; expiration before commit;
maintenance failure retaining the accepted embedding; and exact global/visit/
auxiliary accounting. Use an independently constructed mechanism fixture for
the connected commit. A small actual native/Z12 smoke check should verify
original-graph validity and absence of prohibited imports. Existing off-policy
replays must retain their output/diagnostic behavior. Full-corpus trials require
a new immutable protocol/source freeze and paired control arm after these checks.

Self-critique: sharing work can displace productive ordinary search even when
the auxiliary rule makes no commits, as experiment 037 demonstrated. Allowing
larger center footprints also makes one query more expensive and can exhaust
the allowance early. The integration preserves those risks so its experiment
can measure them; changing allocation simultaneously would confound the new
search rule. Passing core or integration tests establishes neither broader
quality improvement nor publication novelty.
