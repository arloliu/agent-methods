"""Aggregate discovery results per class, and print the material for manual record/load judgements."""

import json
import sys
from collections import Counter, defaultdict


def main(path):
    results = json.load(open(path))
    by_class = defaultdict(Counter)
    rows = []
    for r in sorted(results, key=lambda r: (r.get("case", ""), r.get("rep", 0))):
        if "error" in r:
            rows.append((r["case"], r["rep"], "ERROR", r["error"]))
            continue
        expected, loaded = r["expected"], r["loaded"]
        if expected == "load":
            verdict = "pass" if loaded == "complete" else "fail"
        elif expected == "skip":
            verdict = "pass" if loaded == "not-loaded" else "fail"
        else:  # record: body must not load; fields judged manually
            verdict = (
                "over-trigger" if loaded == "complete" else "not-loaded(judge fields)"
            )
        by_class[(r["class"], expected)][verdict] += 1
        rows.append(
            (
                r["case"],
                r["rep"],
                verdict,
                f"loaded={loaded} tools={','.join(r['tool_names'])} stops={len(r['stop_calls'])} denials={len(r['denials'])} catalog={r['catalog_has_skill']}",
            )
        )
    for row in rows:
        print(f"{row[0]:<12} rep{row[1]} {row[2]:<22} {row[3]}")
    print("\n== counts by class (expected) ==")
    for key, counter in sorted(by_class.items()):
        total = sum(counter.values())
        print(f"{key[0]:<22} expected={key[1]:<7} n={total:<3} {dict(counter)}")
    if len(sys.argv) > 2 and sys.argv[2] == "detail":
        for r in sorted(results, key=lambda r: (r.get("case", ""), r.get("rep", 0))):
            if r.get("expected") == "record" or (
                r.get("expected") == "load" and r.get("loaded") == "complete"
            ):
                print(f"\n##### {r['case']} rep{r['rep']} loaded={r['loaded']}")
                for launch in r["launches"]:
                    print("LAUNCH:", json.dumps(launch, ensure_ascii=False)[:300])
                print("TOOLS:", r["tool_names"])
                print("STOPS:", r["stop_calls"])
                print("TEXT:", r["final_text"][:1200])


if __name__ == "__main__":
    main(sys.argv[1])
