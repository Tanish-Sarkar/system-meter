# System Meter

System Meter (`speakup`) is a cross-platform command-line tool for getting a fast snapshot of a computer's system information. It aims to help developers, IT/helpdesk teams, and operators quickly inspect resource usage without opening a graphical system monitor.

> **Status:** The default `speakup` command displays a human-readable snapshot. `speakup --json` emits versioned JSON, `speakup --quiet` silently checks whether snapshot collection succeeds, and `speakup doctor` prints a local diagnostic summary. Watch mode is not implemented yet.

## Product direction

System Meter is **CLI-only** and snapshot-oriented. The default command should be quick to run and easy to read in a terminal. It will not become a graphical app or a live dashboard.

The project should be useful to:

- **Developers** investigating slow builds, tests, or local services.
- **IT and helpdesk teams** collecting consistent workstation troubleshooting details.
- **Operators and SREs** taking a quick host snapshot during incident response.
- **Everyday terminal users** who want a clear system overview without a separate system monitor.

## What it should do

### A useful default snapshot

Show concise, labeled metrics with clear units and a simple overall health summary:

- CPU activity and basic processor/system details.
- Memory usage and capacity.
- Available storage on drives or mounted filesystems.
- Battery level and charging state when the device exposes them.
- Uptime and other useful, portable system details.
- GPU or NPU information only where it can be reported reliably without compromising core portability.

Unavailable metrics should be explained plainly rather than shown as empty values or errors. The core command should work without administrator privileges wherever possible.

### Useful to people and automation

- Human-readable terminal output by default, with restrained color and clear status indicators.
- A `--json` option with a versioned schema for scripts and integrations.
- A `--quiet` option that silently checks collection success and communicates failures through its exit status; it does not judge system health.
- Predictable exit codes, a no-color mode, and sensible behavior in pipes and CI logs.
- Thresholds that can eventually be configured to match a team's environment rather than imposing universal assumptions.

### Practical troubleshooting

A future `speakup doctor` command should print a local, reviewable diagnostic summary that is easy to inspect or intentionally redirect to a support file. It should explain what information is included, avoid personal data, and never upload or transmit diagnostics automatically.

### The `watch` command

`speakup watch` should periodically refresh the same compact snapshot in the terminal so a user can observe changing values. It remains a terminal command—not a separate graphical app or a full-screen dashboard. It should be easy to stop and should avoid excessive resource use.

## Planned command interface

These commands describe the CLI. Implemented behavior is noted; planned behavior remains **not implemented yet**:

| Command | Intended purpose |
| --- | --- |
| `speakup` | Print one concise, human-readable system snapshot. |
| `speakup --json` | **Implemented:** Print one snapshot as versioned JSON. See the [JSON schema plan](docs/phase-4-json-and-quiet-plan.md#proposed-json-contract). |
| `speakup --quiet` | **Implemented:** Silently check collection success; no health thresholds are applied. |
| `speakup doctor` | **Implemented:** Print a local diagnostic summary of collected metrics and limitations. The report is not a health assessment. |
| `speakup watch` | **Planned:** Repeatedly refresh the compact terminal snapshot until stopped. |

The options and subcommands should have consistent help text and clear errors. The [Phase 4 plan](docs/phase-4-json-and-quiet-plan.md) documents JSON compatibility and quiet-mode exit behavior.

## What makes it feel polished

- Fast startup and a compact layout that works in narrow terminals.
- Clear units, consistent rounding, and understandable health labels.
- Subtle terminal styling that remains readable without color.
- Helpful explanations for warnings and unavailable hardware metrics.
- Output that remains useful when copied into an issue, support ticket, or CI log.

“Cool” should mean polished, fast, and dependable—not noisy or distracting.

## Learning-first development plan

Work through these phases in order. For each phase, study the linked material **before implementing**, then build and test a small deliverable. The links are the starting references; the project code and tests are where the concepts get practiced.

### Phase 0 — Get comfortable with the project and its tools

- **Before implementing — learn:** How Python environments, project metadata, and dependency locking fit together.
- **Read:** [uv projects](https://docs.astral.sh/uv/guides/projects/), [Python Packaging User Guide: `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/), and [Python's `unittest` documentation](https://docs.python.org/3/library/unittest.html).
- **What we will do:** Use Python 3.13 and uv consistently; understand the `src/` layout, installed command entry point, lockfile, and existing smoke test.
- **Deliverable:** A reproducible local setup using `uv sync`, with tests runnable using `uv run python -m unittest discover -s tests`.
- **What you will learn:** Environments, dependencies, lockfiles, package layout, command entry points, and the purpose of automated tests.

### Phase 1 — Design and implement the command-line interface

- **Before implementing — learn:** How command-line arguments, options, subcommands, help, and parse errors work.
- **Read:** [Python's `argparse` tutorial](https://docs.python.org/3/howto/argparse.html), [the `argparse` reference](https://docs.python.org/3/library/argparse.html), and [Python Packaging: entry points](https://packaging.python.org/en/latest/specifications/entry-points/).
- **Status:** CLI skeleton implemented; see the [Phase 1 CLI plan](docs/phase-1-cli-plan.md) for its command contract and acceptance checklist.
- **Deliverable:** All requested commands appear in `--help`, route to deliberate handlers, and have parser tests—even where a handler temporarily reports that its feature is not ready.
- **What you will learn:** CLI design, argument parsing, separation of responsibilities, error handling, and how to test command behavior without depending on a real machine's metrics.

### Phase 2 — Collect reliable system information

- **Before implementing — learn:** Which system metrics `psutil` provides, which are platform-dependent, and how to represent unavailable values.
- **Read:** [psutil documentation](https://psutil.readthedocs.io/en/latest/), especially its CPU, memory, disk, battery, and system functions; [Python's `dataclasses` documentation](https://docs.python.org/3/library/dataclasses.html).
- **Status:** Implemented and tested; see the [Phase 2 metrics and testing plan](docs/phase-2-metrics-plan.md) for data model, collector behavior, and test coverage.
- **What we will do:** Create a typed snapshot and independent collectors for CPU, memory, disks, optional battery, uptime, and basic operating-system details. Mock platform calls so missing metrics and collection errors can be tested deterministically.
- **Deliverable:** Structured snapshot data and unit tests for available, unavailable, and failed metric collection.
- **What you will learn:** Calling a third-party API, modeling data, type hints, platform differences, exceptions, and isolating hardware access behind testable functions.

### Phase 3 — Make the default snapshot clear and polished

- **Before implementing — learn:** How to format values consistently and how terminal output should behave in interactive terminals and pipes.
- **Read:** [Rich documentation](https://rich.readthedocs.io/en/stable/), especially [console output](https://rich.readthedocs.io/en/stable/console.html) and [tables](https://rich.readthedocs.io/en/stable/tables.html); [Python's `shutil.get_terminal_size`](https://docs.python.org/3/library/shutil.html#shutil.get_terminal_size).
- **Status:** Implemented and tested; see the [Phase 3 terminal output plan](docs/phase-3-terminal-output-plan.md) for report content, formatting, and test coverage.
- **What we will do:** Render the Phase 2 snapshot as one concise default report with consistent units, optional fields, warnings, and plain output for pipes. Do not add arbitrary health scores or thresholds.
- **Deliverable:** A readable default report, with deterministic tests for formatting, missing values, errors, and non-interactive output.
- **What you will learn:** Presentation versus data collection, terminal capabilities, formatting, accessibility, and output testing.

### Phase 4 — Add JSON and quiet automation modes

- **Before implementing — learn:** JSON serialization, designing stable machine-readable interfaces, and how shell scripts consume exit statuses.
- **Read:** [Python's `json` documentation](https://docs.python.org/3/library/json.html), [Python's `sys` documentation](https://docs.python.org/3/library/sys.html), and [pytest's capture and monkeypatch guides](https://docs.pytest.org/en/stable/how-to/capture-stdout-stderr.html) as an optional testing reference (the project can continue using `unittest`).
- **Status:** Implemented and tested; see the [Phase 4 JSON and quiet mode plan](docs/phase-4-json-and-quiet-plan.md) for the schema, exit codes, and test coverage.
- **What we will do:** Implement `speakup --json` from the same snapshot as the human report, and make `speakup --quiet` a silent collection-success check. Quiet mode will not apply undefined health thresholds.
- **Deliverable:** Versioned JSON output, documented exit behavior, and tests for valid output, optional values, errors, and option combinations.
- **What you will learn:** Serialization, backward-compatible interfaces, stdout versus stderr, exit codes, and scripting/CI integration.

### Phase 5 — Build a privacy-conscious `doctor` command

- **Before implementing — learn:** How to distinguish a diagnostic check from normal reporting, and how to minimize sensitive information in support output.
- **Read:** [Python's `platform` documentation](https://docs.python.org/3/library/platform.html), [Python's `tempfile` documentation](https://docs.python.org/3/library/tempfile.html) if report files are needed, and the project's metric and output documentation from earlier phases.
- **Status:** Implemented and tested; see the [Phase 5 doctor and privacy plan](docs/phase-5-doctor-plan.md) for report scope, privacy boundaries, and test coverage.
- **What we will do:** Implement `speakup doctor` as a local stdout report using the existing snapshot. Include collection limitations, do not make health judgments, and require intentional shell redirection if the user wants to save it.
- **Deliverable:** A useful diagnostic report and tests proving sensitive fields are excluded and collection errors are surfaced.
- **What you will learn:** Diagnostic design, data minimization, safe file handling, and testing what a report does not disclose.

### Phase 6 — Add `watch` as a terminal refresh command

- **Before implementing — learn:** How to handle repeated work, intervals, clean shutdown, and terminal refresh behavior without creating a graphical interface.
- **Read:** [Python's `time` documentation](https://docs.python.org/3/library/time.html), [Python's signal handling documentation](https://docs.python.org/3/library/signal.html), and Rich's [live display documentation](https://rich.readthedocs.io/en/stable/live.html).
- **Status:** Planned; behavior and test contract agreed. See the [Phase 6 watch and testing plan](docs/phase-6-watch-plan.md).
- **What we will do:** Implement `speakup watch` with a configurable interval (default 2 seconds), a refreshed human-readable view in interactive terminals, and versioned JSON Lines output with `speakup --json watch`. Stop cleanly on Ctrl+C and avoid unnecessary CPU use. Keep it a terminal command, not a dashboard application.
- **Deliverable:** A responsive watch mode with validated interval settings, testable refresh/error/stop behavior, automation-friendly JSON Lines, and clear help text.
- **What you will learn:** Loops and timing, interruption handling, reusable components, and testing behavior that changes over time.

### Phase 7 — Verify, package, and prepare for real users

- **Before implementing — learn:** How to test a Python package, verify built artifacts, and reason about platform-specific behavior.
- **Read:** [Python Packaging User Guide: packaging projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/), [uv build and publish](https://docs.astral.sh/uv/guides/package/), and the [psutil platform notes](https://psutil.readthedocs.io/en/latest/).
- **What we will do:** Run the test suite and package build, verify installation and entry-point invocation, and document differences and limitations for Windows, macOS, and Linux. Add CI across supported platforms before calling cross-platform behavior verified.
- **Deliverable:** Reproducible builds, documented installation and support, passing automated checks, and a clear first-release checklist.
- **What you will learn:** Packaging, release engineering, CI, cross-platform testing, and how to make support claims based on evidence.

### Later — Optional metrics and integrations

Only after the core commands are dependable, investigate GPU, NPU, temperature, or network metrics individually. **Before each addition**, review the relevant platform or vendor documentation and confirm that it can be optional, privacy-conscious, and tested without making the core CLI unreliable.

## Technology and support

- **Python:** 3.13 or newer.
- **Package and environment management:** [uv](https://docs.astral.sh/uv/).
- **System metrics:** `psutil` for portable metrics where the platform supports them.
- **Terminal output:** `rich` for readable command-line formatting.
- **Packaging:** `pyproject.toml`, setuptools, and the `speakup` command entry point.
- **Target platforms:** Windows, macOS, and Linux.

## Getting started

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Python 3.13 or newer, then run these commands from the repository root:

```bash
uv sync
uv run speakup
```

To install the command as a global uv tool after the repository is published:

```bash
uv tool install git+https://github.com/<OWNER>/<REPOSITORY>.git
speakup
```

Replace `<OWNER>` and `<REPOSITORY>` with the actual GitHub owner and repository name.

## Repository layout

```text
src/
  speakup/       CLI package and system-information modules
tests/           Automated tests
pyproject.toml   Project metadata, dependencies, and CLI entry point
uv.lock          Reproducible dependency resolution
.python-version  Preferred Python version for uv
README.md        Project direction, setup, and roadmap
```
