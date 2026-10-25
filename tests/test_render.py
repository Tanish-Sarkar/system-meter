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
from speakup.render import render_snapshot


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

    def test_default_renderer_respects_no_color_environment(self):
        output = StringIO()
        with (
            patch.dict(os.environ, {"NO_COLOR": "1"}),
            redirect_stdout(output),
        ):
            render_snapshot(make_snapshot())

        self.assertIsNone(re.search(r"\x1b\[[0-?]*[ -/]*[@-~]", output.getvalue()))
