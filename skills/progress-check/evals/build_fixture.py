"""Create the progress-check fixture set for a manual agent evaluation."""

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    from fixture_support import build

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "destination", type=Path, help="New directory; its parent must already exist"
    )
    args = parser.parse_args()
    try:
        root = build(args.destination)
    except OSError as error:
        print(f"Fixture creation failed: {error}", file=sys.stderr)
        return 1
    print(f"Agent workspace: {root / 'workspace'}")
    print(f"Evaluator gates: {root / 'gates'}")
    print(f"Evaluator manifest: {root / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
