"""Run the no-skill baseline on Claude Code, one fixture case per session.

Usage: run_baseline.py <model> <workers> <run-root> [<case-ids>] [<profile>]

The profile comes from the argument or $BASELINE_PROFILE and must not hold the skill.
For each case the runner builds the fixture and moves the manifest to an evaluator directory beside the run root.
It starts a print-mode session inside `repo/` with `input/` added as an allowed directory,
sends the request as written, and records the single answer.
Afterwards it scores the answer and the repository state with the baseline scorer.
"""

import concurrent.futures
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from build_fixture import CASES, build  # noqa: E402
from common import (  # noqa: E402
    EVALS,
    REPO,
    case_ids,
    final_text,
    now,
    refuse_git_tree,
    required_path,
    resolve_profile,
    tool_uses,
)
from score_baseline import score  # noqa: E402

MAX_TURNS = "60"
MAX_BUDGET = "1.50"
SESSION_TIMEOUT = 900


def harness_hashes():
    return {
        name: hashlib.sha256((EVALS / name).read_bytes()).hexdigest()
        for name in ("build_fixture.py", "score_baseline.py")
    }


def run_session(cwd, model, log_path, profile, add_dir, request):
    """One print-mode turn; returns the stream-json events.

    Killed after `SESSION_TIMEOUT`s -- whatever stdout the process produced up to
    that point is still written to `log_path` before the timeout is re-raised, so a
    stalled session leaves partial evidence instead of nothing.
    """
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    env["CLAUDE_CONFIG_DIR"] = str(profile)
    with open(str(log_path) + ".stderr", "ab") as stderr:
        try:
            process = subprocess.run(
                [
                    "claude",
                    "-p",
                    request,
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
                    "--add-dir",
                    str(add_dir),
                ],
                cwd=str(cwd),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=stderr,
                text=True,
                timeout=SESSION_TIMEOUT,
            )
            stdout = process.stdout
        except subprocess.TimeoutExpired as timeout:
            partial = timeout.stdout or ""
            if isinstance(partial, bytes):
                partial = partial.decode("utf-8", errors="replace")
            Path(log_path).write_text(partial, encoding="utf-8")
            raise
    Path(log_path).write_text(stdout, encoding="utf-8")
    if process.returncode:
        raise RuntimeError(f"claude exited {process.returncode}; see {log_path}")
    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def run_case(model, case, root, evaluator, profile):
    workdir = root / case
    fixture = build(case, workdir)
    manifest_path = evaluator / f"{case}.json"
    shutil.move(str(fixture / "manifest.json"), str(manifest_path))
    request = (fixture / "input" / "request.md").read_text(encoding="utf-8")
    started = now()
    events = run_session(
        fixture / "repo",
        model,
        workdir / "events.jsonl",
        profile,
        fixture / "input",
        request,
    )
    answer = final_text(events)
    results = [e for e in events if e.get("type") == "result"]
    record = {
        "case": case,
        "model": model,
        "arm": "baseline",
        "started": started,
        "finished": now(),
        "workdir": str(workdir),
        "request": request,
        "final_text": answer,
        "tool_names": [use["name"] for use in tool_uses(events)],
        "num_turns": sum(r.get("num_turns") or 0 for r in results),
        "cost_usd": round(sum(r.get("total_cost_usd") or 0 for r in results), 4),
        "stop_reasons": [r.get("stop_reason") or r.get("subtype") for r in results],
        "score": score(fixture, manifest_path, answer),
    }
    (workdir / "record.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record


def main():
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    model = sys.argv[1]
    workers = int(sys.argv[2])
    root = refuse_git_tree(
        "the run root", required_path("the run root", sys.argv[3], must_exist=False)
    )
    only = case_ids(sys.argv[4] if len(sys.argv) > 4 else None)
    unknown = only - set(CASES)
    if unknown:
        raise SystemExit(f"unknown case ids: {sorted(unknown)}")
    cases = [case for case in CASES if not only or case in only]
    profile = resolve_profile(
        sys.argv[5] if len(sys.argv) > 5 else None, with_skill=False
    )
    root.mkdir(parents=True)
    evaluator = root.parent / (root.name + "-evaluator")
    evaluator.mkdir(parents=True)
    batch = {
        "model": model,
        "arm": "baseline",
        "claude_version": subprocess.run(
            ["claude", "--version"], capture_output=True, text=True
        ).stdout.strip(),
        "harness_source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
        ).stdout.strip(),
        "harness_hashes": harness_hashes(),
        "max_turns": MAX_TURNS,
        "max_budget_usd": MAX_BUDGET,
        "started": now(),
        "results": [],
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(run_case, model, case, root, evaluator, profile): case
            for case in cases
        }
        for future in concurrent.futures.as_completed(futures):
            case = futures[future]
            try:
                result = future.result()
            except Exception as error:  # noqa: BLE001
                result = {"case": case, "error": repr(error)}
            batch["results"].append(result)
            scored = result.get("score") or {}
            print(
                f"[{now()}] {case}: verdict={scored.get('stated_verdict')} "
                f"expected={scored.get('expected_outcome')} binary={scored.get('binary')} "
                f"unchanged={scored.get('repository_unchanged')} "
                f"cost={result.get('cost_usd')} error={result.get('error')}",
                flush=True,
            )
            (root / "results.json").write_text(
                json.dumps(batch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
    batch["finished"] = now()
    (root / "results.json").write_text(
        json.dumps(batch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"[{now()}] results in {root}", flush=True)


if __name__ == "__main__":
    main()
