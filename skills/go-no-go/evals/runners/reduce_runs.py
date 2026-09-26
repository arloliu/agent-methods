"""Reduce a batch's results.json to a committable summary with machine-specific text scrubbed.

The full evidence stays outside the repository: event streams, fixtures, and host transcripts.
The trial record cites every run's loading state, final response, and verifier output.
That is what this writes.

Usage: reduce_runs.py <run-root> <output.json> [<run-root> <output.json> ...]
"""

import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from common import REPO  # noqa: E402
from verify_report import forbidden_offers, verify  # noqa: E402

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


def restate_verifier(entry, root):
    """Recompute the verifier output from the final text and the still-present fixture.

    A verifier fix then applies to a batch that ran before it.
    Rebuilt from `root` and the case ID rather than the dropped `workdir` field.
    Only skill-arm records produce the report template `verify_report.py` parses --
    a baseline record's free-form prose is never run through it.
    """
    if entry.get("arm") != "skill":
        return entry
    workdir = root / entry.get("case", "")
    manifest_path = (
        root.parent / (root.name + "-evaluator") / f"{entry.get('case')}.json"
    )
    if (
        not (entry.get("report_text") or entry.get("final_text"))
        or not workdir.is_dir()
        or not manifest_path.is_file()
    ):
        return entry
    # Batches before `report_text` existed verify their last text block, as they ran.
    text = entry.get("report_text") or entry["final_text"]
    entry["verifier"] = verify(workdir, manifest_path, text)
    entry["forbidden_offers"] = forbidden_offers(text)
    return entry


def reducer_commit():
    """The commit whose verifier restated this batch; comparable only within one contract."""
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()


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
        reduced.append(scrub(restate_verifier(entry, root), {}))
    header = (
        {k: v for k, v in payload.items() if k != "results"}
        if isinstance(payload, dict)
        else {}
    )
    out = {
        "batch": root.name,
        "runs": len(reduced),
        **header,
        "reduced_with_commit": reducer_commit(),
        "results": reduced,
    }
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
