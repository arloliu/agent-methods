"""Run a check suite and exit with its status."""

import argparse
import sys
import time

SUITES = {
    "unit": (0, "3 checks passed"),
    "lint": (3, "error: unused import in app.py"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=sorted(SUITES))
    parser.add_argument(
        "--delay", type=float, default=2.0, help="seconds before the result"
    )
    args = parser.parse_args()
    print(f"running {args.suite} checks", flush=True)
    time.sleep(args.delay)
    status, line = SUITES[args.suite]
    print(line, file=sys.stderr if status else sys.stdout, flush=True)
    sys.exit(status)


if __name__ == "__main__":
    main()
