import json
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from io import StringIO
from unittest.mock import call, patch

from rich.console import Console

from speakup.models import CpuInfo, MemoryInfo, SystemInfo, SystemSnapshot
from speakup.serialization import SnapshotSerializationError
from speakup.collectors import SnapshotCollectionError
from speakup.watch import run_watch


def make_snapshot(
    cpu_percent: float = 25.0,
    system: SystemInfo | None = None,
) -> SystemSnapshot:
    return SystemSnapshot(
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
        uptime_seconds=60,
        system=system or SystemInfo("Linux", "test", "x86_64"),
        cpu=CpuInfo(8, 4, cpu_percent),
        memory=MemoryInfo(1000, 600, 400, 40.0),
        disks=(),
        battery=None,
        warnings=(),
    )


class FakeLive:
    def __init__(self, *, console, screen, auto_refresh):
        self.console = console
        self.screen = screen
        self.auto_refresh = auto_refresh
        self.updated = []
        self.exited = False

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        self.exited = True

    def update(self, renderable, *, refresh):
        self.updated.append((renderable, refresh))


class WatchTests(unittest.TestCase):
    def test_json_mode_emits_compact_json_lines_and_uses_monotonic_wait(self):
        first = make_snapshot()
        second = make_snapshot(75.0)
        stdout = StringIO()

        with (
            patch(
                "speakup.watch.collect_snapshot",
                side_effect=(first, second),
            ) as collect,
            patch(
                "speakup.watch.time.monotonic",
                side_effect=(0.0, 0.25, 1.0, 1.75),
            ),
            patch(
                "speakup.watch.time.sleep",
                side_effect=(None, KeyboardInterrupt),
            ) as sleep,
            redirect_stdout(stdout),
            self.assertRaises(KeyboardInterrupt),
        ):
            run_watch(1.0, json_output=True)

        lines = stdout.getvalue().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(all("\n" not in line for line in lines))
        self.assertEqual(json.loads(lines[0])["cpu"]["utilization_percent"], 25.0)
        self.assertEqual(json.loads(lines[1])["cpu"]["utilization_percent"], 75.0)
        self.assertEqual(collect.call_count, 2)
        self.assertEqual(sleep.call_args_list, [call(0.75), call(0.25)])

    def test_collection_longer_than_interval_does_not_sleep(self):
        stdout = StringIO()
        with (
            patch(
                "speakup.watch.collect_snapshot",
                side_effect=(make_snapshot(), KeyboardInterrupt),
            ) as collect,
            patch("speakup.watch.time.monotonic", side_effect=(0.0, 1.5, 1.5)),
            patch("speakup.watch.time.sleep") as sleep,
            redirect_stdout(stdout),
            self.assertRaises(KeyboardInterrupt),
        ):
            run_watch(1.0, json_output=True)

        self.assertEqual(collect.call_count, 2)
        sleep.assert_not_called()
        self.assertEqual(len(stdout.getvalue().splitlines()), 1)

    def test_serialization_error_does_not_emit_a_partial_line(self):
        invalid_snapshot = make_snapshot(system=SystemInfo(object(), "test", "x86_64"))
        stdout = StringIO()

        with (
            patch("speakup.watch.collect_snapshot", return_value=invalid_snapshot),
            redirect_stdout(stdout),
            self.assertRaises(SnapshotSerializationError),
        ):
            run_watch(1.0, json_output=True)

        self.assertEqual(stdout.getvalue(), "")

    def test_collection_error_keeps_only_prior_complete_lines(self):
        stdout = StringIO()
        with (
            patch(
                "speakup.watch.collect_snapshot",
                side_effect=(make_snapshot(), SnapshotCollectionError("CPU unavailable")),
            ),
            patch("speakup.watch.time.monotonic", side_effect=(0.0, 0.0, 0.0)),
            patch("speakup.watch.time.sleep"),
            redirect_stdout(stdout),
            self.assertRaises(SnapshotCollectionError),
        ):
            run_watch(1.0, json_output=True)

        lines = stdout.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["schema_version"], 1)

    def test_human_mode_updates_live_display_and_restores_it_on_interrupt(self):
        live_instances = []
        output = StringIO()
        console = Console(file=output, width=100, no_color=True)

        def make_live(**kwargs):
            live = FakeLive(**kwargs)
            live_instances.append(live)
            return live

        with (
            patch("speakup.watch.Live", side_effect=make_live),
            patch("speakup.watch.collect_snapshot", return_value=make_snapshot()),
            patch("speakup.watch.time.monotonic", side_effect=(0.0, 0.0)),
            patch("speakup.watch.time.sleep", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            run_watch(2.0, json_output=False, console=console)

        self.assertEqual(len(live_instances), 1)
        live = live_instances[0]
        self.assertTrue(live.exited)
        self.assertFalse(live.screen)
        self.assertFalse(live.auto_refresh)
        self.assertEqual(len(live.updated), 1)
        self.assertTrue(live.updated[0][1])
        console.print(live.updated[0][0])
        self.assertIn("Linux test", output.getvalue())
        self.assertIn("25.0%", output.getvalue())

    def test_unexpected_collection_errors_propagate(self):
        with patch(
            "speakup.watch.collect_snapshot",
            side_effect=RuntimeError("unexpected bug"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpected bug"):
                run_watch(2.0, json_output=True)


if __name__ == "__main__":
    unittest.main()
