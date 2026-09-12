"""Semi-automatic checks for loaded positives and material for manual record-case judgement."""

import json
import re
import sys

# Both hosts: Claude Code first, then Antigravity CLI.
PROBE_TOOLS = {
    "TaskList",
    "TaskGet",
    "TaskOutput",
    "ListAgents",
    "CronList",
    "Monitor",
    "TaskStatus",
    "BashOutput",
    "manage_task",
    "manage_subagents",
    "command_status",
}
FIELD_PATTERNS = {
    "identity": r"(task id|task-id|task_id|\bid\b|\bpid\b|handle|`b[a-z0-9]{8}`|shell id|background id)",
    "purpose": r"(purpose|heartbeat|worker|why|for )",
    "expected end": r"(expected end|expected (to )?(finish|complete|run)|duration|until|deadline|~?\d+\s*(s|sec|seconds|min|minutes)|no (defined|fixed) end|indefinite|runs? (until|for))",
    "output": r"(output|\.output|log|written to|stdout)",
}


def main(path):
    results = json.load(open(path))
    print("== loaded positives: first-response behaviour ==")
    for r in sorted(results, key=lambda r: (r["case"], r["rep"])):
        if r.get("expected") != "load" or r.get("loaded") != "complete":
            continue
        tools = r["tool_names"]
        after = tools[tools.index("Skill") + 1 :] if "Skill" in tools else tools
        probe = any(t in PROBE_TOOLS for t in after) or any(t == "Bash" for t in after)
        text = r["final_text"]
        coverage = bool(
            re.search(
                r"(Coverage:|no background (work|tasks|processes|jobs)|enumeration boundary|nothing (is )?running|no (active|running) (background )?(tasks|work|processes))",
                text,
                re.I,
            )
        )
        print(
            f"{r['case']:<12} rep{r['rep']} probe={'yes' if probe else 'NO '} coverage_stmt={'yes' if coverage else 'NO '} stops={len(r['stop_calls'])} tools_after_skill={after}"
        )
    print("\n== record cases: launches and final text ==")
    for r in sorted(results, key=lambda r: (r["case"], r["rep"])):
        if r.get("expected") != "record":
            continue
        text = r["final_text"]
        fields = {k: bool(re.search(p, text, re.I)) for k, p in FIELD_PATTERNS.items()}
        print(
            f"\n##### {r['case']} rep{r['rep']} loaded={r['loaded']} fields(auto)={fields} denials={len(r['denials'])}"
        )
        for launch in r["launches"][:3]:
            print("  LAUNCH:", json.dumps(launch, ensure_ascii=False)[:220])
        print("  TEXT:", text[:700].replace("\n", " | "))


if __name__ == "__main__":
    main(sys.argv[1])
