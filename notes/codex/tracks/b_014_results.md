# B014: a connected-contact obstruction rejects the first two blocks

2026-09-08. The fixed component diagnostic rejects **2 of 21** ER66 release blocks: exactly the first two. All six tiny checks pass; all 21 classifications complete, with no unknown or omitted block. No reconstruction or constructor was called.

| Block index | Released owners | B013 port test | B014 component test |
|---:|---|---|---|
| 0 | 53 | Not rejected | Rejected |
| 1 | 55 | Not rejected | Rejected |
| 2 | 31 | Not rejected | Not rejected |
| 3–20 | Remaining fixed blocks | Not rejected | Not rejected |

After releasing 53 and removing protected sites, the available graph contains a 4,580-site component touching required chains 31, 67 and 78, plus the isolated site **1990**, touching only required chain 72. After releasing 55, the small component instead consists of **1955 and 4618**, touching 67 and 72; the large component still cannot touch 72. No connected new chain confined to these unprotected sites can supply all required contacts in either block.

The earliest survivor is index 2, release `[31]`. Its single 4,582-site component touches required chains 67, 72 and 78; newly released site **2002** supplies contact 72. This proves only that the particular necessary obstruction is absent. It does not establish a feasible bounded insertion or restoration of owner 31.

All fixed cases cost **2,400,855 counted operations and 0.911 seconds** of classification wall, under the three-million-operation/five-second diagnostic limits. Setup accounts for 51,048 operations. The first two block classifications cost 111,908 and 111,915 operations, about 0.042 seconds each. These are full-component diagnostic scans, not an integrated constructor speed comparison. The recorded wall starts in the diagnostic main function; interpreter/module loading and final serialization/publication are outside that reported subtotal. Serialization is checked against the same deadline before publication. No runtime advantage is inferred from these local timings.

The [complete result](../../../results/codex/track-b014-components/attempt001/classification.json) retains every component's physical sites, original required contacts, recomputed protected sites, input hashes and tiny outcomes. The [stdlib script](../../../results/codex/track-b014-components/classify_components.py) reuses the hash-bound B013 boundary classifier; no embedding package or solver is invoked. All recomputed B013 classifications agree exactly with their saved counterparts.

The new certificates justify considering a separate skip-only reconstruction experiment with unchanged pool, order and budgets. They do not show that the next block succeeds, and scanning large free regions may itself displace useful routing work. B012 remains unchanged at this evidence checkpoint; no registry or cluster action occurred.
