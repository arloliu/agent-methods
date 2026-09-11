"""Refresh the build cache once the cache-ready marker appears."""

import argparse
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-file", type=Path, required=True)
    args = parser.parse_args()
    print(f"waiting for {args.ready_file}", flush=True)
    while not args.ready_file.exists():
        time.sleep(0.2)
    print("cache refreshed", flush=True)


if __name__ == "__main__":
    main()
