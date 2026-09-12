"""Run the progress-check discovery prompt set on Antigravity CLI (agy) in fresh print-mode sessions.

Host differences from run_discovery.py (see host-agy.md § Local verification):
isolation is an overridden HOME, the skill installs under the global config skills directory,
permissions are whole-command allow rules, and print mode waits for background tasks
until --print-timeout, which is kept short so a launched worker does not hold the run open.

Usage: run_discovery_agy.py <model> <reps> <workers> [<case-ids>] [<run-root>]

The run root falls back to $DISCOVERY_ROOT.  It is required and may not lie inside a git
working tree: agy sessions reach past their workspace through find and grep, and reading
the harness puts discovery.md's expected column in front of the model.  This runner builds
each run's isolated HOME itself, so no profile is supplied; authentication comes from the
system keyring and survives the override.  Set AGY_SANDBOX=1 to add --sandbox.
"""

import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    FIXTURE_DIR,
    FIXTURES,
    LAUNCH_RE,
    SKILL,
    STOP_RE,
    VENV_BIN,
    case_ids,
    now,
    prompt_set,
    reap_workers,
    refuse_git_tree,
    required_path,
    select,
)

PRINT_TIMEOUT = "90s"
# The terminal sandbox is off by default on this version; a batch sets it to separate the
# prompt's effect from how far an unsandboxed session ranges across the filesystem.
# It is a null result for containment: it hides host processes and blocks network, not
# filesystem reads, so the run root has to sit outside every checkout regardless.
SANDBOX = os.environ.get("AGY_SANDBOX") == "1"
# Whole command names; agy denies anything unlisted and a compound command needs every part allowed.
# kill, pkill, killall, rm and sudo are deliberately absent, which is what blocks the negative cases.
ALLOW = [
    "python",
    "python3",
    "pwd",
    "echo",
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "grep",
    "find",
    "stat",
    "date",
    "ps",
    "sleep",
    "mkdir",
    "touch",
    "sed",
    "awk",
    "sort",
    "which",
    "env",
    "true",
    "tr",
    "cut",
    "nohup",
    "setsid",
    "test",
    "dirname",
    "basename",
    "uname",
    "df",
    # Read-only commands the prompts invite; a denied command ends the turn with no text at all,
    # which would leave the run unscorable rather than merely tool-less.
    "git",
    "du",
    "tree",
    "xargs",
    "realpath",
    "readlink",
    "id",
    "whoami",
    "hostname",
    "uptime",
    "jobs",
]


def install(root):
    """Build one run's isolated HOME and workspace; return the installed skill file hashes."""
    home, workspace = root / "home", root / "ws"
    (home / ".gemini/antigravity-cli").mkdir(parents=True)
    workspace.mkdir()
    for name in FIXTURES:
        shutil.copy(FIXTURE_DIR / name, workspace / name)
    target = home / ".gemini/config/skills/progress-check"
    shutil.copytree(
        SKILL, target, ignore=shutil.ignore_patterns("evals", "__pycache__")
    )
    settings = {
        "permissions": {"allow": [f"command({name})" for name in ALLOW]},
        "allowNonWorkspaceAccess": False,
    }
    (home / ".gemini/antigravity-cli/settings.json").write_text(
        json.dumps(settings, indent=2) + "\n"
    )
    return {
        str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(target.rglob("*"))
        if p.is_file()
    }


def run_one(model, case, rep, root):
    run_root = root / f"{case['id']}-{rep}"
    run_root.mkdir(parents=True)
    hashes = install(run_root)
    env = dict(os.environ)
    env["HOME"] = str(run_root / "home")
    env["PATH"] = f"{VENV_BIN}{os.pathsep}{env.get('PATH', '')}"
    cmd = [
        "agy",
        "--output-format",
        "stream-json",
        "--model",
        model,
        "--print-timeout",
        PRINT_TIMEOUT,
        *(["--sandbox"] if SANDBOX else []),
        f"-p={case['prompt']}",
    ]
    started = now()
    proc = subprocess.run(
        cmd,
        cwd=run_root / "ws",
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        stdin=subprocess.DEVNULL,
    )
    (run_root / "events.jsonl").write_text(proc.stdout)
    (run_root / "stderr.txt").write_text(proc.stderr)
    events = [
        json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")
    ]
    return {
        "case": case["id"],
        "class": case["class"],
        "expected": case["expected"],
        "rep": rep,
        "model": model,
        "started": started,
        "finished": now(),
        "returncode": proc.returncode,
        "run_root": str(run_root),
        "hashes": hashes,
        "sandbox": SANDBOX,
        "skill_path": str(
            run_root / "home/.gemini/config/skills/progress-check/SKILL.md"
        ),
        **analyse(events, run_root),
    }


def analyse(events, run_root):
    """Collect every tool step in every state; agy leaves killed steps ACTIVE and denied steps ERROR."""
    steps, result, model_id = {}, {}, None
    for event in events:
        if event.get("event") == "init":
            model_id = event["init"].get("model")
        elif event.get("event") == "result":
            result = event["result"]
        elif event.get("event") == "step_update":
            update = event["step_update"]
            step = steps.setdefault(update["step_index"], {"states": [], "text": ""})
            step["type"] = update["step_type"]
            step["tool"] = update.get("tool_name")
            step["states"].append(update["state"])
            if update.get("text_delta"):
                step["text"] += update["text_delta"]
            if update.get("tool_info"):
                step["params"] = update["tool_info"].get("parameters") or {}
    tools = [s for s in steps.values() if s["type"] == "tool"]
    commands = [
        (s.get("params") or {}).get("CommandLine", "")
        for s in tools
        if s["tool"] == "run_command"
    ]
    skill_marker = str(run_root / "home/.gemini/config/skills/progress-check")
    body_reads = [
        s
        for s in tools
        if s["tool"] in ("view_file", "view_code_item", "grep_search", "find_by_name")
        and skill_marker in json.dumps(s.get("params") or {})
    ]
    launches = [c for c in commands if LAUNCH_RE.search(c)]
    stops = [
        s
        for s in tools
        if (
            s["tool"] == "manage_task"
            and (s.get("params") or {}).get("Action") == "kill"
        )
        or (
            s["tool"] == "manage_subagents"
            and (s.get("params") or {}).get("Action", "").startswith("kill")
        )
        or (
            s["tool"] == "run_command"
            and STOP_RE.search((s.get("params") or {}).get("CommandLine", ""))
        )
    ]
    errored = [s for s in tools if "ERROR" in s["states"]]
    final_text = result.get("response", "")
    return {
        "model_id": model_id,
        "loaded": "complete" if body_reads else "not-loaded",
        "loading_evidence": [s.get("params") for s in body_reads],
        "tool_names": [s["tool"] for s in tools],
        "bash_commands": commands,
        "launches": launches,
        "stop_calls": [s.get("params") for s in stops],
        "denials": result.get("denied_actions") or [],
        "error_steps": [
            {"tool": s["tool"], "params": s.get("params")} for s in errored
        ],
        "status": result.get("status"),
        "num_turns": result.get("num_turns"),
        # A denied command can end the turn with no text at all; such a run is not scorable.
        "invalid": bool(errored) and not final_text.strip(),
        "final_text": final_text,
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    model = sys.argv[1]
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    only = case_ids(sys.argv[4] if len(sys.argv) > 4 else None)
    root = refuse_git_tree(
        "the run root",
        required_path(
            "the run root",
            sys.argv[5] if len(sys.argv) > 5 else None,
            "DISCOVERY_ROOT",
            must_exist=False,
        ),
    )
    root.mkdir(parents=True)
    cases = select(prompt_set(), only)
    jobs = [(case, rep) for rep in range(1, reps + 1) for case in cases]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(run_one, model, case, rep, root): (case["id"], rep)
            for case, rep in jobs
        }
        for future in concurrent.futures.as_completed(futures):
            key = futures[future]
            try:
                result = future.result()
            except Exception as error:  # noqa: BLE001
                result = {"case": key[0], "rep": key[1], "error": repr(error)}
            results.append(result)
            print(
                f"[{now()}] {key[0]}-{key[1]}: loaded={result.get('loaded')} expected={result.get('expected')} "
                f"launches={len(result.get('launches') or [])} stops={len(result.get('stop_calls') or [])} "
                f"invalid={result.get('invalid')} tools={result.get('tool_names')}",
                flush=True,
            )
            (root / "results.json").write_text(
                json.dumps(results, indent=2, ensure_ascii=False) + "\n"
            )
    # agy terminates its own background tasks on exit; this only catches workers started outside a task.
    reap_workers(root)
    print(f"[{now()}] results in {root}", flush=True)


if __name__ == "__main__":
    main()
