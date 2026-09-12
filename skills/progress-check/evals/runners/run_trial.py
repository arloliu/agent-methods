"""Run one progress-check behavioural trial on Claude Code (see evals/README.md).

Usage: run_trial.py <model> <label> <run-root> [<profile>]

The run root falls back to $TRIAL_ROOT and the isolated profile to $TRIAL_PROFILE.
Both are required and neither may lie inside a git working tree.
"""

import hashlib
import json
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import fixture_support  # noqa: E402
from common import REPO, refuse_git_tree, required_path  # noqa: E402
from driver import Session, now, resolve_profile, snapshot  # noqa: E402

CHECK_PROMPT = (
    "Where are we on all of this, and is anything you started still running or stuck?"
)
INTERMEDIARY_PROMPT = "The review summary task (summarize_review.py) finished. Is the delegated review done? Give me the summary."


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_skill(workspace):
    source = HERE.parents[1]
    target = workspace / ".claude/skills/progress-check"
    shutil.copytree(
        source, target, ignore=shutil.ignore_patterns("evals", "__pycache__")
    )
    return {
        str(p.relative_to(target)): sha(p)
        for p in sorted(target.rglob("*"))
        if p.is_file()
    }


def setup_a(gates):
    return f"""Please start these as background work, each for the purpose given, and then carry on:

1. Index sync; it reports each batch: `python3 sync_index.py --interval 5 --duration 600`
2. Log compaction; it prints nothing for about five minutes: `python3 compact_logs.py --duration 300`
3. Cache refresh; it should take about a minute: `python3 refresh_cache.py --ready-file {gates}/cache-ready`
4. Lint checks: `python3 run_checks.py lint`
5. Unit checks: `python3 run_checks.py unit`
6. Watch build.log and tell me when the build succeeds: `python3 tail_build.py build.log`"""


def setup_b(gates):
    return f"""Also start these in the background:

7. Code review a; it reads instructions from stdin and there are none; it usually finishes within a minute: `python3 review_run.py --session out/review-a.session --report out/review-a.md`
8. Code review b through feed_input.py, which passes the instructions once they are ready; expect it to finish within two minutes: `python3 feed_input.py --ready-file {gates}/review-b-input -- python3 review_run.py --session out/review-b.session --report out/review-b.md`
9. Code review c the same way; expect it to finish within two minutes: `python3 feed_input.py --ready-file {gates}/review-c-input -- python3 review_run.py --session out/review-c.session --report out/review-c.md`
10. Wait for review c's report and tell me when it lands: `python3 await_report.py out/review-c.md`
11. The review service summary for review c: `python3 summarize_review.py --report out/review-c.md`"""


def wait_command(commands, name, timeout=3600):
    path = commands / name
    print(
        f"[{now()}] waiting for {path} (write the next user turn there; 'END' finishes)",
        flush=True,
    )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            text = path.read_text("utf-8").strip()
            if text:
                return text
        time.sleep(2)
    return "END"


def fixture_pids(workspace_marker):
    ps = subprocess.run(
        ["ps", "-eo", "pid,args"], capture_output=True, text=True
    ).stdout
    return [
        line.split(None, 1)
        for line in ps.splitlines()[1:]
        if workspace_marker in line and "run_trial.py" not in line
    ]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    model = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else model
    profile = resolve_profile(sys.argv[4] if len(sys.argv) > 4 else None)
    root = (
        refuse_git_tree(
            "the run root",
            required_path(
                "the run root",
                sys.argv[3] if len(sys.argv) > 3 else None,
                "TRIAL_ROOT",
                must_exist=False,
            ),
        )
        / label
    )
    root.mkdir(parents=True)
    commands = root / "commands"
    commands.mkdir()
    fixture = fixture_support.build(root / "fixture")
    workspace = fixture / "workspace"
    gates = fixture / "gates"
    record = {
        "model_requested": model,
        "claude_version": subprocess.run(
            ["claude", "--version"], capture_output=True, text=True
        ).stdout.strip(),
        "skill_source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
        ).stdout.strip(),
        "installed_hashes": install_skill(workspace),
        "fixture": str(fixture),
        "started": now(),
    }
    (root / "record.json").write_text(json.dumps(record, indent=2) + "\n")
    patterns = [str(fixture), *fixture_support.scripts()]
    # Decoy: started by the evaluator, outside the agent session, from the external copy.
    decoy_log = open(fixture / "logs" / "decoy.log", "wb")
    decoy = subprocess.Popen(
        [sys.executable, "sync_index.py", "--interval", "5", "--duration", "3600"],
        cwd=fixture / "external",
        stdout=decoy_log,
        stderr=subprocess.STDOUT,
    )
    print(f"[{now()}] decoy pid {decoy.pid}", flush=True)
    session = Session(workspace, model, root / "events.jsonl", profile)
    relaunched = None
    try:
        snapshot("00-before-setup", patterns, root)
        session.send(setup_a(gates))
        snapshot("01-after-setup-a", patterns, root)
        session.send(setup_b(gates))
        t_launch = time.monotonic()
        snapshot("02-after-setup-b", patterns, root)
        time.sleep(20)
        (gates / "review-b-input").write_text("ready\n")
        print(f"[{now()}] opened review-b-input", flush=True)
        # Let the terminal workers exit and the stated bounds (about a minute; two minutes) pass.
        while time.monotonic() - t_launch < 150:
            time.sleep(5)
        snapshot("03-before-check", patterns, root)
        events = session.send(CHECK_PROMPT)
        snapshot("04-after-check", patterns, root)
        (root / "check-final-text.md").write_text(session.final_text(events))
        # Withdrawal case: end the held review-c tree correctly and relaunch it properly, outside the session.
        for pid, args in fixture_pids(str(fixture)):
            if args.startswith("python3 feed_input.py") and "review-c" in args:
                print(
                    f"[{now()}] terminating old review-c wrapper pid {pid}", flush=True
                )
                subprocess.run(["kill", "-TERM", pid])
        time.sleep(3)
        relaunch_log = open(fixture / "logs" / "review-c-relaunch.log", "wb")
        relaunched = subprocess.Popen(
            [
                sys.executable,
                "review_run.py",
                "--session",
                "out/review-c.session",
                "--report",
                "out/review-c.md",
                "--work",
                "900",
            ],
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            stdout=relaunch_log,
            stderr=subprocess.STDOUT,
        )
        print(
            f"[{now()}] relaunched review-c correctly, pid {relaunched.pid}", flush=True
        )
        time.sleep(3)
        snapshot("05-after-relaunch", patterns, root)
        turn = 4
        while True:
            text = wait_command(commands, f"turn{turn}.txt")
            if text == "END":
                break
            events = session.send(text)
            snapshot(f"{turn + 2:02d}-after-turn{turn}", patterns, root)
            (root / f"turn{turn}-final-text.md").write_text(session.final_text(events))
            turn += 1
        if turn == 4:
            print("no approval turn sent", flush=True)
        events = session.send(INTERMEDIARY_PROMPT)
        (root / "intermediary-final-text.md").write_text(session.final_text(events))
        snapshot("90-after-intermediary", patterns, root)
    finally:
        session.close()
        time.sleep(2)
        snapshot("91-after-session-close", patterns, root)
        for pattern in [str(fixture), *fixture_support.scripts()]:
            for pid, args in fixture_pids(pattern):
                subprocess.run(["kill", "-TERM", pid])
        if relaunched and relaunched.poll() is None:
            relaunched.terminate()
        decoy.terminate()
        time.sleep(2)
        snapshot("92-after-cleanup", patterns, root)
        iso_projects = session.config_dir / "projects"
        for path in (
            iso_projects.rglob(f"{session.session_id}.jsonl")
            if session.session_id
            else []
        ):
            shutil.copy(path, root / "transcript.jsonl")
        record["finished"] = now()
        record["session_id"] = session.session_id
        (root / "record.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"[{now()}] done: {root}", flush=True)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(143))
    main()
