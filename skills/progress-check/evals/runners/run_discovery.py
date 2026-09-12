"""Run the progress-check discovery prompt set on Claude Code in fresh print-mode sessions.

Usage: run_discovery.py <model> <reps> <workers> [<case-ids>] [<run-root>] [<profile>]

The run root falls back to $DISCOVERY_ROOT and the isolated Claude Code profile to
$TRIAL_PROFILE.  Both are required and neither may lie inside a git working tree:
a session that can reach the harness reads the expected column out of discovery.md.
Unlike the agy runner, this one cannot build its own profile, because a Claude Code
profile needs credentials.  evals/README.md says how to prepare one.
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


def install(workdir):
    for name in FIXTURES:
        shutil.copy(FIXTURE_DIR / name, workdir / name)
    target = workdir / ".claude/skills/progress-check"
    shutil.copytree(
        SKILL, target, ignore=shutil.ignore_patterns("evals", "__pycache__")
    )
    return {
        str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(target.rglob("*"))
        if p.is_file()
    }


def run_one(model, case, rep, root, profile):
    workdir = root / f"{case['id']}-{rep}"
    workdir.mkdir(parents=True)
    hashes = install(workdir)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    env["CLAUDE_CONFIG_DIR"] = str(profile)
    env["PATH"] = f"{VENV_BIN}{os.pathsep}{env.get('PATH', '')}"
    cmd = [
        "claude",
        "-p",
        "--model",
        model,
        "--verbose",
        "--output-format",
        "stream-json",
        "--max-turns",
        "12",
        case["prompt"],
    ]
    started = now()
    proc = subprocess.run(
        cmd,
        cwd=workdir,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        stdin=subprocess.DEVNULL,
    )
    (workdir / "events.jsonl").write_text(proc.stdout)
    (workdir / "stderr.txt").write_text(proc.stderr)
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
        "workdir": str(workdir),
        "hashes": hashes,
        **analyse(events),
    }


def analyse(events):
    tool_uses, texts, skills_catalog, model_id, denials = [], [], None, None, []
    for e in events:
        if e.get("type") == "system" and e.get("subtype") == "init":
            skills_catalog = e.get("skills")
            model_id = e.get("model")
        if e.get("type") == "assistant":
            for b in e["message"].get("content", []):
                if b.get("type") == "tool_use":
                    tool_uses.append({"name": b["name"], "input": b.get("input")})
                elif b.get("type") == "text":
                    texts.append(b["text"])
        if e.get("type") == "result":
            denials = e.get("permission_denials", [])
    skill_calls = [
        t
        for t in tool_uses
        if t["name"] == "Skill"
        and (t["input"] or {}).get("skill") in ("progress-check",)
    ]
    body_reads = [
        t
        for t in tool_uses
        if t["name"] == "Read" and "progress-check/SKILL.md" in json.dumps(t["input"])
    ]
    loaded = "complete" if skill_calls or body_reads else "not-loaded"
    bash_commands = [
        (t["input"] or {}).get("command", "") for t in tool_uses if t["name"] == "Bash"
    ]
    # The prompt now contains the script name, so a mention is no longer evidence of a launch:
    # count only commands that actually hand the script to an interpreter.
    launches = [
        t
        for t in tool_uses
        if t["name"] == "Bash"
        and LAUNCH_RE.search((t["input"] or {}).get("command", ""))
    ]
    stops = [
        t
        for t in tool_uses
        if t["name"] in ("TaskStop", "KillShell")
        or (
            t["name"] == "Bash"
            and STOP_RE.search((t["input"] or {}).get("command", ""))
        )
    ]
    return {
        "model_id": model_id,
        "catalog_has_skill": bool(
            skills_catalog and "progress-check" in skills_catalog
        ),
        "loaded": loaded,
        "loading_evidence": [t["input"] for t in skill_calls + body_reads],
        "tool_names": [t["name"] for t in tool_uses],
        "bash_commands": bash_commands,
        "launches": [t["input"] for t in launches],
        "stop_calls": [t["input"] for t in stops],
        "denials": denials,
        "final_text": texts[-1] if texts else "",
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    model = sys.argv[1]
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    only = case_ids(sys.argv[4] if len(sys.argv) > 4 else None)
    profile = refuse_git_tree(
        "the trial profile",
        required_path(
            "the trial profile",
            sys.argv[6] if len(sys.argv) > 6 else None,
            "TRIAL_PROFILE",
        ),
    )
    if not (profile / ".credentials.json").exists():
        raise SystemExit(f"the trial profile has no .credentials.json: {profile}")
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
            pool.submit(run_one, model, case, rep, root, profile): (case["id"], rep)
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
                f"[{now()}] {key[0]}-{key[1]}: loaded={result.get('loaded')} expected={result.get('expected')} tools={result.get('tool_names')} stops={len(result.get('stop_calls') or [])}",
                flush=True,
            )
            (root / "results.json").write_text(
                json.dumps(results, indent=2, ensure_ascii=False) + "\n"
            )
    # leftover heartbeat workers from launch-only cases: match by working directory, not by name
    reap_workers(root)
    print(f"[{now()}] results in {root}", flush=True)


if __name__ == "__main__":
    main()
