#!/usr/bin/env python3
import argparse


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="gtd",
        description="GTD Markdown generator + sync (prototype)"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init")
    sub.add_parser("add")
    sub.add_parser("build")
    sub.add_parser("sync")

    args = parser.parse_args()
    print(f"Command received: {args.cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
