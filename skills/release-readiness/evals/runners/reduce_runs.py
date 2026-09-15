"""Reduce a batch's results.json to a committable summary with machine-specific text scrubbed.

The full evidence stays outside the repository: event streams, fixtures, and host transcripts.
The trial record cites every run's classification, commands, verifier output, and final responses.
That is what this writes.

Usage: reduce_runs.py <run-root> <output.json> [<run-root> <output.json> ...]
"""

import json
import os
import re
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO, stated_verdict  # noqa: E402

DROP = ("workdir",)
UUID_RE = re.compile(
    r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![0-9a-f])",
    re.I,
)
SCRATCH_RE = re.compile(r"claude-\d+")


def scrubber(root):
    """A function rewriting machine-specific text, with per-run identifier mapping."""
    root = Path(root).resolve()
    home, repo = str(Path.home()), str(REPO)
    literals = [
        (str(root), "<run-root>"),
        (str(root.parent / (root.name + "-evaluator")), "<evaluator-root>"),
        (repo, "<repo>"),
        (home, "<home>"),
        (repo.replace("/", "-"), "<repo-slug>"),
        (home.replace("/", "-"), "<home-slug>"),
        (os.environ.get("TMPDIR", "/tmp"), "<tmp>"),
        (socket.gethostname(), "<host>"),
        (os.environ.get("USER", ""), "<user>"),
    ]
    literals = [(text, name) for text, name in literals if text and len(text) > 3]
    literals.sort(key=lambda pair: len(pair[0]), reverse=True)

    def scrub(value, seen):
        if isinstance(value, str):
            for text, name in literals:
                value = value.replace(text, name)
            value = SCRATCH_RE.sub("<scratch>", value)
            return UUID_RE.sub(
                lambda m: seen.setdefault(m.group(0).lower(), f"<id-{len(seen) + 1}>"),
                value,
            )
        if isinstance(value, list):
            return [scrub(item, seen) for item in value]
        if isinstance(value, dict):
            return {key: scrub(item, seen) for key, item in value.items()}
        return value

    return scrub


def restate_verdict(entry):
    """Recompute the stated verdict from the final texts so a pattern fix applies to old batches."""
    if "turn1_final_text" in entry:
        entry["verdict_stated"] = stated_verdict(
            entry.get("turn1_final_text")
        ) or stated_verdict(entry.get("turn2_final_text"))
    return entry


def reduce_batch(root, destination):
    root = Path(root)
    payload = json.load(open(root / "results.json"))
    scrub = scrubber(root)
    results = payload["results"] if isinstance(payload, dict) else payload
    reduced = []
    for result in sorted(
        results, key=lambda r: (r.get("case", ""), int(r.get("rep", 0)))
    ):
        entry = {key: value for key, value in result.items() if key not in DROP}
        reduced.append(scrub(restate_verdict(entry), {}))
    header = (
        {k: v for k, v in payload.items() if k != "results"}
        if isinstance(payload, dict)
        else {}
    )
    out = {"batch": root.name, "runs": len(reduced), **header, "results": reduced}
    Path(destination).write_text(
        json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True) + "\n", "utf-8"
    )
    print(f"{root.name}: {len(reduced)} runs -> {destination}")


def main(arguments):
    if len(arguments) < 2 or len(arguments) % 2:
        raise SystemExit(__doc__)
    for index in range(0, len(arguments), 2):
        reduce_batch(arguments[index], arguments[index + 1])


if __name__ == "__main__":
    main(sys.argv[1:])
