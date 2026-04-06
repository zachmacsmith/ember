# CLI Reference — ember

All commands are invoked as `ember <command>`. Run `ember --help` or `ember <command> --help` at any time.

---

## ember run

Run a benchmark from a YAML experiment file or CLI flags.

```
ember run [experiment.yaml] [flags]
```

| Flag | Type | Description |
|---|---|---|
| `experiment.yaml` | positional (optional) | Path to a YAML experiment file |
| `--graphs SPEC` | string | Graph selection expression or preset name |
| `--algorithms NAMES` | string | Comma-separated algorithm names |
| `--topologies NAMES` | string | Comma-separated topology names |
| `--trials N` | int | Measured trials per combination |
| `--warmup N` | int | Warmup trials (not saved) |
| `--timeout SECS` | float | Seconds per trial before TIMEOUT |
| `--seed N` | int | Master random seed |
| `--workers N` | int | Parallel worker processes |
| `--fault-rate R` | float | Fraction of qubits to disable (0.0–1.0) |
| `--fault-seed N` | int | Seed for fault placement |
| `--output-dir PATH` | string | Override output directory |
| `--note TEXT` | string | Annotation stored with results |
| `--analyze` | flag | Run `ember-analysis report` on the completed batch |

CLI flags override YAML values. YAML values override stored config. Stored config overrides package defaults.

**Examples:**

```bash
# From a YAML file
ember run experiment.yaml

# Entirely from flags
ember run --algorithms minorminer,clique --graphs installed --topologies pegasus_16 --trials 5

# Override specific YAML keys
ember run experiment.yaml --trials 10 --workers 4

# Run and generate analysis report
ember run experiment.yaml --analyze
```

Every run writes `<name>_resolved.yaml` alongside the results recording all parameters as actually used.

---

## ember resume

Resume an interrupted benchmark or manage incomplete runs.

```
ember resume [BATCH_ID] [flags]
```

| Flag | Type | Description |
|---|---|---|
| `BATCH_ID` | positional (optional) | Batch directory name; omit to select interactively |
| `--workers N` | int | Override worker count for the resumed run |
| `--output-dir PATH` | string | Override output directory |
| `--delete` | flag | Delete this incomplete run instead of resuming |
| `--delete-all` | flag | Delete all incomplete runs (prompts for confirmation) |

**Examples:**

```bash
ember resume                         # interactive list of incomplete runs
ember resume my_experiment_2026-...  # resume a specific run
ember resume my_experiment_2026-... --delete
ember resume --delete-all
```

Incomplete runs live in `runs_unfinished/` (a sibling of your `results/` directory). A run in `results/` is complete.

---

## ember graphs

Manage and browse the graph library of 31,083 graphs across 36 types. Graphs bundled with the package are always available offline; all others are downloaded from HuggingFace and cached locally on first use.

### ember graphs list

```
ember graphs list [TYPE] [-a]
```

| Argument / Flag | Description |
|---|---|
| `TYPE` | Graph type name (e.g. `complete`, `random_er`); omit for type-level overview |
| `-a` / `--available` | Show only types or graphs that are installed locally |

```bash
ember graphs list                    # type overview: ID ranges, total count, installed count
ember graphs list complete           # all complete graphs with node/edge counts
ember graphs list random_er          # all Erdos-Renyi graphs
ember graphs list -a                 # installed types only
ember graphs list complete -a        # installed complete graphs only
```

### ember graphs info

```
ember graphs info ID
```

Prints full metadata for a single graph: ID, name, type, nodes, edges, density, topology hints, and whether it is installed.

```bash
ember graphs info 1004               # K6 complete graph
ember graphs info 37760              # Petersen graph
```

### ember graphs install

```
ember graphs install SPEC [--dry-run]
```

Downloads graphs matching `SPEC` from HuggingFace and saves them to the local cache.

| Flag | Description |
|---|---|
| `--dry-run` | Show what would be downloaded without downloading |

```bash
ember graphs install benchmark       # install the benchmark preset (~82 graphs)
ember graphs install physics         # install all physics graphs (~4490 graphs)
ember graphs install 1000-1055       # install all complete graphs
ember graphs install "5550-5600, !5575"  # range with exclusions
ember graphs install --dry-run default   # preview without downloading
```

See [graph-library.md](graph-library.md) for selection syntax and all preset names.

### ember graphs presets

```
ember graphs presets
```

Lists all named presets with their resolved graph counts.

```bash
ember graphs presets
```

### ember graphs search

```
ember graphs search [filters]
```

Search the manifest by graph properties without loading any files.

| Flag | Description |
|---|---|
| `--type TYPE` | Filter by graph type (e.g. `random_er`, `complete`) |
| `--min-nodes N` | Minimum node count |
| `--max-nodes N` | Maximum node count |
| `--topology TOPO` | Filter by topology hint (e.g. `chimera`, `pegasus`) |
| `-a` / `--available` | Installed graphs only |

```bash
ember graphs search --type random_er --max-nodes 20
ember graphs search --topology chimera --min-nodes 50 --max-nodes 200
ember graphs search --type complete -a    # installed complete graphs only
```

### ember graphs cache

```
ember graphs cache
ember graphs cache delete SPEC [--all]
```

```bash
ember graphs cache                       # disk usage summary by type
ember graphs cache delete benchmark      # remove graphs matching a preset or selection
ember graphs cache delete 1000-1055      # remove a range
ember graphs cache delete --all          # wipe entire cache (prompts confirmation)
```

### ember graphs verify

```
ember graphs verify [--fix]
```

Runs SHA-256 integrity checks on all cached graphs.

| Flag | Description |
|---|---|
| `--fix` | Re-download any files that fail the integrity check |

```bash
ember graphs verify                      # check all cached graphs
ember graphs verify --fix                # repair corrupt or missing files
```

---

## ember topologies

List and inspect registered hardware topologies.

### ember topologies list

```
ember topologies list [--family FAMILY]
```

| Flag | Description |
|---|---|
| `--family FAMILY` | Filter to one family: chimera, pegasus, or zephyr |

```bash
ember topologies list
ember topologies list --family pegasus
```

### ember topologies info

```
ember topologies info
```

Prints a full table with node counts, edge counts, and descriptions for all registered topologies.

---

## ember results

Inspect and manage completed benchmark batches.

### ember results list

```
ember results list [--output-dir PATH]
```

Lists all completed batches in the output directory.

### ember results show

```
ember results show BATCH_ID [--output-dir PATH]
```

Prints a summary table for the batch: algorithms, success rates, timing, chain lengths.

### ember results delete

```
ember results delete BATCH_ID [--output-dir PATH]
```

Deletes a completed batch directory after confirmation.

---

## ember algos

Manage algorithms.

### ember algos list

```
ember algos list [--available] [--custom]
```

| Flag | Description |
|---|---|
| `--available` | Show only algorithms available in the current environment |
| `--custom` | Show only custom (user-defined) algorithms |

```bash
ember algos list
ember algos list --available
ember algos list --custom
```

### ember algos template

```
ember algos template
```

Prints a fully documented algorithm template to stdout. Redirect to a file to start implementing:

```bash
ember algos template > my_algorithm.py
```

### ember algos dir

```
ember algos dir
```

Prints the path to the user algorithms directory. Files placed there are loaded automatically.

### ember algos add / remove / validate / reset

These commands are registered but not yet implemented. To manage custom algorithms, place or remove `.py` files in the directory shown by `ember algos dir`.

---

## ember config

Manage persistent user configuration. Settings are stored in a JSON file in the platform user config directory.

### ember config show

```
ember config show
```

Prints all config keys, their current values, and where each value comes from (default / config file / env var).

### ember config get

```
ember config get KEY
```

Prints the resolved value for one key.

### ember config set

```
ember config set KEY VALUE
```

Sets a persistent config value.

### ember config reset

```
ember config reset
```

Deletes the config file, reverting all keys to package defaults.

### ember config path

```
ember config path
```

Prints the path to the config file.

**Config keys:**

| Key | Type | Default | Description |
|---|---|---|---|
| `output_dir` | string | `./results/` | Default output directory for benchmark results |
| `default_workers` | int | `1` | Default parallel worker count |
| `default_timeout` | float | `60.0` | Default per-trial timeout in seconds |
| `default_topology` | string | `chimera_16x16x4` | Default hardware topology |
| `default_seed` | int | `42` | Default master random seed |
| `default_n_trials` | int | `5` | Default trial count |
| `default_warmup_trials` | int | `1` | Default warmup trial count |
| `default_graphs` | string | `*` | Default graph selection |
| `default_fault_rate` | float | `0.0` | Default fault rate |

**Environment variable overrides:**

| Variable | Config key |
|---|---|
| `EMBER_OUTPUT_DIR` | `output_dir` |
| `EMBER_WORKERS` | `default_workers` |
| `EMBER_TIMEOUT` | `default_timeout` |
| `EMBER_TOPOLOGY` | `default_topology` |
| `EMBER_SEED` | `default_seed` |
| `EMBER_N_TRIALS` | `default_n_trials` |

---

## ember install-binary

Download and install pre-built C++ algorithm binaries from GitHub releases.

```
ember install-binary [atom|oct] [--version X.Y.Z] [--force] [--list]
```

| Argument / Flag | Description |
|---|---|
| `atom` | Install the ATOM binary |
| `oct` | Install the OCT binary |
| `--version X.Y.Z` | Pin a specific release version (default: latest) |
| `--force` | Overwrite an already-installed binary |
| `--list` | Show install status for all binaries |

```bash
ember install-binary atom               # install latest ATOM
ember install-binary oct --version 0.5.0
ember install-binary atom --force       # reinstall
ember install-binary --list             # check status
ember install-binary                    # same as --list
```

Supported platforms: `linux/x86_64`, `darwin/x86_64`, `darwin/arm64`.

Binaries are downloaded from GitHub release assets and installed to the platform user data directory (`~/.local/share/ember-qc/binaries/` on Linux, `~/Library/Application Support/ember-qc/binaries/` on macOS).

---

## ember version

```
ember version
```

Prints the installed `ember-qc` package version.
