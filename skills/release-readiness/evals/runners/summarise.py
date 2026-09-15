"""Print per-case tables for a trial or discovery batch, from results.json or a reduced summary.

Usage: summarise.py <results.json | runs/<batch>.json> [detail]
"""

import json
import sys
from collections import Counter


def load(path):
    data = json.load(open(path))
    return data["results"] if isinstance(data, dict) else data


def discovery(results, detail):
    counts = Counter()
    for r in sorted(results, key=lambda r: (r["case"], int(r.get("rep", 0)))):
        if "error" in r:
            print(f"{r['case']:<20} rep{r.get('rep')} ERROR {r['error']}")
            counts[("error", "error")] += 1
            continue
        verdict = (
            "pass"
            if (r["loaded"] == "complete") == (r["expected"] == "load")
            else "fail"
        )
        unsolicited = sorted(r.get("consequential_commands") or {})
        counts[(r["expected"], verdict)] += 1
        print(
            f"{r['case']:<20} rep{r['rep']} {verdict:<5} loaded={r['loaded']:<11} "
            f"tools={len(r['tool_names'])} consequential={unsolicited} cost={r.get('cost_usd')}"
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
            print(f"{r['case']:<22} ERROR {r['error']}")
            continue
        v = r.get("verifier") or {}
        failing = sorted(k for k, c in (v.get("checks") or {}).items() if not c["pass"])
        total += r.get("cost_usd") or 0
        print(
            f"{r['case']:<22} loaded={r['loaded']:<11} plan={str(r['plan_shown']):<5} "
            f"match={str(r['plan_matches']):<5} approved={str(r['approved']):<5} "
            f"verdict={str(r.get('verdict_stated')):<9} verifier={'pass' if v.get('pass') else 'FAIL'} "
            f"premature={len(r.get('consequential_before_approval') or [])} "
            f"checks={len((r.get('commands') or {}).get('check') or [])} "
            f"statuses={len(r.get('statuses_named') or [])} cost={r.get('cost_usd')}"
        )
        if failing:
            print("    failing:", failing)
        if r.get("plan_mismatch_reasons") and not r["plan_matches"]:
            print("    mismatch:", r["plan_mismatch_reasons"])
        if detail:
            print(
                "    T1:", (r.get("turn1_final_text") or "")[:600].replace("\n", " | ")
            )
            if r.get("turn2_final_text"):
                print("    T2:", r["turn2_final_text"][:600].replace("\n", " | "))
    print(f"\ntotal cost USD {total:.2f}")


def main():
    results = load(sys.argv[1])
    detail = len(sys.argv) > 2 and sys.argv[2] == "detail"
    if results and "verifier" in results[0] or any("plan_shown" in r for r in results):
        trial(results, detail)
    else:
        discovery(results, detail)


if __name__ == "__main__":
    main()
