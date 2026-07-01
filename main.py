import argparse
import sys
from pathlib import Path

from src import BaseVM, VM, VMError, run_src


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run a special-A source file.")
    parser.add_argument(
        "source",
        nargs="?",
        default="examples/demo.src",
        help="source file to run; use '-' to read from stdin",
    )
    parser.add_argument(
        "--base-vm",
        action="store_true",
        help="run with the base VM without raise/except support",
    )
    parser.add_argument(
        "--opt",
        action="store_true",
        help="enable compile-time optimizations",
    )
    return parser.parse_args(argv)


def read_source(source):
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def main(argv=None):
    args = parse_args(argv)
    vm_class = BaseVM if args.base_vm else VM

    try:
        run_src(read_source(args.source), vm_class, optimize=args.opt)
    except (OSError, SyntaxError, ValueError, VMError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
