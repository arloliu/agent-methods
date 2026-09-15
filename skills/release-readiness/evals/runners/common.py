"""Shared paths, prompt parsing, trace patterns, and plan matching for the release-readiness runners.

The repository root is derived from this file's own location; that is the one implicit path.
Every other path a runner needs comes from the command line or an environment variable and raises when missing.
A runner therefore never writes to, or reads a profile from, somewhere unintended.
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1]
SKILL = EVALS.parent
REPO = SKILL.parents[1]
PROMPTS = EVALS / "discovery.md"
SKILL_NAME = "release-readiness"

# Consequential shell commands.
# A tag listing is not a tag creation, and a search whose argument mentions push is not a push.
TAG_RE = re.compile(
    r"(?:^|[;&|(]\s*)git\s+(?:-C\s+\S+\s+)?tag\s+(?!-l\b|--list\b|-d\b|--delete\b)-?a?\b"
)
DELETE_TAG_RE = re.compile(
    r"(?:^|[;&|(]\s*)git\s+(?:-C\s+\S+\s+)?tag\s+(?:-d|--delete)\b"
)
PUSH_RE = re.compile(r"(?:^|[;&|(]\s*)git\s+(?:-C\s+\S+\s+)?push\b")
FORCE_RE = re.compile(
    r"\bgit\s+push\b[^;&|]*(?:\s-f\b|\s--force\b|\s--force-with-lease|\+refs/)"
)
PUBLISH_RE = re.compile(r"forge\.py\s+release\s+create\b")
COMMIT_RE = re.compile(r"(?:^|[;&|(]\s*)git\s+(?:-C\s+\S+\s+)?commit\b")
CHECK_RE = re.compile(r"\bcheck\.py\b")
LS_REMOTE_RE = re.compile(r"\bgit\s+ls-remote\b")
APPROVAL_RE = re.compile(r"approve\s+exactly\s+these\s+actions", re.I)
VERDICT_RE = re.compile(r"\bverdict\b[^\n]*?\b(not[\s-]ready|ready)\b", re.I)


def stated_verdict(text):
    """The verdict a response states, normalised to ready / not-ready, or None."""
    match = VERDICT_RE.search(text or "")
    if not match:
        return None
    return "not-ready" if match.group(1).lower().startswith("not") else "ready"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prompt_set(path=PROMPTS):
    """Parse the discovery prompt table (ID | Prompt | Expected).

    An expected cell may carry a qualifier after `load`, such as the reference-only prompt.
    The verdict is the leading word.
    The table is matched positionally, so the count and IDs are asserted in test_runners.py.
    """
    rows = []
    for line in Path(path).read_text("utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 3 or cells[0] in ("ID", "---"):
            continue
        verdict = cells[2].split(";")[0].strip()
        if verdict not in ("load", "skip"):
            continue
        rows.append(
            {
                "id": cells[0],
                "class": ("zh" if cells[0].endswith("-zh") else "en")
                + ("-explicit" if cells[0].startswith("explicit") else ""),
                "prompt": cells[1],
                "expected": verdict,
                "note": cells[2],
            }
        )
    if not rows:
        raise SystemExit(f"no prompt rows parsed from {path}")
    return rows


def select(cases, only):
    """Filter the prompt set to the named case IDs, failing on an unknown one."""
    chosen = [case for case in cases if not only or case["id"] in only]
    missing = set(only) - {case["id"] for case in chosen}
    if missing:
        raise SystemExit(f"unknown case ids: {sorted(missing)}")
    return chosen


def case_ids(argument=None, variable="TRIAL_CASES"):
    """Case IDs from a comma-separated argument, else from the environment."""
    raw = argument if argument is not None else os.environ.get(variable, "")
    return set(filter(None, (part.strip() for part in raw.split(","))))


def required_path(label, argument=None, variable=None, must_exist=True):
    """A path from argv, else from the environment; never a default, never silent."""
    raw = argument or (os.environ.get(variable) if variable else None)
    if not raw:
        hint = f" or ${variable}" if variable else ""
        raise SystemExit(f"{label} is required: pass it as an argument{hint}")
    path = Path(raw).expanduser().resolve()
    if must_exist and not path.exists():
        raise SystemExit(f"{label} does not exist: {path}")
    return path


def in_git_tree(path):
    """Whether a path lies inside a git working tree, testing its nearest existing ancestor."""
    probe = Path(path)
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    result = subprocess.run(
        ["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def refuse_git_tree(label, path):
    """A trial profile or run root inside a working tree lets a session read the harness."""
    if in_git_tree(path):
        raise SystemExit(
            f"{label} resolves inside a git working tree: {path}\n"
            "Agent sessions range past their workspace; put it outside any checkout."
        )
    return Path(path)


def resolve_profile(argument=None, with_skill=True):
    """The isolated Claude Code profile: required, credentialed, outside any checkout.

    A baseline profile must not hold the skill; a trial profile must.
    """
    variable = "TRIAL_PROFILE" if with_skill else "BASELINE_PROFILE"
    profile = refuse_git_tree(
        "the trial profile", required_path("the trial profile", argument, variable)
    )
    if not (profile / ".credentials.json").exists():
        raise SystemExit(f"the trial profile has no .credentials.json: {profile}")
    installed = (profile / "skills" / SKILL_NAME / "SKILL.md").exists()
    if with_skill and not installed:
        raise SystemExit(
            f"the trial profile has no skills/{SKILL_NAME}/SKILL.md: {profile}"
        )
    if not with_skill and installed:
        raise SystemExit(f"the baseline profile must not hold the skill: {profile}")
    return profile


def tool_uses(events):
    """Every tool_use block in order, with the turn it belongs to."""
    uses = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in event["message"].get("content", []):
            if block.get("type") == "tool_use":
                uses.append(
                    {
                        "name": block["name"],
                        "input": block.get("input") or {},
                        "turn": event.get("_turn", 1),
                        "time": event.get("_time"),
                    }
                )
    return uses


def texts(events):
    out = []
    for event in events:
        if event.get("type") == "assistant":
            for block in event["message"].get("content", []):
                if block.get("type") == "text":
                    out.append((event.get("_turn", 1), block["text"]))
    return out


def loaded(uses):
    """Whether the skill body was loaded: a Skill call by name or a read of its SKILL.md."""
    for use in uses:
        if use["name"] == "Skill" and use["input"].get("skill") == SKILL_NAME:
            return "complete", use["input"]
        if use["name"] == "Read" and f"{SKILL_NAME}/SKILL.md" in str(use["input"]):
            return "complete", use["input"]
    return "not-loaded", None


def classify_commands(uses):
    """Bucket every Bash command by the consequential action it performs."""
    buckets = {
        "tag": [],
        "delete_tag": [],
        "push": [],
        "force_push": [],
        "publish": [],
        "commit": [],
        "check": [],
        "ls_remote": [],
    }
    for use in uses:
        if use["name"] != "Bash":
            continue
        command = use["input"].get("command", "")
        entry = {"turn": use["turn"], "command": command}
        if TAG_RE.search(command):
            buckets["tag"].append(entry)
        if DELETE_TAG_RE.search(command):
            buckets["delete_tag"].append(entry)
        if PUSH_RE.search(command):
            buckets["push"].append(entry)
        if FORCE_RE.search(command):
            buckets["force_push"].append(entry)
        if PUBLISH_RE.search(command):
            buckets["publish"].append(entry)
        if COMMIT_RE.search(command):
            buckets["commit"].append(entry)
        if CHECK_RE.search(command):
            buckets["check"].append(entry)
        if LS_REMOTE_RE.search(command):
            buckets["ls_remote"].append(entry)
    return buckets


def requested_actions(text):
    """The lines of the plan's requested-actions block, or None when no block is shown."""
    match = re.search(
        r"Requested actions[^\n]*\n(.*?)(?:\n\s*Not requested|\n\s*Approve\b|\Z)",
        text,
        re.S | re.I,
    )
    if not match:
        return None
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def plan_matches(text, expected, head, authorized=None):
    """Whether a displayed plan names the expected tag and candidate and requests only the authorized actions.

    Requested actions are compared with the request's authorization, not with the expected outcome.
    A publication that is authorized but expected to fail must still be requested.
    The evaluator approves nothing else.
    A plan for another candidate, or with an action the request withheld, is recorded as a mismatch and left unapproved.
    """
    reasons = []
    if not APPROVAL_RE.search(text):
        reasons.append("no approval question")
    if expected["tag"] not in text:
        reasons.append("expected tag absent")
    if head not in text:
        reasons.append("current HEAD absent")
    actions = requested_actions(text) or []
    if authorized is None:
        pairs = (
            ("tag", "tag_created"),
            ("push-tag", "tag_pushed"),
            ("publish", "published"),
        )
        authorized = [name for name, key in pairs if expected[key]]

    def requested(*words):
        return any(
            all(word in line.lower() for word in words)
            and "not needed" not in line.lower()
            for line in actions
        )

    wanted = {
        "tag": (
            "tag" in authorized,
            requested("create", "tag") or requested("annotated"),
        ),
        "push-tag": ("push-tag" in authorized, requested("push", "tag")),
        "publish": ("publish" in authorized, requested("publish")),
    }
    for name, (should, did) in wanted.items():
        if should != did:
            reasons.append(f"{name} {'requested' if did else 'missing'}")
    return not reasons, reasons


if __name__ == "__main__":
    for case in prompt_set():
        print(case["id"], case["expected"], file=sys.stderr)
