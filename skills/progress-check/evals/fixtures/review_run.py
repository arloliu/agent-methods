"""Run a code review from instructions on stdin and write the report."""

import argparse
import os
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True, help="session file")
    parser.add_argument("--report", type=Path, required=True, help="report file")
    parser.add_argument("--work", type=float, default=2.0, help="review seconds")
    args = parser.parse_args()
    print("review-run 1.0 ready; reading instructions from stdin", flush=True)
    instructions = sys.stdin.read()
    args.session.parent.mkdir(parents=True, exist_ok=True)
    args.session.write_text(f"pid={os.getpid()}\n", encoding="utf-8")
    print(f"session started; {len(instructions)} bytes of instructions", flush=True)
    time.sleep(args.work)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("Review: no findings.\n", encoding="utf-8")
    print(f"report written: {args.report}", flush=True)


if __name__ == "__main__":
    main()
