"""Reduce a discovery batch's results.json to a committable per-run summary.

The full evidence -- event streams, per-run HOMEs, host transcripts -- stays outside
the repository.  What the trial records cite is every run's classification, its tool
and shell calls, and its response in full, and that is what this writes.

Machine-specific text is rewritten to placeholders, because a response quotes the
paths it worked in: the user's home, the scratch root the batch ran under, this
checkout, the machine's name, and the host-assigned conversation and task identifiers.
The identifiers are rewritten consistently within a run, so a response that refers
back to its own task still reads correctly.

Usage: reduce_runs.py <run-root> <output.json> [<run-root> <output.json> ...]
"""

import json
import os
import re
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO  # noqa: E402
from score_over_trigger import read_events, structures, unsolicited_checks  # noqa: E402

# Dropped: they record this machine's directory layout and nothing a record cites.
DROP = ("workdir", "run_root", "skill_path")
# Hoisted to the batch: identical across every run, and 5 digests per run is most of the file.
HOIST = ("hashes",)
UUID_RE = re.compile(
    r"(?<![0-9a-f])[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![0-9a-f])",
    re.I,
)
# A per-uid harness scratch root, which names the uid.
SCRATCH_RE = re.compile(r"claude-\d+")


def scrubber(root):
    """A function rewriting machine-specific text, with per-run identifier mapping."""
    root = Path(root).resolve()
    home, repo = str(Path.home()), str(REPO)
    literals = [
        (str(root), "<run-root>"),
        (repo, "<repo>"),
        (home, "<home>"),
        # Hosts encode a project path as one directory name by replacing every slash.
        (repo.replace("/", "-"), "<repo-slug>"),
        (home.replace("/", "-"), "<home-slug>"),
        (os.environ.get("TMPDIR", "/tmp"), "<tmp>"),
        (socket.gethostname(), "<host>"),
        (os.environ.get("USER", ""), "<user>"),
    ]
    literals = [(text, name) for text, name in literals if text and len(text) > 3]
    literals.sort(key=lambda pair: len(pair[0]), reverse=True)
    # A batch is scored where it ran and read where it was moved to,
    # so a response quotes a scratch path the current run root no longer matches.
    # Any absolute path ending in the batch directory is that same root under its original name.
    moved = re.compile(r"(?:/[^/\s\"'\\)\]]+)+/" + re.escape(root.name))

    def scrub(value, seen):
        if isinstance(value, str):
            value = moved.sub("<run-root>", value)
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


def reduce_batch(root, destination):
    root = Path(root)
    results = json.load(open(root / "results.json"))
    scrub = scrubber(root)
    hoisted, reduced = {}, []
    for result in sorted(
        results, key=lambda r: (r.get("case", ""), int(r.get("rep", 0)))
    ):
        run_dir = root / f"{result.get('case')}-{result.get('rep')}"
        calls = read_events(run_dir)
        entry = {key: value for key, value in result.items() if key not in DROP + HOIST}
        for key in HOIST:
            if key in result:
                hoisted.setdefault(key, result[key])
        if result.get("expected") == "record":
            entry["over_trigger"] = {
                "report_structures": structures(result.get("final_text") or ""),
                "unsolicited_checks": [
                    {"kind": kind, "detail": detail, "counts_because": why}
                    for kind, detail, why in unsolicited_checks(result, calls)
                ],
            }
        reduced.append(scrub(entry, {}))
    payload = {"batch": root.name, "runs": len(reduced), **hoisted, "results": reduced}
    Path(destination).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "utf-8",
    )
    print(f"{root.name}: {len(reduced)} runs -> {destination}")


def main(arguments):
    if len(arguments) < 2 or len(arguments) % 2:
        raise SystemExit(__doc__)
    for index in range(0, len(arguments), 2):
        reduce_batch(arguments[index], arguments[index + 1])


if __name__ == "__main__":
    main(sys.argv[1:])
