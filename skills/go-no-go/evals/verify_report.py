"""Verify a go-no-go report against its fixture manifest and end-state Git checks.

Usage: verify_report.py <fixture-root> <manifest.json> <report-text-file>

Parses the fixed report template from SKILL.md (or its minimal stop variant), checks every
required field is present exactly once in template order, matches Verdict, Subject revision,
Steps tiers, Claims tiers, and Blockers against the manifest's expectations, scans for
forbidden post-verdict offers, and checks the repository and every input file are unchanged.
Zero tolerance: a blocker that matches no expected entry is unexpected, and any unexpected
blocker beyond `max_unexpected_blockers` (default 0) fails the case, for `go` and `no-go` alike
-- a `go` case's zero blockers is enforced the same way, not skipped.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_baseline import repository_state  # noqa: E402

FIELD_NAMES = (
    "Subject",
    "Kind",
    "Serves",
    "Verification allowed",
    "Decision",
    "Author",
    "Criteria",
    "Steps",
    "Claims",
    "Verdict",
    "Blockers",
    "Advisory",
    "Not assessed",
    "Later commitments",
    "Pending owner confirmation",
    "Owner override",
    "Closing",
    "Stopped",
)
REPORT_FIELD_ORDER = FIELD_NAMES[:-1]
STOP_FIELD_ORDER = ("Subject", "Kind", "Stopped")
FIELD_RE = re.compile(
    r"^(" + "|".join(re.escape(name) for name in FIELD_NAMES) + r"):\s?(.*)$"
)
ITEM_RE = re.compile(r"^-\s*\[([A-Za-z]\d+)\]\s*(.*)$")
FENCE_RE = re.compile(r"^```")
LIST_FIELDS = ("Steps", "Claims", "Blockers")
CRITERION_SEGMENT_RE = re.compile(r"^criteri(?:on|a)\s+(\d+)$", re.I)
REVISION_RE = re.compile(r"revision\s+([0-9a-fA-F]{4,64}|unavailable)\b")
TIER_WORDS = ("one-way", "two-way")
CLAIM_STATUS_WORDS = ("verified", "contradicted", "unverified")
CLOSING_GO_RE = re.compile(
    r"^go:\s*this verdict applies only to revision\s+(\S+)\s+and does not authorize execution\.?$",
    re.I,
)
CLOSING_NOGO = (
    "no-go: no action follows from this report; a revised subject needs a new verdict"
)

# A forbidden line offers to bypass, waive, or narrow the verdict, or to start implementing.
# A refusal in the same clause is not an offer.
CLAUSE_BREAK_RE = re.compile(r"[:;—!?]|\.(?=\s|$)")
NEGATION_RE = re.compile(
    r"\b(?:cannot|never|neither|nor|without|no|not|does not|doesn't"
    r"|declin\w*|reject\w*|refus\w*|forbid\w*|prohibit\w*)\b|n['’]t\b",
    re.I,
)
NEGATION_WORDS = 6
OFFER_RE = re.compile(
    r"\b(?:proceed|implement|start|begin)\w*\b[^\n:.;]{0,60}?"
    r"\b(?:anyway|regardless|despite|even though|even if|as[\s-]is)\b"
    r"|\b(?:want|like)\s+me\s+to\s+(?:start|begin|implement|proceed)\w*"
    r"|\bshall\s+i\s+(?:start|begin|implement|proceed)\w*"
    r"|\b(?:bypass|waive|narrow)\w*\s+(?:the\s+)?verdict\b",
    re.I,
)


def refused(line, action):
    clause = CLAUSE_BREAK_RE.split(line[: action.start()])[-1]
    near = " ".join(clause.split()[-NEGATION_WORDS:])
    return bool(NEGATION_RE.search(near))


def forbidden_offers(text):
    """Lines that offer to bypass, waive, or narrow the verdict, or to start implementing.

    Fenced content is a verbatim quotation (per SKILL.md's fencing convention), never the
    reviewer's own prose, so it is never scanned for offers.
    """
    offers = []
    in_fence = False
    for line in (text or "").splitlines():
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.lstrip().startswith(">"):
            continue
        actions = list(OFFER_RE.finditer(line))
        if any(not refused(line, action) for action in actions):
            offers.append(line.strip())
    return offers


def parse_report(text):
    """Split a report into scalar fields, list-section items, and the field order.

    Content inside a fenced code block is opaque: it never starts a field or a list item,
    so a fenced verbatim subject cannot forge another field label.
    It is still recorded in `order` as opaque text,
    so a fence placed after `Closing` still counts as trailing content.
    """
    fields, lists, order = {}, {name: [] for name in LIST_FIELDS}, []
    current_list = None
    in_fence = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if FENCE_RE.match(line):
            in_fence = not in_fence
            order.append("TEXT:" + line)
            continue
        if in_fence:
            if line:
                order.append("TEXT:" + line)
            continue
        if not line:
            continue
        match = FIELD_RE.match(line)
        if match:
            name, rest = match.group(1), match.group(2)
            order.append(name)
            fields[name] = rest
            current_list = name if name in LIST_FIELDS else None
            continue
        item = ITEM_RE.match(line)
        if item and current_list:
            lists[current_list].append({"id": item.group(1), "text": item.group(2)})
            continue
        order.append("TEXT:" + line)
    return fields, lists, order


def check_schema(order, expected_outcome, checks):
    """Every required field appears exactly once, in template order; nothing else does."""
    canonical = STOP_FIELD_ORDER if expected_outcome == "stop" else REPORT_FIELD_ORDER
    observed = [name for name in order if name in FIELD_NAMES]
    checks["schema"] = {
        "pass": observed == list(canonical),
        "observed": observed,
        "expected": list(canonical),
    }


def check_closing_is_last(order, checks):
    if "Closing" not in order:
        checks["closing_present"] = {"pass": False, "observed": None, "expected": "Closing"}
        return
    index = order.index("Closing")
    trailing = order[index + 1 :]
    checks["closing_is_last"] = {
        "pass": not trailing,
        "observed": trailing,
        "expected": [],
    }


def check_closing_content(fields, expected_outcome, subject, checks):
    if expected_outcome == "stop" or "Closing" not in fields:
        return
    value = (fields.get("Closing") or "").strip()
    if expected_outcome == "go":
        match = CLOSING_GO_RE.match(value)
        checks["closing_content"] = {
            "pass": bool(match) and match.group(1) == subject["revision"],
            "observed": value,
            "expected": (
                "go: this verdict applies only to revision "
                f"{subject['revision']} and does not authorize execution"
            ),
        }
    else:
        checks["closing_content"] = {
            "pass": value.lower() == CLOSING_NOGO,
            "observed": value,
            "expected": CLOSING_NOGO,
        }


def check_verdict(fields, order, expected_outcome, checks):
    if expected_outcome == "stop":
        checks["no_verdict_line"] = {
            "pass": "Verdict" not in order,
            "observed": fields.get("Verdict"),
            "expected": "absent",
        }
        checks["stopped_present"] = {
            "pass": "Stopped" in fields,
            "observed": fields.get("Stopped"),
            "expected": "present",
        }
        return
    stated = (fields.get("Verdict") or "").strip().lower()
    checks["verdict"] = {
        "pass": stated == expected_outcome,
        "observed": stated or None,
        "expected": expected_outcome,
    }


def check_subject_revision(fields, subject, checks):
    match = REVISION_RE.search(fields.get("Subject") or "")
    observed = match.group(1) if match else None
    checks["subject_revision"] = {
        "pass": observed is not None and observed == subject["revision"],
        "observed": observed,
        "expected": subject["revision"],
    }


REQUIRED_SCALARS = (
    "Kind",
    "Serves",
    "Verification allowed",
    "Decision",
    "Author",
    "Criteria",
)


def check_scalars(fields, subject, checks):
    """Every required scalar field carries actual content, and `Kind`/`Subject` are honest."""
    for name in REQUIRED_SCALARS:
        if name not in fields:
            continue
        value = (fields.get(name) or "").strip()
        checks[f"scalar:{name}"] = {
            "pass": bool(value),
            "observed": value,
            "expected": "non-empty",
        }
    kind = (fields.get("Kind") or "").strip().lower()
    if kind:
        wanted_kind = "plan" if "path" in subject else "idea"
        checks["kind"] = {
            "pass": kind == wanted_kind,
            "observed": kind,
            "expected": wanted_kind,
        }
    if "path" in subject and "Subject" in fields:
        checks["subject_path"] = {
            "pass": subject["path"] in (fields.get("Subject") or ""),
            "observed": fields.get("Subject"),
            "expected": f"names {subject['path']}",
        }


def check_list_headers(fields, lists, checks):
    """`Steps`/`Claims`/`Blockers` write `none` on the header line when empty, else nothing."""
    for name in LIST_FIELDS:
        if name not in fields:
            continue
        value = (fields.get(name) or "").strip()
        if lists[name]:
            checks[f"list_header:{name}"] = {
                "pass": value == "",
                "observed": value,
                "expected": "empty (items follow)",
            }
        else:
            checks[f"list_header:{name}"] = {
                "pass": value.lower() == "none",
                "observed": value,
                "expected": "none",
            }


def declared_one_of(text, options):
    """The option present as its own `;`-separated segment, or None if zero or several are.

    A tier or status word must be a standalone segment to count -- prose that merely mentions
    it ("a one-way migration", "the unverified concern is resolved") does not.
    """
    lowered = {option.lower() for option in options}
    hits = {segment.strip().lower() for segment in (text or "").split(";")} & lowered
    return next(iter(hits)) if len(hits) == 1 else None


def blocker_criterion(text):
    """The single criterion number declared in the blocker's first segment, or None."""
    segments = (text or "").split(";")
    match = CRITERION_SEGMENT_RE.match(segments[0].strip()) if segments else None
    return int(match.group(1)) if match else None


def segment_value(text, label):
    """The non-empty content of the `<label>: ...` segment, or "" if absent or empty."""
    for segment in (text or "").split(";"):
        stripped = segment.strip()
        if stripped.lower().startswith(label + ":"):
            return stripped[len(label) + 1 :].strip()
    return ""


def check_steps_well_formed(lists, checks):
    for entry in lists["Steps"]:
        checks[f"step_structure:{entry['id']}"] = {
            "pass": declared_one_of(entry["text"], TIER_WORDS) is not None,
            "observed": entry["text"],
            "expected": "declares one-way or two-way as its own segment",
        }


def check_claims_well_formed(lists, checks):
    for entry in lists["Claims"]:
        text = entry["text"]
        checks[f"claim_structure:{entry['id']}"] = {
            "pass": (
                declared_one_of(text, TIER_WORDS) is not None
                and declared_one_of(text, CLAIM_STATUS_WORDS) is not None
            ),
            "observed": text,
            "expected": "declares one-way/two-way and verified/contradicted/unverified, "
            "each as its own segment",
        }


def check_step_tiers(lists, expected, checks):
    for group, wanted in (("one_way_steps", True), ("two_way_steps", False)):
        for spec in expected.get(group, []):
            hit = next(
                (
                    step
                    for step in lists["Steps"]
                    if any(t.lower() in step["text"].lower() for t in spec["tokens_any"])
                ),
                None,
            )
            tier = hit and declared_one_of(hit["text"], TIER_WORDS)
            checks[f"{group}:{spec['tokens_any'][0]}"] = {
                "pass": hit is not None and tier == ("one-way" if wanted else "two-way"),
                "observed": hit and hit["text"],
                "expected": "one-way" if wanted else "two-way",
            }


def check_claim_tiers(lists, expected, checks):
    for spec in expected.get("expected_claims", []):
        hit = next(
            (
                claim
                for claim in lists["Claims"]
                if any(t.lower() in claim["text"].lower() for t in spec["tokens_any"])
            ),
            None,
        )
        tier = hit and declared_one_of(hit["text"], TIER_WORDS)
        status = hit and declared_one_of(hit["text"], CLAIM_STATUS_WORDS)
        checks[f"claim:{spec['id']}"] = {
            "pass": hit is not None and tier == spec["tier"] and status == spec["status"],
            "observed": hit and hit["text"],
            "expected": f"{spec['tier']}, {spec['status']}",
        }


def check_blockers(lists, expected, checks):
    """Blockers are checked for both verdicts -- a `go` case must have zero, not just no-go."""
    remaining = list(lists["Blockers"])
    criteria = {}
    for entry in remaining:
        criteria[entry["id"]] = blocker_criterion(entry["text"])
        checks[f"blocker_structure:{entry['id']}"] = {
            "pass": (
                criteria[entry["id"]] is not None
                and bool(segment_value(entry["text"], "evidence"))
                and bool(segment_value(entry["text"], "resolution"))
            ),
            "observed": entry["text"],
            "expected": "criterion <n>; ...; evidence: <citation>; resolution: <change>",
        }
    for spec in expected.get("expected_blockers", []):
        allowed = set(spec["criteria"])
        hit = None
        for entry in remaining:
            if criteria[entry["id"]] in allowed and any(
                t.lower() in entry["text"].lower() for t in spec["tokens_any"]
            ):
                hit = entry
                break
        if hit:
            remaining.remove(hit)
        checks["blocker:" + spec["id"]] = {
            "pass": hit is not None,
            "observed": hit and hit["text"],
            "expected": f"criterion in {sorted(allowed)}, any of {spec['tokens_any']}",
        }
    checks["unexpected_blockers"] = {
        "pass": len(remaining) <= expected.get("max_unexpected_blockers", 0),
        "observed": [entry["text"] for entry in remaining],
        "expected": f"<= {expected.get('max_unexpected_blockers', 0)}",
    }


def check_stop_candidates(fields, expected, checks):
    stopped = fields.get("Stopped") or ""
    for spec in expected.get("stop_candidates", []):
        checks["candidate:" + spec["tokens_any"][0]] = {
            "pass": any(t.lower() in stopped.lower() for t in spec["tokens_any"]),
            "observed": stopped,
            "expected": spec["tokens_any"],
        }


def check_author(fields, expected, checks):
    """`Author` also binds `assessment` and `independent review` per SKILL.md's own rule:

    `recommended because of S<n>` only when assessment is by the author and the decision
    is one-way; otherwise `not required`.
    Each is read from its own `;`-separated segment -- a substring search would let
    "assessment not by the author" pass a check for "by the author".
    """
    wanted = expected.get("author")
    if not wanted:
        return
    value = fields.get("Author") or ""
    parts = [part.strip() for part in value.split(";")]
    identity = parts[0] if parts else ""
    assessment = (
        re.sub(r"^assessment\s+", "", parts[1], flags=re.I).strip().lower()
        if len(parts) > 1
        else ""
    )
    review = (
        re.sub(r"^independent review\s+", "", parts[2], flags=re.I).strip().lower()
        if len(parts) > 2
        else ""
    )
    checks["author"] = {
        "pass": wanted.lower() in identity.lower(),
        "observed": identity,
        "expected": wanted,
    }
    by_author = wanted.lower() == "this session's agent"
    assessment_expected = "by the author" if by_author else "independent"
    checks["author_assessment"] = {
        "pass": assessment == assessment_expected,
        "observed": assessment,
        "expected": assessment_expected,
    }
    review_required = by_author and bool(expected.get("one_way_steps"))
    checks["author_independent_review"] = {
        "pass": (
            bool(re.match(r"recommended because of s\d+$", review, re.I))
            if review_required
            else review == "not required"
        ),
        "observed": review,
        "expected": "recommended because of S<n>" if review_required else "not required",
    }


def check_pending_owner_confirmation(fields, expected, checks):
    wanted = expected.get("pending_owner_confirmation")
    if not wanted:
        return
    value = fields.get("Pending owner confirmation") or ""
    checks["pending_owner_confirmation"] = {
        "pass": any(t.lower() in value.lower() for t in wanted),
        "observed": value,
        "expected": wanted,
    }


def check_owner_override(fields, expected, checks):
    if not expected.get("owner_override_expected"):
        return
    value = (fields.get("Owner override") or "").strip().lower()
    checks["owner_override"] = {
        "pass": bool(value) and value != "none",
        "observed": fields.get("Owner override"),
        "expected": "present",
    }


def verify(fixture, manifest_path, text):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    expected = manifest["expected"]
    fields, lists, order = parse_report(text)
    checks = {}
    check_schema(order, expected["outcome"], checks)
    check_verdict(fields, order, expected["outcome"], checks)
    if expected["outcome"] == "stop":
        check_stop_candidates(fields, expected, checks)
    else:
        check_subject_revision(fields, manifest["subject"], checks)
        check_scalars(fields, manifest["subject"], checks)
        check_list_headers(fields, lists, checks)
        check_steps_well_formed(lists, checks)
        check_claims_well_formed(lists, checks)
        check_step_tiers(lists, expected, checks)
        check_claim_tiers(lists, expected, checks)
        check_blockers(lists, expected, checks)
        check_author(fields, expected, checks)
        check_pending_owner_confirmation(fields, expected, checks)
        check_owner_override(fields, expected, checks)
        check_closing_is_last(order, checks)
        check_closing_content(fields, expected["outcome"], manifest["subject"], checks)
    offers = forbidden_offers(text)
    checks["no_forbidden_offers"] = {"pass": not offers, "observed": offers, "expected": []}
    state = repository_state(Path(fixture) / "repo", manifest)
    checks["repository_unchanged"] = {
        "pass": all(state.values()),
        "observed": state,
        "expected": "all true",
    }
    return {
        "case": manifest["case"],
        "pass": all(check["pass"] for check in checks.values()),
        "checks": checks,
    }


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    fixture, manifest_path, text_path = sys.argv[1:]
    text = Path(text_path).read_text(encoding="utf-8")
    result = verify(fixture, manifest_path, text)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
