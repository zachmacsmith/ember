# A065 saved-base recovery preparation

2026-09-10. The [before-code diagnostic plan](065_base_recovery_plan.md) is
implemented under `results/codex/a065-base-recovery`; root outcome-execution
review is pending. Existing constructor notes, readers and raw archives are
unchanged. No real constructor map has yet been reversed by this diagnostic.

`recovery.py` checks each recorded after-chain against the current ordered chain,
reverses changed owners simultaneously, reconciles Q, and checks both sides
against the resulting forward sequence. It maps indices using frozen node order,
not seeded ranks or JSON key order. The unchanged independent oracle validates
only the recovered entry map; intermediate maps remain receipt-derived. Paired
comparisons use actual full values, retaining chain order and reporting physical
site-set equality separately. They compare both complete state prefixes and
semantic receipt prefixes, excluding timing/work fields.

The one tiny supplied fixture passed first execution, with nontrivial external
label order and three commits. It independently validates the recovered entry
and rejects two corruptions that preserve chain site sets: an after-chain order
change and an inconsistent linked before-chain order. Source/fixture data remain
unchanged. Recorded process wall is 0.0390s, with zero development outcome reads
and zero constructor calls. Exact test/source bytes were frozen before execution.

`execution_preparation.json` binds the checked implementation, passing original
and receipt audits, screen, manifest, unchanged oracle and relevant frozen
serialization/indexing sources. It permits only nine paired A064/A065 recovery
comparisons; actual map recovery remains unexecuted for root review. MM map
files and hidden witnesses are outside the diagnostic. Any findings will go in
a new recovery result note; the existing frozen constructor result note remains
untouched.
