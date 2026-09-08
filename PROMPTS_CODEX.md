# Codex session prompts

Append-only record of user prompts for this research session. Preserve wording; record
later steering and answers here before dependent work. Environment context is recorded
separately from the research request. Agent task briefs are recorded in
`notes/codex/session_log.md`.

## 2026-09-07 — environment context

Working directory: `/Users/dabh/ember`; shell: `zsh`; timezone:
`America/Chicago`. The workspace permits project file writes; `.git`, `.agents`,
and `.codex` are read-only without escalation. Temporary directories are writable.

## 2026-09-07 — user prompt 1 (verbatim)

```text
/plan This repo contains algorithms for graph minor embedding for quantum annealers (D-Wave).  MinorMiner (MM) is the default stock algorithm D-Wave
  uses for embedding.  We built a benchmark suite (Ember) for testing out embedding algorithms on different classes of  graphs, and on different hardware
  architectures.  For now we're focused just on Zephyr, but we are interested in embedding performance across each class of graph.  We previously had a
  less capable LLM attempting to invent a new algorithm that is better than MM.  That remains the goal of our current project and should be your goal:
  create an algorithm - one that *does not call MM under the hood in any way* - that *outperforms MM on all classes of graphs*, at least on Zephyr.  Our
  primary performance metrics are mean ACL, variance in ACL, and time/speed; if we just win on mean ACL, though, that's sufficient for a nice research
  paper.  The lesser LLM has written handoff documentation (docs/handoff) of what it's done recently to make a better algorithm.  There's also some paper
  drafts in there too.  For these handoff notes and paper drafts and source code etc., *do not assume they are true or good*.  You must have maximum
  skepticism.  A lesser LLM created these, so there could be bugs, inconsistencies, inefficiencies, calls to MM, etc.  (Note: we also *must not* just call
  busclique, which is the other built-in; we are trying to invent a *novel algorithm* suitable for a publication in a venue like ACM TQC.)  Begin the plan
  by brainstorming a list of at least ten candidate algorithms that could outperform MM across the classes of graphs Ember contains.  Then you may start
  looking at the existing notes and drafts and see how those stack up against what you brainstormed.  Ultimately, we want to implement new algorithms that
  you invent and/or improve the algorithm(s) that have been drafted in this repo so far (particularly the one that was created by the lesser LLM - it
  seems to beat MM on some classes of graph already, albeit not every class - so it might actually be close to what we want).  You may also fan out
  subagents to explore existing literature on embedding algorithms such as CHARME, ATOM, etc. (you can conduct a comprehensive sweep of the literature to
  learn about embedding and to find any resources that may aid us in our quest).  As you invent or improve algorithm(s), keep in mind that we have this
  Ember benchmark suite here and can run tests to find out about mean ACL etc.  We have a cluster of compute nodes available to us: hyde01.dabh.io,
  hyde02.dabh.io, hyde03.dabh.io, hyde04.dabh.io, hyde05.dabh.io, and hyde06.dabh.io (note, these are different machines, so timing may vary).  All the
  machines can be reached via hyde01.dabh.io as a jump host.  I may change wifi networks so ensure that our connections can be robust to wifi network
  switching.  If you identify algorithms that are clearly failing, save some lessons learned and then fold those lessons (if any) into the remaining
  algorithms.  Your strategy should be to never give up until we defeat MM on all graph classes, and to keep iteratively refining and self-improving /
  learning from prior experiments about what does and does not work.  You should prompt me and ask questions whenever helpful - we can work together on
  this to achieve a better algorithm than MM.  Along the way, as you're working, please document all of your work in some notes/.md files, saving code,
  pseudocode, markdown notes, diagrams, etc. as useful.  Conduct all your work on a new branch, "codex".  Should you stumble across an algorithm that wins
  across the board, you can also validate whether it wins on Pegasus and/or Chimera architectures, too, but Zephyr is the priority.  You can also consider
  drafting an ACM TQC paper describing our algorithm, should we arrive at an algorithm that succeeds across the board (at least on Zephyr).  Please also
  save every prompt during this session to a PROMPTS_CODEX.md file in the repo (just keep appending prompts), and save the plan you generate in the repo
  too.  Perform two rounds of self-critique on the plan before finalizing it, and perform one round of self critique on each candidate algorithm you come
  up with before any implementation.  (Note, I would like 10 algorithms, but if you can only come up with 3-5 that seem worth our time, that's fine, I
  understand.)  Don't let the werid terminology/vocabulary of the lesser LLM poision your output or thinking ("judges", "dials", "levers", "buttons",
  "knobs", "courthouses", etc.); in all your work, try to write with scientific precision and accuracy but also in a way that is as plainly understandable
  as possible.
```

## 2026-09-07 — user prompt 2 (verbatim)

```text
Quality first; allow slower candidates initially.  For cluster, use username dabh (on all the machines).  Use whatever CPU/memory you want.  One additional note, I think you caught onto this a little already, but we do not want to consider any "portfolio" approaches that combine the best results from multiple algorithms run in parallel - that is a non-starter.  We are seeking a single, non-portfolio algorithm here.
```

## 2026-09-07 — user prompt 3 (verbatim)

```text
I think we should just use Z12 for now since that is what Ember uses.  We can revisit non-ideal and other types of hardware graphs later.
```

## 2026-09-07 — user prompt 4 (verbatim)

```text
Just a note - while I think it's ok to have algorithm that is slower than MM, just doing integer programming and explicitly solving the optimization problem is going to be infeasibly slow, especially at scale.  So while maybe some exact solves could be a subroutine of some small clusters of nodes in the graph, just using an IP solver is not the right approach we are going for here.  We need to be at least roughly on the order of magnitude as the performance of MM.
```
