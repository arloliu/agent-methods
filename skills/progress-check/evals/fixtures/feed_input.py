"""Start a command and close its stdin once the input-ready marker appears."""

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path

GRACE = 2.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("command required after --")

    def forward(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, forward)
    child = None
    try:
        child = subprocess.Popen(command, stdin=subprocess.PIPE)
        print(f"holding input for pid {child.pid} until {args.ready_file}", flush=True)
        while not args.ready_file.exists():
            if child.poll() is not None:
                break
            time.sleep(0.2)
        child.stdin.close()
        print("input closed", flush=True)
        return child.wait()
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=GRACE)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    sys.exit(main())
