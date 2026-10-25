# Phase 1 — CLI Design and Implementation Plan

This document turns Phase 1 of the [project roadmap](../README.md#learning-first-development-plan) into an implementation-ready plan. It defines the first version of the `speakup` command interface without implementing system metric collection.

**Status:** CLI skeleton implemented and tested. Snapshot data, JSON serialization, diagnostics, and watch behavior remain for later phases.

## Goal

Replace the initialization-only entry point with a small, tested command-line interface for:

```text
speakup
speakup --json
speakup --quiet
speakup doctor
speakup watch
```

Phase 1 establishes command syntax, argument validation, routing, and error/exit behavior. It does **not** collect metrics, format the final snapshot, create diagnostic reports, or run a watch loop. Those belong to later phases.

## Before coding: learn

Study these in order, then refer back while implementing:

1. [Python's `argparse` tutorial](https://docs.python.org/3/howto/argparse.html) — parser, options, subcommands, and help.
2. [`argparse` reference](https://docs.python.org/3/library/argparse.html) — subparsers, mutually exclusive groups, and parser errors.
3. [Python Packaging: entry points](https://packaging.python.org/en/latest/specifications/entry-points/) — how the `speakup` shell command calls the Python function.
4. [Python's `unittest` documentation](https://docs.python.org/3/library/unittest.html) — test the parser and handlers without collecting real machine metrics.

## Proposed first-version command contract

These are the recommended defaults for implementation. Keep them documented and test them so later behavior changes are deliberate.

| Invocation | Phase 1 behavior | Later intended behavior |
| --- | --- | --- |
| `speakup` | Route to the snapshot handler. Until the collector and renderer exist, report that the snapshot feature is not implemented yet. | Collect and print one human-readable system snapshot. |
| `speakup --json` | Route to the snapshot handler with JSON output selected. Until implemented, report that JSON output is not implemented yet. | Print one snapshot as JSON on stdout. |
| `speakup --quiet` | Route to the snapshot handler in quiet mode. Until collection exists, report that the check is not implemented yet. | Suppress normal stdout; return an exit status indicating whether the snapshot check completed. |
| `speakup doctor` | Route to the doctor handler and report that diagnostics are not implemented yet. | Print a local diagnostic summary; do not upload or transmit it. |
| `speakup watch` | Route to the watch handler and report that watch mode is not implemented yet. | Repeatedly refresh the compact terminal snapshot until interrupted. |
| `speakup --help` | Print top-level usage and command help; exit successfully. | Same. |
| `speakup --version` | Print the installed package version; exit successfully. | Same. |

For this learning phase, a clear “not implemented yet” message is intentional. Do not return an empty or success-shaped fake snapshot.

### Output streams and exit statuses

- Successful help/version output goes to stdout and returns **0**.
- Invalid syntax, unknown commands, and incompatible options are reported by `argparse` on stderr and return **2**.
- A recognized but not-yet-implemented feature reports its status on stderr and returns **1**.
- Later, operational collection failures also return **1** and explain the failure on stderr.
- `--quiet` suppresses normal snapshot output. Errors/status explanations may still go to stderr. In the future, a successful collection returns **0**; a collection failure returns **1**. Health thresholds are intentionally out of scope until the project defines what “unhealthy” means.

This keeps exit status `1` for a failed or unavailable operation and avoids claiming a host is healthy based on thresholds that have not been designed.

### Option and subcommand compatibility

- `--json` and `--quiet` apply to the default one-shot snapshot only.
- `--json` and `--quiet` are mutually exclusive: JSON must produce a document on stdout, while quiet mode must not produce the normal snapshot.
- `doctor` and `watch` are subcommands. Do not accept top-level snapshot options with them in this first version; reject combinations such as `speakup doctor --json` and `speakup watch --quiet` with a clear usage error.
- A later phase may add `doctor --json` if a stable diagnostic schema is useful. Do not add it now.
- `watch` starts with a fixed default refresh interval in this phase's interface. A configurable interval can be considered after the basic watch behavior is working.

Examples:

```text
speakup --json          valid
speakup --quiet         valid
speakup --json --quiet  invalid: mutually exclusive output modes
speakup doctor          valid
speakup watch           valid
speakup doctor --json   invalid in the first version
```

## Design boundaries

Use the standard-library `argparse`; do not add a CLI framework dependency for this interface.

Keep responsibilities distinct:

1. **Parser** — describes arguments, validates combinations, and returns parsed options.
2. **Dispatcher/entry point** — selects the requested handler.
3. **Handlers** — initially provide explicit “not implemented yet” responses; later call collectors and renderers.
4. **Process exit status** — returned from the CLI function and used by the console entry point.

Avoid placing system calls, formatting, or business rules in parser setup. Phase 2 should be able to add collectors without rewriting the command grammar.

## Suggested implementation sequence

1. Read the learning resources above and sketch the commands and invalid combinations on paper.
2. Add a parser builder that defines top-level help, `--version`, the mutually exclusive snapshot modes, and the `doctor`/`watch` subcommands.
3. Add small handlers or dispatch functions for the recognized commands. Make unfinished features visibly unfinished.
4. Make the console entry point return an integer status and ensure the generated `speakup` command exits with that status.
5. Add unit tests using explicit argument lists and captured stdout/stderr; do not rely on machine-specific metrics.
6. Run the focused tests and manually inspect `speakup --help` and representative invalid invocations.

## Suggested file responsibility

Keep the existing package small. A reasonable starting point is:

```text
src/speakup/
  __init__.py
  main.py       # CLI entry point and parser/dispatch wiring for Phase 1
tests/
  test_cli.py   # parser, routing, output-stream, and exit-status tests
```

Do not split modules preemptively. Introduce a separate CLI module only if `main.py` becomes hard to understand as real behavior is added.

## Acceptance checklist

- [x] `speakup --help` lists the default invocation and both subcommands.
- [x] `speakup --version` prints the package version.
- [x] The default invocation, `--json`, and `--quiet` route to explicit not-yet-implemented responses.
- [x] `doctor` and `watch` route to their own handlers.
- [x] `--json --quiet` is rejected with an argparse usage error.
- [x] Snapshot options on `doctor` or `watch` are rejected in this first version.
- [x] Unknown options and commands return exit status 2 and write an error to stderr.
- [x] Not-yet-implemented handlers say so explicitly and return exit status 1.
- [x] Tests cover parsing, routing, stdout/stderr, and exit statuses without accessing real system metrics.
- [x] The installed `speakup` entry point resolves to the CLI and propagates its return status.

## Deliverable and learning outcome

**Deliverable:** A tested CLI skeleton with documented syntax, compatible option rules, explicit placeholder handlers, useful help/version output, and predictable exit statuses.

**You will learn:** Argument parsing, subcommands, entry points, separating interface from implementation, process exit codes, and unit testing command-line behavior.

## Out of scope for Phase 1

- Reading CPU, memory, disk, battery, uptime, or hardware metrics.
- Deciding universal health thresholds.
- Final human-readable or JSON snapshot schemas.
- Saving or sharing diagnostic reports.
- Refresh timing, terminal redraw, or watch-loop implementation.
- GPU/NPU or other optional hardware features.
