# System Meter

<p align="center">
  <strong>A colorful, cross-platform system snapshot for your terminal.</strong><br>
  CPU, memory, storage, battery, and uptime—without opening a dashboard.
</p>

<p align="center">
  <a href="https://github.com/Tanish-Sarkar/system-meter/actions/workflows/ci.yml"><img src="https://github.com/Tanish-Sarkar/system-meter/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.13%2B-3776AB?logo=python&logoColor=white" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/interface-CLI-6E56CF" alt="CLI">
</p>

**System Meter** is a Python CLI for developers, IT teams, operators, and anyone who wants a quick view of what their computer is doing. Run `speakup` for a framed, color-coded snapshot, use JSON in scripts, or watch metrics refresh live.

> **Project status:** The CLI and its core commands are implemented. Automated cross-platform CI and TestPyPI release setup are in progress; see the [Phase 7 plan](docs/phase-7-release-readiness-plan.md). Metrics may vary by OS and hardware. This tool reports measurements, not a diagnosis or health score.

## Highlights

- **Readable at a glance:** Color-coded frames, clear units, and a layout that adapts to terminal width.
- **Useful in scripts:** Versioned JSON snapshots, JSON Lines watch output, and predictable exit codes.
- **Easy to troubleshoot:** `doctor` summarizes collected information and limitations locally.
- **No dashboard or telemetry:** Terminal-only, read-only collection; no automatic uploads.
- **Portable by design:** Python 3.13+ and psutil, with optional metrics shown only when available.

## Preview

```text
╔══════════════════════════════════════════════════════════════╗
║  System Meter                                               ║
║  Captured: 2026-01-02 03:04:05 UTC                          ║
╚══════════════════════════════════════════════════════════════╝
╭──────────────────────────── CPU ────────────────────────────╮
│ Usage          18.4%                                         │
│ Logical cores  8                                             │
│ Physical cores 4                                             │
╰─────────────────────────────────────────────────────────────╯
╭────────────────────────── MEMORY ───────────────────────────╮
│ Used       6.0 GiB / 16.0 GiB (37.5%)                        │
│ Available  10.0 GiB                                          │
╰─────────────────────────────────────────────────────────────╯
```

Example values are illustrative; available metrics depend on the host.

## Install

System Meter requires **Python 3.13 or newer**. Choose one installation method below.

Project website and installation guide: [System Meter on GitHub Pages](https://tanish-sarkar.github.io/system-meter/).

### Step 1 — Install Python 3.13

Skip this step if you already have Python 3.13+ installed.

**Windows (PowerShell)**

```powershell
winget install Python.Python.3.13
```

Restart your terminal after installation, then verify with `py -3.13 --version`.

**macOS (Homebrew)**

```bash
brew install python@3.13
```

Verify with `python3.13 --version`.

**Linux (Ubuntu / Debian)**

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13
```

Verify with `python3.13 --version`.

### Step 2 — Install speakup (choose a method)

#### Install globally with pip

Installs `speakup` as a globally available command — no virtual environment needed.

**Windows PowerShell**

```powershell
py -3.13 -m pip install git+https://github.com/Tanish-Sarkar/system-meter.git
```

**macOS / Linux**

```bash
python3.13 -m pip install git+https://github.com/Tanish-Sarkar/system-meter.git
```

To upgrade to the latest version or commit:

**Windows PowerShell**

```powershell
py -3.13 -m pip install --upgrade --force-reinstall --no-cache-dir git+https://github.com/Tanish-Sarkar/system-meter.git
```

**macOS / Linux**

```bash
python3.13 -m pip install --upgrade --force-reinstall --no-cache-dir git+https://github.com/Tanish-Sarkar/system-meter.git
```

#### Install as a user-level tool with uv

```bash
uv tool install git+https://github.com/Tanish-Sarkar/system-meter.git
```

This installs the command in an isolated environment managed by uv. If the shell cannot find `speakup`, ensure uv's tool executable directory is on your `PATH` (see `uv tool update-shell`).

#### Run from a local checkout (development)

```bash
git clone https://github.com/Tanish-Sarkar/system-meter.git
cd system-meter
uv sync
uv run speakup
```

`uv run speakup` uses the project's `.venv` and dependencies. It is intended for development and does not install the command globally.

### Step 3 — Run speakup

After installation, open a new terminal and run:

```bash
speakup
```

That's it. You should see a colorful, framed system snapshot.

## Commands

| Command | What it does |
| --- | --- |
| `speakup` | Collect and display one human-readable system snapshot. |
| `speakup --json` | Print one versioned JSON snapshot to stdout. |
| `speakup --quiet` | Collect a snapshot silently; exit status indicates collection success, not machine health. |
| `speakup doctor` | Print a local diagnostic report with collected metrics and limitations. |
| `speakup watch` | Refresh the human-readable snapshot in an interactive terminal. |
| `speakup watch --interval 5` | Refresh every 5 seconds; the interval must be at least 1 second (default: 2). |
| `speakup --json watch` | Stream one JSON object per line (JSON Lines), suitable for pipes and logs. |
| `speakup --help` | Show available commands and options. |
| `speakup --version` | Show the installed version. |

Press **Ctrl+C** to stop `watch`; it exits with status 130. Human-readable watch mode requires an interactive terminal; use `--json` when piping or redirecting output. `--quiet` is not a watch option.

`--json` has a versioned schema. See the [JSON contract](docs/phase-4-json-and-quiet-plan.md#proposed-json-contract) and [watch/JSON Lines contract](docs/phase-6-watch-plan.md).

## Host the website with GitHub Pages

The single-page site is in [`site/index.html`](site/index.html); its CSS and JavaScript are included in that file. The folder also contains SEO crawler files. A GitHub Actions workflow in `.github/workflows/pages.yml` publishes the `site/` folder.

1. Push this repository to GitHub. For an openly accessible website and anonymous tool installation, set the repository visibility to **Public** in **Settings → General → Danger Zone → Change visibility**.
2. Open **Settings → Pages**.
3. Under **Build and deployment → Source**, select **GitHub Actions**.
4. Push a change to `site/` on the `main` branch, or manually run **Actions → Deploy GitHub Pages → Run workflow**.
5. Wait for the workflow to finish successfully. The project site will be at **https://tanish-sarkar.github.io/system-meter/**.

Subsequent changes under `site/` deploy automatically when pushed to `main`. GitHub may take a few minutes to make the first deployment available.

## Develop and test

Install [uv](https://docs.astral.sh/uv/) and Python 3.13+, then from the repository root:

```bash
uv sync --locked
uv run python -m unittest discover -s tests -v
uv build
```

CI is configured for Python 3.13 on Windows, macOS, and Linux, plus the newest stable Python on Ubuntu. Check the [Actions tab](https://github.com/Tanish-Sarkar/system-meter/actions) for hosted results. Cross-platform behavior still depends on successful runs and real OS/hardware testing.

## Privacy and limitations

- Metrics are collected locally; the program does not automatically transmit them.
- `doctor` is informational and does not make health judgments.
- `--quiet` means required snapshot collection succeeded; it does not mean the computer is healthy.
- Battery, storage, CPU, and other details can differ or be unavailable across platforms.
- Avoid sharing diagnostic output without reviewing it first. Storage mount points may reveal local filesystem names.

## Learning-first development plan

Work through these phases in order. For each phase, study the linked material **before implementing**, then build and test a small deliverable. The links are the starting references; the project code and tests are where the concepts get practiced.

### Phase 0 — Get comfortable with the project and its tools

- **Before implementing — learn:** How Python environments, project metadata, and dependency locking fit together.
- **Read:** [uv projects](https://docs.astral.sh/uv/guides/projects/), [Python Packaging User Guide: `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/), and [Python's `unittest` documentation](https://docs.python.org/3/library/unittest.html).
- **Status:** Complete.
- **What we will do:** Use Python 3.13 and uv consistently; understand the `src/` layout, installed command entry point, lockfile, and existing smoke test.
- **Deliverable:** A reproducible local setup using `uv sync`, with tests runnable using `uv run python -m unittest discover -s tests`.
- **What you will learn:** Environments, dependencies, lockfiles, package layout, command entry points, and the purpose of automated tests.

### Phase 1 — Design and implement the command-line interface

- **Before implementing — learn:** How command-line arguments, options, subcommands, help, and parse errors work.
- **Read:** [Python's `argparse` tutorial](https://docs.python.org/3/howto/argparse.html), [the `argparse` reference](https://docs.python.org/3/library/argparse.html), and [Python Packaging: entry points](https://packaging.python.org/en/latest/specifications/entry-points/).
- **Status:** Implemented and tested; see the [Phase 1 CLI plan](docs/phase-1-cli-plan.md) for its command contract and acceptance checklist.
- **Deliverable:** All commands appear in `--help`, route to deliberate handlers, and have parser and behavior tests.
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
- **What we will do:** Render the Phase 2 snapshot as one concise default report with consistent units, optional fields, warnings, color, and framed sections that adapt to terminal width. Do not add arbitrary health scores or thresholds.
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
- **Status:** Implemented and tested; see the [Phase 6 watch and testing plan](docs/phase-6-watch-plan.md).
- **What we will do:** Implement `speakup watch` with a configurable interval (default 2 seconds), a refreshed human-readable view in interactive terminals, and versioned JSON Lines output with `speakup --json watch`. Stop cleanly on Ctrl+C and avoid unnecessary CPU use. Keep it a terminal command, not a dashboard application.
- **Deliverable:** A responsive watch mode with validated interval settings, testable refresh/error/stop behavior, automation-friendly JSON Lines, and clear help text.
- **What you will learn:** Loops and timing, interruption handling, reusable components, and testing behavior that changes over time.

### Phase 7 — Verify, package, and prepare for real users

- **Before implementing — learn:** How to test a Python package, verify built artifacts, and reason about platform-specific behavior.
- **Read:** [Python Packaging User Guide: packaging projects](https://packaging.python.org/en/latest/tutorials/packaging-projects/), [uv build and publish](https://docs.astral.sh/uv/guides/package/), and the [psutil platform notes](https://psutil.readthedocs.io/en/latest/).
- **Status:** In progress; CI and manually gated TestPyPI workflows are implemented locally. Remote GitHub environment and Trusted Publisher configuration, and hosted CI results, remain to be completed. See the [Phase 7 packaging, CI, and release-readiness plan](docs/phase-7-release-readiness-plan.md).
- **What we will do:** Verify GitHub Actions checks using Python 3.13 on Windows, macOS, and Linux, plus the newest stable Python on Ubuntu. Test, build, install the built package in a clean environment, and smoke-test the installed CLI. Configure and validate the manually approved TestPyPI publishing path; do not publish automatically or target production PyPI.
- **Deliverable:** Reproducible cross-platform checks, verified package artifacts and entry point, documented support limitations, and a manually gated TestPyPI release candidate checklist.
- **What you will learn:** Packaging, release engineering, CI, cross-platform testing, and how to make support claims based on evidence.

### Later — Optional metrics and integrations

Only after the core commands are dependable, investigate GPU, NPU, temperature, or network metrics individually. **Before each addition**, review the relevant platform or vendor documentation and confirm that it can be optional, privacy-conscious, and tested without making the core CLI unreliable.

## Project structure

```text
.github/
  workflows/       CI, TestPyPI, and GitHub Pages deployment
docs/              Phase-by-phase learning and implementation plans
scripts/           Installed-package smoke test used by CI
site/              Single-page GitHub Pages website
src/speakup/       CLI, collectors, renderers, and serialization
tests/             Automated unittest suite
MANIFEST.in        Source distribution contents
pyproject.toml     Package metadata, dependencies, and CLI entry point
uv.lock            Reproducible dependency resolution
.python-version    Preferred Python version for uv
```
