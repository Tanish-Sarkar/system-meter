import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version


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

    if args.command == "doctor":
        return _not_implemented("The doctor command")
    if args.command == "watch":
        return _not_implemented("Watch mode")

    if args.json:
        return _not_implemented("JSON snapshot output")
    if args.quiet:
        return _not_implemented("Quiet snapshot check mode")
    return _not_implemented("System snapshot output")


if __name__ == "__main__":
    raise SystemExit(main())
