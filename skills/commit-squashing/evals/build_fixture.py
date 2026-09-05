"""Create one fixture for a manual agent evaluation."""

import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True


def main():
    from fixture_support import build, cases

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=cases())
    parser.add_argument(
        "destination", type=Path, help="New directory; its parent must already exist"
    )
    args = parser.parse_args()
    try:
        repo = build(args.case, args.destination)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Fixture creation failed: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stderr, file=sys.stderr)
        return 1
    print(f"Repository: {repo.path}")
    print(f"User request: {repo.root / 'request.md'}")
    print(f"Evaluator baseline: {repo.root / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
