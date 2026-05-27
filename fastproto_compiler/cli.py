from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TextIO

from . import __version__
from .generator import generate_code
from .model import FastprotoError


def build_parser():
    parser = argparse.ArgumentParser(
        prog="fastproto",
        description="Generate C++ fastproto headers from .fastproto schema files.",
    )
    parser.add_argument("input", help="Input .fastproto schema file")
    parser.add_argument(
        "-o",
        "--output",
        metavar="HEADER",
        default="-",
        help="Write the generated header to HEADER. Defaults to stdout.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"fastproto {__version__}",
    )
    return parser


def _read_input(path: str, stdin: TextIO) -> tuple[str, str]:
    if path == "-":
        return stdin.read(), "<stdin>"

    input_path = Path(path)
    return input_path.read_text(), str(input_path)


def _write_output(path: str | Path, contents: str, stdout: TextIO):
    if str(path) == "-":
        stdout.write(contents)
        return

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(contents)


def run(
    argv: list[str] | None = None,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        source, source_name = _read_input(args.input, stdin)
        contents = generate_code(source, source_name=source_name)
        _write_output(args.output, contents, stdout)
        return 0
    except (FastprotoError, OSError) as error:
        stderr.write(f"fastproto: error: {error}\n")
        return 1


def main(argv: list[str] | None = None) -> int:
    return run(argv)
