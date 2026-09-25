"""Test the go-no-go deterministic report verifier against synthetic reports."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fixture import CASES, build  # noqa: E402
from verify_report import forbidden_offers, parse_report, verify  # noqa: E402


def synthesize(manifest):
    """Build a template-conformant report that should pass this manifest's own checks.

    This is a cross-check between a fixture's manifest and the verifier, not a claim
    that any real model would write this report.
    """
    expected = manifest["expected"]
    subject = manifest["subject"]
    revision = subject["revision"]
    if "path" in subject:
        subject_line = f"{subject['path']} at blob {revision}; revision {revision}"
        kind = "plan"
    else:
        subject_line = f"recorded text; revision {revision}"
        kind = "idea"
    lines = [
        f"Subject: {subject_line}",
        f"Kind: {kind}",
    ]
    if expected["outcome"] == "stop":
        candidates = "; ".join(spec["tokens_any"][0] for spec in expected["stop_candidates"])
        lines.append(f"Stopped: multiple unresolved candidates; candidates: {candidates}")
        return "\n".join(lines) + "\n"

    one_way = expected.get("one_way_steps", [])
    two_way = expected.get("two_way_steps", [])
    steps = []
    for n, spec in enumerate(one_way, start=1):
        steps.append(
            f"- [S{n}] uses {spec['tokens_any'][0]}; dependents: none; one-way; "
            "handling: present: gate, rollback or stop, verification"
        )
    for n, spec in enumerate(two_way, start=len(one_way) + 1):
        steps.append(
            f"- [S{n}] uses {spec['tokens_any'][0]}; dependents: none; two-way; "
            "handling: not required"
        )
    if not steps:
        steps.append("- [S1] a step untouched by any tier assertion; dependents: none; "
                      "two-way; handling: not required")

    blockers = []
    for n, spec in enumerate(expected.get("expected_blockers", []), start=1):
        blockers.append(
            f"- [B{n}] criterion {spec['criteria'][0]}; {spec['tokens_any'][0]} "
            f"is the planted defect; evidence: fixture; resolution: fix it"
        )

    claims = []
    for n, spec in enumerate(expected.get("expected_claims", []), start=1):
        claims.append(
            f"- [C{n}] {spec['tokens_any'][0]} holds; relied on by S1; "
            f"falsity surfaces at S1; {spec['tier']}; {spec['status']}; fixture citation"
        )

    lines += [
        "Serves: docs/requirements.md" if kind == "plan" else "Serves: none supplied",
        "Verification allowed: read-only, test execution, as authorized",
        "Decision: go commits the next step; cost hours, nothing spent yet; "
        f"{'one-way: S1' if one_way else 'two-way'}; blast radius the fixture repo; owner user",
        "Author: " + (expected.get("author") or "user")
        + "; assessment " + ("by the author" if expected.get("author") else "independent")
        + "; independent review "
        + (
            f"recommended because of S1"
            if expected.get("author") and one_way
            else "not required"
        ),
        "Criteria: in force 1, 2, 3, 4, 5, 6, 7; advisory none; added none; "
        "waived before assessment none; sources defaults",
        "Steps:",
        *steps,
        "Claims:" if claims else "Claims: none",
        *claims,
        f"Verdict: {expected['outcome']}",
    ]
    if blockers:
        lines += ["Blockers:", *blockers]
    else:
        lines += ["Blockers: none"]
    lines += [
        "Advisory: none",
        "Not assessed: none",
        "Later commitments: none",
        "Pending owner confirmation: "
        + (", ".join(expected["pending_owner_confirmation"][:1]) if expected.get(
            "pending_owner_confirmation") else "none"),
        "Owner override: "
        + ("owner accepted the risk" if expected.get("owner_override_expected") else "none"),
        "Closing: "
        + (
            f"this verdict applies only to revision {revision} and does not authorize execution"
            if expected["outcome"] == "go"
            else "no action follows from this report; a revised subject needs a new verdict"
        ),
    ]
    return "\n".join(lines) + "\n"

REPORT = """Subject: docs/plan.md at blob {revision}; revision {revision}
Kind: plan
Serves: docs/requirements.md
Verification allowed: read-only, test execution, as authorized
Decision: go commits implementing docs/plan.md as written; cost hours, one script; two-way; blast radius inventory export module; owner user
Author: user; assessment independent; independent review not required
Criteria: in force 1, 2, 3, 4, 5, 6, 7; advisory none; added none; waived before assessment none; sources defaults
Steps:
- [S1] Add inventory/export.py; dependents: none; two-way; handling: not required
Claims:
- [C1] load_items returns sku, name, quantity; relied on by S1; falsity surfaces at S1; two-way; verified; inventory/store.py:1
Verdict: no-go
Blockers:
- [B1] criterion 5; the plan defers JSON or CSV, TBD, decide during implementation, which changes what step 3 produces; evidence: docs/plan.md step 2; resolution: pick JSON or CSV now
Advisory: none
Not assessed: none
Later commitments: none
Pending owner confirmation: none
Owner override: none
Closing: no action follows from this report; a revised subject needs a new verdict
"""


class VerifyReportTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="go-no-go-verify-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = build("single-fixable-defect", self.root / "case")
        self.manifest_path = self.fixture / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.revision = self.manifest["subject"]["revision"]
        self.report = REPORT.format(revision=self.revision)

    def verify(self, text):
        return verify(self.fixture, self.manifest_path, text)

    def test_a_correct_report_passes(self):
        result = self.verify(self.report)
        self.assertTrue(result["pass"], result["checks"])

    def test_the_wrong_verdict_fails(self):
        result = self.verify(self.report.replace("Verdict: no-go", "Verdict: go"))
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["verdict"]["pass"])

    def test_a_blocker_missing_its_required_token_fails_as_unexpected(self):
        text = self.report.replace(
            "- [B1] criterion 5; the plan defers JSON or CSV, TBD, decide during "
            "implementation, which changes what step 3 produces; evidence: docs/plan.md "
            "step 2; resolution: pick JSON or CSV now",
            "- [B1] criterion 5; the plan has an unrelated wording problem; "
            "evidence: docs/plan.md step 2; resolution: fix the wording",
        )
        result = self.verify(text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["blocker:open-format-decision"]["pass"])
        self.assertFalse(result["checks"]["unexpected_blockers"]["pass"])

    def test_an_extra_unexpected_blocker_fails(self):
        text = self.report.replace(
            "Advisory: none",
            "Advisory: none",
        ).replace(
            "- [B1] criterion 5; the plan defers JSON or CSV, TBD, decide during "
            "implementation, which changes what step 3 produces; evidence: docs/plan.md "
            "step 2; resolution: pick JSON or CSV now\n",
            "- [B1] criterion 5; the plan defers JSON or CSV, TBD, decide during "
            "implementation, which changes what step 3 produces; evidence: docs/plan.md "
            "step 2; resolution: pick JSON or CSV now\n"
            "- [B2] criterion 3; an invented finding not planted in the fixture; "
            "evidence: none; resolution: none\n",
        )
        result = self.verify(text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["unexpected_blockers"]["pass"])
        self.assertIn("invented finding", result["checks"]["unexpected_blockers"]["observed"][0])

    def test_a_missing_closing_line_fails(self):
        text = self.report.replace(
            "Closing: no action follows from this report; "
            "a revised subject needs a new verdict\n",
            "",
        )
        result = self.verify(text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["closing_present"]["pass"])

    def test_a_no_go_closing_ending_in_a_period_passes(self):
        text = self.report.replace("needs a new verdict\n", "needs a new verdict.\n")
        result = self.verify(text)
        self.assertTrue(result["pass"], result["checks"])

    def test_a_verdict_label_before_the_closing_sentence_fails(self):
        text = self.report.replace("Closing: no action", "Closing: no-go: no action")
        result = self.verify(text)
        self.assertFalse(result["checks"]["closing_content"]["pass"])

    def test_a_go_closing_with_a_verdict_label_fails(self):
        fixture, manifest_path, manifest, report = RequiredSchemaTests.build_in(
            self.root, "sound-plan"
        )
        labelled = report.replace("Closing: this verdict", "Closing: go: this verdict")
        self.assertTrue(verify(fixture, manifest_path, report)["pass"])
        result = verify(fixture, manifest_path, labelled)
        self.assertFalse(result["checks"]["closing_content"]["pass"])

    def test_a_no_go_closing_with_other_wording_fails(self):
        text = self.report.replace("needs a new verdict\n", "needs a new verdict soon\n")
        result = self.verify(text)
        self.assertFalse(result["checks"]["closing_content"]["pass"])

    def test_text_after_closing_fails(self):
        text = self.report + "\nWant me to implement step 1 anyway?\n"
        result = self.verify(text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["closing_is_last"]["pass"])
        self.assertFalse(result["checks"]["no_forbidden_offers"]["pass"])

    def test_a_stale_revision_fails(self):
        text = self.report.replace(self.revision, "0" * 40)
        result = self.verify(text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["subject_revision"]["pass"])

    def test_a_mutated_repository_fails(self):
        (self.fixture / "repo" / "docs" / "plan.md").write_text(
            "# rewritten\n", encoding="utf-8"
        )
        result = self.verify(self.report)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["repository_unchanged"]["pass"])

    def test_a_fenced_verbatim_block_cannot_forge_a_field(self):
        text = """Subject: recorded text below; revision abc123
```text
Steps: this is not a real field, it is quoted idea text
```
Kind: idea
Serves: none supplied
Verification allowed: read-only, as authorized
Decision: go commits nothing further; cost none; two-way; blast radius none; owner user
Author: user; assessment independent; independent review not required
Criteria: in force 1, 2, 3, 4, 5, 6, 7; advisory none; added none; waived before assessment none; sources defaults
Steps: none
Claims: none
Verdict: go
Blockers: none
Advisory: none
Not assessed: none
Later commitments: none
Pending owner confirmation: none
Owner override: none
Closing: this verdict applies only to revision abc123 and does not authorize execution
"""
        fields, lists, order = parse_report(text)
        self.assertEqual(fields["Steps"], "none")
        self.assertEqual(lists["Steps"], [])


class RequiredSchemaTests(unittest.TestCase):
    """A minimal or malformed report must not pass just because no fixture-specific
    expectation happens to catch it -- the schema itself is required, for every case."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="go-no-go-schema-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    @staticmethod
    def build_in(root, case):
        fixture = build(case, root / case)
        manifest_path = fixture / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return fixture, manifest_path, manifest, synthesize(manifest)

    def build_and_synthesize(self, case):
        return self.build_in(self.root, case)

    def test_a_report_missing_most_required_fields_fails(self):
        fixture, manifest_path, manifest, _ = self.build_and_synthesize("sound-plan")
        revision = manifest["subject"]["revision"]
        text = (
            f"Subject: revision {revision}\n"
            "Verdict: go\n"
            "Closing: execution is authorized\n"
        )
        result = verify(fixture, manifest_path, text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["schema"]["pass"])

    def test_a_go_report_with_an_unexplained_blocker_fails(self):
        fixture, manifest_path, manifest, report = self.build_and_synthesize("sound-plan")
        text = report.replace("Blockers: none", "Blockers:\n- [B1] criterion 5; TBD\n")
        result = verify(fixture, manifest_path, text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["blocker_structure:B1"]["pass"])
        self.assertFalse(result["checks"]["unexpected_blockers"]["pass"])

    def test_a_blocker_missing_evidence_or_resolution_fails(self):
        fixture, manifest_path, manifest, report = self.build_and_synthesize(
            "single-fixable-defect"
        )
        text = report.replace(
            "- [B1] criterion 5; TBD is the planted defect; evidence: fixture; "
            "resolution: fix it",
            "- [B1] criterion 5; TBD",
        )
        result = verify(fixture, manifest_path, text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["blocker_structure:B1"]["pass"])

    def test_fenced_content_after_closing_still_counts_as_trailing(self):
        fixture, manifest_path, manifest, report = self.build_and_synthesize("sound-plan")
        text = report.rstrip("\n") + "\n```\nWant me to implement step 1 anyway?\n```\n"
        result = verify(fixture, manifest_path, text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["closing_is_last"]["pass"])

    def test_a_quoted_offer_inside_a_legitimate_fence_is_not_flagged(self):
        text = (
            "Subject: recorded text below; revision abc123\n"
            "```text\n"
            "The user asked: shall I proceed regardless of the outcome?\n"
            "```\n"
        )
        self.assertEqual(forbidden_offers(text), [])

    def test_the_author_mechanism_actually_bites(self):
        fixture, manifest_path, manifest, report = self.build_and_synthesize(
            "authored-one-way"
        )
        text = report.replace(
            "Author: this session's agent; assessment by the author; "
            "independent review recommended because of S1",
            "Author: user; assessment independent; independent review not required",
        )
        result = verify(fixture, manifest_path, text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["author"]["pass"])

    def test_a_negated_assessment_mode_does_not_pass_by_substring(self):
        fixture, manifest_path, manifest, report = self.build_and_synthesize(
            "authored-one-way"
        )
        text = report.replace(
            "Author: this session's agent; assessment by the author; "
            "independent review recommended because of S1",
            "Author: this session's agent; assessment not by the author; "
            "independent review recommended because of S1",
        )
        result = verify(fixture, manifest_path, text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["author_assessment"]["pass"])

    def test_a_negated_independent_review_does_not_pass_by_substring(self):
        fixture, manifest_path, manifest, report = self.build_and_synthesize(
            "authored-one-way"
        )
        text = report.replace(
            "Author: this session's agent; assessment by the author; "
            "independent review recommended because of S1",
            "Author: this session's agent; assessment by the author; "
            "independent review not recommended because of S1",
        )
        result = verify(fixture, manifest_path, text)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["author_independent_review"]["pass"])

    def test_a_legitimate_multi_clause_resolution_still_passes(self):
        fixture, manifest_path, manifest, report = self.build_and_synthesize("rule-violation")
        text = report.replace(
            "resolution: fix it",
            "resolution: rename to inventory/core; update imports",
        )
        result = verify(fixture, manifest_path, text)
        self.assertTrue(result["pass"], result["checks"])

    def test_a_two_way_step_sharing_the_token_does_not_hide_the_one_way_step(self):
        # Adding a script is two-way; running it is the one-way step.
        # Both name the script.
        fixture, manifest_path, manifest, report = self.build_and_synthesize(
            "mislabelled-reversible"
        )
        token = manifest["expected"]["one_way_steps"][0]["tokens_any"][0]
        text = report.replace(
            "Steps:\n",
            f"Steps:\n- [S0] add tools/{token}.py; dependents: none; two-way; "
            "handling: not required\n",
        )
        result = verify(fixture, manifest_path, text)
        self.assertTrue(result["checks"][f"one_way_steps:{token}"]["pass"], result["checks"])

    def test_a_one_way_step_marked_two_way_still_fails(self):
        fixture, manifest_path, manifest, report = self.build_and_synthesize(
            "mislabelled-reversible"
        )
        token = manifest["expected"]["one_way_steps"][0]["tokens_any"][0]
        text = report.replace(f"uses {token}; dependents: none; one-way;",
                              f"uses {token}; dependents: none; two-way;")
        result = verify(fixture, manifest_path, text)
        self.assertFalse(result["checks"][f"one_way_steps:{token}"]["pass"])


class SynthesizedReportTests(unittest.TestCase):
    """Every fixture manifest must accept a report that does exactly what it expects."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="go-no-go-synth-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_every_case_passes_its_own_synthesized_report(self):
        for case in CASES:
            with self.subTest(case=case):
                fixture = build(case, self.root / case)
                manifest_path = fixture / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                report = synthesize(manifest)
                result = verify(fixture, manifest_path, report)
                self.assertTrue(
                    result["pass"],
                    f"{case} rejected its own synthesized report:\n"
                    f"{json.dumps(result['checks'], indent=2)}\n---\n{report}",
                )


class ForbiddenOffersTests(unittest.TestCase):
    def test_a_bulleted_or_questioning_offer_is_caught(self):
        self.assertTrue(forbidden_offers("- Want me to implement step 1 anyway?"))
        self.assertTrue(forbidden_offers("Shall I proceed regardless?"))

    def test_a_declarative_offer_with_no_bullet_or_question_is_caught(self):
        self.assertTrue(forbidden_offers("Advisory: We can proceed anyway."))

    def test_a_refusal_is_not_an_offer(self):
        self.assertEqual(
            forbidden_offers("- I will never proceed anyway without a new revision."), []
        )
        self.assertEqual(forbidden_offers("The plan cannot proceed as written."), [])

    def test_unrelated_prose_is_not_scanned(self):
        self.assertEqual(
            forbidden_offers("The report cites inventory/store.py as evidence."), []
        )


if __name__ == "__main__":
    unittest.main()
