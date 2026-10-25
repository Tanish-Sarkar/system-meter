import json
import math

from speakup.models import SystemSnapshot

JSON_SCHEMA_VERSION = 1


class SnapshotSerializationError(ValueError):
    """Raised when a snapshot cannot be represented by the public JSON schema."""


def _validate_finite_percentages(snapshot: SystemSnapshot) -> None:
    percentages = [snapshot.cpu.utilization_percent, snapshot.memory.utilization_percent]
    percentages.extend(disk.utilization_percent for disk in snapshot.disks)
    if snapshot.battery is not None and snapshot.battery.percent is not None:
        percentages.append(snapshot.battery.percent)

    if not all(math.isfinite(value) for value in percentages):
        raise SnapshotSerializationError(
            "Snapshot contains a non-finite percentage value."
        )


def snapshot_to_dict(snapshot: SystemSnapshot) -> dict[str, object]:
    _validate_finite_percentages(snapshot)

    return {
        "schema_version": JSON_SCHEMA_VERSION,
        "captured_at": snapshot.captured_at.isoformat(),
        "uptime_seconds": snapshot.uptime_seconds,
        "system": {
            "operating_system": snapshot.system.operating_system,
            "release": snapshot.system.release,
            "architecture": snapshot.system.architecture,
        },
        "cpu": {
            "logical_cores": snapshot.cpu.logical_cores,
            "physical_cores": snapshot.cpu.physical_cores,
            "utilization_percent": snapshot.cpu.utilization_percent,
        },
        "memory": {
            "total_bytes": snapshot.memory.total_bytes,
            "available_bytes": snapshot.memory.available_bytes,
            "used_bytes": snapshot.memory.used_bytes,
            "utilization_percent": snapshot.memory.utilization_percent,
        },
        "disks": [
            {
                "device": disk.device,
                "mount_point": disk.mount_point,
                "filesystem": disk.filesystem,
                "total_bytes": disk.total_bytes,
                "used_bytes": disk.used_bytes,
                "free_bytes": disk.free_bytes,
                "utilization_percent": disk.utilization_percent,
            }
            for disk in snapshot.disks
        ],
        "battery": (
            {
                "percent": snapshot.battery.percent,
                "power_plugged": snapshot.battery.power_plugged,
            }
            if snapshot.battery is not None
            else None
        ),
        "warnings": list(snapshot.warnings),
    }


def serialize_snapshot(snapshot: SystemSnapshot) -> str:
    try:
        return json.dumps(
            snapshot_to_dict(snapshot),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
        )
    except (TypeError, ValueError) as exc:
        if isinstance(exc, SnapshotSerializationError):
            raise
        raise SnapshotSerializationError(
            "Snapshot contains data that cannot be encoded as valid JSON."
        ) from exc
