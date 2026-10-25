from dataclasses import dataclass
from datetime import datetime


def _validate_percentage(name: str, value: float | None) -> None:
    if value is not None and not 0 <= value <= 100:
        raise ValueError(f"{name} must be between 0 and 100.")


def _validate_bytes(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")


@dataclass(frozen=True)
class SystemInfo:
    operating_system: str | None
    release: str | None
    architecture: str | None


@dataclass(frozen=True)
class CpuInfo:
    logical_cores: int
    physical_cores: int | None
    utilization_percent: float

    def __post_init__(self) -> None:
        if self.logical_cores < 1:
            raise ValueError("logical_cores must be positive.")
        if self.physical_cores is not None and self.physical_cores < 1:
            raise ValueError("physical_cores must be positive when available.")
        _validate_percentage("utilization_percent", self.utilization_percent)


@dataclass(frozen=True)
class MemoryInfo:
    total_bytes: int
    available_bytes: int
    used_bytes: int
    utilization_percent: float

    def __post_init__(self) -> None:
        _validate_bytes("total_bytes", self.total_bytes)
        _validate_bytes("available_bytes", self.available_bytes)
        _validate_bytes("used_bytes", self.used_bytes)
        _validate_percentage("utilization_percent", self.utilization_percent)


@dataclass(frozen=True)
class DiskInfo:
    device: str | None
    mount_point: str
    filesystem: str | None
    total_bytes: int
    used_bytes: int
    free_bytes: int
    utilization_percent: float

    def __post_init__(self) -> None:
        if not self.mount_point:
            raise ValueError("mount_point cannot be empty.")
        _validate_bytes("total_bytes", self.total_bytes)
        _validate_bytes("used_bytes", self.used_bytes)
        _validate_bytes("free_bytes", self.free_bytes)
        _validate_percentage("utilization_percent", self.utilization_percent)


@dataclass(frozen=True)
class BatteryInfo:
    percent: float | None
    power_plugged: bool | None

    def __post_init__(self) -> None:
        _validate_percentage("percent", self.percent)


@dataclass(frozen=True)
class SystemSnapshot:
    captured_at: datetime
    uptime_seconds: int
    system: SystemInfo
    cpu: CpuInfo
    memory: MemoryInfo
    disks: tuple[DiskInfo, ...]
    battery: BatteryInfo | None
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware.")
        if self.uptime_seconds < 0:
            raise ValueError("uptime_seconds cannot be negative.")
