# Phase 3 — Human-Readable Terminal Snapshot Plan

This document turns Phase 3 of the [project roadmap](../README.md#learning-first-development-plan) into an implementation and testing plan. Phase 2 already collects a structured `SystemSnapshot`; Phase 3 will format that data and make `speakup` display one snapshot.

**Status:** Implemented and tested. The checklist below records the completed Phase 3 scope.

## Goal

Make a regular `speakup` invocation:

1. Collect exactly one snapshot using `collect_snapshot()`.
2. Render it as a compact, readable terminal report.
3. Return success on completion, or explain a collection failure on stderr and return a non-zero status.

Keep the existing `--json`, `--quiet`, `doctor`, and `watch` placeholder behavior unchanged. They belong to later phases.

## Before coding: learn

Study these resources before building the renderer:

1. [Rich console output](https://rich.readthedocs.io/en/stable/console.html) — console configuration, color, and output streams.
2. [Rich tables](https://rich.readthedocs.io/en/stable/tables.html) — readable tabular data without hand-built padding.
3. [Rich text and markup](https://rich.readthedocs.io/en/stable/markup.html) — safe use of styles and avoiding accidental interpretation of metric text as markup.
4. [Python `shutil.get_terminal_size`](https://docs.python.org/3/library/shutil.html#shutil.get_terminal_size) — terminal width, if the chosen layout needs it.
5. [Python `unittest.mock`](https://docs.python.org/3/library/unittest.mock.html) — substitute a fixed snapshot and collect output without relying on local hardware.

## Proposed report content

Use the same structured model for every displayed value. Keep collection logic out of the renderer and keep the renderer free of system calls.

Suggested sections:

- **System:** OS name/release, architecture, capture time, and uptime.
- **CPU:** utilization percentage, logical cores, and physical cores when available.
- **Memory:** used and total bytes, available bytes, and usage percentage.
- **Storage:** one row per collected mount, showing mount point, used/total space, free space, and usage percentage.
- **Battery:** percentage and charging/discharging state when the state is known; omit the section if no battery is reported.
- **Notes:** collection warnings, including storage or battery availability warnings.

Do not present a global “healthy” score, red/yellow/green health judgment, or high-usage warning threshold in this phase. The project has not defined policy thresholds, and arbitrary severity labels could mislead users. Show measured values plainly; threshold-based interpretation can be considered after requirements are agreed.

## Formatting rules

- Use a concise title and clear section labels.
- Format bytes with binary units (KiB, MiB, GiB, TiB), consistently and with limited decimal places; retain raw values in the model.
- Format percentages consistently, for example one decimal place.
- Format uptime as readable days/hours/minutes without losing the underlying seconds.
- Display unavailable optional values as “not available” or omit the optional field/section; never display `0` as a substitute for unknown data.
- Use restrained styling for emphasis only. The text must remain understandable without color.
- Keep disk rows readable in narrow terminals; do not truncate a mount in a way that makes two mounts indistinguishable.
- Ensure metric text is rendered as literal text, not interpreted as Rich markup.

## Terminal, pipe, and error behavior

- Write the normal report to stdout.
- Configure Rich not to emit ANSI color/control codes when stdout is not an interactive terminal. Plain text written to a pipe or redirected file must remain useful.
- Respect `NO_COLOR` and provide a plain output path. Do not force terminal styling in CI or redirected output.
- Send collection errors to stderr with a concise, actionable message; do not print tracebacks for expected operational failures.
- Preserve exit status `1` for collection failures and `0` when a snapshot was collected and displayed.
- Do not catch arbitrary exceptions as if they were ordinary metric failures. Handle `SnapshotCollectionError` explicitly; unexpected programming errors should remain visible during development.

## Suggested module layout

```text
src/speakup/
  main.py          # CLI dispatch and error/exit handling
  collectors.py    # Existing system data collection
  models.py        # Existing typed snapshot model
  formatting.py    # Pure helpers for units and durations
  render.py        # Rich renderer for a SystemSnapshot
tests/
  test_cli.py
  test_collectors.py
  test_formatting.py
  test_render.py
```

Keep pure formatting helpers separate from Rich rendering so units, rounding, and duration behavior are easy to test. The renderer should accept a snapshot and an output console/stream; it should not call `collect_snapshot()` itself.

## Testing strategy

Tests must use fixed `SystemSnapshot` instances and captured output. They must not assert real CPU load, disk names, battery availability, or installed terminal colors.

### Unit tests: formatting helpers

- Convert values at unit boundaries (bytes, KiB, MiB, GiB, TiB) with the agreed rounding.
- Verify percentages at 0, intermediate values, and 100.
- Format uptime at minute, hour, and day boundaries.
- Handle zero-sized values and `None` without division errors or fabricated measurements.
- Verify negative values are rejected or impossible under validated model constraints.

### Unit tests: renderer

- Assert required report sections and metrics appear with labels and units.
- Assert optional physical CPU count, battery, OS metadata, and disk metadata handle `None`.
- Verify no battery section appears when `battery is None`.
- Verify warnings appear under a notes/warnings section.
- Verify narrow terminal output remains readable and mount points remain distinguishable.
- Verify user-provided or platform-provided text containing Rich markup characters is rendered literally.
- Render with color disabled and assert the output contains no ANSI escape sequences.
- Keep assertions semantic and resilient to harmless whitespace/styling changes; avoid snapshotting every Rich padding character.

### CLI integration tests

- Patch `collect_snapshot()` with a fixed snapshot, invoke `main([])`, and assert the renderer receives that snapshot and stdout contains a report.
- Verify successful snapshot output returns status 0.
- Patch the collector to raise `SnapshotCollectionError`; verify concise stderr output, empty normal report stdout, and status 1.
- Verify unexpected exceptions are not silently converted into a successful report.
- Re-run existing CLI contract tests to ensure help/version, parser errors, and later-phase placeholders are unchanged.

### Manual checks

After deterministic tests pass:

1. Run `uv run speakup` in an interactive terminal and inspect compactness/readability.
2. Redirect output with `uv run speakup > snapshot.txt` and confirm no ANSI escape sequences or terminal control codes are present.
3. Check the report with color disabled.
4. Confirm startup latency remains acceptable despite the CPU sample interval.

These are usability smoke checks, not substitutes for deterministic unit tests. Cross-platform claims still require Phase 7 testing.

## Suggested implementation sequence

1. Read the Rich console/table and formatting references.
2. Agree on the report fields and formatting examples before coding.
3. Implement and test pure byte, percentage, and uptime formatters.
4. Implement `render_snapshot(snapshot, console)` and test it using fixed model objects.
5. Update only the default no-option CLI path to collect and render one snapshot.
6. Handle `SnapshotCollectionError` at the CLI boundary and keep unexpected failures visible.
7. Run all unit and CLI tests, then perform the manual terminal and pipe checks.
8. Confirm that `--json`, `--quiet`, `doctor`, and `watch` remain explicitly unimplemented.

## Acceptance checklist

- [x] `speakup` collects and displays one snapshot using the Phase 2 model.
- [x] Rendering is separate from collection and makes no system calls.
- [x] The report includes system, CPU, memory, storage, uptime, optional battery, and warnings where available.
- [x] Byte values, percentages, and uptime are formatted consistently and tested at boundaries.
- [x] Unknown values are not shown as zero or as fabricated measurements.
- [x] Output is understandable without color and contains no ANSI codes when piped.
- [x] Collection failures go to stderr, return status 1, and do not produce a success-shaped report.
- [x] Tests use fixed snapshots and mocks rather than machine-specific values.
- [x] All Phase 1 CLI tests still pass.
- [x] `--json`, `--quiet`, `doctor`, and `watch` remain outside Phase 3.

## Deliverable and learning outcome

**Deliverable:** A polished, compact, accessible terminal snapshot for the default `speakup` command, with deterministic formatting, rendering, and CLI error tests.

**You will learn:** Human-readable units, separation of presentation from collection, Rich console behavior, terminal and pipe differences, accessibility without color, and testing command-line output.

## Out of scope for Phase 3

- JSON serialization and schema guarantees (Phase 4).
- Quiet/health-check thresholds and health exit statuses (Phase 4).
- `doctor` report behavior (Phase 5).
- Repeated terminal refresh for `watch` (Phase 6).
- Custom thresholds, configuration files, historical data, GPU/NPU/temperature metrics.
- Overall health scoring or red/yellow/green judgments before their thresholds have been defined.
