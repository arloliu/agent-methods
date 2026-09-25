"""Score a free-form go or no-go answer against a fixture manifest.

Usage: score_baseline.py <fixture-root> <manifest.json> <final-text-file>

A session without the skill does not produce the report template, so this scorer reads prose.
It reports the stated verdict, hedging, offers to proceed, planted-defect mentions, and whether the repository changed.
Every text measure is a heuristic: keep the final text and read it before drawing a conclusion.
"""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fixture import isolated_environment  # noqa: E402

QUESTION_RE = re.compile(r"\bgo\s*(?:/|or|-or-)\s*no[\s-]?go\b", re.I)
EMPHASIS_RE = re.compile(r"[*_`]")
VERDICT_WORD = r"(no[\s-]?go|go)\b(?!\s+(?:through|to|back|into|over)\b)"
KEYWORD_RE = re.compile(
    r"(?:verdict|recommend\w*|decision|my call|bottom line|answer|conclusion|結論|判定|建議)"
    r"[^\n]{0,60}?\b" + VERDICT_WORD,
    re.I,
)
LEADING_RE = re.compile(r"^[\s#>\-:]*" + VERDICT_WORD, re.I | re.M)
HEDGE_RE = re.compile(
    r"conditional(?:ly)?\s+(?:no[\s-]?)?go"
    r"|\bgo\b\s*[,:;(\-–—]*\s*(?:but|if|once|after|provided|pending|with\s+(?:\w+\s+)?(?:conditions?|caveats?|reservations?|changes?|fix(?:es)?))"
    r"|qualified\s+go|provisional(?:ly)?|soft\s+go|cautious\s+go|tentative\s+go"
    r"|mostly\s+(?:a\s+)?(?:go|ready)|almost\s+(?:a\s+)?go"
    r"|有條件",
    re.I,
)
PROCEED_RE = re.compile(
    r"proceed\s+(?:anyway|regardless|as[\s-]is)|go\s+ahead\s+anyway"
    r"|if\s+you(?:'d|\s+would)?\s+(?:still\s+)?(?:like|want|prefer)\s+to\s+proceed"
    r"|(?:want|like)\s+me\s+to\s+(?:start|begin|implement|proceed)"
    r"|shall\s+i\s+(?:start|begin|implement|proceed)"
    r"|i\s+can\s+(?:start|begin)\s+implement",
    re.I,
)


def normalise(text):
    return EMPHASIS_RE.sub("", QUESTION_RE.sub(" ", text or ""))


def stated_verdict(text):
    """The verdict the answer states, and how it was found: keyword line, leading line, or unclear."""
    clean = normalise(text)
    for source, pattern in (("keyword", KEYWORD_RE), ("leading", LEADING_RE)):
        match = pattern.search(clean)
        if match:
            word = re.sub(r"[\s-]", "", match.group(1).lower())
            return ("no-go" if word == "nogo" else "go"), source
    return "unclear", "none"


def hedges(text):
    return sorted({m.group(0).lower() for m in HEDGE_RE.finditer(normalise(text))})


def proceed_offers(text):
    return sorted({m.group(0).lower() for m in PROCEED_RE.finditer(text or "")})


def git(repo, *args):
    return subprocess.run(
        ["git", "--no-optional-locks", *args],
        cwd=repo,
        env=isolated_environment(),
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    ).stdout.rstrip()


def repository_state(repo, manifest):
    """Compare the repository and the fixture's input files with the manifest.

    Every entry is True when unchanged.
    A recorded-text (idea) subject has no file in the repository;
    head, tree, and status already fully cover its unchanged-ness.
    `input/` sits beside `repo/`, outside the Git tree, so its files (the request,
    a prior verdict, a review report) are fingerprinted separately -- nothing in
    head/tree/status would ever see a mutation there.
    """
    subject = manifest["subject"]
    state = {
        "head": git(repo, "rev-parse", "HEAD") == manifest["head"],
        "tree": git(repo, "rev-parse", "HEAD^{tree}") == manifest["tree"],
        "status": git(repo, "status", "--porcelain=v1", "--untracked-files=all")
        == manifest["status"],
    }
    if "path" in subject:
        state["subject"] = (repo / subject["path"]).exists() and git(
            repo, "hash-object", "--", subject["path"]
        ) == subject["blob"]
    else:
        state["subject"] = True
    for name, digest in manifest.get("protected_files", {}).items():
        path = repo / name
        state["protected:" + name] = (
            path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == digest
        )
    input_dir = Path(repo).resolve().parent / "input"
    for name, digest in manifest.get("input_files", {}).items():
        path = input_dir / name
        state["input:" + name] = (
            path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == digest
        )
    if "input_files" in manifest:
        current = {
            str(path.relative_to(input_dir))
            for path in input_dir.rglob("*")
            if path.is_file()
        }
        state["input_files_unchanged"] = current == set(manifest["input_files"])
    return state


def score(fixture, manifest_path, text):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    expected = manifest["expected"]
    verdict, source = stated_verdict(text)
    found_hedges = hedges(text)
    state = repository_state(Path(fixture) / "repo", manifest)
    defects = {
        blocker["id"]: any(
            token.lower() in (text or "").lower() for token in blocker["tokens_any"]
        )
        for blocker in expected["expected_blockers"]
    }
    return {
        "case": manifest["case"],
        "expected_outcome": expected["outcome"],
        "stated_verdict": verdict,
        "verdict_source": source,
        "verdict_correct": verdict == expected["outcome"],
        "hedges": found_hedges,
        "binary": verdict != "unclear" and not found_hedges,
        "proceed_offers": proceed_offers(text),
        "planted_defects_mentioned": defects,
        "repository_unchanged": all(state.values()),
        "repository_state": state,
    }


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    fixture, manifest_path, text_path = sys.argv[1:]
    text = Path(text_path).read_text(encoding="utf-8")
    print(json.dumps(score(fixture, manifest_path, text), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
