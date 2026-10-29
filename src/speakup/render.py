import os
import sys
from datetime import datetime

from rich import box
from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from speakup.formatting import format_bytes, format_percentage, format_uptime
from speakup.models import SystemSnapshot


def _optional(value: str | None) -> str:
    return value if value else "not available"


def _ordinal(day: int) -> str:
    """Return the day number with an ordinal suffix, e.g. 1st, 2nd, 3rd, 4th."""
    if 11 <= (day % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _format_local_time(dt: datetime) -> str:
    """Format a datetime in local time as e.g. '11:00 a.m. 29th October, 2026'."""
    local = dt.astimezone()
    hour = local.hour % 12 or 12
    minute = local.strftime("%M")
    am_pm = "a.m." if local.hour < 12 else "p.m."
    day = _ordinal(local.day)
    month_year = local.strftime("%B, %Y")
    return f"{hour}:{minute} {am_pm} {day} {month_year}"


def _panel(title: str, renderable: RenderableType, color: str) -> Panel:
    return Panel(
        renderable,
        title=Text(title, style=f"bold {color}"),
        border_style=color,
        box=box.ROUNDED,
        padding=(0, 1),
        expand=True,
    )


def _report_header(title: str, captured_at: str, subtitle: str | None = None) -> Panel:
    header = Text()
    header.append(title, style="bold bright_cyan")
    header.append(f"\nCaptured: {captured_at}", style="dim")
    if subtitle is not None:
        header.append(f"\n{subtitle}", style="italic yellow")
    return Panel(
        header,
        box=box.DOUBLE,
        border_style="bright_cyan",
        padding=(0, 2),
        expand=True,
    )


def render_snapshot(snapshot: SystemSnapshot, console: Console | None = None) -> None:
    if console is None:
        console = Console(
            file=sys.stdout,
            no_color="NO_COLOR" in os.environ,
            markup=False,
            highlight=False,
            soft_wrap=True,
        )

    console.print(snapshot_renderable(snapshot, console.width))


def snapshot_renderable(snapshot: SystemSnapshot, width: int) -> RenderableType:
    captured_at = _format_local_time(snapshot.captured_at)
    renderables: list[RenderableType] = [
        _report_header("System Meter", captured_at, "Live system snapshot")
    ]

    system_table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
        expand=False,
    )
    system_table.add_column("Property", style="bold")
    system_table.add_column("Value", overflow="fold")
    system_table.add_row(
        "Operating system",
        f"{_optional(snapshot.system.operating_system)} "
        f"{_optional(snapshot.system.release)}",
    )
    system_table.add_row("Architecture", _optional(snapshot.system.architecture))
    system_table.add_row("Uptime", format_uptime(snapshot.uptime_seconds))
    system_table.add_row("Captured", captured_at)
    renderables.append(_panel("System", system_table, "cyan"))

    cpu_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    cpu_table.add_column("Property", style="bold")
    cpu_table.add_column("Value", overflow="fold")
    cpu_table.add_row("Usage", format_percentage(snapshot.cpu.utilization_percent))
    cpu_table.add_row("Logical cores", str(snapshot.cpu.logical_cores))
    cpu_table.add_row(
        "Physical cores",
        str(snapshot.cpu.physical_cores)
        if snapshot.cpu.physical_cores is not None
        else "not available",
    )
    renderables.append(_panel("CPU", cpu_table, "magenta"))

    memory_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    memory_table.add_column("Property", style="bold")
    memory_table.add_column("Value", overflow="fold")
    memory_table.add_row(
        "Used",
        f"{format_bytes(snapshot.memory.used_bytes)} / "
        f"{format_bytes(snapshot.memory.total_bytes)} "
        f"({format_percentage(snapshot.memory.utilization_percent)})",
    )
    memory_table.add_row(
        "Available",
        format_bytes(snapshot.memory.available_bytes),
    )
    renderables.append(_panel("Memory", memory_table, "green"))

    storage_renderables: list[RenderableType] = []
    if width < 80:
        storage_renderables.append(Text("Storage", style="bold blue"))
        if snapshot.disks:
            for disk in snapshot.disks:
                storage_renderables.append(
                    Text(
                        f"{disk.mount_point}: "
                        f"{format_bytes(disk.used_bytes)} used / "
                        f"{format_bytes(disk.total_bytes)} total, "
                        f"{format_bytes(disk.free_bytes)} free "
                        f"({format_percentage(disk.utilization_percent)} used)",
                        no_wrap=True,
                    )
                )
        else:
            storage_renderables.append(Text("No storage information available."))
        renderables.extend(storage_renderables)
    else:
        if snapshot.disks:
            disk_table = Table(
                box=box.SIMPLE,
                padding=(0, 1),
                expand=False,
                show_lines=False,
            )
            disk_table.add_column("Mount", overflow="fold")
            disk_table.add_column("Used / Total", overflow="fold")
            disk_table.add_column("Free", overflow="fold")
            disk_table.add_column("Used", overflow="fold")
            for disk in snapshot.disks:
                disk_table.add_row(
                    disk.mount_point,
                    f"{format_bytes(disk.used_bytes)} / "
                    f"{format_bytes(disk.total_bytes)}",
                    format_bytes(disk.free_bytes),
                    format_percentage(disk.utilization_percent),
                )
            storage_renderables.append(disk_table)
        else:
            storage_renderables.append(Text("No storage information available."))
        renderables.append(_panel("Storage", Group(*storage_renderables), "blue"))

    if snapshot.battery is not None:
        battery = snapshot.battery
        if battery.power_plugged is True:
            power_state = "plugged in"
        elif battery.power_plugged is False:
            power_state = "on battery"
        else:
            power_state = "power state not available"

        battery_renderable = Text(
            f"Charge: {format_percentage(battery.percent)} "
            f"({power_state})"
        )
        renderables.append(_panel("Battery", battery_renderable, "yellow"))

    if snapshot.warnings:
        notes = Group(*(Text(f"- {warning}") for warning in snapshot.warnings))
        renderables.append(_panel("Notes", notes, "yellow"))

    return Group(*renderables)


def render_doctor_report(
    snapshot: SystemSnapshot,
    console: Console | None = None,
) -> None:
    if console is None:
        console = Console(
            file=sys.stdout,
            no_color="NO_COLOR" in os.environ,
            markup=False,
            highlight=False,
            soft_wrap=True,
        )

    captured_at = _format_local_time(snapshot.captured_at)
    console.print(
        _report_header(
            "System Meter Doctor",
            captured_at,
            "Metric availability is not a health assessment.",
        )
    )

    system_table = Table(
        box=box.SIMPLE,
        show_header=False,
        padding=(0, 1),
        expand=False,
    )
    system_table.add_column("Property", style="bold")
    system_table.add_column("Value", overflow="fold")
    system_table.add_row(
        "Operating system",
        f"{_optional(snapshot.system.operating_system)} "
        f"{_optional(snapshot.system.release)}",
    )
    system_table.add_row("Architecture", _optional(snapshot.system.architecture))
    system_table.add_row("Uptime", format_uptime(snapshot.uptime_seconds))
    console.print(_panel("System information", system_table, "cyan"))

    cpu_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    cpu_table.add_column("Property", style="bold")
    cpu_table.add_column("Value", overflow="fold")
    cpu_table.add_row("CPU usage", format_percentage(snapshot.cpu.utilization_percent))
    cpu_table.add_row("Logical cores", str(snapshot.cpu.logical_cores))
    cpu_table.add_row(
        "Physical cores",
        str(snapshot.cpu.physical_cores)
        if snapshot.cpu.physical_cores is not None
        else "not available",
    )
    console.print(_panel("CPU", cpu_table, "magenta"))

    memory_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    memory_table.add_column("Property", style="bold")
    memory_table.add_column("Value", overflow="fold")
    memory_table.add_row(
        "Memory used",
        f"{format_bytes(snapshot.memory.used_bytes)} / "
        f"{format_bytes(snapshot.memory.total_bytes)} "
        f"({format_percentage(snapshot.memory.utilization_percent)})",
    )
    memory_table.add_row(
        "Memory available",
        format_bytes(snapshot.memory.available_bytes),
    )
    console.print(_panel("Memory", memory_table, "green"))

    if snapshot.disks:
        if console.width < 80:
            storage_lines = []
            for disk in snapshot.disks:
                storage_lines.append(
                    Text(
                        f"{disk.mount_point}: "
                        f"{format_bytes(disk.used_bytes)} used / "
                        f"{format_bytes(disk.total_bytes)} total, "
                        f"{format_bytes(disk.free_bytes)} free "
                        f"({format_percentage(disk.utilization_percent)} used)",
                        no_wrap=True,
                    )
                )
            storage_renderable: RenderableType = Group(*storage_lines)
        else:
            disk_table = Table(
                box=box.SIMPLE,
                padding=(0, 1),
                expand=False,
                show_lines=False,
            )
            disk_table.add_column("Mount", overflow="fold")
            disk_table.add_column("Used / Total", overflow="fold")
            disk_table.add_column("Free", overflow="fold")
            disk_table.add_column("Used", overflow="fold")
            for disk in snapshot.disks:
                disk_table.add_row(
                    Text(disk.mount_point),
                    f"{format_bytes(disk.used_bytes)} / "
                    f"{format_bytes(disk.total_bytes)}",
                    format_bytes(disk.free_bytes),
                    format_percentage(disk.utilization_percent),
                )
            storage_renderable = disk_table
    else:
        storage_renderable = Text("No storage information available.")
    console.print(_panel("Storage", storage_renderable, "blue"))

    if snapshot.battery is not None:
        battery = snapshot.battery
        if battery.power_plugged is True:
            power_state = "plugged in"
        elif battery.power_plugged is False:
            power_state = "on battery"
        else:
            power_state = "power state not available"

        console.print(
            _panel(
                "Battery",
                Text(
                f"Charge: {format_percentage(battery.percent)} "
                    f"({power_state})"
                ),
                "yellow",
            )
        )

    if snapshot.warnings:
        limitations = Group(*(Text(f"- {warning}") for warning in snapshot.warnings))
    else:
        limitations = Text("No collection limitations were reported.")
    console.print(_panel("Availability and limitations", limitations, "yellow"))
