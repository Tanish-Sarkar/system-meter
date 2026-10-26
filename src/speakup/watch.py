import os
import sys
import time

from rich.console import Console
from rich.live import Live

from speakup.collectors import collect_snapshot
from speakup.render import snapshot_renderable
from speakup.serialization import serialize_snapshot_line


def _default_console() -> Console:
    return Console(
        file=sys.stdout,
        no_color="NO_COLOR" in os.environ,
        markup=False,
        highlight=False,
        soft_wrap=True,
    )


def _sleep_until_next_sample(started_at: float, interval: float) -> None:
    remaining = interval - (time.monotonic() - started_at)
    if remaining > 0:
        time.sleep(remaining)


def run_watch(
    interval: float,
    *,
    json_output: bool,
    console: Console | None = None,
) -> None:
    if json_output:
        while True:
            started_at = time.monotonic()
            snapshot = collect_snapshot()
            output = serialize_snapshot_line(snapshot)
            print(output, flush=True)
            _sleep_until_next_sample(started_at, interval)

    if console is None:
        console = _default_console()

    with Live(console=console, screen=False, auto_refresh=False) as live:
        while True:
            started_at = time.monotonic()
            snapshot = collect_snapshot()
            live.update(
                snapshot_renderable(snapshot, console.width),
                refresh=True,
            )
            _sleep_until_next_sample(started_at, interval)
