import os
import re
import unittest
from contextlib import redirect_stdout
from datetime import UTC, datetime
from io import StringIO
from unittest.mock import patch

from rich.console import Console

from speakup.models import (
    BatteryInfo,
    CpuInfo,
    DiskInfo,
    MemoryInfo,
    SystemInfo,
    SystemSnapshot,
)
from speakup.render import render_doctor_report, render_snapshot


def make_snapshot(
    *,
    system: SystemInfo | None = None,
    cpu: CpuInfo | None = None,
    disks: tuple[DiskInfo, ...] | None = None,
    battery: BatteryInfo | None = None,
    warnings: tuple[str, ...] = (),
) -> SystemSnapshot:
    return SystemSnapshot(
        captured_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        uptime_seconds=183_845,
        system=system or SystemInfo("Windows", "11", "AMD64"),
        cpu=cpu or CpuInfo(8, 4, 37.5),
        memory=MemoryInfo(16 * 1024**3, 10 * 1024**3, 6 * 1024**3, 37.5),
        disks=disks
        if disks is not None
        else (
            DiskInfo(
                "C:",
                "C:\\",
                "NTFS",
                100 * 1024**3,
                40 * 1024**3,
                60 * 1024**3,
                40.0,
            ),
        ),
        battery=battery,
        warnings=warnings,
    )


def render_to_string(snapshot: SystemSnapshot, *, width: int = 100) -> str:
    output = StringIO()
    console = Console(
        file=output,
        width=width,
        no_color=True,
        markup=False,
        highlight=False,
        soft_wrap=True,
    )
    render_snapshot(snapshot, console)
    return output.getvalue()


def render_doctor_to_string(
    snapshot: SystemSnapshot,
    *,
    width: int = 100,
) -> str:
    output = StringIO()
    console = Console(
        file=output,
        width=width,
        no_color=True,
        markup=False,
        highlight=False,
        soft_wrap=True,
    )
    render_doctor_report(snapshot, console)
    return output.getvalue()


class RenderTests(unittest.TestCase):
    def test_report_contains_snapshot_sections_and_formatted_metrics(self):
        output = render_to_string(
            make_snapshot(
                battery=BatteryInfo(73.0, True),
                warnings=("A storage mount could not be checked.",),
            )
        )

        for text in (
            "System Meter",
            "System",
            "Windows 11",
            "Architecture",
            "2d 3h 4m",
            "CPU",
            "37.5%",
            "Logical cores",
            "Memory",
            "6.0 GiB / 16.0 GiB",
            "Storage",
            "C:\\",
            "40.0 GiB / 100.0 GiB",
            "Battery",
            "73.0%",
            "plugged in",
            "Notes",
            "A storage mount could not be checked.",
        ):
            with self.subTest(text=text):
                self.assertIn(text, output)

    def test_optional_data_is_not_fabricated(self):
        snapshot = make_snapshot(
            system=SystemInfo(None, None, None),
            cpu=CpuInfo(4, None, 0.0),
            disks=(),
            battery=None,
        )
        output = render_to_string(snapshot)

        self.assertIn("not available", output)
        self.assertIn("No storage information available.", output)
        self.assertNotIn("Battery", output)
        self.assertNotIn("0.0% charge", output)

    def test_optional_disk_metadata_can_be_missing(self):
        disk = DiskInfo(
            None,
            "/long/mount/path",
            None,
            1024,
            512,
            512,
            50.0,
        )
        output = render_to_string(make_snapshot(disks=(disk,)))

        self.assertIn("/long/mount/path", output)

    def test_mount_points_remain_present_in_narrow_terminal(self):
        disks = (
            DiskInfo(
                "disk-a",
                "/mount/alpha/with/a/long/name",
                "fs",
                100,
                25,
                75,
                25.0,
            ),
            DiskInfo(
                "disk-b",
                "/mount/beta/with/a/long/name",
                "fs",
                100,
                75,
                25,
                75.0,
            ),
        )
        output = render_to_string(make_snapshot(disks=disks), width=32)

        self.assertIn("/mount/alpha/with/a/long/name", output)
        self.assertIn("/mount/beta/with/a/long/name", output)

    def test_platform_text_is_rendered_literally_not_as_rich_markup(self):
        snapshot = make_snapshot(
            system=SystemInfo("[bold]literal[/bold]", "release", "arch"),
        )
        output = render_to_string(snapshot)

        self.assertIn("[bold]literal[/bold]", output)

    def test_color_disabled_render_has_no_ansi_escape_sequences(self):
        output = render_to_string(make_snapshot())

        self.assertIsNone(re.search(r"\x1b\[[0-?]*[ -/]*[@-~]", output))

    def test_report_uses_framed_sections(self):
        output = render_to_string(make_snapshot())

        self.assertIn("╔", output)
        self.assertIn("┌", output)
        self.assertIn("System", output)
        self.assertIn("Storage", output)

    def test_report_uses_color_when_terminal_supports_it(self):
        output = StringIO()
        console = Console(
            file=output,
            width=100,
            force_terminal=True,
            color_system="standard",
            markup=False,
            highlight=False,
        )

        render_snapshot(make_snapshot(), console)

        self.assertRegex(output.getvalue(), r"\x1b\[[0-9;]*m")

    def test_default_renderer_respects_no_color_environment(self):
        output = StringIO()
        with (
            patch.dict(os.environ, {"NO_COLOR": "1"}),
            redirect_stdout(output),
        ):
            render_snapshot(make_snapshot())

        self.assertIsNone(re.search(r"\x1b\[[0-?]*[ -/]*[@-~]", output.getvalue()))

    def test_doctor_report_contains_metrics_and_availability_notice(self):
        output = render_doctor_to_string(
            make_snapshot(
                battery=BatteryInfo(73.0, False),
                warnings=("Unable to collect storage information for mount point '/mnt/data'.",),
            )
        )

        for text in (
            "System Meter Doctor",
            "Captured:",
            "Metric availability is not a health assessment.",
            "Windows 11",
            "CPU usage",
            "Memory used",
            "Storage",
            "Battery",
            "73.0%",
            "on battery",
            "Availability and limitations",
            "Unable to collect storage information",
        ):
            with self.subTest(text=text):
                self.assertIn(text, output)

    def test_doctor_report_handles_missing_optional_values(self):
        snapshot = make_snapshot(
            system=SystemInfo(None, None, None),
            cpu=CpuInfo(4, None, 0.0),
            disks=(),
            battery=None,
            warnings=(),
        )
        output = render_doctor_to_string(snapshot)

        self.assertIn("not available", output)
        self.assertIn("No storage information available.", output)
        self.assertIn("No collection limitations were reported.", output)
        self.assertNotIn("Battery", output)
        self.assertIn("not a health assessment", output)

    def test_doctor_report_renders_external_text_literally(self):
        warning = "[bold]warning[/bold] C:\\private\\profile"
        snapshot = make_snapshot(warnings=(warning,))

        output = render_doctor_to_string(snapshot)

        self.assertIn(warning, output)

    def test_doctor_report_is_plain_without_color(self):
        output = render_doctor_to_string(make_snapshot())

        self.assertIsNone(re.search(r"\x1b\[[0-?]*[ -/]*[@-~]", output))
