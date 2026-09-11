"""Follow a build log from its current end and exit when the trigger line arrives."""

import argparse
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--until", default="BUILD SUCCEEDED", help="trigger text")
    args = parser.parse_args()
    with args.log.open(encoding="utf-8", errors="replace") as handle:
        handle.seek(0, 2)
        print(f"watching {args.log}", flush=True)
        while True:
            line = handle.readline()
            if not line:
                time.sleep(0.2)
                continue
            if args.until in line:
                print(f"trigger seen: {line.strip()}", flush=True)
                return


if __name__ == "__main__":
    main()
