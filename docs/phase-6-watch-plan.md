# Phase 6 — Terminal Watch Mode and Testing Plan

This document turns Phase 6 of the [project roadmap](../README.md#learning-first-development-plan) into an implementation and testing plan. Watch mode will repeatedly collect the existing system snapshot and present it either as a refreshed terminal view or as JSON Lines for automation.

**Status:** Planned; behavior decisions confirmed. Watch mode is not implemented yet.

## Goal

Implement:

```text
speakup watch [--interval SECONDS]
speakup --json watch [--interval SECONDS]
```

The normal `speakup`, `speakup --json`, `speakup --quiet`, and `speakup doctor` behaviors remain one-shot commands. Watch mode is still a CLI command; it is not a dashboard application or background service.

## Before coding: learn

Study these resources before implementation:

1. [Python `time` documentation](https://docs.python.org/3/library/time.html) — use monotonic time for elapsed-time scheduling and sleep rather than busy-waiting.
2. [Python signal handling documentation](https://docs.python.org/3/library/signal.html) — understand how Ctrl+C becomes `KeyboardInterrupt` in the main thread.
3. Rich's [live display documentation](https://rich.readthedocs.io/en/stable/live.html) — refresh one display in place without flooding the terminal with full reports.
4. [Python `unittest.mock` documentation](https://docs.python.org/3/library/unittest.mock.html) — replace collection and waiting in deterministic loop tests.
5. The project's [snapshot renderer](../src/speakup/render.py), [collector](../src/speakup/collectors.py), [JSON schema](./phase-4-json-and-quiet-plan.md), and [serialization implementation](../src/speakup/serialization.py) — reuse existing output and data contracts.

## Watch behavior contract

### Refresh interval

- The default interval is **2 seconds**.
- `--interval SECONDS` accepts a finite number of seconds greater than or equal to **1**. Fractional values are allowed.
- Reject missing values, non-numeric values, zero, negative values, `NaN`, and infinities through `argparse` with exit status **2**.
- Schedule against a monotonic clock and sleep rather than spinning. The interval is the target time between snapshot starts; if collection takes longer than the interval, start the next collection after the current one completes.
- Do not impose an arbitrary maximum interval.

### Human-readable interactive mode

- `speakup watch` requires stdout to be an interactive terminal. If stdout is redirected or piped without JSON mode, print a concise message to stderr that points to `--json` and return **2** instead of producing an unbounded, hard-to-read stream.
- In a terminal, refresh one human-readable snapshot in place. Reuse the existing snapshot content, formatting, warnings, and optional metric handling; do not accumulate a new full report on every refresh.
- Keep the capture time visible so users can tell how current the displayed values are.
- Do not switch to an alternate screen or clear the user's scrollback.

### JSON Lines mode

- `speakup --json watch` writes one complete JSON object followed by one newline for every successful collection. This is JSON Lines: each line independently follows the existing schema version 1 contract.
- JSON Lines go to stdout with no Rich styling, status text, blank separators, or terminal-control sequences. This output is suitable for pipes and log collection.
- Reuse the existing schema mapping and validation in `serialization.py`. The current one-shot serializer is pretty-printed across multiple lines, so add a compact serialization path for watch output while keeping existing `speakup --json` formatting unchanged.
- `--quiet` has no meaningful watch behavior and must be rejected with exit status **2**. `--json` and `--quiet` remain mutually exclusive.

### Errors and clean shutdown

- Collect a new snapshot for each refresh using `collect_snapshot()`. Do not add a second collector or cache prior metric values.
- Optional metric warnings stay attached to each successful snapshot and do not stop watch mode.
- If required collection fails, stop, write a concise error to stderr, and return **1**. Do not present stale data as a newly collected snapshot.
- If JSON serialization fails, stop with a concise stderr error and return **1**; do not emit a malformed or partial JSON line.
- Catch Ctrl+C at the watch loop boundary, allow Rich to restore the terminal, emit no traceback, and return the standard interrupt status **130**.
- Unexpected programming errors must not be hidden by a broad exception handler.
- The command remains read-only and performs no network requests or file writes.

## Suggested implementation design

- Keep command routing and exit statuses in `main.py`, with a focused watch loop in a small module or helper if that makes timing and output mode responsibilities easier to test.
- Inject or patch the collector, monotonic clock, sleep function, and output console in tests; tests must not wait for real intervals or inspect the host's live metrics.
- Reuse the existing `SystemSnapshot`, schema mapping, and validation. Add a compact JSONL encoding path without changing the existing pretty-printed one-shot JSON output.
- Refactor the snapshot presentation only as needed to let the existing renderer provide a renderable that Rich Live can update. Keep the ordinary one-shot renderer's content and behavior unchanged.
- Use Rich Live for human output only. JSON Lines must bypass Rich Live and write directly to stdout.
- Validate interval input before starting collection. Ensure `--quiet watch` and human watch output redirected to a non-terminal cannot silently appear to succeed.
- Avoid adding new dependencies; Rich, psutil, and the standard library already cover the planned behavior.

Suggested layout:

```text
src/speakup/
  main.py          # Parse options, route watch, report command failures and statuses
  render.py        # Share snapshot content with the live human display
  watch.py         # Optional focused loop for timing and repeated collection
tests/
  test_cli.py      # Watch argument routing, output modes, errors, and exit statuses
  test_render.py   # Snapshot renderable remains useful in both one-shot and live output
  test_watch.py    # Deterministic interval, repeated collection, JSON Lines, and stop tests
```

Only add `watch.py` if it improves separation and testability; a small, clear implementation in an existing module is also acceptable.

## Testing strategy

All tests should use fixed snapshots and mocks. Do not depend on real hardware metrics, terminal dimensions, elapsed wall-clock time, or user interruption.

### Argument and CLI tests

- Verify `watch` help describes the interval and supported output behavior.
- Verify the default interval is 2 seconds and an explicit fractional interval is accepted.
- Verify invalid interval values (non-numeric, less than 1, `NaN`, and positive/negative infinity) return argparse status **2**.
- Verify `--quiet watch` is rejected, and existing mutual exclusion of `--json` and `--quiet` remains intact.
- Verify human watch mode rejects non-interactive stdout with an actionable stderr message and status **2**.
- Verify the default snapshot, one-shot JSON, quiet mode, doctor, and existing parser behavior are unchanged.

### Watch-loop tests

- Patch collection and time functions; assert that repeated iterations collect one fresh snapshot per cycle and wait without busy-spinning.
- Use a controlled monotonic-clock sequence to verify interval scheduling, including collection taking longer than the requested interval.
- Trigger `KeyboardInterrupt` during the wait; assert the loop exits promptly with status **130**, no traceback, and the expected cleanup behavior.
- Inject `SnapshotCollectionError`; assert the watch stops with status **1**, writes a concise error to stderr, and does not treat stale output as a new sample.
- Inject an unexpected exception; assert it is not silently converted into a successful exit.
- Verify optional warnings are rendered/serialized in each successful sample and do not stop the loop.

### Human-rendering tests

- Use a Rich `Console` with a controlled in-memory output; verify the displayed frame includes the expected fixed snapshot values and capture time.
- Verify multiple updates replace/update the live display rather than appending full snapshots as separate reports.
- Verify ordinary `render_snapshot` output remains compatible with current tests and does not acquire live-control behavior.
- Verify Rich Live cleanup is performed after normal failure and Ctrl+C without brittle assertions about terminal escape sequences.

### JSON Lines tests

- Run multiple fixed snapshots through `speakup --json watch`; parse stdout one line at a time with the standard JSON parser.
- Assert each line is exactly one complete schema-version-1 object, in order, with a trailing newline and no non-JSON content on stdout.
- Assert JSON Lines contain no ANSI escape sequences or human-readable status messages.
- Verify a serialization error stops with status **1**, writes only the error to stderr, and never emits a partial line for the failed snapshot.
- Verify a collection error leaves stdout containing only previously completed valid lines.

### Manual checks

After the automated tests pass:

1. Run `uv run speakup watch` in a terminal, confirm the display refreshes in place, and stop it with Ctrl+C.
2. Run `uv run speakup watch --interval 1.5`; confirm the configured interval is accepted and the terminal remains responsive.
3. Run `uv run speakup --json watch --interval 1` and pipe it to a JSON-lines parser; confirm each line parses independently.
4. Redirect human-mode output and confirm it fails promptly with the `--json` guidance rather than filling a file.
5. Verify the normal one-shot snapshot, `--json`, `--quiet`, and `doctor` commands still work.

## Suggested implementation sequence

1. Read the timing, signal, Rich Live, and mocking references above.
2. Add interval parser tests, output-mode tests, and deterministic loop tests before implementation.
3. Refactor snapshot rendering only as required to provide a reusable Rich renderable for live updates.
4. Implement the watch loop with monotonic scheduling, bounded waiting, explicit errors, and Ctrl+C status **130**.
5. Add compact JSON Lines encoding using the existing schema mapping and validation; preserve the one-shot JSON output format.
6. Run focused tests, the complete test suite, the manual terminal checks, and a package build.

## Acceptance checklist

- [ ] `speakup watch` refreshes a human-readable view in place when stdout is a terminal.
- [ ] Human watch mode rejects redirected stdout with a clear instruction to use `--json`.
- [ ] The default refresh interval is 2 seconds; finite intervals of at least 1 second are accepted.
- [ ] Invalid intervals and unsupported output-mode combinations return **2** with useful usage feedback.
- [ ] `speakup --json watch` emits one valid, versioned JSON object per successful sample, one per line.
- [ ] Collection and serialization failures return **1**, report to stderr, and do not produce a false or partial success.
- [ ] Ctrl+C exits without a traceback, cleans up the live display, and returns **130**.
- [ ] The loop sleeps and uses monotonic time; it does not busy-spin or recollect while displaying the same sample.
- [ ] Existing snapshot, JSON, quiet, doctor, and help/version behavior remains unchanged.
- [ ] Tests use controlled clocks, fixed snapshots, and mocks; no real wait or hardware dependency is required.
- [ ] No new dependency, file-write behavior, network behavior, or graphical dashboard is introduced.

## Deliverable and learning outcome

**Deliverable:** A responsive terminal watch command with predictable interval settings, clean interruption behavior, and JSON Lines support for scripts and log pipelines.

**You will learn:** Monotonic timing, repeated work, signal/interruption handling, Rich live rendering, structured streaming output, and deterministic testing of time-dependent behavior.

## Out of scope for Phase 6

- User-defined health thresholds, alerts, or automatic remediation.
- Recording snapshots to a file or database.
- Remote monitoring, telemetry, or a network service.
- Background execution, daemon behavior, or a graphical dashboard.
- New metrics or a new JSON schema.
