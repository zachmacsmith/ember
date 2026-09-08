# 053 launch record

2026-09-08. Run `053-site-transfer-pipeline` on hyde03 compares fixed050 and053
on the same34 exposed structures/35 memberships, seed0,Z12,60 seconds each.
The [protocol](053_site_transfer_screen.md) is frozen before all68 calls.

- Source snapshot: `a31c828398a6c46d080767684602ebc91777358fb3b0df56b46be0e38e59ee99`.
- Task manifest: `a2464802ae68b14d9f6d79ecd31a42225b68d552c5d8e773ad035aedb76d7404`.
- Protocol: `275d280349b3ee70ac98c9746ba0690b325f3aa42d2dc2cfdb242a643b39e966`.
- Pilot: `afb5d5536f284373e3c7d8be34681b63cd110256e0da1b9f097717c20a661170`.
- Transport input digest: `28889462c3633ccffafd2838986cbe57095af8d8f85aaf0a852701766e54ad2a`.

Freeze/stage succeed once. `start001` is a preserved local argument error:
the start CLI requires a basename, and rejected the supplied local path before
any SSH/action. `start002` uses that basename and starts the one detached
controller at Unix1788902567.8981576. It reports tmux
`ember-codex-e6d60f27aa11f6508439` alive,6420-second outer bound, no finalized
tasks yet. This is one remote launch, not a restarted experiment.

All invocations use `results/codex/053-launch/cli.py`, recording exact argv,
stdout, stderr and exit code under unique invocation directories. Root owns
observation/retrieval; track A owns the minimal saved-result screen. Observe
this same handle after an SSH interruption. Do not infer failure or restart
from a lost connection. Status004 is terminal:68/68SUCCESS, controller197491 finished at Unix1788902985.1875544, free lock, absent tmux and supervisor exit0. The last active-record PID198629 is historical; it is not evidence of a live worker. Fetch001 succeeds:462 files verified, archive digest `fc533127acc57d0dba5e804c2646066e2a6b6a0a09e4cbc0f49936c825ecaf23`, destination `results/codex/retrieved/hyde03/053-site-transfer-pipeline`. The prepared saved-result screen passes on its first execution; all68 outputs are independently original-valid. No candidate rerun.
