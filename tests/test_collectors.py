import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import psutil

from speakup.collectors import (
    CPU_SAMPLE_INTERVAL_SECONDS,
    SnapshotCollectionError,
    collect_battery,
    collect_cpu_info,
    collect_disks,
    collect_memory_info,
    collect_snapshot,
    collect_system_info,
    collect_uptime_seconds,
)
from speakup.models import (
    BatteryInfo,
    CpuInfo,
    DiskInfo,
    MemoryInfo,
    SystemInfo,
    SystemSnapshot,
)


class ModelTests(unittest.TestCase):
    def test_models_accept_raw_values_and_optional_metrics(self):
        captured_at = datetime(2026, 1, 1, tzinfo=UTC)
        snapshot = SystemSnapshot(
            captured_at=captured_at,
            uptime_seconds=60,
            system=SystemInfo("Windows", "11", "AMD64"),
            cpu=CpuInfo(8, None, 25.5),
            memory=MemoryInfo(1000, 600, 400, 40.0),
            disks=(
                DiskInfo("C:", "C:\\", "NTFS", 1000, 400, 600, 40.0),
            ),
            battery=None,
            warnings=(),
        )

        self.assertEqual(snapshot.memory.total_bytes, 1000)
        self.assertIsNone(snapshot.cpu.physical_cores)
        self.assertIsNone(snapshot.battery)
        self.assertIsInstance(snapshot.memory.total_bytes, int)

    def test_models_reject_invalid_percentages_and_naive_capture_time(self):
        with self.assertRaises(ValueError):
            CpuInfo(8, 4, 101.0)

        with self.assertRaises(ValueError):
            BatteryInfo(-1.0, False)

        with self.assertRaises(ValueError):
            SystemSnapshot(
                captured_at=datetime(2026, 1, 1),
                uptime_seconds=1,
                system=SystemInfo("Linux", "test", "x86_64"),
                cpu=CpuInfo(1, 1, 0.0),
                memory=MemoryInfo(1, 1, 0, 0.0),
                disks=(),
                battery=None,
                warnings=(),
            )


class CollectorTests(unittest.TestCase):
    def test_collect_system_info_excludes_host_identity(self):
        with (
            patch("speakup.collectors.platform.system", return_value="Linux"),
            patch("speakup.collectors.platform.release", return_value="test-release"),
            patch("speakup.collectors.platform.machine", return_value="x86_64"),
        ):
            result = collect_system_info()

        self.assertEqual(
            result,
            SystemInfo("Linux", "test-release", "x86_64"),
        )
        self.assertFalse(hasattr(result, "hostname"))
        self.assertFalse(hasattr(result, "username"))

    def test_system_info_uses_none_for_unavailable_platform_strings(self):
        with (
            patch("speakup.collectors.platform.system", return_value=""),
            patch("speakup.collectors.platform.release", return_value=""),
            patch("speakup.collectors.platform.machine", return_value=""),
        ):
            result = collect_system_info()

        self.assertEqual(result, SystemInfo(None, None, None))

    def test_cpu_collector_uses_short_blocking_sample(self):
        with (
            patch("speakup.collectors.psutil.cpu_count", side_effect=[8, 4]),
            patch(
                "speakup.collectors.psutil.cpu_percent",
                return_value=37.5,
            ) as cpu_percent,
        ):
            result = collect_cpu_info()

        self.assertEqual(result, CpuInfo(8, 4, 37.5))
        cpu_percent.assert_called_once_with(interval=CPU_SAMPLE_INTERVAL_SECONDS)

    def test_cpu_collector_allows_unknown_physical_core_count(self):
        with (
            patch("speakup.collectors.psutil.cpu_count", side_effect=[8, None]),
            patch("speakup.collectors.psutil.cpu_percent", return_value=0.0),
        ):
            result = collect_cpu_info()

        self.assertIsNone(result.physical_cores)

    def test_cpu_required_failure_is_surfaced(self):
        with patch(
            "speakup.collectors.psutil.cpu_count",
            side_effect=psutil.AccessDenied("private detail"),
        ):
            with self.assertRaisesRegex(
                SnapshotCollectionError,
                "Unable to collect CPU information",
            ) as raised:
                collect_cpu_info()

        self.assertNotIn("private detail", str(raised.exception))

    def test_cpu_missing_logical_core_count_is_surfaced(self):
        with (
            patch("speakup.collectors.psutil.cpu_count", return_value=None),
            patch("speakup.collectors.psutil.cpu_percent", return_value=0.0),
        ):
            with self.assertRaisesRegex(
                SnapshotCollectionError,
                "logical CPU core count",
            ):
                collect_cpu_info()

    def test_memory_collector_maps_raw_values(self):
        memory = SimpleNamespace(
            total=16_000,
            available=10_000,
            used=6_000,
            percent=37.5,
        )
        with patch("speakup.collectors.psutil.virtual_memory", return_value=memory):
            result = collect_memory_info()

        self.assertEqual(result, MemoryInfo(16_000, 10_000, 6_000, 37.5))

    def test_memory_required_failure_is_surfaced(self):
        with patch(
            "speakup.collectors.psutil.virtual_memory",
            side_effect=psutil.Error("private detail"),
        ):
            with self.assertRaisesRegex(
                SnapshotCollectionError,
                "Unable to collect memory information",
            ) as raised:
                collect_memory_info()

        self.assertNotIn("private detail", str(raised.exception))

    def test_disks_collect_multiple_mounts_and_skip_duplicate_mounts(self):
        partitions = [
            SimpleNamespace(device="disk-a", mountpoint="/a", fstype="testfs"),
            SimpleNamespace(device="disk-b", mountpoint="/b", fstype="testfs"),
            SimpleNamespace(device="disk-a-duplicate", mountpoint="/a", fstype="testfs"),
        ]
        usage = SimpleNamespace(total=1000, used=400, free=600, percent=40.0)

        with (
            patch("speakup.collectors.psutil.disk_partitions", return_value=partitions),
            patch("speakup.collectors.psutil.disk_usage", return_value=usage) as disk_usage,
        ):
            disks, warnings = collect_disks()

        self.assertEqual(len(disks), 2)
        self.assertEqual([disk.mount_point for disk in disks], ["/a", "/b"])
        self.assertEqual(disks[0].total_bytes, 1000)
        self.assertEqual(warnings, ())
        self.assertEqual(disk_usage.call_count, 2)

    def test_disk_metadata_uses_none_when_unavailable(self):
        partition = SimpleNamespace(device="", mountpoint="/", fstype="")
        usage = SimpleNamespace(total=1000, used=400, free=600, percent=40.0)

        with (
            patch("speakup.collectors.psutil.disk_partitions", return_value=[partition]),
            patch("speakup.collectors.psutil.disk_usage", return_value=usage),
        ):
            disks, warnings = collect_disks()

        self.assertIsNone(disks[0].device)
        self.assertIsNone(disks[0].filesystem)
        self.assertEqual(warnings, ())

    def test_inaccessible_disk_warns_without_losing_other_mounts(self):
        partitions = [
            SimpleNamespace(device="disk-a", mountpoint="/good", fstype="testfs"),
            SimpleNamespace(device="disk-b", mountpoint="/private", fstype="testfs"),
        ]
        usage = SimpleNamespace(total=1000, used=400, free=600, percent=40.0)

        with (
            patch("speakup.collectors.psutil.disk_partitions", return_value=partitions),
            patch(
                "speakup.collectors.psutil.disk_usage",
                side_effect=[usage, PermissionError("secret path")],
            ),
        ):
            disks, warnings = collect_disks()

        self.assertEqual([disk.mount_point for disk in disks], ["/good"])
        self.assertEqual(
            warnings,
            ("Unable to collect storage information for mount point '/private'.",),
        )
        self.assertNotIn("secret path", warnings[0])

    def test_disk_enumeration_failure_returns_warning(self):
        with patch(
            "speakup.collectors.psutil.disk_partitions",
            side_effect=psutil.Error("private detail"),
        ):
            disks, warnings = collect_disks()

        self.assertEqual(disks, ())
        self.assertEqual(warnings, ("Unable to enumerate storage devices.",))

    def test_battery_is_optional_when_not_present(self):
        with patch("speakup.collectors.psutil.sensors_battery", return_value=None):
            battery, warning = collect_battery()

        self.assertIsNone(battery)
        self.assertIsNone(warning)

    def test_battery_maps_charge_and_power_state(self):
        battery_value = SimpleNamespace(percent=73.0, power_plugged=True)
        with patch(
            "speakup.collectors.psutil.sensors_battery",
            return_value=battery_value,
        ):
            battery, warning = collect_battery()

        self.assertEqual(battery, BatteryInfo(73.0, True))
        self.assertIsNone(warning)

    def test_battery_unavailable_error_becomes_warning(self):
        with patch(
            "speakup.collectors.psutil.sensors_battery",
            side_effect=NotImplementedError,
        ):
            battery, warning = collect_battery()

        self.assertIsNone(battery)
        self.assertEqual(warning, "Battery information is unavailable on this system.")

    def test_uptime_uses_utc_capture_time(self):
        captured_at = datetime(2026, 1, 1, 0, 1, 1, tzinfo=UTC)
        boot_timestamp = datetime(2026, 1, 1, tzinfo=UTC).timestamp()

        with patch("speakup.collectors.psutil.boot_time", return_value=boot_timestamp):
            uptime = collect_uptime_seconds(captured_at)

        self.assertEqual(uptime, 61)

    def test_uptime_failure_is_surfaced(self):
        captured_at = datetime(2026, 1, 1, tzinfo=UTC)
        with patch(
            "speakup.collectors.psutil.boot_time",
            side_effect=psutil.Error("private detail"),
        ):
            with self.assertRaisesRegex(
                SnapshotCollectionError,
                "Unable to collect system uptime",
            ):
                collect_uptime_seconds(captured_at)

    def test_snapshot_assembles_collected_values_and_warnings(self):
        system = SystemInfo("Linux", "test", "x86_64")
        cpu = CpuInfo(8, 4, 25.0)
        memory = MemoryInfo(1000, 600, 400, 40.0)
        disks = (DiskInfo("disk", "/", "testfs", 1000, 400, 600, 40.0),)
        capture_time = datetime(2026, 1, 1, tzinfo=UTC)

        with (
            patch("speakup.collectors.datetime") as datetime_mock,
            patch("speakup.collectors.collect_system_info", return_value=system),
            patch("speakup.collectors.collect_cpu_info", return_value=cpu),
            patch("speakup.collectors.collect_memory_info", return_value=memory),
            patch(
                "speakup.collectors.collect_disks",
                return_value=(disks, ("disk warning",)),
            ),
            patch(
                "speakup.collectors.collect_battery",
                return_value=(None, "battery warning"),
            ),
            patch(
                "speakup.collectors.collect_uptime_seconds",
                return_value=100,
            ) as collect_uptime,
        ):
            datetime_mock.now.return_value = capture_time
            snapshot = collect_snapshot()

        collect_uptime.assert_called_once_with(capture_time)
        self.assertEqual(snapshot.captured_at, capture_time)
        self.assertEqual(snapshot.system, system)
        self.assertEqual(snapshot.cpu, cpu)
        self.assertEqual(snapshot.memory, memory)
        self.assertEqual(snapshot.disks, disks)
        self.assertIsNone(snapshot.battery)
        self.assertEqual(snapshot.warnings, ("disk warning", "battery warning"))


if __name__ == "__main__":
    unittest.main()
