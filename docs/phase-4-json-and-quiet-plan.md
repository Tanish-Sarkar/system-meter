# Phase 4 — JSON Output and Quiet Checks Plan

This document turns Phase 4 of the [project roadmap](../README.md#learning-first-development-plan) into an implementation and testing plan. Phase 2 provides structured snapshots and Phase 3 renders them for people; Phase 4 will expose the same snapshot to scripts and add a silent collection check.

**Status:** Implemented and tested. The acceptance checklist below records the completed Phase 4 behavior.

## Goal

Implement:

```text
speakup --json
speakup --quiet
```

Both modes collect one `SystemSnapshot` using the existing collector. JSON serializes the snapshot for automation; quiet mode discards successful snapshot data and reports success through its process exit status. Neither mode changes the default human-readable output.

**Quiet means “collection succeeded,” not “the machine is healthy.”** No health thresholds or severity judgments are introduced in this phase.

## Before coding: learn

Study these resources before implementing:

1. [Python `json` documentation](https://docs.python.org/3/library/json.html) — JSON encoding and decoding, and handling values that JSON cannot represent.
2. [Python `datetime` documentation](https://docs.python.org/3/library/datetime.html) — stable ISO formatting for timezone-aware capture times.
3. [Python `sys` documentation](https://docs.python.org/3/library/sys.html) — stdout, stderr, and process exit statuses.
4. [Python `unittest.mock`](https://docs.python.org/3/library/unittest.mock.html) — fixed snapshots and injected collection failures in CLI tests.
5. [JSON specification, RFC 8259](https://www.rfc-editor.org/rfc/rfc8259) — the interchange format consumed by standard tools.

## Proposed JSON contract

Emit exactly one JSON object followed by a newline on stdout. Use ASCII escapes for non-ASCII characters so the JSON remains valid UTF-8 even when a Windows terminal uses a legacy output encoding. Use standard JSON types, with no Rich styling or other text before or after the object. Make the schema explicit and version it from its first release.

Example shape:

```json
{
  "schema_version": 1,
  "captured_at": "2026-01-02T03:04:05+00:00",
  "uptime_seconds": 183845,
  "system": {
    "operating_system": "Windows",
    "release": "11",
    "architecture": "AMD64"
  },
  "cpu": {
    "logical_cores": 8,
    "physical_cores": 4,
    "utilization_percent": 37.5
  },
  "memory": {
    "total_bytes": 17179869184,
    "available_bytes": 10737418240,
    "used_bytes": 6442450944,
    "utilization_percent": 37.5
  },
  "disks": [
    {
      "device": "C:",
      "mount_point": "C:\\",
      "filesystem": "NTFS",
      "total_bytes": 107374182400,
      "used_bytes": 42949672960,
      "free_bytes": 64424509440,
      "utilization_percent": 40.0
    }
  ],
  "battery": {
    "percent": 73.0,
    "power_plugged": true
  },
  "warnings": []
}
```

Contract rules:

- `schema_version` is an integer beginning at `1`. A breaking change to names, types, units, or meanings requires a deliberate schema-version change.
- `captured_at` is an ISO 8601 timestamp with its UTC offset retained; do not serialize a naive local timestamp.
- Byte quantities and uptime remain integers in bytes and seconds. Percentages remain JSON numbers, not preformatted strings with `%`.
- Optional fields whose values are unavailable serialize as JSON `null`; do not replace unknown values with zero or omit them inconsistently.
- `battery` is either `null` or an object with nullable `percent` and `power_plugged`.
- `disks` and `warnings` are always arrays, including when empty.
- Preserve stable field names and meanings. Additive fields may be considered compatible, but removing or reinterpreting fields requires a documented schema-version decision.
- Do not include usernames, hostnames, process lists, network details, serial numbers, or other identity data.
- Serialize with non-finite float output disabled (`NaN` and `Infinity` are not valid JSON values). If such a value is ever encountered, fail explicitly rather than emitting invalid JSON.

## Quiet mode contract

`speakup --quiet` performs the same required collection as the default command, then discards the snapshot:

- Successful collection returns **0**, writes nothing to stdout or stderr, and does not apply a health threshold.
- A `SnapshotCollectionError` returns **1**, writes a concise error to stderr, and writes nothing to stdout.
- Optional metric warnings (for example, unavailable battery or a disk mount) do not fail quiet mode by themselves; collection completed and returned a snapshot.
- Invalid arguments continue to be handled by `argparse` with exit status **2** and a usage message on stderr.

This gives scripts a clear “could the tool collect its required snapshot?” check without pretending to know whether resource usage is acceptable for a particular team.

## JSON mode and errors

- `speakup --json` collects one snapshot and serializes it to stdout according to the schema above.
- Collection warnings are included in the `warnings` array; they do not make an otherwise valid snapshot fail.
- If required collection fails, return **1**, write a concise error to stderr, and do not write a partial JSON object to stdout.
- JSON serialization failures must not be silently replaced with an empty object or a success-shaped fallback.
- If encoding fails because snapshot data cannot be represented as valid JSON, return **1**, report the serialization failure on stderr, and leave stdout empty.
- Keep `speakup --json --quiet` invalid: JSON requires stdout output, while quiet mode promises no output.
- Keep JSON and quiet options limited to the default snapshot. `doctor --json` and `watch --json` remain invalid/out of scope here.

## Suggested implementation design

- Add a serialization module/function that maps `SystemSnapshot` into the explicitly versioned JSON-compatible dictionary. Do not serialize dataclasses generically if that would leak future fields into the public schema.
- Use the standard library `json` module and deterministic key ordering for reviewable output.
- Keep collection shared: default human mode, JSON mode, and quiet mode each collect once and use the same snapshot producer.
- Keep mode-specific output at the CLI boundary. JSON uses stdout; errors use stderr; quiet success prints nothing.
- Keep renderer behavior from Phase 3 unchanged.

Suggested files:

```text
src/speakup/
  serialization.py  # Explicit snapshot-to-JSON contract
  main.py           # Mode routing and stdout/stderr/exit handling
tests/
  test_serialization.py
  test_cli.py       # JSON/quiet integration and error behavior
```

Do not add a JSON library dependency; Python includes what is needed.

## Testing strategy

All tests should use a fixed `SystemSnapshot` and mocked collector calls. They should not depend on the host machine’s disk list, battery, CPU load, or clock.

### Unit tests: snapshot serialization

- Parse the serialized text with `json.loads` and compare the resulting object to the agreed schema.
- Assert `schema_version` is present and the schema’s field names and nesting are stable.
- Verify `captured_at` includes an offset and retains UTC semantics.
- Verify byte counts, uptime, and percentages remain numeric with documented units.
- Verify unavailable OS metadata, physical core count, battery values, and absent battery serialize as `null`.
- Verify empty disks/warnings serialize as `[]`.
- Verify strings containing quotes, backslashes, Unicode, or markup characters are escaped/represented as valid JSON and round-trip correctly.
- Verify no non-finite numbers are emitted.

### CLI integration tests: JSON mode

- Patch `collect_snapshot()` with a known snapshot, invoke `main(["--json"])`, and parse all stdout as exactly one JSON document.
- Assert the collector is called once and no Rich table, ANSI escape, banner, or human report contaminates stdout.
- Assert successful serialization returns `0` and writes no error to stderr.
- Inject `SnapshotCollectionError`; assert status `1`, concise stderr, and empty stdout (no partial JSON).
- Assert unexpected programming errors are not silently converted to valid JSON.

### CLI integration tests: quiet mode

- Patch the collector with a valid snapshot; assert status `0` and empty stdout/stderr.
- Inject `SnapshotCollectionError`; assert status `1`, empty stdout, and an error on stderr.
- Supply a snapshot with optional metric warnings; verify quiet mode still returns `0` without output.
- Assert the collector is called once.

### Argument compatibility tests

- `--json --quiet` is rejected with status `2`.
- `doctor --json`, `watch --json`, and snapshot options after those subcommands remain rejected.
- Existing default human output, `--help`, `--version`, and subcommand placeholder behavior remain unchanged.

## Suggested implementation sequence

1. Read the JSON, datetime, and process-stream references above.
2. Review and agree on the schema example and the meaning of quiet success before writing the serializer.
3. Write schema serialization tests for a representative snapshot and for optional/null values.
4. Implement an explicit snapshot-to-dictionary mapper and JSON encoder.
5. Route `--json` to collect once and emit only the JSON document.
6. Route `--quiet` to collect once and emit nothing on success.
7. Reuse the existing collection error boundary; keep partial output out of stdout on failure.
8. Add CLI compatibility/error tests and rerun the full test suite.
9. Manually pipe JSON to a standard parser and confirm quiet mode produces no output.

## Acceptance checklist

- [x] The JSON schema is versioned, documented, and mapped explicitly from `SystemSnapshot`.
- [x] `speakup --json` emits exactly one valid JSON document and newline on stdout.
- [x] JSON includes the defined snapshot fields, numeric units, null optional values, and warnings.
- [x] JSON output has no Rich styling, ANSI escape codes, or human-readable banner.
- [x] JSON collection failures return 1, explain the error on stderr, and leave stdout empty.
- [x] `speakup --quiet` collects once, returns 0 on successful collection, and emits no output.
- [x] Quiet collection failures return 1 and report to stderr without stdout output.
- [x] Quiet mode does not infer health or apply thresholds.
- [x] `--json --quiet` and mode flags on `doctor`/`watch` remain invalid.
- [x] Tests parse output using `json.loads`, use mocks/fixed snapshots, and cover error and optional-value cases.
- [x] Existing default output and Phase 1/2/3 tests still pass.

## Deliverable and learning outcome

**Deliverable:** A documented, versioned JSON snapshot interface and a genuinely silent collection check suitable for shell scripts and CI.

**You will learn:** JSON serialization, public schema design, backwards compatibility, stdout/stderr contracts, process exit statuses, and testing command-line integration without host-dependent data.

## Out of scope for Phase 4

- Health thresholds, warnings based on high utilization, or an overall health score.
- `doctor` JSON output or diagnostic report schema (Phase 5).
- JSON streaming or watch output (Phase 6).
- Configuration files or user-adjustable thresholds.
