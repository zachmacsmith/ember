# track-c-007b-atomic-growth: launch record

Frozen complete-constructor screen on hyde03. All arms run serially on the
same host in the existing isolated candidate and MM environments. There was
one successful stage and one actual detached start on this host.

- Source snapshot: `202453c03321f9b35dd52a597c893d934789e5d805265266bf0d837ac0faf89d`.
- Manifest: `613b410e3d3f3eec812136f7d6abdee94e770714eb8157d7393da7b3fa2dd273`.
- Protocol: `90d9f28be639ec520660ad58d1ccefbe3100dfd900511fcc9496ebb0e06c22e4`.
- Plan: `fd0452cdfb9125ef953f1a9676d0a25704810814376bc62b92e3d9486bb062db`.
- Transport: `848395903a78349b94c1f629e9ac26a8233df0364e0001178ea929fdf9087501`.
- Tasks / inputs: 24 / 8.
- Start Unix: 1788908249.1429067.
- Session: `ember-codex-b8e5671886b8f9bb593e`.
- Outer bound: 1380 seconds.
- Controller: 205697.

Latest saved observation: 8/24 finalized,
statuses `{"SUCCESS": 7, "TIMEOUT": 1}`. Lock and detached session
remain active. These are provisional controller counts, not reviewed quality
results. Root owns transport; a failed SSH observation does not authorize a
replacement run. Full analysis waits for the quiescent archive.

The [host amendment](c_007_host_amendment.md) preserves the refused hyde04
start and its zero-call status. Only the new hyde03 run may execute.
Correction to the amendment's task-ID prediction: interpreter paths belong to
the manifest, not task records, so all 24 task IDs actually remain identical
to the unstarted04 bundle. The manifest and run name differ; there is no
duplicate execution. Source/target/task templates are unchanged.

Root reviewed the saved-data analyzer amendment and its three injected-record
check groups. All 14 file/reference bindings pass. Errors after structural
scoring erase quality credit; late/nonzero/missing records remain visible.
Analyzer SHA256: `bef8eda6fa823cfac6cfc0811a3f27658c6176128647d8079d47a5d8f2acb765`.

Terminal update: all24 finalized, controller205697 completed at Unix1788908493.9812398; lock free, tmux absent, supervisor exit0. Retrieval verifies223files, digest`0a644a40dd66b3d2ff5353bb8ba024614e7ba96819b21eb889902752c2df9da5`. One saved analysis passes with no audit errors; root reviews the report, mechanism projection and all32 final bindings. Both candidates complete2/8 versusMM6/8 and fail the predeclared rule. Retire both fixed policies. See[c_007_results.md](c_007_results.md).
