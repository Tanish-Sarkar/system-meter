def format_bytes(value: int) -> str:
    if value < 0:
        raise ValueError("Byte values cannot be negative.")
    if value < 1024:
        return f"{value} B"

    size = float(value)
    for unit in ("KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"):
        size /= 1024
        if size < 1024 or unit == "YiB":
            return f"{size:.1f} {unit}"
    raise AssertionError("Unreachable byte unit conversion.")


def format_percentage(value: float | None) -> str:
    if value is None:
        return "not available"
    if not 0 <= value <= 100:
        raise ValueError("Percentage values must be between 0 and 100.")
    return f"{value:.1f}%"


def format_uptime(seconds: int) -> str:
    if seconds < 0:
        raise ValueError("Uptime cannot be negative.")

    days, remainder = divmod(seconds, 86_400)
    hours, remainder = divmod(remainder, 3_600)
    minutes = remainder // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)
