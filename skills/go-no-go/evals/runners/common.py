"""Shared helpers for the go-no-go evaluation runners."""

import datetime
import os
import subprocess
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parents[1]
SKILL = EVALS.parent
REPO = SKILL.parents[1]
SKILL_NAME = "go-no-go"
PROMPTS = EVALS / "discovery.md"


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


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
    """Every tool_use block in order."""
    uses = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in event["message"].get("content", []):
            if block.get("type") == "tool_use":
                uses.append({"name": block["name"], "input": block.get("input") or {}})
    return uses


WRITE_TOOLS = ("Edit", "Write", "NotebookEdit", "MultiEdit")


def final_text(events):
    """The last assistant text block: the answer the user would read."""
    parts = [
        block["text"]
        for event in events
        if event.get("type") == "assistant"
        for block in event["message"].get("content", [])
        if block.get("type") == "text"
    ]
    return parts[-1] if parts else ""


def text_and_tools(events):
    """Assistant content in order, as ("text", str) and ("tool", name) pairs."""
    return [
        ("text", block["text"])
        if block.get("type") == "text"
        else ("tool", block["name"])
        for event in events
        if event.get("type") == "assistant"
        for block in event["message"].get("content", [])
        if block.get("type") in ("text", "tool_use")
    ]


def starts_a_line(value, label):
    return any(line.strip().startswith(label) for line in value.splitlines())


def report_text(events):
    """The reply from the last text block that opens a report (`Subject:`) to the end.

    A pre-authorized step runs after the report, so the last block alone may hold only
    the step's outcome. Falls back to `final_text` when no block opens a report.
    """
    texts = [value for kind, value in text_and_tools(events) if kind == "text"]
    starts = [i for i, value in enumerate(texts) if starts_a_line(value, "Subject:")]
    return "\n".join(texts[starts[-1] :]) if starts else final_text(events)


def writes_before_closing(events):
    """Write-class tool calls made before the text block that holds `Closing:`."""
    count = 0
    for kind, value in text_and_tools(events):
        if kind == "text" and starts_a_line(value, "Closing:"):
            break
        if kind == "tool" and value in WRITE_TOOLS:
            count += 1
    return count


def loaded(uses):
    """Whether the skill body was loaded: a Skill call by name or a read of its SKILL.md."""
    for use in uses:
        if use["name"] == "Skill" and use["input"].get("skill") == SKILL_NAME:
            return "complete", use["input"]
        if use["name"] == "Read" and f"{SKILL_NAME}/SKILL.md" in str(use["input"]):
            return "complete", use["input"]
    return "not-loaded", None


def prompt_set(path=PROMPTS):
    """Parse the discovery prompt table (ID | Prompt | Expected).

    The verdict is the leading word of the expected cell; a qualifier may follow it.
    The table is matched positionally, so its count and IDs are asserted in test_runners.py.
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


if __name__ == "__main__":
    for case in prompt_set():
        print(case["id"], case["expected"], file=sys.stderr)
