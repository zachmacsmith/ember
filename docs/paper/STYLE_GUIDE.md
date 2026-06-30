# Writing style guide for ACM Transactions on Quantum Computing (TQC)

Distilled from a fan-out analysis of papers published in (or accepted to) **ACM Transactions
on Quantum Computing**, read via their arXiv full text. Each subagent extracted 10 style
characteristics; this file merges them into one deduplicated, actionable rule set.

**Grounded in (confirmed TQC):** CHARME (RL for minor embedding, TQC 7, 2026); i-QER (ML error
reduction, 10.1145/3539613); PyMatching (MWPM decoding, TQC 3, 2022); Leblond et al. (lattice-
surgery resource estimation, TQC 5(4), 2024); Chen et al. (circuit cutting for classical
shadows, TQC 5(2), 2024); OpenQASM 3 (TQC 3(3), 2022); Iten et al. (circuit-optimization
pattern matching, TQC 3(1), 2022); Pozzi et al. (RL qubit routing, 10.1145/3520434).
**Corroborated by adjacent `acmart`/quantum-systems papers** (ISCA/IEEE/TOSEM) that share the
prose conventions but not the journal layout. Where TQC papers diverge, the rule says so.

> How to use this file: it is a checklist for writing and reviewing a TQC submission. "MUST"
> = near-universal across the sample; "SHOULD" = strong majority; "MAY" = a real but optional
> pattern. The companion per-paper analyses are in `docs/paper/style-analysis/`.

---

## 1. Layout & length (TQC-specific — the most distinctive rules)
- **MUST use the single-column `acmsmall` journal format** (`\documentclass[acmsmall]{acmart}`).
  TQC is a *journal*: single-column with per-article pagination (e.g. "5:1–5:28"), **not** the
  two-column `sigconf` conference look. (Every confirmed TQC paper is single-column.)
- **MUST include ACM front-matter:** CCS Concepts (`\ccsdesc`), keywords, and the ACM Reference
  Format block. (Camera-ready; anonymized for review.)
- **SHOULD keep section nesting to 2–3 levels** (`\section`/`\subsection`/`\subsubsection`).
  Numeric section numbers ("3.1.2"), not Roman numerals (that is IEEE).
- **Length is generous:** confirmed TQC articles run ~12–28 pages. Short "tool/software"
  papers (PyMatching, ~12 pp.) and long studies (CHARME 28 pp.) both fit; do not pad or
  artificially compress.

## 2. Voice, tense & tone
- **MUST write in the first-person plural active "we"** for the authors' own actions
  ("we introduce", "we benchmark", "we find"); reserve **passive voice for definitions and
  generic procedures** ("a stabiliser code is defined by…", "the circuit is fragmented").
- **MUST track tense to rhetorical role:** present for exposition and claims, past (or
  present-perfect) for prior work and completed procedures, "we will" to preview upcoming
  sections.
- **SHOULD keep a formal, expert register that is plain-spoken, not ornate.** Avoid flourishes
  ("a blazing domain", "wondrous enthusiasm" — seen and best avoided). State results plainly.
- **SHOULD hedge claims with calibrated qualifiers** ("typically", "empirically", "can",
  "may", "to the best of our knowledge") rather than blanket superlatives — even strong
  results are reported with their qualifier ("beats X by ~1%, small but statistically
  significant").

## 3. Sentences & word choice
- **SHOULD favour medium-to-long, compound-complex sentences** (≈15–30 words), often
  front-loaded with a subordinate/participial clause, **interleaved with short declaratives**
  for definitions and emphasis. Vary length; do not write a wall of 30-word sentences.
- **MUST open sentences with explicit logical connectives** to carry the argument: *However,
  Therefore, Moreover, Consequently, Thus, In contrast, To this end, Note that*.
- **MUST expand every acronym parenthetically on first use** then reuse the bare acronym:
  "quantum annealing (QA)", "graph neural network (GNN)". Expert jargon may be used without
  basic-definition padding, but anything load-bearing for the paper gets a one-clause gloss.
- **SHOULD set software names, parameters, and identifiers in monospace** (`\texttt{}`):
  `minorminer`, `var_order`, `num_lanes = 2`. Brand your method/artifact with a consistent
  capitalized name and use it identically throughout.
- Pick one spelling convention (US or British — PyMatching uses British) and apply it
  consistently.

## 4. Document structure & signposting
- **MUST end the Introduction with an explicit contributions statement.** Two accepted forms:
  a **bulleted/numbered list** ("This paper makes four contributions: (1)…") [i-QER, PyMatching,
  Leblond], or **colon-separated narrative enumeration** ("CHARME includes three key
  components: a GNN…, a state-transition algorithm…, and an order-exploration strategy…")
  [CHARME, Chen]. State the same contributions in the abstract and the intro.
- **SHOULD add an explicit roadmap paragraph** near the end of the Introduction: "The remainder
  of the paper is organized as follows. Section 2 reviews…; Section 3 presents…." (Very common;
  pairs well with section cross-references.)
- **SHOULD follow an IMRaD-plus arc:** Introduction → Background/Preliminaries → Method(s) →
  Evaluation/Results → (Discussion) → Limitations/Future Work → Conclusion, with a late or
  integrated Related Work. Theoretical papers add numbered Theorem/Lemma/Proof, proofs in
  lettered appendices.
- **MAY use a "naive-then-refined" narrative** — present a deliberately weak baseline, name its
  flaw, then give the real contribution as the fix (CHARME's NaiveRL→CHARME; this also matches a
  preliminary→optimized or naive→corrected arc).
- **MUST make the Conclusion mirror the abstract/intro** — restate the problem framing and the
  headline results, and keep it in sync with the body (no contribution mentioned in the body
  should be missing from the abstract, intro contributions, and conclusion).

## 5. Abstract
- **SHOULD follow problem → gap/limitation → method → quantified result** (sometimes
  results-first). Lead with the bottleneck, state precisely what is new, and close on concrete
  numbers ("reduces runtime by 40% on average").
- Keep it self-contained and tight: name the method, the evaluation setting, and the headline
  numbers; do not narrate every section. If the paper has many studies, summarize each in one
  clause, not one sentence.
- **MAY put the artifact/code URL in the abstract** (i-QER, PyMatching do) — for anonymous
  submission, defer it.

## 6. Figures & tables
- **MUST write descriptive captions that state the takeaway / orient the reader**, not bare
  labels — full declarative sentences are the TQC norm ("Workflow of the CHARME framework. The
  detailed architecture … is described below."); noun-phrase fragments are acceptable but
  less common. End-punctuate consistently.
- **SHOULD number sequentially and reference inline** ("shown in Fig. 1", "Table 5"). Pick
  **"Fig. N." or "Figure N" and use it consistently** (most TQC papers abbreviate "Fig.";
  Chen spells "Figure" — either is fine if uniform).
- **SHOULD label multi-panel figures (a)/(b)/(c)** and describe each panel in the caption.
- **SHOULD bold the best value per row/column in result tables**; reference the metric and units
  in the caption.
- **MAY include a dedicated notation table** ("Common notation used in this paper") — a recurring
  TQC device (CHARME Table 1, Chen Table 1, i-QER) for symbol-heavy papers.
- Figure types: conceptual/workflow diagrams, architecture schematics, and line/bar performance
  plots; pseudocode and code listings where relevant (see §7).

## 7. Mathematics, algorithms & notation
- **MUST fix notation up front and use it consistently** — either a notation table or a short
  "Notational Remarks" subsection (Chen) — then never deviate.
- **SHOULD number display equations** and introduce them with a colon lead-in ("is defined
  as:", "can be written as:"). Use standard symbols (calligraphic sets, bold vectors, Dirac
  kets where physical); state complexity inline with big-O.
- **SHOULD present algorithms as formal floats** (`algorithm`/`algpseudocode` or algorithm2e)
  with explicit **Input/Output** and numbered lines (CHARME, i-QER, PyMatching, Leblond) — not
  only as running prose. Worked numeric examples in-text are a nice complement.
- For software/spec papers, **MAY include syntax-highlighted code listings** and inline
  monospace API names (PyMatching, OpenQASM 3).

## 8. Citations
- **MUST use an ACM citation style** — both are accepted in TQC: **numeric `[n]`**
  (i-QER, PyMatching, Chen) or **author–year** (`acmauthoryear`: CHARME, Leblond). Choose one
  and configure `acmart` accordingly.
- **SHOULD cite densely in the Introduction/Background** (≈1–3 references per sentence, often
  clustered: "[1, 2, 3, 4]") and **sparsely in the methods.** Cite tools/software too.
- Reference entries give full author lists, sentence-case titles, venue, and DOIs/arXiv IDs.
- **MAY weave citations into prose** with author names ("Huang, Kueng, and Preskill recast…
  [n]"; "Terhal points out that…").

## 9. Reproducibility & end-matter
- **SHOULD state artifact/code availability explicitly** — a GitHub URL (in the abstract, a
  footnote, or a statement), an install command, and a license (PyMatching: "distributed under
  the Apache 2.0 license"). For anonymous review, include an anonymized note and add the link
  for camera-ready.
- **SHOULD disclose datasets and full hyperparameters in-text** so results are reproducible
  (CHARME lists graph sizes, learning rates, batch size, episodes).
- **SHOULD include a Limitations/Future-Work** paragraph (or "Conclusion and Outlook") and an
  **Acknowledgements** (funder/grant); a **Conflict-of-Interest** line appears in some TQC
  papers (Chen, i-QER). Use **footnotes** for URLs, vendor specifics, and tangential asides.

## 10. Pitfalls to avoid (anti-patterns seen, or venue-mismatched)
- Do **not** use the two-column `sigconf` layout or Roman-numeral sections (that signals an
  IEEE/conference paper, not TQC).
- Do **not** let the abstract, intro contributions, and conclusion drift out of sync with the
  body as the paper grows — every section's contribution must appear in all three.
- Do **not** over-hedge to the point of vagueness, nor over-claim with bare superlatives; give
  the qualified, quantified statement.
- Do **not** bury algorithms in prose when a numbered Input/Output float would be clearer.
- Do **not** mix citation styles or figure-label styles within one paper.
- Avoid ornate or non-native flourishes; prefer plain, precise, technical phrasing.
- Do **not** import software-engineering-venue scaffolding (RQ-numbered results, "Threats to
  Validity", "Replication Package") unless genuinely warranted — these are TOSEM/SE norms, not
  TQC conventions.
