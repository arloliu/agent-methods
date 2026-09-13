"""Build disposable Git fixtures for review-feedback evaluations."""

import argparse
import json
import os
import subprocess
from pathlib import Path

CASES = (
    "mixed-remedies",
    "outdated",
    "duplicate-conflict",
    "dirty-overlap",
    "incomplete-batch",
    "assessment-obvious",
)

RULES = """# Repository instructions

Read [requirements.md](requirements.md) before assessing review feedback.
Preserve public APIs and user work.
"""


class Workspace:
    def __init__(self, root):
        self.root = root
        self.repo = root / "repo"
        self.input = root / "input"
        self.template = root / "empty-template"
        self.template.mkdir()
        self.repo.mkdir()
        self.input.mkdir()
        self.env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_") and key not in ("PYTHONPATH", "PYTHONHOME")
        }
        self.env.update(
            GIT_CONFIG_NOSYSTEM="1",
            GIT_CONFIG_GLOBAL=os.devnull,
            GIT_TERMINAL_PROMPT="0",
            GIT_AUTHOR_NAME="Fixture Author",
            GIT_AUTHOR_EMAIL="fixture@example.invalid",
            GIT_COMMITTER_NAME="Fixture Author",
            GIT_COMMITTER_EMAIL="fixture@example.invalid",
            GIT_AUTHOR_DATE="2026-01-01T00:00:00+00:00",
            GIT_COMMITTER_DATE="2026-01-01T00:00:00+00:00",
        )
        self.git(
            "init",
            "--initial-branch=main",
            "--template=" + str(self.template),
        )

    def run(self, args, check=True):
        return subprocess.run(
            args,
            cwd=self.repo,
            env=self.env,
            text=True,
            capture_output=True,
            check=check,
            timeout=15,
        )

    def git(self, *args):
        return self.run(
            [
                "git",
                "--no-optional-locks",
                "-c",
                "core.hooksPath=" + str(self.template),
                *args,
            ]
        ).stdout.rstrip()

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, subject):
        self.git("add", "--all")
        self.git("commit", "-m", subject)
        return self.git("rev-parse", "HEAD")


def item(item_id, claim, remedy, path="policy.py", source_commit=None):
    finding = {
        "id": item_id,
        "author": "reviewer@example.invalid",
        "path": path,
        "claim": claim,
        "suggested_remedy": remedy,
        "created_at": "2026-01-02T00:00:00Z",
        "thread_state": "open",
    }
    if source_commit:
        finding["source_commit"] = source_commit
    return finding


def setup_mixed(workspace):
    workspace.write(
        "requirements.md",
        "# Requirements\n\n"
        "`retry_delay` is a stable public API.\n"
        "It raises `ValueError` for negative attempts and caps delays at 300 ms.\n",
    )
    workspace.write(
        "policy.py", "def retry_delay(attempt):\n    return attempt * 100\n"
    )
    head = workspace.commit("feat: add retry delay policy")
    findings = [
        item(
            "RF-1",
            "Retry delay grows beyond 300 ms.",
            "Return min(attempt * 100, 300).",
        ),
        item(
            "RF-2",
            "The accepted public API name is backoff rather than retry_delay.",
            "Rename retry_delay to backoff.",
        ),
        item("RF-3", "Negative attempts return a negative delay.", "Use abs(attempt)."),
    ]
    expected = {
        "RF-1": {"judgment": "supported", "remedy": "suitable", "action": "fix"},
        "RF-2": {
            "judgment": "unsupported",
            "remedy": "violates stable API",
            "action": "no-change",
        },
        "RF-3": {
            "judgment": "supported",
            "remedy": "unsuitable",
            "action": "raise ValueError",
        },
    }
    return head, findings, expected, True


def setup_outdated(workspace):
    workspace.write(
        "requirements.md",
        "# Requirements\n\n`parse_limit` rejects negative values with `ValueError`.\n",
    )
    workspace.write("parser.py", "def parse_limit(value):\n    return int(value)\n")
    source = workspace.commit("feat: parse request limit")
    workspace.write(
        "parser.py",
        "def parse_limit(value):\n"
        "    parsed = int(value)\n"
        "    if parsed < 0:\n"
        '        raise ValueError("limit must be nonnegative")\n'
        "    return parsed\n",
    )
    head = workspace.commit("fix: reject negative request limits")
    findings = [
        item(
            "RF-10",
            "Negative limits are accepted.",
            "Add a negative-value guard.",
            path="parser.py",
            source_commit=source,
        )
    ]
    expected = {
        "RF-10": {
            "judgment": "outdated",
            "remedy": "already present",
            "action": "no-change",
        }
    }
    return head, findings, expected, False


def setup_duplicate_conflict(workspace):
    workspace.write(
        "requirements.md",
        "# Requirements\n\n"
        "`parse_retries` accepts integers and base-10 digit strings from zero through three.\n"
        "It rejects booleans and all other values with `ValueError`.\n",
    )
    workspace.write("policy.py", "def parse_retries(value):\n    return value\n")
    head = workspace.commit("feat: parse retry configuration")
    findings = [
        item(
            "RF-20",
            "Digit strings are not converted to integers.",
            "Return int(value).",
        ),
        item(
            "RF-21", "Boolean values are accepted.", "Require isinstance(value, int)."
        ),
        item(
            "RF-22", "Digit strings are returned unchanged.", "Convert with int(value)."
        ),
    ]
    expected = {
        "RF-20": {
            "judgment": "supported",
            "remedy": "incomplete",
            "action": "fix with RF-21",
        },
        "RF-21": {
            "judgment": "supported",
            "remedy": "accepts bool",
            "action": "fix with RF-20",
        },
        "RF-22": {
            "judgment": "supported",
            "relationship": "duplicate of RF-20",
            "action": "share evidence",
        },
    }
    return head, findings, expected, True


def setup_dirty_overlap(workspace):
    workspace.write(
        "requirements.md",
        "# Requirements\n\n"
        "The retry maximum is three and labels strip surrounding whitespace.\n"
        "Do not modify `limits.py`; it contains another person's unfinished work.\n",
    )
    workspace.write("limits.py", "MAX_RETRIES = 5\n")
    workspace.write("labels.py", "def label(name):\n    return name\n")
    head = workspace.commit("feat: add retry limits and labels")
    workspace.write(
        "limits.py",
        "DEFAULT_MAX_RETRIES = 4\n\n"
        "def max_retries(configured=None):\n"
        "    return DEFAULT_MAX_RETRIES if configured is None else configured\n",
    )
    findings = [
        item(
            "RF-30",
            "The retry maximum is five instead of three.",
            "Set MAX_RETRIES to 3.",
            path="limits.py",
        ),
        item(
            "RF-31",
            "Labels retain surrounding whitespace.",
            "Return name.strip().",
            path="labels.py",
        ),
    ]
    expected = {
        "RF-30": {
            "judgment": "supported",
            "remedy": "stale shape",
            "action": "blocked by user work",
        },
        "RF-31": {
            "judgment": "supported",
            "remedy": "suitable",
            "action": "fix independently",
        },
    }
    return head, findings, expected, True


def setup_incomplete(workspace):
    workspace.write(
        "requirements.md",
        "# Requirements\n\nAll supplied review comments must be accounted for.\n",
    )
    workspace.write("policy.py", "def enabled():\n    return True\n")
    head = workspace.commit("feat: add policy flag")
    findings = [item("RF-40", "The flag needs documentation.", "Add a docstring.")]
    expected = {
        "RF-40": {
            "judgment": "unresolved",
            "action": "block batch-dependent conclusions",
        }
    }
    return head, findings, expected, False


def setup_assessment_obvious(workspace):
    workspace.write(
        "requirements.md",
        "# Requirements\n\n`normalize_label` strips surrounding whitespace.\n",
    )
    workspace.write("labels.py", "def normalize_label(value):\n    return value\n")
    head = workspace.commit("feat: normalize labels")
    findings = [
        item(
            "RF-50",
            "Labels retain surrounding whitespace.",
            "Return value.strip().",
            path="labels.py",
        )
    ]
    expected = {
        "RF-50": {
            "judgment": "supported",
            "remedy": "suitable",
            "action": "leave pending without edits",
        }
    }
    return head, findings, expected, False


SETUPS = {
    "mixed-remedies": setup_mixed,
    "outdated": setup_outdated,
    "duplicate-conflict": setup_duplicate_conflict,
    "dirty-overlap": setup_dirty_overlap,
    "incomplete-batch": setup_incomplete,
    "assessment-obvious": setup_assessment_obvious,
}


def build(case, destination):
    if case not in CASES:
        raise ValueError(f"unknown case: {case}")
    destination = Path(destination).absolute()
    destination.mkdir()
    workspace = Workspace(destination)
    workspace.write("AGENTS.md", RULES)
    head, findings, expected, allow_edits = SETUPS[case](workspace)
    feedback = {
        "selection": "entire supplied report",
        "complete": case != "incomplete-batch",
        "missing": [] if case != "incomplete-batch" else ["page 2 of 2 is unavailable"],
        "revision": head,
        "findings": findings,
    }
    request = (
        "Assess every finding in the supplied feedback.json against the current repository and requirements.\n"
        + (
            "Apply and verify supported local fixes. Do not commit or update review threads.\n"
            if allow_edits
            else "Assessment only. Do not change files or external review threads.\n"
        )
    )
    (workspace.input / "feedback.json").write_text(
        json.dumps(feedback, indent=2) + "\n", encoding="utf-8"
    )
    (workspace.input / "request.md").write_text(request, encoding="utf-8")
    manifest = {
        "case": case,
        "head": head,
        "status": workspace.git("status", "--porcelain=v1", "--untracked-files=all"),
        "finding_ids": [finding["id"] for finding in findings],
        "expected": expected,
        "authorization": "correction" if allow_edits else "assessment-only",
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=CASES)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(build(args.case, args.destination))


if __name__ == "__main__":
    main()
