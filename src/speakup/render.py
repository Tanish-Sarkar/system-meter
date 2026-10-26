import os
import sys
from datetime import UTC

from rich import box
from rich.console import Console, Group, RenderableType
from rich.table import Table
from rich.text import Text

from speakup.formatting import format_bytes, format_percentage, format_uptime
from speakup.models import SystemSnapshot


def _optional(value: str | None) -> str:
    return value if value else "not available"


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
    renderables: list[RenderableType] = [Text("System Meter", style="bold cyan")]
    captured_at = snapshot.captured_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

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
    renderables.extend((Text("System", style="bold"), system_table))

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
    renderables.extend((Text("CPU", style="bold"), cpu_table))

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
    renderables.extend((Text("Memory", style="bold"), memory_table))

    renderables.append(Text("Storage", style="bold"))
    if snapshot.disks:
        if width < 80:
            for disk in snapshot.disks:
                renderables.append(
                    Text(
                        f"{disk.mount_point}: "
                        f"{format_bytes(disk.used_bytes)} used / "
                        f"{format_bytes(disk.total_bytes)} total, "
                        f"{format_bytes(disk.free_bytes)} free "
                        f"({format_percentage(disk.utilization_percent)} used)"
                    )
                )
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
                    disk.mount_point,
                    f"{format_bytes(disk.used_bytes)} / "
                    f"{format_bytes(disk.total_bytes)}",
                    format_bytes(disk.free_bytes),
                    format_percentage(disk.utilization_percent),
                )
            renderables.append(disk_table)
    else:
        renderables.append(Text("No storage information available."))

    if snapshot.battery is not None:
        battery = snapshot.battery
        if battery.power_plugged is True:
            power_state = "plugged in"
        elif battery.power_plugged is False:
            power_state = "on battery"
        else:
            power_state = "power state not available"

        renderables.extend(
            (
                Text("Battery", style="bold"),
                Text(
                    f"Charge: {format_percentage(battery.percent)} "
                    f"({power_state})"
                ),
            )
        )

    if snapshot.warnings:
        renderables.append(Text("Notes", style="bold"))
        for warning in snapshot.warnings:
            renderables.append(Text(f"- {warning}"))

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

    captured_at = snapshot.captured_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    console.print(Text("System Meter Doctor", style="bold cyan"))
    console.print(Text(f"Captured: {captured_at}"))
    console.print(Text("Metric availability is not a health assessment."))

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
    console.print(Text("System information", style="bold"))
    console.print(system_table)

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
    console.print(Text("CPU", style="bold"))
    console.print(cpu_table)

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
    console.print(Text("Memory", style="bold"))
    console.print(memory_table)

    console.print(Text("Storage", style="bold"))
    if snapshot.disks:
        if console.width < 80:
            for disk in snapshot.disks:
                console.print(
                    Text(
                        f"{disk.mount_point}: "
                        f"{format_bytes(disk.used_bytes)} used / "
                        f"{format_bytes(disk.total_bytes)} total, "
                        f"{format_bytes(disk.free_bytes)} free "
                        f"({format_percentage(disk.utilization_percent)} used)"
                    ),
                    soft_wrap=True,
                )
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
            console.print(disk_table)
    else:
        console.print("No storage information available.")

    if snapshot.battery is not None:
        battery = snapshot.battery
        if battery.power_plugged is True:
            power_state = "plugged in"
        elif battery.power_plugged is False:
            power_state = "on battery"
        else:
            power_state = "power state not available"

        console.print(Text("Battery", style="bold"))
        console.print(
            Text(
                f"Charge: {format_percentage(battery.percent)} "
                f"({power_state})"
            )
        )

    console.print(Text("Availability and limitations", style="bold"))
    if snapshot.warnings:
        for warning in snapshot.warnings:
            console.print(Text(f"- {warning}"))
    else:
        console.print(Text("No collection limitations were reported."))
