import argparse
from collections.abc import Sequence
import sys
from importlib.metadata import version

from speakup.collectors import SnapshotCollectionError, collect_snapshot
from speakup.render import render_doctor_report, render_snapshot
from speakup.serialization import SnapshotSerializationError, serialize_snapshot


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
    subparsers.add_parser("watch", help="Refresh the system snapshot repeatedly.")
    return parser


def _not_implemented(feature: str) -> int:
    print(f"{feature} is not implemented yet.", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "watch":
        return _not_implemented("Watch mode")

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
