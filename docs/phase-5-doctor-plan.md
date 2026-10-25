# Phase 5 — Privacy-Conscious `doctor` Command Plan

This document turns Phase 5 of the [project roadmap](../README.md#learning-first-development-plan) into an implementation and testing plan. The command will reuse the structured snapshot from Phase 2 and the presentation principles from Phase 3 to produce a local diagnostic summary.

**Status:** Implemented and tested. The acceptance checklist below records the completed Phase 5 behavior.

## Goal

Implement:

```text
speakup doctor
```

The command should help a user or support technician quickly understand which supported system metrics were collected and which were unavailable. It should report facts and collection limitations—not make unsupported claims that the machine is healthy or broken.

## Before coding: learn

Study these resources before implementation:

1. [Python `platform` documentation](https://docs.python.org/3/library/platform.html) — understand which system identity fields exist and which are deliberately out of scope.
2. [Python `unittest.mock`](https://docs.python.org/3/library/unittest.mock.html) — test doctor behavior using fixed snapshots and controlled collection failures.
3. [OWASP: Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) — data minimization and avoiding secrets or personal data in diagnostic output.
4. The project's [snapshot model](../src/speakup/models.py), [collector behavior](./phase-2-metrics-plan.md), and [terminal-output contract](./phase-3-terminal-output-plan.md) — reuse known data and output conventions rather than adding duplicate collectors.

## Proposed report contract

### Output destination

- Print the diagnostic summary to stdout by default.
- Do not create or overwrite files automatically. A user can intentionally save a report with normal shell redirection, for example `speakup doctor > system-report.txt`.
- Do not upload, transmit, or phone home with any diagnostic data.
- Do not add a doctor-specific JSON schema in this phase; that would need its own schema and compatibility contract.

### Report contents

Include only the data required to describe collection and supported system metrics:

- A report title and UTC capture time.
- Operating-system name/release and machine architecture when available.
- CPU logical/physical core counts and the collected utilization value.
- Memory totals, available/used amounts, and utilization.
- Collected storage mount points and usage values.
- Battery charge/power state only when the platform reports a battery.
- A clearly labeled availability/limitations section containing the snapshot's collection warnings.
- A short explanation that “available” means the metric was collected; it is not a health judgment.

Reuse the existing human-readable formatters/rendering conventions where practical. Avoid producing a second system collector or a near-duplicate general snapshot implementation.

### Privacy boundary

The report must not contain:

- Username, hostname, home directory, or process names/arguments.
- Full paths to files or project directories.
- Network addresses, adapters, or connection details.
- Hardware serial numbers or unique identifiers not already required to report disk mount usage.
- Environment variables, secrets, arbitrary command output, or raw exception messages/tracebacks.
- Any data sent to a remote service.

Storage mount points are included because they identify which filesystem the reported capacity belongs to. Do not include file/directory contents. Keep warning messages concise and sanitized as defined by the collector contract.

## Status and exit behavior

- If the snapshot is collected, print the report and return **0**, even if optional metrics produced warnings. A warning means a metric was unavailable, not that the machine failed a health test.
- If required collection fails with `SnapshotCollectionError`, print a concise doctor-specific failure to stderr and return **1**. Do not print a success-shaped partial report.
- Unexpected programming errors should not be hidden by a broad exception handler.
- Invalid arguments continue to return **2** via argparse.
- The command is read-only: it does not change system settings or files.

## Suggested implementation design

- Add a focused `render_doctor_report(snapshot, console)` function, or a small report module if separation from the standard snapshot renderer improves clarity.
- Keep presentation separate from collection. `main()` handles the command routing, calls `collect_snapshot()` once, sends its result to the doctor renderer, and returns the documented status.
- Reuse the same snapshot collector. Do not recollect individual fields in the doctor renderer.
- Keep output local and stdout-only. Rely on the user's explicit shell redirection if they want a file.
- Do not add `--output`, `--force`, network, or diagnostic upload options in this phase.

Suggested layout:

```text
src/speakup/
  main.py          # Route doctor, collection errors, and exit status
  render.py        # Existing snapshot renderer; add a focused doctor report if appropriate
tests/
  test_render.py   # Doctor report contents and privacy boundary
  test_cli.py      # doctor routing, stdout/stderr, and exit status
```

Prefer extending existing rendering modules over creating a new module for a small amount of report code.

## Testing strategy

Use fixed snapshots and mocks. Tests must not inspect the real host's identity or depend on its actual devices, battery, or system configuration.

### Renderer unit tests

- Verify the report includes capture time, system summary, collected metrics, and an availability/limitations section.
- Verify optional OS fields and physical core count display as unavailable rather than fabricated values.
- Verify no battery section appears if the snapshot has no battery.
- Verify warnings are displayed as limitations, not turned into health failures.
- Verify the report explains that metric availability is not a health assessment.
- Verify the report is readable without color and external text is rendered literally.
- Supply fixture strings that look like usernames, hostnames, file paths, network data, and secrets in fields that must not be rendered; assert those values do not appear.
- Verify only the approved snapshot fields are rendered. Do not put private fixture values into the approved fields and then expect the formatter to redact them; those values must not be collected into this report.

### CLI integration tests

- Invoke `doctor` with a fixed snapshot; assert `collect_snapshot()` is called exactly once, report goes to stdout, stderr stays empty, and status is 0.
- Use a snapshot with optional metric warnings; assert the report includes them and still returns 0.
- Inject `SnapshotCollectionError`; assert concise stderr, empty stdout, and status 1.
- Verify unexpected errors are not silently converted to success.
- Verify `doctor --json`, `doctor --quiet`, and unrelated unknown options remain invalid unless a later phase explicitly adds them.
- Verify normal `speakup`, `--json`, `--quiet`, `watch`, help, and version behavior remain unchanged.

### Manual checks

After tests pass:

1. Run `uv run speakup doctor` and review its contents.
2. Save intentionally with `uv run speakup doctor > system-report.txt`; confirm the tool itself did not create any other file.
3. Review the saved report for personal, host, network, and secret information before sharing it.
4. Verify no upload/network behavior is introduced.

## Suggested implementation sequence

1. Read the privacy and testing references above.
2. Agree on the fields listed in the report contract and confirm stdout-only behavior.
3. Write renderer tests for a fixed normal snapshot, missing optional values, warnings, and forbidden fields.
4. Implement a doctor report renderer using existing snapshot data and output conventions.
5. Route `speakup doctor` through the shared collector once, with explicit collection error handling.
6. Verify output and exit behavior through CLI integration tests.
7. Run the complete suite and perform the manual save/review check.

## Acceptance checklist

- [x] `speakup doctor` prints one local diagnostic summary to stdout and returns 0 when collection completes.
- [x] The report accurately distinguishes collected metrics from unavailable metrics.
- [x] Optional metric warnings do not become a health failure.
- [x] Required collection failures return 1, explain the failure on stderr, and produce no partial report.
- [x] The command collects a snapshot once and reuses existing collectors.
- [x] The command does not create or overwrite files unless the user redirects stdout.
- [x] No automatic upload or network transmission is added.
- [x] The report excludes usernames, hostnames, user directories, process data, network data, serial numbers, environment variables, and raw errors.
- [x] Tests use fixed snapshots/mocks and assert report content and optional-data behavior.
- [x] Existing snapshot, JSON, quiet, parser, and watch-placeholder behavior remains unchanged.

## Deliverable and learning outcome

**Deliverable:** A local, read-only diagnostic report that helps users and support teams understand available metrics and collection limitations without exposing unnecessary personal data.

**You will learn:** Data minimization, designing support diagnostics, reusing structured data, safe exception reporting, and testing privacy boundaries with explicit fixtures.

## Out of scope for Phase 5

- Machine-readable `doctor --json` output or a separate doctor schema.
- Writing files directly, overwrite prompts, or an output-path option.
- Uploading, telemetry, or contacting remote services.
- Health scores, threshold judgments, automatic remediation, or system changes.
- Recollecting metrics independently from the Phase 2 snapshot API.
