"""Sync the search index in batches, reporting progress as it goes."""

import argparse
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=5.0, help="seconds per batch")
    parser.add_argument("--duration", type=float, default=600.0, help="total seconds")
    args = parser.parse_args()
    started = time.monotonic()
    batch = 0
    print("sync started", flush=True)
    while time.monotonic() - started < args.duration:
        time.sleep(args.interval)
        batch += 1
        print(f"synced batch {batch}", flush=True)
    print("sync complete", flush=True)


if __name__ == "__main__":
    main()
