import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from io import StringIO
from unittest.mock import patch

from speakup.collectors import SnapshotCollectionError
from speakup.main import build_parser, main
from speakup.models import CpuInfo, MemoryInfo, SystemInfo, SystemSnapshot


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

    def test_json_and_quiet_modes_remain_unimplemented(self):
        expected = {
            ("--json",): "JSON snapshot output is not implemented yet.\n",
            ("--quiet",): "Quiet snapshot check mode is not implemented yet.\n",
        }

        for argv, message in expected.items():
            with self.subTest(argv=argv):
                status, stdout, stderr = self.run_cli(list(argv))
                self.assertEqual(status, 1)
                self.assertEqual(stdout, "")
                self.assertEqual(stderr, message)

    def test_subcommands_report_not_implemented_on_stderr(self):
        expected = {
            "doctor": "The doctor command is not implemented yet.\n",
            "watch": "Watch mode is not implemented yet.\n",
        }

        for command, message in expected.items():
            with self.subTest(command=command):
                status, stdout, stderr = self.run_cli([command])
                self.assertEqual(status, 1)
                self.assertEqual(stdout, "")
                self.assertEqual(stderr, message)

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
