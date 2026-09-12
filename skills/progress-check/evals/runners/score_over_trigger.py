"""Score discovery `record` runs for the two over-trigger signals in evals/discovery.md.

Over-trigger means the agent did work nobody asked for.  It is detected as two
independent signals and reported as two numbers.

Signal 1, report structures: the response carries one of the skill's own report
structures -- the scope ledger, the inventory table, the candidate table, the
proposal closing block, or the final report block.  The block field labels are
taken from ``verifier.py``; the two tables are matched on their fixed columns.

Signal 2, unsolicited check: the run enumerated or probed for work it did not
itself start.  A probe whose target is something the same run launched does not
count.  A bare enumeration that returns nothing and is never mentioned in the
response does not count either.

Usage: score_over_trigger.py <run-root> [<run-root> ...]

Each run root holds ``results.json`` and one ``<case>-<rep>/events.jsonl`` per run.
Both host event formats are read: Claude Code stream-json and Antigravity NDJSON.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import verifier  # noqa: E402

BLOCK_FIELDS = sorted(
    {name for name, _, _ in verifier.PROPOSAL_FIELDS}
    | {name for name, _, _ in verifier.FINAL_FIELDS}
)
BLOCK_RE = re.compile(
    r"^[-*>|\s]*(" + "|".join(re.escape(f) for f in BLOCK_FIELDS) + r")\s*[:?]",
    re.MULTILINE,
)
INVENTORY_RE = re.compile(r"\|[^\n]*\bOwnership\b[^\n]*\bLifecycle\b[^\n]*\|", re.I)
CANDIDATE_RE = re.compile(r"\|[^\n]*\bOperation\b[^\n]*\bMechanism\b[^\n]*\|", re.I)
LEDGER_RE = re.compile(
    r"\b(done-verified|done-claimed|in-progress|blocked|pending|dropped)\b"
)
# A single block label can appear in ordinary prose; the block is a set of them.
BLOCK_MINIMUM = 3

# Host tools that enumerate or report on background work.
PROBE_TOOLS = {
    # Claude Code
    "TaskList",
    "TaskGet",
    "TaskOutput",
    "TaskStatus",
    "ListAgents",
    "CronList",
    "Monitor",
    "BashOutput",
    # Antigravity CLI
    "manage_task",
    "manage_subagents",
    "command_status",
    "list_tasks",
}
# Shell enumerations of processes, jobs, or a host task directory.
PROBE_SHELL_RE = re.compile(
    r"(?<![\w/-])(ps|pgrep|pidof|pstree|jobs|top|htop|lsof|systemctl\s+status|"
    r"docker\s+ps|screen\s+-ls|tmux\s+ls)(?![\w-])"
)
EMPTY_RE = re.compile(
    r"\A(?:\[\]|\{\}|none|(?:\w+\s+)?no (?:tasks|subagents|agents|jobs|processes|"
    r"results|matching|background [\w ]+)[^\n]*)\Z",
    re.I | re.S,
)
MENTION_RE = re.compile(r"\b(background|running|subagent|process|task|job|pid)\b", re.I)
# A probe naming one identifier is aimed at a specific item.  Every discovery run
# starts a fresh session with nothing running, so such an item is always its own;
# only an untargeted enumeration can reach work the run did not start.
TARGETED_RE = re.compile(
    r"task-\d+|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|"
    r'"(?:bash_id|shell_id|TaskId|task_id|id)"\s*:\s*"[^"]+"',
    re.I,
)


def read_events(run_dir):
    """Yield (tool name, parameters blob, result text) for every tool call in a run."""
    path = Path(run_dir) / "events.jsonl"
    if not path.exists():
        return []
    calls, results, order = {}, {}, []
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        for part in content if isinstance(content, list) else ():
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_use":
                calls[part.get("id")] = (
                    part.get("name"),
                    json.dumps(part.get("input"), ensure_ascii=False),
                )
                order.append(part.get("id"))
            elif part.get("type") == "tool_result":
                body = part.get("content")
                if isinstance(body, list):
                    body = " ".join(
                        p.get("text", "") for p in body if isinstance(p, dict)
                    )
                results[part.get("tool_use_id")] = str(body or "")
        update = event.get("step_update")
        if isinstance(update, dict) and update.get("step_type") == "tool":
            key = f"{update.get('conversation_id')}#{update.get('step_index')}"
            info = update.get("tool_info") or {}
            if key not in calls:
                order.append(key)
            calls[key] = (
                update.get("tool_name"),
                json.dumps(info.get("parameters"), ensure_ascii=False),
            )
            if update.get("state") == "DONE":
                results[key] = str(info.get("result") or update.get("output") or "")
    return [
        (*calls[key], results.get(key)) for key in dict.fromkeys(order) if key in calls
    ]


def own_tokens(result, calls):
    """Identifiers of what this run started: its scripts, PIDs, and host task IDs."""
    tokens = set()
    blobs = [json.dumps(result.get("launches") or [], ensure_ascii=False)]
    blobs += [params for name, params, _ in calls if name in ("Bash", "run_command")]
    for blob in blobs:
        tokens.update(re.findall(r"[\w.-]+\.py", blob))
        tokens.update(re.findall(r"\btask-\d+\b", blob))
    return tokens


def structures(text):
    """Report structures present in the response, as a list of labels."""
    hits = []
    fields = sorted(set(BLOCK_RE.findall(text)))
    if len(fields) >= BLOCK_MINIMUM:
        hits.append("report block (" + ", ".join(fields) + ")")
    if INVENTORY_RE.search(text):
        hits.append("inventory table")
    if CANDIDATE_RE.search(text):
        hits.append("candidate table")
    if len(set(LEDGER_RE.findall(text))) >= 2:
        hits.append("scope ledger")
    return hits


def unsolicited_checks(result, calls):
    """Probes for work this run did not start, as a list of (kind, detail, why)."""
    text = result.get("final_text") or ""
    mine = own_tokens(result, calls)
    hits = []
    for name, params, output in calls:
        if name in PROBE_TOOLS:
            kind, detail = "tool", f"{name} {params}"
        elif name in ("Bash", "run_command") and PROBE_SHELL_RE.search(params):
            kind, detail = "shell", params
        else:
            continue
        if any(token in params for token in mine) or TARGETED_RE.search(params):
            continue  # a probe aimed at this run's own launch
        empty = output is not None and bool(EMPTY_RE.match(output.strip()))
        mentioned = bool(MENTION_RE.search(text))
        if empty and not mentioned:
            continue  # a bare enumeration that found nothing and was never mentioned
        hits.append(
            (kind, detail[:160], "mentioned" if mentioned else "returned output")
        )
    return hits


def main(roots):
    print(f"{'case':<12} {'rep':<5} {'body-load':<12} structures / unsolicited checks")
    for root in roots:
        root = Path(root)
        results = json.load(open(root / "results.json"))
        record = [r for r in results if r.get("expected") == "record"]
        loads = structs = probes = 0
        print(f"\n===== {root.name}: {len(record)} record runs =====")
        for result in sorted(
            record, key=lambda r: (r.get("case", ""), int(r.get("rep", 0)))
        ):
            run_dir = root / f"{result['case']}-{result['rep']}"
            calls = read_events(run_dir)
            found = structures(result.get("final_text") or "")
            checks = unsolicited_checks(result, calls)
            loads += result.get("loaded") == "complete"
            structs += bool(found)
            probes += bool(checks)
            print(
                f"{result['case']:<12} rep{result['rep']:<4} {result.get('loaded'):<12} "
                f"{'; '.join(found) or '-'} | {'; '.join(f'{k}: {d} ({w})' for k, d, w in checks) or '-'}"
            )
        print(
            f"-- totals: body-load {loads}/{len(record)}, "
            f"report structures {structs}/{len(record)}, "
            f"unsolicited checks {probes}/{len(record)}"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
