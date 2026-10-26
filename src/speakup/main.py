import argparse
from collections.abc import Sequence
import math
import sys
from importlib.metadata import version

from speakup.collectors import SnapshotCollectionError, collect_snapshot
from speakup.render import render_doctor_report, render_snapshot
from speakup.serialization import (
    SnapshotSerializationError,
    serialize_snapshot,
)
from speakup.watch import run_watch


DEFAULT_WATCH_INTERVAL_SECONDS = 2.0


def _parse_watch_interval(value: str) -> float:
    try:
        interval = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "interval must be a finite number of at least 1 second"
        ) from exc

    if not math.isfinite(interval) or interval < 1:
        raise argparse.ArgumentTypeError(
            "interval must be a finite number of at least 1 second"
        )
    return interval


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="speakup",
        usage="%(prog)s [-h] [--version] [--json | --quiet] [doctor | watch]",
        description="Get a quick snapshot of system health from the terminal.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('system-meter')}",
    )

    output_modes = parser.add_mutually_exclusive_group()
    output_modes.add_argument(
        "--json",
        action="store_true",
        help="Output the snapshot as JSON.",
    )
    output_modes.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the normal snapshot output and use the exit status.",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("doctor", help="Check system information availability.")
    watch_parser = subparsers.add_parser(
        "watch",
        help="Refresh the system snapshot repeatedly.",
        description="Refresh system snapshots until interrupted with Ctrl+C.",
    )
    watch_parser.add_argument(
        "--interval",
        type=_parse_watch_interval,
        default=DEFAULT_WATCH_INTERVAL_SECONDS,
        metavar="SECONDS",
        help="Time between snapshot starts; at least 1 second (default: 2).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "watch":
        if args.quiet:
            parser.error("--quiet cannot be used with watch.")
        if not args.json and not sys.stdout.isatty():
            parser.error(
                "watch requires an interactive terminal; use --json for piped output."
            )
        try:
            run_watch(args.interval, json_output=args.json)
        except KeyboardInterrupt:
            return 130
        except SnapshotCollectionError as exc:
            print(f"Unable to collect watch snapshot: {exc}", file=sys.stderr)
            return 1
        except SnapshotSerializationError as exc:
            print(f"Unable to serialize watch snapshot: {exc}", file=sys.stderr)
            return 1
        return 0

    try:
        snapshot = collect_snapshot()
    except SnapshotCollectionError as exc:
        action = "doctor report" if args.command == "doctor" else "system snapshot"
        print(f"Unable to collect {action}: {exc}", file=sys.stderr)
        return 1

    if args.command == "doctor":
        render_doctor_report(snapshot)
        return 0

    if args.quiet:
        return 0

    if args.json:
        try:
            output = serialize_snapshot(snapshot)
        except SnapshotSerializationError as exc:
            print(f"Unable to serialize system snapshot: {exc}", file=sys.stderr)
            return 1
        print(output)
        return 0

    render_snapshot(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
