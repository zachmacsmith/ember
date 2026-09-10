# A064/A065 outer-censoring exposure check

2026-09-10. **No affected receipt was found in the four completed cohorts.** The
potential `epoch_exhausted` override defect was latent in these calls; this is
not proof that the code path is harmless or that other cohorts are unaffected.

| Completed cohort | A064/A065 calls inspected | `epoch_exhausted` | Known outer censoring erased |
|---|---:|---:|---:|
| A064 initial | 9 | 0 | 0 |
| A064 broader | 22 | 0 | 0 |
| A065 initial, including paired A064 | 18 | 0 | 0 |
| A065 remaining, including paired A064 | 30 | 0 | 0 |

All 79 operators recorded `deadline`; every saved mechanism row already reports
`cost_censored=True`. None has the original helper's known outer-censoring
condition (`late=True`, `TIMEOUT` or `WATCHDOG_TIMEOUT`). Thus none entered the
suspect completed-epoch override, and no historical classification changes are
needed within this scope. These are 55 A064 and 24 A065 calls, with repeated
development inputs; call count is not independent generalization evidence.

The passive check bound 102 files: prior audit/mechanism summaries and rows,
four archived manifests, all 79 relevant native raw results, the original
censoring/interpretation sources and this check's source. Raw bytes match both
the passing common audit and its saved mechanism reader. No running cohort,
MM result map, constructor, candidate module or validator was read or executed.
The check uses only saved status fields and their historical classifications.

Evidence: `results/codex/a064-a065-censoring-impact/`. Source `audit.py` SHA256
`5f6d1237b8c79ff3a3c63b1a2cb5d20d3d182c60f7af5835854cecbd020aa6f7`;
before-execution binding SHA256
`5f9badaff8c93522c86e781e975916cfd938ad39ff8f01bffb545d4156101b0c`.
The first and only recorded execution passed in 0.986 s process time
(0.949 s analysis). `analysis001/summary.json` SHA256
`3224296ebdd24f9e8ae6aa4d68544c62f711870f64583d6e88b391a2670d7331`
preserves all 79 scalar rows and exact input hashes.
