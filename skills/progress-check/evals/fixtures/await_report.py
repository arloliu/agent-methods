"""Wait for the review report and announce it."""

import argparse
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    print(f"waiting for {args.report}", flush=True)
    while not args.report.exists():
        time.sleep(0.2)
    print("report available", flush=True)


if __name__ == "__main__":
    main()
