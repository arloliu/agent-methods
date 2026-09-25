"""Print per-case tables for a go-no-go trial or discovery batch, from results.json or a reduced summary.

Usage: summarise.py <results.json | runs/<batch>.json> [detail]

Dispatches on the batch header's `arm` (`skill` -> trial table, absent -> discovery table),
never on the shape of the first result -- a batch whose first completed run errored, or a
baseline batch whose records carry neither `loaded` nor `verifier`, must not be misrouted.
"""

import json
import sys
from collections import Counter


def discovery(results, detail):
    counts = Counter()
    for r in sorted(results, key=lambda r: (r["case"], int(r.get("rep", 0)))):
        if "error" in r:
            print(f"{r['case']:<20} rep{r.get('rep')} ERROR {r['error']}")
            counts[("error", "error")] += 1
            continue
        if r.get("returncode"):
            print(f"{r['case']:<20} rep{r['rep']} CRASHED returncode={r['returncode']}")
            counts[(r["expected"], "crashed")] += 1
            continue
        verdict = (
            "pass"
            if (r["loaded"] == "complete") == (r["expected"] == "load")
            else "fail"
        )
        counts[(r["expected"], verdict)] += 1
        print(
            f"{r['case']:<20} rep{r['rep']} {verdict:<5} loaded={r['loaded']:<11} "
            f"tools={len(r['tool_names'])} cost={r.get('cost_usd')}"
        )
        if detail:
            print("   ", (r.get("final_text") or "")[:400].replace("\n", " | "))
    print("\n== counts (expected, verdict) ==")
    for key, n in sorted(counts.items()):
        print(f"{key[0]:<8} {key[1]:<6} {n}")


def trial(results, detail):
    total = 0.0
    for r in sorted(results, key=lambda r: r["case"]):
        if "error" in r:
            print(f"{r['case']:<26} ERROR {r['error']}")
            continue
        v = r.get("verifier") or {}
        failing = sorted(k for k, c in (v.get("checks") or {}).items() if not c["pass"])
        total += r.get("cost_usd") or 0
        print(
            f"{r['case']:<26} loaded={r['loaded']:<11} "
            f"verifier={'pass' if v.get('pass') else 'FAIL'} cost={r.get('cost_usd')}"
        )
        if failing:
            print("    failing:", failing)
        if detail:
            print("    text:", (r.get("final_text") or "")[:600].replace("\n", " | "))
    print(f"\ntotal cost USD {total:.2f}")


def main():
    path = sys.argv[1]
    data = json.load(open(path))
    results = data["results"] if isinstance(data, dict) else data
    detail = len(sys.argv) > 2 and sys.argv[2] == "detail"
    arm = data.get("arm") if isinstance(data, dict) else None
    if arm == "skill":
        trial(results, detail)
    elif arm == "baseline":
        raise SystemExit(
            f"{path}: this is a baseline batch; summarise.py only formats skill trial "
            "and discovery batches -- read score_baseline.py's per-record `score` fields directly"
        )
    else:
        discovery(results, detail)


if __name__ == "__main__":
    main()
