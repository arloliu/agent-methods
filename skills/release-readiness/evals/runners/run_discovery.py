"""Run the release-readiness discovery prompt set on Claude Code in fresh print-mode sessions.

Usage: run_discovery.py <model> <reps> <workers> [<case-ids>] [<run-root>] [<profile>]

Each run gets its own `clean-release` fixture and starts inside its `repo/`.
Every prompt therefore refers to a real release policy, tags, and remote.
The run root falls back to $DISCOVERY_ROOT and the isolated profile to $TRIAL_PROFILE.
Neither may lie inside a git working tree, and the profile must hold credentials and the installed skill.
"""

import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from build_fixture import build  # noqa: E402
from common import (  # noqa: E402
    SKILL_NAME,
    case_ids,
    classify_commands,
    loaded,
    now,
    prompt_set,
    refuse_git_tree,
    required_path,
    resolve_profile,
    select,
    texts,
    tool_uses,
)

MAX_TURNS = "10"
MAX_BUDGET = "1.50"


def skill_hashes(profile):
    target = profile / "skills" / SKILL_NAME
    return {
        str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(target.rglob("*"))
        if p.is_file()
    }


def run_one(model, case, rep, root, profile):
    workdir = root / f"{case['id']}-{rep}"
    fixture = build("clean-release", workdir)
    (fixture / "manifest.json").unlink()
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    env["CLAUDE_CONFIG_DIR"] = str(profile)
    cmd = [
        "claude",
        "-p",
        "--model",
        model,
        "--verbose",
        "--output-format",
        "stream-json",
        "--permission-mode",
        "bypassPermissions",
        "--max-turns",
        MAX_TURNS,
        "--max-budget-usd",
        MAX_BUDGET,
        case["prompt"],
    ]
    started = now()
    proc = subprocess.run(
        cmd,
        cwd=fixture / "repo",
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
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
        "note": case["note"],
        "rep": rep,
        "model": model,
        "started": started,
        "finished": now(),
        "returncode": proc.returncode,
        "workdir": str(workdir),
        **analyse(events),
    }


def analyse(events):
    uses = tool_uses(events)
    catalog, model_id, result = None, None, {}
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            catalog = event.get("skills")
            model_id = event.get("model")
        if event.get("type") == "result":
            result = event
    state, evidence = loaded(uses)
    commands = classify_commands(uses)
    consequential = {
        key: value
        for key, value in commands.items()
        if key in ("tag", "push", "publish", "commit") and value
    }
    all_texts = texts(events)
    return {
        "model_id": model_id,
        "catalog_has_skill": bool(catalog and SKILL_NAME in catalog),
        "loaded": state,
        "loading_evidence": evidence,
        "tool_names": [use["name"] for use in uses],
        "bash_commands": [
            use["input"].get("command", "") for use in uses if use["name"] == "Bash"
        ],
        "consequential_commands": consequential,
        "num_turns": result.get("num_turns"),
        "cost_usd": result.get("total_cost_usd"),
        "stop_reason": result.get("stop_reason") or result.get("subtype"),
        "final_text": all_texts[-1][1] if all_texts else "",
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    model = sys.argv[1]
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    only = case_ids(sys.argv[4] if len(sys.argv) > 4 else None, "DISCOVERY_CASES")
    profile = resolve_profile(sys.argv[6] if len(sys.argv) > 6 else None)
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
    hashes = skill_hashes(profile)
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
                f"[{now()}] {key[0]}-{key[1]}: loaded={result.get('loaded')} "
                f"expected={result.get('expected')} tools={len(result.get('tool_names') or [])} "
                f"consequential={sorted((result.get('consequential_commands') or {}).keys())} "
                f"cost={result.get('cost_usd')}",
                flush=True,
            )
            (root / "results.json").write_text(
                json.dumps(
                    {"model": model, "hashes": hashes, "results": results},
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"[{now()}] results in {root}", flush=True)


if __name__ == "__main__":
    main()
