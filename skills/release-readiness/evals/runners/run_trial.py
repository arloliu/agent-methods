"""Run release-readiness behavioural trials on Claude Code, one fixture case per session.

Usage: run_trial.py <model> <workers> [<case-ids>] [<run-root>] [<profile>]

For each case the runner builds the fixture and moves the manifest to an evaluator directory beside the run root.
It starts a print-mode session inside `repo/` with `input/` added as an allowed directory and sends the request.
When the case expects a tag and the displayed plan names the expected tag, the current HEAD, and only the authorized actions,
the runner sends one approval turn; otherwise nothing is approved.
Afterwards it runs the end-state verifier and records the trace analysis.
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
from build_fixture import CASES, build, isolated_environment  # noqa: E402
from common import (  # noqa: E402
    APPROVAL_RE,
    REPO,
    SKILL_NAME,
    case_ids,
    classify_commands,
    loaded,
    now,
    plan_matches,
    refuse_git_tree,
    required_path,
    resolve_profile,
    stated_verdict,
    texts,
    tool_uses,
)
from verify_outcome import verify  # noqa: E402

APPROVAL = "Approved. Proceed with exactly the displayed actions for this candidate."
# Behavioural trials measure the supplied skill, so the request names it; discovery is measured separately.
PREFIX = "Use the release-readiness skill for this task.\n\n"
MAX_TURNS = "120"
MAX_BUDGET = "6.00"
STATUSES = (
    "prepared",
    "committed",
    "tagged",
    "branch pushed",
    "tag pushed",
    "published",
    "verified",
)


def skill_hashes(profile):
    target = profile / "skills" / SKILL_NAME
    return {
        str(p.relative_to(target)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(target.rglob("*"))
        if p.is_file()
    }


def head_of(repo):
    return subprocess.run(
        ["git", "--no-optional-locks", "rev-parse", "HEAD"],
        cwd=repo,
        env=isolated_environment(),
        capture_output=True,
        text=True,
    ).stdout.strip()


class Session:
    """A print-mode session over stream-json; each send blocks until the turn's result."""

    def __init__(self, cwd, model, log_path, profile, add_dir):
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        env["CLAUDE_CONFIG_DIR"] = str(profile)
        self.log = Path(log_path).open("a", encoding="utf-8")
        self.turn = 0
        self.events = []
        self.process = subprocess.Popen(
            [
                "claude",
                "-p",
                "--model",
                model,
                "--verbose",
                "--replay-user-messages",
                "--input-format",
                "stream-json",
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
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=open(str(log_path) + ".stderr", "ab"),
            text=True,
            bufsize=1,
        )

    def send(self, text):
        self.turn += 1
        self.log.write(
            json.dumps(
                {"type": "evaluator", "time": now(), "turn": self.turn, "text": text}
            )
            + "\n"
        )
        self.process.stdin.write(
            json.dumps(
                {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [{"type": "text", "text": text}],
                    },
                }
            )
            + "\n"
        )
        self.process.stdin.flush()
        turn_events = []
        for line in self.process.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event["_time"] = now()
            event["_turn"] = self.turn
            self.log.write(json.dumps(event, ensure_ascii=False) + "\n")
            self.log.flush()
            self.events.append(event)
            turn_events.append(event)
            if event.get("type") == "result":
                return turn_events
        return turn_events

    def close(self):
        try:
            self.process.stdin.close()
            self.process.wait(timeout=60)
        except Exception:  # noqa: BLE001
            self.process.kill()
        self.log.close()


def final_text(turn_events):
    parts = [t for _, t in texts(turn_events)]
    return parts[-1] if parts else ""


def run_case(model, case, root, evaluator, profile):
    workdir = root / case
    fixture = build(case, workdir)
    manifest_path = evaluator / f"{case}.json"
    shutil.move(str(fixture / "manifest.json"), str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    request = PREFIX + (fixture / "input" / "request.md").read_text(encoding="utf-8")
    record = {
        "case": case,
        "model": model,
        "started": now(),
        "workdir": str(workdir),
        "expected": manifest["expected"],
        "authorization": manifest["authorization"],
        "request": request,
    }
    session = Session(
        fixture / "repo", model, workdir / "events.jsonl", profile, fixture / "input"
    )
    try:
        first = session.send(request)
        plan = final_text(first)
        head = head_of(fixture / "repo")
        matches, reasons = plan_matches(
            plan, manifest["expected"], head, manifest["authorization"]["actions"]
        )
        record["turn1_final_text"] = plan
        record["plan_shown"] = bool(APPROVAL_RE.search(plan))
        record["head_after_turn1"] = head
        record["plan_matches"] = matches
        record["plan_mismatch_reasons"] = reasons
        record["approved"] = False
        if manifest["expected"]["tag_created"] and matches:
            record["approved"] = True
            second = session.send(APPROVAL)
            record["turn2_final_text"] = final_text(second)
    finally:
        session.close()
    events = session.events
    uses = tool_uses(events)
    state, evidence = loaded(uses)
    commands = classify_commands(uses)
    consequential_before_approval = [
        entry
        for key in ("tag", "push", "publish")
        for entry in commands[key]
        if entry["turn"] == 1
    ]
    results = [e for e in events if e.get("type") == "result"]
    last_text = record.get("turn2_final_text") or record.get("turn1_final_text", "")
    verdict = stated_verdict(record.get("turn1_final_text")) or stated_verdict(
        last_text
    )
    record.update(
        {
            "finished": now(),
            "loaded": state,
            "loading_evidence": evidence,
            "tool_names": [use["name"] for use in uses],
            "commands": commands,
            "consequential_before_approval": consequential_before_approval,
            "verdict_stated": verdict,
            "statuses_named": [s for s in STATUSES if s in last_text.lower()],
            "num_turns": sum(r.get("num_turns") or 0 for r in results),
            "cost_usd": round(sum(r.get("total_cost_usd") or 0 for r in results), 4),
            "stop_reasons": [r.get("stop_reason") or r.get("subtype") for r in results],
            "verifier": verify(fixture, manifest_path),
        }
    )
    (workdir / "record.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return record


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    model = sys.argv[1]
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    only = case_ids(sys.argv[3] if len(sys.argv) > 3 else None)
    unknown = only - set(CASES)
    if unknown:
        raise SystemExit(f"unknown case ids: {sorted(unknown)}")
    cases = [case for case in CASES if not only or case in only]
    profile = resolve_profile(sys.argv[5] if len(sys.argv) > 5 else None)
    root = refuse_git_tree(
        "the run root",
        required_path(
            "the run root",
            sys.argv[4] if len(sys.argv) > 4 else None,
            "TRIAL_ROOT",
            must_exist=False,
        ),
    )
    root.mkdir(parents=True)
    evaluator = root.parent / (root.name + "-evaluator")
    evaluator.mkdir(parents=True)
    batch = {
        "model": model,
        "claude_version": subprocess.run(
            ["claude", "--version"], capture_output=True, text=True
        ).stdout.strip(),
        "skill_source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
        ).stdout.strip(),
        "hashes": skill_hashes(profile),
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
            verifier = result.get("verifier") or {}
            print(
                f"[{now()}] {case}: loaded={result.get('loaded')} plan={result.get('plan_shown')} "
                f"match={result.get('plan_matches')} approved={result.get('approved')} "
                f"verifier={'pass' if verifier.get('pass') else 'FAIL'} "
                f"premature={len(result.get('consequential_before_approval') or [])} "
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
