import json
import math
import unittest
from datetime import UTC, datetime, timedelta, timezone

from speakup.models import (
    BatteryInfo,
    CpuInfo,
    DiskInfo,
    MemoryInfo,
    SystemInfo,
    SystemSnapshot,
)
from speakup.serialization import (
    JSON_SCHEMA_VERSION,
    SnapshotSerializationError,
    serialize_snapshot,
    snapshot_to_dict,
)


def make_snapshot(
    *,
    system: SystemInfo | None = None,
    cpu: CpuInfo | None = None,
    disks: tuple[DiskInfo, ...] = (),
    battery: BatteryInfo | None = None,
    warnings: tuple[str, ...] = (),
) -> SystemSnapshot:
    return SystemSnapshot(
        captured_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        uptime_seconds=183_845,
        system=system or SystemInfo("Windows", "11", "AMD64"),
        cpu=cpu or CpuInfo(8, 4, 37.5),
        memory=MemoryInfo(
            17_179_869_184,
            10_737_418_240,
            6_442_450_944,
            37.5,
        ),
        disks=disks,
        battery=battery,
        warnings=warnings,
    )


class SerializationTests(unittest.TestCase):
    def test_serialized_snapshot_matches_versioned_schema(self):
        snapshot = make_snapshot(
            disks=(
                DiskInfo(
                    "C:",
                    "C:\\",
                    "NTFS",
                    107_374_182_400,
                    42_949_672_960,
                    64_424_509_440,
                    40.0,
                ),
            ),
            battery=BatteryInfo(73.0, True),
        )

        result = json.loads(serialize_snapshot(snapshot))

        self.assertEqual(
            result,
            {
                "schema_version": JSON_SCHEMA_VERSION,
                "captured_at": "2026-01-02T03:04:05+00:00",
                "uptime_seconds": 183845,
                "system": {
                    "operating_system": "Windows",
                    "release": "11",
                    "architecture": "AMD64",
                },
                "cpu": {
                    "logical_cores": 8,
                    "physical_cores": 4,
                    "utilization_percent": 37.5,
                },
                "memory": {
                    "total_bytes": 17_179_869_184,
                    "available_bytes": 10_737_418_240,
                    "used_bytes": 6_442_450_944,
                    "utilization_percent": 37.5,
                },
                "disks": [
                    {
                        "device": "C:",
                        "mount_point": "C:\\",
                        "filesystem": "NTFS",
                        "total_bytes": 107_374_182_400,
                        "used_bytes": 42_949_672_960,
                        "free_bytes": 64_424_509_440,
                        "utilization_percent": 40.0,
                    }
                ],
                "battery": {
                    "percent": 73.0,
                    "power_plugged": True,
                },
                "warnings": [],
            },
        )

    def test_optional_values_are_null_and_empty_sequences_are_arrays(self):
        snapshot = make_snapshot(
            system=SystemInfo(None, None, None),
            cpu=CpuInfo(4, None, 0.0),
            battery=BatteryInfo(None, None),
        )

        result = snapshot_to_dict(snapshot)

        self.assertEqual(
            result["system"],
            {
                "operating_system": None,
                "release": None,
                "architecture": None,
            },
        )
        self.assertEqual(result["cpu"]["physical_cores"], None)
        self.assertEqual(result["battery"], {"percent": None, "power_plugged": None})
        self.assertEqual(result["disks"], [])
        self.assertEqual(result["warnings"], [])

        without_battery = snapshot_to_dict(make_snapshot())
        self.assertIsNone(without_battery["battery"])

    def test_timestamp_retains_non_utc_offset(self):
        timestamp = datetime(
            2026,
            1,
            2,
            8,
            34,
            5,
            tzinfo=timezone(timedelta(hours=5, minutes=30)),
        )
        snapshot = make_snapshot()
        snapshot = SystemSnapshot(
            captured_at=timestamp,
            uptime_seconds=snapshot.uptime_seconds,
            system=snapshot.system,
            cpu=snapshot.cpu,
            memory=snapshot.memory,
            disks=snapshot.disks,
            battery=snapshot.battery,
            warnings=snapshot.warnings,
        )

        result = json.loads(serialize_snapshot(snapshot))

        self.assertEqual(result["captured_at"], "2026-01-02T08:34:05+05:30")

    def test_special_characters_and_unicode_round_trip(self):
        snapshot = make_snapshot(
            system=SystemInfo('Host "test" \\ [bold] café', "release", "arch"),
            warnings=("path: C:\\temp\\item; text: \"hello\" — café",),
        )

        encoded = serialize_snapshot(snapshot)
        result = json.loads(encoded)

        self.assertIn(r"caf\u00e9", encoded)
        self.assertEqual(result["system"]["operating_system"], 'Host "test" \\ [bold] café')
        self.assertEqual(result["warnings"], ['path: C:\\temp\\item; text: "hello" — café'])

    def test_non_finite_percentages_are_rejected_as_invalid_json(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    CpuInfo(8, 4, value)

    def test_non_json_field_types_raise_serialization_error(self):
        snapshot = make_snapshot(
            system=SystemInfo(object(), "release", "architecture")
        )

        with self.assertRaises(SnapshotSerializationError):
            serialize_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
