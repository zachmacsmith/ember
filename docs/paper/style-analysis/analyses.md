# Per-paper style analyses (provenance for STYLE_GUIDE.md)

Thirteen papers were analyzed by one subagent each (via arXiv full text; ACM's `dl.acm.org`
is 403-blocked). Each agent verified the venue and extracted ten writing-style characteristics.
Eight are **confirmed ACM TQC**; five candidates turned out to be adjacent venues (their arXiv
IDs had surfaced in TQC-themed searches) and are retained as corroborating `acmart`/quantum-
systems exemplars. The ten-characteristic outputs were merged into `../STYLE_GUIDE.md`; the
distinctive signature of each paper is recorded below.

## Confirmed ACM TQC (the guide's primary basis)

| # | Paper | Venue | Source read |
|---|-------|-------|-------------|
| 1 | CHARME — chain-based RL for minor embedding | TQC 7 (2026), 10.1145/3763244 | arXiv 2406.07124 (HTML v2) |
| 2 | i-QER — intelligent quantum error reduction | TQC, 10.1145/3539613 | arXiv 2110.06347 (PDF) |
| 3 | PyMatching — MWPM decoding | TQC 3 (2022), 10.1145/3505637 | arXiv 2105.13082 (PDF) |
| 4 | Realistic Cost / Lattice-Surgery Compilation (Leblond et al.) | TQC 5(4) (2024), 10.1145/3689826 | arXiv 2311.10686 (HTML) |
| 5 | Quantum Circuit Cutting for Classical Shadows (Chen et al.) | TQC 5(2) (2024), 10.1145/3665335 | arXiv 2212.00761 |
| 6 | Using RL to Perform Qubit Routing (Pozzi et al.) | TQC 3(2) (2022), 10.1145/3520434 | ar5iv 2007.15957 |
| 7 | Exact & Practical Pattern Matching (Iten et al.) | TQC 3(1) (2022), 10.1145/3498325 | arXiv 1909.05270 (v2) |
| 8 | OpenQASM 3 (Cross et al.) | TQC 3(3) (2022), 10.1145/3505636 | arXiv 2104.14722 (v2 + LaTeX) |

Distinctive signatures:
- **CHARME** — naive-then-refined arc (NaiveRL → CHARME); colon-enumerated contributions (no
  itemize); author–year citations; numbered Algorithm floats with Input/Output; a dedicated
  notation table; single-column `acmsmall`, 28 pp.; reproducibility via in-text hyperparameters.
- **i-QER** — IMRaD with a bulleted contributions list + explicit "structure of this paper"
  roadmap; numeric `[n]` citations; ALL-CAPS top headings; Algorithm float; artifact GitHub URL
  in the abstract; occasional ornate flourishes (flagged as an anti-pattern).
- **PyMatching** — short "tool paper"; confident first-person "we"; British spelling; heavily
  hedged empirical claims; algorithm2e pseudocode + runnable Python listings; tutorial "Usage"
  section; Apache-2.0 + GitHub statement; no tables (figures only).
- **Leblond** — author–year (natbib) citations; bulleted "we present the first…" contributions;
  "this paper is divided as follows" roadmap; monospace for code/params; noun-phrase figure
  captions; "Conclusion and Outlook"; single-column `acmsmall`, ~28 pp.
- **Chen** — theory paper: numbered Theorem/Corollary/Remark with proofs in lettered appendices;
  a "1.1 Notational Remarks" subsection; "Figure" spelled out, full-sentence captions; narrative
  contributions + "organization of the paper"; numeric citations; "Conflict of Interest" line.
- **Pozzi** — present/active framing, past/passive procedure; British spelling; conversational
  subsection titles ("A word on runtime"); figure-heavy (plots), sparse tables; author–year
  citations; equations not Algorithm floats; code-availability statement; keywords list.
- **Iten** — two-tier body (10-pp summary then 23-pp detail + appendix); named, double-numbered
  Theorems/Definitions; run-in "Proof." with QED; seven numbered Algorithms; "Notation"
  subsection + "Organisation." roadmap; "i.e./e.g./More precisely" connectives; equal-contribution
  markers; grant acknowledgements.
- **OpenQASM 3** — long spec (~50 pp.); modal-heavy (may/should) to mark optional vs required
  behaviour; ~60 code listings (un-numbered, line-numbered) as the dominant exhibit; exactly one
  figure with a paragraph-length caption; no bulleted contributions (narrative + scope
  disclaimer); GitHub "live document" as the artifact; marginal footnotes for asides.

**Layout consensus (7 of 8):** TQC is single-column `acmsmall` (journal), per-article pagination,
CCS Concepts + ACM Reference Format + keywords; 2–3 heading levels; 12–50 pp. (One agent guessed
"two-column" for Iten and flagged the uncertainty — outvoted.)

## Adjacent venues (corroborate the prose conventions, not the TQC layout)
- **Context Switching for Secure Multi-programming** (arXiv 2504.07048) — standalone preprint in
  `acmart`; bulleted contributions, Threat-Model subsection, branded acronyms (ZKTA, QONTEXTS),
  result-stating multi-panel captions, numeric citations.
- **Understanding/Estimating Execution Time of Quantum Circuits** (arXiv 2411.15631) — **TOSEM**
  (10.1145/3778031), single-column `acmsmall`; RQ-driven results, "Threats to Validity",
  replication package — software-engineering norms, *not* TQC conventions (noted as a pitfall).
- **A Compilation Framework … Mid-Circuit Measurement** (arXiv 2511.10921) — IEEE-style preprint;
  Roman-numeral sections, bracketed cite-keys, score-function equations, prose pipeline (no float).
- **SWIPER / Predictive Window Decoding** (arXiv 2412.05115) — **ISCA 2025** (10.1145/3695053.3731022);
  ACM `sigconf` two-column; problem→limitation→solution→quantified-result abstract; data-availability
  statement; method shown as flowcharts not pseudocode.
- **Automatic Implementation/Evaluation of Error-Correcting Codes** (arXiv 2301.05731) — **VLSID 2023**
  IEEE conference; Dirac notation, worked "Example" blocks, repeated open-source/artifact footnotes,
  IEEE numeric citations.
