"""Shared paths, prompt parsing, and trace patterns for the evaluation runners.

The repository root is derived from this file's own location, which is the one
path allowed to be implicit.  Every other path a runner needs is supplied on the
command line or in an environment variable and raises when it is missing, so a
runner never silently writes to, or reads a profile from, somewhere unintended.
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
FIXTURE_DIR = EVALS / "fixtures"
# The launch-only prompts spell the command as `python <script>`.  A machine that
# provides only python3 needs a `python` on PATH for the prompt's command to resolve.
VENV_BIN = REPO / ".venv/bin"
# The two fixture scripts the discovery prompts name.
FIXTURES = ("sync_index.py", "run_checks.py")

# A launch is an interpreter actually handed one of the fixture scripts.  The prompts
# now contain the script name, so a mention of it is not evidence of a launch.
LAUNCH_RE = re.compile(
    r"(?:^|[;&|(]|\bnohup\b|\bsetsid\b|\bexec\b)\s*(?:/\S*/)?python[\d.]*\s+"
    r"(?:-\S+\s+)*\S*(?:sync_index|run_checks)\.py\b"
)
# A stop is the command being run, not the word appearing as an argument to a search.
STOP_RE = re.compile(r"(?:^|[;&|(]\s*)(?:sudo\s+)?(?:kill|pkill|killall)\b")

EXPECTED = ("load", "skip", "record")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prompt_set(path=PROMPTS):
    """Parse the discovery prompt table.

    The table is matched positionally, so an editorial change to discovery.md can
    drop a case without any error.  The count and the IDs are asserted in
    test_runners.py; change that test deliberately when the prompt set changes.
    """
    rows = []
    for line in Path(path).read_text("utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[3] in EXPECTED and cells[0] != "ID":
            rows.append(
                {
                    "id": cells[0],
                    "class": cells[1],
                    "prompt": cells[2],
                    "expected": cells[3],
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


def case_ids(argument=None, variable="DISCOVERY_CASES"):
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
    """A trial profile or run root inside a working tree lets a session read the harness.

    ALLOW_GIT_TREE=1 overrides the refusal, for the one measurement that needs it:
    comparing how a batch behaves rooted inside a checkout against rooted outside one.
    Whichever it was belongs in the trial record, so the override announces itself.
    """
    if in_git_tree(path):
        if os.environ.get("ALLOW_GIT_TREE") == "1":
            print(
                f"warning: {label} is inside a git working tree ({path}); "
                "ALLOW_GIT_TREE=1 is set, so the session can reach the harness. "
                "Record this as the run's condition.",
                file=sys.stderr,
                flush=True,
            )
            return Path(path)
        raise SystemExit(
            f"{label} resolves inside a git working tree: {path}\n"
            "Agent sessions range past their workspace and have read the harness from there; "
            "put it somewhere outside any checkout, or set ALLOW_GIT_TREE=1 to measure that on purpose."
        )
    return Path(path)


def reap_workers(root):
    """Terminate fixture workers left behind under a run root (POSIX /proc only)."""
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return
    for entry in proc_dir.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cwd = os.readlink(entry / "cwd")
            cmdline = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if cwd.startswith(str(root)) and any(
            name.encode() in cmdline for name in FIXTURES
        ):
            subprocess.run(["kill", "-TERM", entry.name], check=False)
