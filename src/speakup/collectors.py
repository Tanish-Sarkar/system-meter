from datetime import UTC, datetime, timezone
import platform

import psutil

from speakup.models import (
    BatteryInfo,
    CpuInfo,
    DiskInfo,
    MemoryInfo,
    SystemInfo,
    SystemSnapshot,
)

CPU_SAMPLE_INTERVAL_SECONDS = 0.1


def _optional_text(value: str) -> str | None:
    return value or None


class SnapshotCollectionError(RuntimeError):
    """Raised when a required system metric cannot be collected."""


def collect_system_info() -> SystemInfo:
    return SystemInfo(
        operating_system=_optional_text(platform.system()),
        release=_optional_text(platform.release()),
        architecture=_optional_text(platform.machine()),
    )


def collect_cpu_info() -> CpuInfo:
    try:
        logical_cores = psutil.cpu_count(logical=True)
        physical_cores = psutil.cpu_count(logical=False)
        utilization_percent = psutil.cpu_percent(
            interval=CPU_SAMPLE_INTERVAL_SECONDS
        )
    except (OSError, psutil.Error, NotImplementedError) as exc:
        raise SnapshotCollectionError("Unable to collect CPU information.") from exc

    if logical_cores is None or logical_cores < 1:
        raise SnapshotCollectionError("Unable to determine logical CPU core count.")

    return CpuInfo(
        logical_cores=logical_cores,
        physical_cores=physical_cores,
        utilization_percent=utilization_percent,
    )


def collect_memory_info() -> MemoryInfo:
    try:
        memory = psutil.virtual_memory()
    except (OSError, psutil.Error, NotImplementedError) as exc:
        raise SnapshotCollectionError("Unable to collect memory information.") from exc

    return MemoryInfo(
        total_bytes=memory.total,
        available_bytes=memory.available,
        used_bytes=memory.used,
        utilization_percent=memory.percent,
    )


def collect_disks() -> tuple[tuple[DiskInfo, ...], tuple[str, ...]]:
    disks: list[DiskInfo] = []
    warnings: list[str] = []

    try:
        partitions = psutil.disk_partitions(all=False)
    except (OSError, psutil.Error, NotImplementedError):
        return (), ("Unable to enumerate storage devices.",)

    seen_mount_points: set[str] = set()
    for partition in partitions:
        if partition.mountpoint in seen_mount_points:
            continue
        seen_mount_points.add(partition.mountpoint)

        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except (OSError, psutil.Error, NotImplementedError):
            warnings.append(
                f"Unable to collect storage information for mount point "
                f"{partition.mountpoint!r}."
            )
            continue

        disks.append(
            DiskInfo(
                device=_optional_text(partition.device),
                mount_point=partition.mountpoint,
                filesystem=_optional_text(partition.fstype),
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                utilization_percent=usage.percent,
            )
        )

    return tuple(disks), tuple(warnings)


def collect_battery() -> tuple[BatteryInfo | None, str | None]:
    try:
        battery = psutil.sensors_battery()
    except (OSError, psutil.Error, NotImplementedError):
        return None, "Battery information is unavailable on this system."

    if battery is None:
        return None, None

    return (
        BatteryInfo(
            percent=battery.percent,
            power_plugged=battery.power_plugged,
        ),
        None,
    )


def collect_uptime_seconds(captured_at: datetime) -> int:
    try:
        boot_time = psutil.boot_time()
    except (OSError, psutil.Error, NotImplementedError) as exc:
        raise SnapshotCollectionError("Unable to collect system uptime.") from exc

    boot_datetime = datetime.fromtimestamp(boot_time, UTC)
    uptime_seconds = int((captured_at - boot_datetime).total_seconds())
    if uptime_seconds < 0:
        raise SnapshotCollectionError("System boot time is later than capture time.")
    return uptime_seconds


def collect_snapshot() -> SystemSnapshot:
    captured_at = datetime.now(timezone.utc).astimezone()
    system = collect_system_info()
    cpu = collect_cpu_info()
    memory = collect_memory_info()
    disks, warnings = collect_disks()
    battery, battery_warning = collect_battery()
    uptime_seconds = collect_uptime_seconds(captured_at)

    if battery_warning is not None:
        warnings += (battery_warning,)

    return SystemSnapshot(
        captured_at=captured_at,
        uptime_seconds=uptime_seconds,
        system=system,
        cpu=cpu,
        memory=memory,
        disks=disks,
        battery=battery,
        warnings=warnings,
    )
