# 062-ready-lifting-screen: launch record

Frozen and launched once on hyde06; 36 fixed complete-constructor calls.
Candidate and MM use separate existing environments on the same host.
Detached tmux supervision has a fixed outer timeout; observation failure never
permits another start. Source review, focused checks and exact task/input
verification preceded the launch. No outcome claim is made here.

- Source snapshot: `bd447f6cb4333e8e7a567a5b595aaf4fde95746552887044c1e1cda6d17ef63a`.
- Manifest: `deabfff2cfd9d45b3699ab332964ada7796b234b429f9694d43db09dfdccb9db`.
- Plan/metadata: `6981017b240b0df0c38efb1707d79f043974fd9db8329aebf50683e4128cda4a`.
- Author evidence: `7d0bfded78d6517f8e4c1be61f3685d6ddc0ee6e9437e1e2c955bcb65ad4ea9d`; root verified 60 bindings.
- Transport input digest: `2ebb3ccceeb88bb64f2dbfaca16efe20811faa55b5b3fdcfa92246b4907cb772`.
- Start epoch: `1788920074.390534`; supervisor: `tmux-with-timeout`.
- Complete action stdout/stderr/status: `results/codex/062-launch`.

Root retained existing worker/import/validation behavior. A structural AST check
confirmed that the only shared pilot changes are three new constructor registry
entries; all 30 inherited entries remain identical. B024 was frozen before the
A/C registry entries were added; A062 and C010 share the later source snapshot.
The extra modules do not run in another candidate's process.

Terminal retrieval completed once: 293 files, digest
`402a4ca919cfc1bb89c63b594777bef2fc7e277ef4773b06d7b6c93e998fe725`. Controller `205784`
finished at `1788920407.1035812`; all 36 calls finalized, lock free,
tmux absent and supervisor exit 0. Root independently checked every retrieved
file and aggregate digest. The reviewed saved-data analyzer and its 23 bound
references are unchanged before its single authorized execution. No candidate
rerun or schedule/cap change is authorized by this receipt.


The single saved-data analysis passed with zero errors. Root read the
[result report](062_ready_lifting_results.md) and verified48 final evidence
bindings, manifest
`26b361c9103b16ed72c0c9467610d80f03a0dd53de714d42d814c0bb98aa3713`.
The fixed ready-row policy fails its continuation rule and is retired.
