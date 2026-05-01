# Building the CHARME binary from source

CHARME's policy network picks a logical node per step; the compiled C++ helper
here extends the current Chimera embedding to cover that node. It is **not**
the same CLI as `external/atom/main` — it is an incremental-state variant.

## Requirements
- g++ with C++11 support, pthreads
- `make`

## Build
```
cd external/CHARME
make
```

This produces `external/CHARME/main`. To install into the ember-qc user
binary directory (`<user_binary_dir>/charme/main`):
```
make install
```

Or use the normal installer (once per-platform release assets exist):
```
ember install-binary charme
```

## Runtime layout
The wrapper (`ember_qc.algorithms.charme`) expects the binary at:
```
<user_binary_dir>/charme/main
```
and will auto-create `<user_binary_dir>/charme/atom_log/` for per-step scratch
files. Override the path via `EMBER_CHARME_BINARY`.

## What the binary expects
The wrapper passes positional arguments matching the original CHARME source
(see `ember_qc/algorithms/charme/env_infer.py:call_atom`):

```
main n m  <edge pairs...>  topo_row topo_column seed is_beginning
     [curr_node old_len <old_nodes...> emb_len <x y z c>...]   <output_path>
```

The binary writes the resulting partial embedding (one line per `(x y z c)`)
followed by a final `rr cc` line to `<output_path>`.

## Trained weights
The PPO actor-critic weights (`ppo_CHARME_ep1800.pth`) ship alongside this
folder. The wrapper hard-codes topology = **Chimera 16×16×4** and source
node count = **120** to match the training distribution of this checkpoint.
