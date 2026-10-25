# Phase 2 — System Snapshot and Metrics Testing Plan

This document turns Phase 2 of the [project roadmap](../README.md#learning-first-development-plan) into an implementation and test plan. The goal is to collect structured system information reliably; formatting the terminal report and wiring real output into the CLI remain Phase 3.

**Status:** Implemented and tested. See the acceptance checklist for completed scope; CLI rendering remains for Phase 3.

## Goal

Build a small, typed snapshot model and collectors for portable system information:

- Operating system name, release, and machine architecture.
- CPU logical/physical core counts and utilization.
- Virtual memory totals, available/used memory, and usage percentage.
- Storage totals, used/free space, and usage percentage for accessible filesystems.
- Battery charge and charging state when the platform exposes them.
- System uptime.

The collection layer should return data, not print it. It should avoid terminal formatting, health thresholds, JSON serialization, configuration, and graphical UI concerns.

## Before coding: learn

Study enough to understand the APIs and how to test code that calls them:

1. [psutil documentation](https://psutil.readthedocs.io/en/latest/) — CPU, virtual memory, disk partitions/usage, battery, boot time, and platform limitations.
2. [Python dataclasses](https://docs.python.org/3/library/dataclasses.html) and [typing](https://docs.python.org/3/library/typing.html) — representing a snapshot with clear field types.
3. [`unittest.mock`](https://docs.python.org/3/library/unittest.mock.html) — replacing system calls with controlled values and exceptions in unit tests.
4. [Python's `datetime` documentation](https://docs.python.org/3/library/datetime.html) — representing capture time and calculating uptime without local-time ambiguity.
5. [psutil FAQ](https://psutil.readthedocs.io/en/latest/faq.html) — understand caveats such as the first non-blocking CPU percentage reading.

## Data model proposal

Represent one collection result with dataclasses in a dedicated model module. Keep measurements numeric and unformatted so later renderers can use the same data for terminal and JSON output.

```text
SystemSnapshot
  captured_at: timezone-aware UTC datetime
  uptime_seconds: non-negative integer
  system: SystemInfo
  cpu: CpuInfo
  memory: MemoryInfo
  disks: tuple[DiskInfo, ...]
  battery: BatteryInfo | None
  warnings: tuple[str, ...]
```

Recommended field choices:

- `SystemInfo`: operating-system name, release, and machine architecture. Do not collect username or hostname in the default snapshot.
- `CpuInfo`: logical core count, optional physical core count, and utilization percentage in the inclusive range 0–100.
- `MemoryInfo`: total, available, and used bytes as integers, plus utilization percentage.
- `DiskInfo`: device identifier when available, mount point, filesystem type when available, total/used/free bytes, and utilization percentage. Do not include file or directory contents.
- `BatteryInfo`: charge percentage and charging state. Use `None` for the battery object when psutil reports no battery or does not expose battery information; do not invent a percentage.
- `warnings`: human-readable notes for individual metrics that could not be collected. A disk warning may identify its already-collected mount point, but must not include usernames, unrelated paths from exception text, or raw exception dumps.

Use `None` for a value that is genuinely unavailable; do not use magic numbers, empty strings, or zero to mean “unknown.” Store byte counts as integers and percentages as floats. Apply rounding and human-readable units only in Phase 3.

## Collection design

Keep external system calls behind a small collector module. A single `collect_snapshot()` function should assemble the model by calling focused helpers for system, CPU, memory, disks, battery, and uptime.

Recommended behavior:

- Capture one UTC timestamp for the snapshot.
- Use `psutil` for portable metrics and Python's standard library for basic OS details and UTC time.
- CPU utilization requires a sampling interval: a non-blocking first `psutil.cpu_percent()` result may be meaningless. Test and document the chosen interval; measure its startup cost before deciding whether a future CLI option is needed.
- Enumerate normal disk partitions and query their usage individually. If one mount is inaccessible or disappears during collection, add a concise warning and continue with other mounts.
- Treat battery data as optional. A machine with no reported battery still gets a valid snapshot.
- Treat failures in required system, CPU, or memory collection as collection failures rather than returning fabricated values. Define a narrow exception boundary; do not broadly catch every exception.
- Keep warnings deterministic and free from raw tracebacks. A later CLI layer can decide how to show them.
- Do not gather process lists, network addresses, serial numbers, hostnames, or user identity in this phase.

### CPU sampling decision

The CPU percentage API has a trade-off between an immediate result and a short blocking sample. For the initial collector, prefer a short, explicit sample interval that produces a meaningful reading. Measure the resulting latency on the development machine and document the interval in code and tests. Do not silently return the misleading first non-blocking reading just to make collection appear instantaneous.

## Suggested project layout

```text
src/speakup/
  __init__.py
  main.py          # Existing CLI; remains a placeholder until Phase 3 output exists
  models.py        # Snapshot and metric dataclasses
  collectors.py    # psutil/stdlib access and collect_snapshot()
tests/
  test_cli.py      # Existing Phase 1 command tests
  test_collectors.py
```

Keep this small. Split collectors into more modules only if implementation shows a real need. The CLI should remain unchanged in Phase 2: until Phase 3 defines report output, `speakup` can continue to say its snapshot command is not implemented.

## Testing strategy

The test suite must be deterministic, fast, and independent of the host machine's actual hardware.

### Unit tests: model and calculations

- Construct snapshot and metric dataclasses with representative values.
- Verify optional fields accept unavailable values.
- Test calculations such as memory/disk percentages and uptime using fixed inputs if calculations are implemented in our code.
- Cover boundary values: zero usage, full usage, small capacities, and values that should be unavailable.
- Assert percentages stay between 0 and 100; guard against division by zero.
- Verify bytes remain integers and no display formatting is embedded in the data model.

### Unit tests: collectors with mocks

Patch psutil and platform/time calls so tests provide known values and exceptions.

- CPU: verify core counts and a realistic utilization sample are mapped correctly.
- Memory: verify total, available, used, and percentage values.
- Disks: verify multiple mounts are returned; a failed mount yields a warning without losing other mounts.
- Battery: verify a reported battery, charging and discharging states, and `None` when no battery is reported.
- System information: verify platform fields are mapped without including host identity.
- Uptime: verify calculation from a controlled boot time and captured UTC time.
- Required collector errors: verify failures are surfaced rather than converted into success-shaped empty data.
- Warning behavior: verify messages may identify the affected mount point but do not leak raw exception text, tracebacks, or unrelated paths.

Do not assert this machine's exact CPU percentage, disk list, battery presence, memory size, or uptime. Those change by machine and over time.

### Optional manual smoke check

After deterministic tests pass, run a local snippet or temporary test to inspect one real `collect_snapshot()` result on the development machine. Treat this as a smoke check only; do not make CI assertions depend on local hardware. Later, Phase 7 should add automated runs on Windows, macOS, and Linux before claiming cross-platform support.

## Suggested implementation sequence

1. Read the resources above, especially the psutil CPU percentage caveat.
2. Define the dataclasses and field semantics before collecting values.
3. Add tests for the model and any calculations using fixed input values.
4. Implement and test system, memory, and CPU collectors.
5. Implement and test disk enumeration, including an inaccessible mount.
6. Implement and test optional battery reporting and uptime.
7. Add `collect_snapshot()` to assemble data, warnings, and capture time.
8. Run the complete test suite; then perform a local smoke check without adding machine-specific assertions.
9. Keep the Phase 1 CLI behavior unchanged until Phase 3 provides a renderer.

## Acceptance checklist

- [x] Snapshot and metric model types are explicit, typed, and contain raw values rather than formatted strings.
- [x] `collect_snapshot()` returns system, CPU, memory, storage, battery-if-reported, uptime, and capture time.
- [x] Unsupported or missing battery data does not fail the snapshot or invent a value.
- [x] A disk that cannot be queried does not prevent collecting other accessible disks; a warning explains the omission.
- [x] Failures in required collectors are surfaced explicitly.
- [x] CPU sampling uses a meaningful documented interval, not an invalid first non-blocking reading.
- [x] Unit tests use mocks/fixed values and do not depend on actual host metrics.
- [x] Tests cover normal values, missing optional values, inaccessible mounts, and required-call failures.
- [x] No usernames, hostnames, process lists, or network details are collected.
- [x] Existing Phase 1 CLI tests still pass and the CLI remains a placeholder until Phase 3.

## Deliverable and learning outcome

**Deliverable:** A tested, typed snapshot model and deterministic collectors that handle common platform and hardware limitations without printing or fabricating data.

**You will learn:** Dataclasses and type hints, using a third-party system API, testing external calls with mocks, time and units, platform variability, and the difference between optional unavailable data and actual collection failure.

## Out of scope for Phase 2

- Human-readable terminal layout, colors, or tables (Phase 3).
- JSON output and quiet health-check thresholds (Phase 4).
- Diagnostic report generation (Phase 5).
- Repeated refresh/watch behavior (Phase 6).
- GPU/NPU, temperatures, network statistics, process lists, historical storage, or configurable thresholds.
- Claiming full Windows/macOS/Linux support before cross-platform CI and manual verification (Phase 7).
