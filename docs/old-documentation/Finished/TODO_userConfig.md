# EMBER User Data Directory — Requirements Document

## Purpose

This document defines the requirements for EMBER's user-level persistent state system. It covers four features: user configuration, custom algorithm registration, compiled binary management, and the CLI commands that expose all of the above. It defines what each feature must do and what constraints apply. It does not specify implementation details.

---

## 1. User Data Directory

### 1.1 Location

EMBER must store all persistent user-level state in a single root directory whose path is determined by the operating system convention for user application data:

- Linux: follows the XDG Base Directory specification
- macOS: follows Apple's recommended application support directory convention
- Windows: follows the Windows known folder convention for local application data

The directory must be named consistently with the package name across all platforms.

### 1.2 Creation

The directory and all subdirectories must be created automatically on first use. No installation step or manual setup should be required from the user. If the directory already exists, creation must be a no-op.

### 1.3 Persistence across package updates

The user data directory must not be located inside the installed package directory. It must survive `pip install --upgrade ember-qc` without any data loss. Package updates must never modify, migrate, or delete user data.

### 1.4 Subdirectory structure

The following subdirectories must exist within the user data directory:

| Subdirectory | Purpose |
|---|---|
| `algorithms/` | User-defined custom algorithm files |
| `binaries/` | Compiled C++ binaries installed via CLI |

The following file must exist at the root of the user data directory when any config has been set:

| File | Purpose |
|---|---|
| `config.json` | Persistent user configuration |

---

## 2. User Configuration

### 2.1 Config keys

The following configuration keys must be supported:

| Key | Type | Default | Description |
|---|---|---|---|
| `output_dir` | string path or null | null | Directory where benchmark results are written. Null means the current working directory at run time. |
| `default_workers` | integer | 4 | Number of parallel workers for benchmark runs |
| `default_timeout` | float | 60.0 | Per-trial timeout in seconds |
| `default_topology` | string or null | null | Target topology to run against. Null means all topologies. |
| `log_level` | string | "WARNING" | Logging verbosity |

### 2.2 Priority layering

Any config value must be resolvable from four sources, applied in this strict priority order:

1. **Explicit argument** — a value passed directly to a function or CLI command at call time. Always takes precedence over everything else.
2. **Environment variable** — a value set in the process environment. Takes precedence over stored config and defaults. Must be documented for each key.
3. **Stored config** — a value previously saved to `config.json` via `ember config set`. Persists across sessions.
4. **Package default** — the fallback value when no other source provides one.

Every config key must support all four layers. A value set at a lower-priority layer must never override a value set at a higher-priority layer.

### 2.3 Backwards compatibility

Adding a new config key in a future package version must not break existing stored config files. Keys present in the stored file but absent from the current package must be silently ignored. Keys absent from the stored file must fall back to the package default.

### 2.4 Storage format

Config must be stored in a human-readable, human-editable format. Users must be able to edit the config file directly in a text editor as an alternative to using the CLI.

### 2.5 Output directory resolution

The output directory specifically must be resolved consistently everywhere in the codebase. No part of the benchmark runner or related code may hardcode an output path or independently implement output directory logic. All output path resolution must go through a single shared function.

---

## 3. Custom Algorithm Registration

### 3.1 Purpose

Users must be able to write a custom embedding algorithm in a `.py` file and register it with EMBER's algorithm registry so it is available in all subsequent benchmark runs without re-importing or re-declaring it each time.

### 3.2 Contract compliance

A custom algorithm file must follow the same algorithm contract as built-in algorithms. The contract is defined separately in the algorithm contract document. A file that does not comply with the contract must be rejected at add time with a clear error message identifying the specific violations.

### 3.3 Loading

All `.py` files in the user algorithms directory must be loaded automatically when EMBER initialises. This must happen without any explicit user action beyond having added the file. Custom algorithms must appear in `ember algos list` alongside built-in algorithms.

### 3.4 Failure isolation

A custom algorithm file that fails to load — due to a syntax error, import error, or contract violation discovered at load time — must not prevent EMBER from initialising or other algorithms from loading. The failure must produce a warning message that identifies the file and the error, and directs the user to a remediation command.

### 3.5 Naming

Custom algorithm names must not conflict with built-in algorithm names. If a user attempts to register an algorithm with a name that is already registered, the add operation must fail with a clear error before copying the file.

### 3.6 Persistence

Custom algorithms must persist across sessions and across package upgrades. They must not be removed by upgrading or reinstalling `ember-qc`.

### 3.7 Optional dependencies

A custom algorithm may declare additional Python packages it requires, using the same mechanism as built-in algorithms. If those packages are not installed, the algorithm must be registered but marked unavailable, with the same install-instruction behaviour as built-in optional algorithms. Custom algorithms must not be auto-installed or silently failed — the same error-prompt pattern applies.

---

## 4. Compiled Binary Management

### 4.1 Binaries are not part of the PyPI package

Compiled C++ binaries must not be distributed through PyPI. The PyPI package contains only Python wrappers. The C++ source lives in the GitHub repository. Compiled binaries live in the user binary directory after the user builds them.

### 4.2 Binary discovery

Each algorithm wrapper that depends on a compiled binary must search for that binary in the following locations, in priority order:

1. A per-algorithm environment variable (e.g. `EMBER_ATOM_BINARY`) pointing to an explicit path. This supports HPC environments where the binary is built centrally and loaded via a module system.
2. The user binary directory managed by EMBER.

If the binary is found and is executable, the algorithm is considered available. If it is not found in either location, the algorithm must be registered as unavailable with a clear error message pointing to the install command.

### 4.3 Binary verification

When a binary is installed via the CLI, EMBER must verify that the installed binary is executable and produces a valid response before reporting success.

### 4.4 Platform constraints

The binary install command must check for required build tools before attempting compilation. If build tools are absent, the command must report clearly which tools are missing and how to install them for common platforms. It must not attempt compilation if build tools are missing.

---

## 5. CLI Requirements

### 5.1 `ember config` commands

#### `ember config show`
- Display all config keys, their current resolved values, and the source of each value (default / stored config / environment variable)
- Must make it unambiguous where each value is coming from
- Must indicate if any environment variable overrides are active

#### `ember config set <key> <value>`
- Write the given value for the given key to the stored config file
- Must validate that the key is a known config key; unknown keys must be rejected with a list of valid keys
- Must validate that the value is the correct type for the key; invalid types must be rejected with a clear error

#### `ember config get <key>`
- Print the current resolved value for a single key
- Must reflect the full priority layering — if an environment variable is overriding the stored value, the environment variable's value must be shown

#### `ember config reset`
- Remove the stored config file, reverting all keys to package defaults
- Must prompt for confirmation before deleting

#### `ember config path`
- Print the absolute path to the config file
- Must print the path even if the file does not yet exist

---

### 5.2 `ember algos` commands

#### `ember algos list`
- Display all registered algorithms — built-in and custom — with name, version, and availability status
- Unavailable algorithms must display the reason and the exact command to make them available
- Built-in and custom algorithms must be visually distinguished
- Custom algorithms must display the filename they were loaded from

#### `ember algos list --custom`
- Display custom algorithms only

#### `ember algos list --available`
- Display only algorithms that are currently available

#### `ember algos add <file>`
- Validate the file against the algorithm contract before copying
- If validation fails, print all violations and do not copy the file
- If the algorithm name conflicts with an existing registration, reject with a clear error
- If the filename already exists in the user algorithms directory, prompt for confirmation before overwriting
- On success, confirm the file has been added and suggest `ember algos list` to verify

#### `ember algos add <directory>`
- Add all `.py` files in the given directory
- Report results per file — success or specific failure for each

#### `ember algos remove <name>`
- Remove the custom algorithm with the given name
- Must identify the file to be removed and prompt for confirmation
- Must not remove built-in algorithms

#### `ember algos validate <file>`
- Run the contract validation check without adding the file
- Report all violations if any; report success if none
- Must not modify the registry or copy any files

#### `ember algos template`
- Print a fully documented algorithm template to stdout
- Template must conform to the current algorithm contract
- User can redirect to a file: `ember algos template > my_algo.py`

#### `ember algos reset`
- Remove all custom algorithms from the user algorithms directory
- Must prompt for confirmation and display the list of files that will be deleted before proceeding

#### `ember algos dir`
- Print the absolute path to the user algorithms directory

---

### 5.3 `ember install-binary` commands

#### `ember install-binary <name>`
- Valid names are `atom` and `oct`
- Check for required build tools before proceeding; fail clearly if absent
- Download the C++ source, compile it, and install the resulting binary to the user binary directory
- Verify the binary after installation
- Report the installed path on success
- Must not leave partial build artifacts on failure

#### `ember install-binary --list`
- List available binaries, their install status, and the path if installed

---

## 6. Cross-cutting Constraints

### 6.1 No silent failures

Every failure in the user data directory system — failed algorithm load, missing binary, config parse error — must produce a visible warning or error. Nothing in this system may fail silently.

### 6.2 No silent environment mutation

EMBER must never install Python packages automatically. If a required package is missing, EMBER must raise an error with explicit install instructions. The user's environment is theirs to manage.

### 6.3 Inspectability

A user must be able to inspect the full state of the user data directory system using only CLI commands — what is configured, what custom algorithms are registered, what binaries are available, and where all of this is stored on disk. Nothing must require directly inspecting the filesystem to understand EMBER's state.

### 6.4 Graceful degradation

If the user data directory cannot be created or accessed — due to permissions or filesystem constraints — EMBER must still function with built-in algorithms and package defaults. The failure to access the user data directory must produce a clear warning, not a crash.