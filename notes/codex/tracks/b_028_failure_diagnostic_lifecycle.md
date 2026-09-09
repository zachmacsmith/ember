# B028 fixed-state diagnostic: lifecycle preparation

Prepared locally on 2026-09-09. No remote action, diagnostic, constructor, or
authentication action was performed. Root reviews and authorizes launch separately.
The frozen packet and all candidate/helper bytes remain unchanged.

The two adapters in `results/codex/b028-failure-diagnostic/` are exact copies of
the reviewed `track-b028-routing` adapters with these substitutions:

- Remote run becomes `/home/dabh/ember-codex/diagnostics/b028-failure001`; the
  tmux session becomes `ember-codex-b028-failure001` on socket `ember-codex`.
- Manifest SHA becomes
  `8e5e27072c4757d5275a0f1e431e7264cdf32a9a15c9959111e088a3f690d40d`.
- `manifest['arm_order']` becomes `manifest['cases']`; status records the four
  cases `g0001`, `g0017`, `g0101`, `g0102` in that order.
- The worker becomes `run_packet.py`; the overall watchdog becomes 480 s.

The native interpreter remains
`/home/dabh/ember-codex/envs/4e1fb892db12754e/native/bin/python` on `hyde02`.
Each fresh worker retains its 60 s inclusive timer and 90 s outer watchdog.
GNU time, standard streams, each outer exit and supervisor exit remain recorded.
All cases run sequentially; each receives a separate fresh process. The existing
jump-host transport, 55 s observation timeout, exclusive launch marker, and
no-restart behavior are unchanged. An observation timeout requires polling the
same handle, never another start. Preflight checks the host, interpreter,
Numba/llvmlite/NumPy versions and absence of prohibited embedders before launch.
Current remote readiness has not been rechecked by this preparation.

`prepare_lifecycle.py` ran once using the local isolated Python and returned 0.
It parsed adapter syntax without importing or executing either adapter. It
verified all 13 packet files; six check/preparation hash bindings; both recorded
invocation/source-status maps; and all four frozen states against their prepared
hashes, candidate result, source, target and passing audit bindings. This verifies
data provenance, not new diagnostic results or trajectory reconstruction.
The exact diffs and verification are in `lifecycle001/`.

| Artifact | SHA-256 |
|---|---|
| `packet_remote_control.py` | `d5526645054b0e3a0be22f94dec9413bcca3799f6b690cf0c92932790eccc460` |
| `packet_action.py` | `a6f2be7438935ebd9fc22b95aeb491c2594c07a6f1d2a79a41e74f97e25fb394` |
| `lifecycle001/verification.json` | `657b140a8f28eadf387ad5e19405d26e63b64ded908f2d254ed62ade40d258e8` |

Intended commands from the repository root, after root's authorization, follow.
Each action's recorded result must be inspected before the dependent next action.
Further status observations use fresh labels on the same run. Inventory and fetch
follow terminal status only; a partial observation does not authorize a restart.

```sh
.venv/codex-native/bin/python -I -B results/codex/b028-failure-diagnostic/packet_action.py prepare prepare001
.venv/codex-native/bin/python -I -B results/codex/b028-failure-diagnostic/packet_action.py transfer transfer001
.venv/codex-native/bin/python -I -B results/codex/b028-failure-diagnostic/packet_action.py preflight preflight001
.venv/codex-native/bin/python -I -B results/codex/b028-failure-diagnostic/packet_action.py start start001
.venv/codex-native/bin/python -I -B results/codex/b028-failure-diagnostic/packet_action.py status status001
.venv/codex-native/bin/python -I -B results/codex/b028-failure-diagnostic/packet_action.py inventory inventory001
.venv/codex-native/bin/python -I -B results/codex/b028-failure-diagnostic/packet_action.py fetch fetch001
```

Evidence will be under `remote001/<action-label>/`; fetched artifacts will be
under `retrieved001/`. The packet manifest's `remote_launch_authorized: false`
records its freeze-time status; any subsequent authorization is recorded
separately without changing packet bytes.
