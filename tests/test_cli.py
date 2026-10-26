import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
import json
from io import StringIO
from unittest.mock import patch

from speakup.collectors import SnapshotCollectionError
from speakup.main import build_parser, main
from speakup.models import CpuInfo, MemoryInfo, SystemInfo, SystemSnapshot
from speakup.serialization import JSON_SCHEMA_VERSION, SnapshotSerializationError


class MainTests(unittest.TestCase):
    def run_cli(self, argv):
        stdout = StringIO()
        stderr = StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(argv)

        return status, stdout.getvalue(), stderr.getvalue()

    def test_help_lists_commands_and_snapshot_options(self):
        output = StringIO()

        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("[doctor | watch]", output.getvalue())
        self.assertIn("--json", output.getvalue())
        self.assertIn("--quiet", output.getvalue())
        self.assertIn("doctor", output.getvalue())
        self.assertIn("watch", output.getvalue())

    def test_version_prints_installed_version(self):
        output = StringIO()

        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])

        self.assertEqual(raised.exception.code, 0)
        self.assertRegex(output.getvalue(), r"^speakup \d+\.\d+\.\d+\n$")

    def test_default_command_renders_one_collected_snapshot(self):
        snapshot = SystemSnapshot(
            captured_at=datetime(2026, 1, 1, tzinfo=UTC),
            uptime_seconds=60,
            system=SystemInfo("Linux", "test", "x86_64"),
            cpu=CpuInfo(8, 4, 25.0),
            memory=MemoryInfo(1000, 600, 400, 40.0),
            disks=(),
            battery=None,
            warnings=(),
        )

        with patch("speakup.main.collect_snapshot", return_value=snapshot) as collect:
            status, stdout, stderr = self.run_cli([])

        self.assertEqual(status, 0)
        self.assertIn("System Meter", stdout)
        self.assertIn("Linux test", stdout)
        self.assertIn("40.0%", stdout)
        self.assertEqual(stderr, "")
        collect.assert_called_once_with()

    def test_collection_failure_is_reported_on_stderr(self):
        with patch(
            "speakup.main.collect_snapshot",
            side_effect=SnapshotCollectionError("Unable to collect CPU information."),
        ):
            status, stdout, stderr = self.run_cli([])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(
            stderr,
            "Unable to collect system snapshot: Unable to collect CPU information.\n",
        )

    def test_unexpected_collection_errors_are_not_silenced(self):
        with patch(
            "speakup.main.collect_snapshot",
            side_effect=RuntimeError("unexpected bug"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpected bug"):
                main([])

    def test_json_mode_serializes_one_snapshot_without_human_output(self):
        snapshot = SystemSnapshot(
            captured_at=datetime(2026, 1, 1, tzinfo=UTC),
            uptime_seconds=60,
            system=SystemInfo("Linux", "test", "x86_64"),
            cpu=CpuInfo(8, 4, 25.0),
            memory=MemoryInfo(1000, 600, 400, 40.0),
            disks=(),
            battery=None,
            warnings=(),
        )

        with patch("speakup.main.collect_snapshot", return_value=snapshot) as collect:
            status, stdout, stderr = self.run_cli(["--json"])

        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout)["schema_version"], JSON_SCHEMA_VERSION)
        self.assertTrue(stdout.endswith("\n"))
        self.assertNotIn("System Meter", stdout)
        self.assertNotIn("\x1b[", stdout)
        self.assertEqual(stderr, "")
        collect.assert_called_once_with()

    def test_quiet_mode_collects_once_and_emits_nothing(self):
        snapshot = SystemSnapshot(
            captured_at=datetime(2026, 1, 1, tzinfo=UTC),
            uptime_seconds=60,
            system=SystemInfo("Linux", "test", "x86_64"),
            cpu=CpuInfo(8, 4, 25.0),
            memory=MemoryInfo(1000, 600, 400, 40.0),
            disks=(),
            battery=None,
            warnings=("optional metric unavailable",),
        )

        with patch("speakup.main.collect_snapshot", return_value=snapshot) as collect:
            status, stdout, stderr = self.run_cli(["--quiet"])

        self.assertEqual(status, 0)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        collect.assert_called_once_with()

    def test_json_collection_failure_has_no_partial_output(self):
        with patch(
            "speakup.main.collect_snapshot",
            side_effect=SnapshotCollectionError("CPU unavailable"),
        ):
            status, stdout, stderr = self.run_cli(["--json"])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Unable to collect system snapshot", stderr)

    def test_quiet_collection_failure_is_silent_on_stdout(self):
        with patch(
            "speakup.main.collect_snapshot",
            side_effect=SnapshotCollectionError("CPU unavailable"),
        ):
            status, stdout, stderr = self.run_cli(["--quiet"])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Unable to collect system snapshot", stderr)

    def test_json_serialization_failure_has_no_partial_output(self):
        with (
            patch("speakup.main.collect_snapshot"),
            patch(
                "speakup.main.serialize_snapshot",
                side_effect=SnapshotSerializationError("invalid snapshot"),
            ),
        ):
            status, stdout, stderr = self.run_cli(["--json"])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertIn("Unable to serialize system snapshot", stderr)

    def test_unexpected_json_serialization_errors_are_not_silenced(self):
        with (
            patch("speakup.main.collect_snapshot"),
            patch(
                "speakup.main.serialize_snapshot",
                side_effect=RuntimeError("unexpected bug"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpected bug"):
                main(["--json"])

    def test_doctor_renders_one_snapshot_to_stdout(self):
        snapshot = SystemSnapshot(
            captured_at=datetime(2026, 1, 1, tzinfo=UTC),
            uptime_seconds=60,
            system=SystemInfo("Linux", "test", "x86_64"),
            cpu=CpuInfo(8, 4, 25.0),
            memory=MemoryInfo(1000, 600, 400, 40.0),
            disks=(),
            battery=None,
            warnings=("optional metric unavailable",),
        )

        with patch("speakup.main.collect_snapshot", return_value=snapshot) as collect:
            status, stdout, stderr = self.run_cli(["doctor"])

        self.assertEqual(status, 0)
        self.assertIn("System Meter Doctor", stdout)
        self.assertIn("optional metric unavailable", stdout)
        self.assertEqual(stderr, "")
        collect.assert_called_once_with()

    def test_doctor_collection_failure_reports_error_without_partial_report(self):
        with patch(
            "speakup.main.collect_snapshot",
            side_effect=SnapshotCollectionError("Unable to collect CPU information."),
        ):
            status, stdout, stderr = self.run_cli(["doctor"])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(
            stderr,
            "Unable to collect doctor report: Unable to collect CPU information.\n",
        )

    def test_unexpected_doctor_errors_are_not_silenced(self):
        with patch(
            "speakup.main.collect_snapshot",
            side_effect=RuntimeError("unexpected bug"),
        ):
            with self.assertRaisesRegex(RuntimeError, "unexpected bug"):
                main(["doctor"])

    def test_watch_parser_defaults_to_two_seconds_and_accepts_fractional_interval(self):
        parser = build_parser()

        default_args = parser.parse_args(["watch"])
        fractional_args = parser.parse_args(["watch", "--interval", "1.5"])

        self.assertEqual(default_args.interval, 2.0)
        self.assertEqual(fractional_args.interval, 1.5)

    def test_watch_help_documents_interval(self):
        stderr = StringIO()
        output = StringIO()
        with (
            redirect_stdout(output),
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            main(["watch", "--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--interval SECONDS", output.getvalue())
        self.assertIn("default: 2", output.getvalue())

    def test_watch_parser_rejects_invalid_intervals(self):
        for interval in ("abc", "0", "0.5", "-1", "nan", "inf", "-inf"):
            with self.subTest(interval=interval):
                stderr = StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                    build_parser().parse_args(["watch", f"--interval={interval}"])

                self.assertEqual(raised.exception.code, 2)
                self.assertIn("finite number of at least 1 second", stderr.getvalue())

    def test_watch_rejects_redirected_human_output_with_json_guidance(self):
        stderr = StringIO()
        with (
            redirect_stderr(stderr),
            redirect_stdout(StringIO()),
            self.assertRaises(SystemExit) as raised,
        ):
            main(["watch"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("use --json for piped output", stderr.getvalue())

    def test_quiet_watch_is_rejected(self):
        stderr = StringIO()
        with (
            redirect_stderr(stderr),
            self.assertRaises(SystemExit) as raised,
        ):
            main(["--quiet", "watch"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("--quiet cannot be used with watch", stderr.getvalue())

    def test_watch_returns_interrupt_status_without_traceback(self):
        with patch(
            "speakup.main.run_watch",
            side_effect=KeyboardInterrupt,
        ) as run_watch:
            status, stdout, stderr = self.run_cli(["--json", "watch"])

        self.assertEqual(status, 130)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        run_watch.assert_called_once_with(2.0, json_output=True)

    def test_watch_collection_failure_is_reported(self):
        with patch(
            "speakup.main.run_watch",
            side_effect=SnapshotCollectionError("CPU unavailable"),
        ):
            status, stdout, stderr = self.run_cli(["--json", "watch"])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "Unable to collect watch snapshot: CPU unavailable\n")

    def test_watch_serialization_failure_is_reported(self):
        with patch(
            "speakup.main.run_watch",
            side_effect=SnapshotSerializationError("invalid snapshot"),
        ):
            status, stdout, stderr = self.run_cli(["--json", "watch"])

        self.assertEqual(status, 1)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "Unable to serialize watch snapshot: invalid snapshot\n")

    def test_snapshot_output_modes_are_mutually_exclusive(self):
        stderr = StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            build_parser().parse_args(["--json", "--quiet"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("not allowed with argument", stderr.getvalue())

    def test_snapshot_options_are_rejected_after_subcommands(self):
        for argv in (["doctor", "--json"], ["watch", "--quiet"]):
            with self.subTest(argv=argv):
                stderr = StringIO()
                with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
                    build_parser().parse_args(argv)

                self.assertEqual(raised.exception.code, 2)
                self.assertIn("unrecognized arguments", stderr.getvalue())

    def test_unknown_command_returns_argparse_error(self):
        stderr = StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            build_parser().parse_args(["unknown"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("invalid choice", stderr.getvalue())

    def test_unknown_option_returns_argparse_error(self):
        stderr = StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            build_parser().parse_args(["--unknown"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("unrecognized arguments", stderr.getvalue())
