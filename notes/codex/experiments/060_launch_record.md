# 060 replication: detached launch records

Two fixed36-call cohorts, original06 and additional03, each with fresh A053,
branched path and MM, seeds0/1,60s. No algorithm edits. Source snapshot
`ffa391885f99bccfc2babfb71ce27cdca21e7c16fd3b9160f1cbf14157182660`
matches059 exactly. Each cohort initializes, stages and starts once.

Plan `54f6f275a7c39da1c753c50e80e8ce455c463b7059247f792aeb6967f812bc75`;
protocol `e785ab3f45684682bf2225a983bb3f893ce334bb0653a7b7c8ff41dd3299fd9f`.

## additional: hyde03

Run `060-branched-path-additional`. Invocations: `results/codex/060-additional-launch`.
Manifest `6ce7a186b188705164c0b15c7b9defc060e55d1c987bb7375fbef5273aa414c6`.
Transport `df49b4137dd4016bb6ab0d742c4be9c035091e68cb9902042b7f8f669ab9dc91`.
Detached start Unix1788914497.7347674; outer bound3540s.
Unit `ember-codex-868451474d7c8842632a.service`. Start observed tmux live; controller not yet recorded.

## original: hyde06

Run `060-branched-path-original`. Invocations: `results/codex/060-original-launch`.
Manifest `dbf95d8686b5254f91d7e9044d40bc66968a0e63917baff4bed29612116d60f0`.
Transport `6824df01df0fc69e08108a42056c544b832fd1370deb9d9626c53b932869c1ed`.
Detached start Unix1788914585.7715178; outer bound3540s.
Unit `ember-codex-b6ceaf9f893c1a87d682.service`. Start observed tmux live; controller not yet recorded.

Reconnect to the existing run after network changes. Observation loss is not
authorization to restart or replace a task. Retrieve once after controller
completion, free lock, absent tmux and supervisor exit0. Saved analyzer is
being adapted from059/057; no current outcome has analytical credit yet.

## Terminal retrieval

additional: controller214033 finished Unix1788914628.2050402,36/36 finalized,
lock free, tmux absent, supervisor exit0. Verified286files; digest
`82634587e0c83deb8bef79420143988884946bc5acf99454bec19922b99ddbb6`.

original: controller127852 finished Unix1788914808.6841927,36/36 finalized,
lock free, tmux absent, supervisor exit0. Verified286files; digest
`feb082a5926c09be246da0f0976cd84e9ade9f2269ab8b5c29cb25b37da55963`.

One combined saved analysis passes all original-label, identity, failure/time
and stage-receipt gates. The unchanged replication criterion passes; see
[results](060_branched_path_results.md). No solver rerun or source change.
