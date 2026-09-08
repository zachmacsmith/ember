# Reproducible pilot analysis and continued work

Date: 2026-09-07 local / September 8 UTC. The previous goal turn made concrete
progress: independent algorithms and correctness repairs were committed, and the
prespecified cluster ablation was launched. At this continuation's first check,
the actual tmux supervisor and inherited worker lock were live, with 15 of 90
finalized observations. Subsequent checks observed progress; no restart was issued.

`scripts/codex/analyze_pilot.py` now revalidates completed frozen runs and writes
per-input and paired-trial CSV/JSON plus a Markdown table. It checks source-file,
target, input and task hashes; finalized result identity; every returned embedding
against the original graph pair; deadline classification; recorded quality; and
candidate dependency guards. It refuses incomplete runs, mixed host timing,
duplicate trials and mixed configurations within a method/input summary.

Primary ACL means and sample variances use only timely valid successes. Failure
and late counts remain explicit. Within-embedding chain variance and across-trial
ACL variance are separate columns. Pairing requires the same source/target hashes
and solver seed; an absent MM trial is not a failure or an available comparator.
No per-input best algorithm is selected. A few seeds are insufficient to establish
family-wide superiority or a precise variance estimate.

The nine focused analysis regressions passed. They cover independently invalid
embeddings, late successes, false quality, dependency violations, unfinalized
records, exclusion of timeout diagnostic quality, exact pairing, sample variance,
and mixed configurations. The script also successfully revalidated all 45 results
of experiment 009: 44 timely successes and one MM timeout. These counts agree with
the earlier independent review. Generated tables are under that run's `analysis/`.

The remote ablation subsequently completed and was retrieved after verified
quiescence. The analyzer passed all 90 finalized observations: 88 timely successes
and two late MM results. A separate audit checked all 90 returned embeddings,
source/task/result identities, and 392 trajectory entries; see
`011_results_review.md`. Both audits agree that the fixed width-one joint method
has the lowest candidate mean but still loses to MM on all six sparse inputs.

Reproduce the analysis with:

```sh
.venv/bin/python scripts/codex/analyze_pilot.py results/codex/retrieved/hyde03/011-search-contact-ablation
```

Parallel bounded investigations in this continuation:

- Experiment 012: select actual Ember corpus inputs by fixed family/size rules,
  without consulting embedding performance; preserve missing inputs and structural
  duplicates. All inherited corpus data remain development data.
- Experiment 013: diagnose contact-search proposal and region limitations on the
  saved independent native-search incumbents, using identical initial states and
  bounded controls; never use an MM embedding as a candidate input.
- Experiment 014: profile cold/warm native search and fixed global proposal budgets
  on preselected development inputs. No algorithm was altered by profiling.

The outcome of 011 and these diagnostics should guide the next actual algorithm
revision. Infrastructure checks are not evidence that the research objective has
been achieved. Generality, all-family quality, success and practical runtime remain
open requirements.
