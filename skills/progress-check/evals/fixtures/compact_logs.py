"""Compact archived logs; prints nothing until the pass finishes."""

import argparse
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=300.0, help="seconds of work")
    args = parser.parse_args()
    time.sleep(args.duration)
    print("compacted 0 archives", flush=True)


if __name__ == "__main__":
    main()
