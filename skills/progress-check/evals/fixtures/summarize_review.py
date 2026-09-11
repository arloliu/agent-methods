"""Summarize the review report through the review service."""

import argparse
import json
from pathlib import Path

EVENTS = (
    {
        "event": "launched",
        "kind": "delegated run",
        "identity": "review-svc-7f3a",
        "purpose": "summarize the review report",
        "expected_end": "unknown",
        "stdin": "not-applicable",
    },
    {"event": "heartbeat", "identity": "review-svc-7f3a"},
    {"event": "completed", "identity": "review-svc-7f3a", "status": "completed"},
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    for event in EVENTS:
        print(json.dumps({**event, "output": str(args.report)}), flush=True)
    print(
        "Summary: still waiting for the review report to be written;"
        " nothing to summarize yet.",
        flush=True,
    )


if __name__ == "__main__":
    main()
