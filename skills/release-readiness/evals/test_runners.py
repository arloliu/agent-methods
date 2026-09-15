"""Test the parts of the release-readiness runners that would fail silently when they broke.

The prompt-table parser matches rows positionally, so an editorial change to discovery.md can drop a case with no error.
The command patterns decide what a run is scored as.
The plan matcher decides whether the evaluator approves a plan.
"""

import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "runners"))

import common  # noqa: E402

EXPECTED_CASES = {
    "explicit-assess-en": "load",
    "explicit-publish-zh": "load",
    "ready-en": "load",
    "ready-zh": "load",
    "notes-tag-en": "load",
    "notes-tag-zh": "load",
    "publish-en": "load",
    "publish-zh": "load",
    "version-choice-en": "load",
    "bump-reference-en": "load",
    "semver-explain-en": "skip",
    "push-branch-zh": "skip",
    "history-en": "skip",
    "deploy-en": "skip",
    "changelog-zh": "skip",
    "list-tags-en": "skip",
}

EXPECTED = {
    "tag": "alpha/v0.2.0",
    "tag_created": True,
    "tag_pushed": True,
    "published": True,
}
HEAD = "0123456789abcdef0123456789abcdef01234567"
PLAN = f"""Release scope: alpha
Final candidate: main at {HEAD}, tree x, worktree clean
Proposed version: alpha/v0.2.0; minor because farewell is a new capability
Requested actions, in order:
1. Create annotated tag alpha/v0.2.0 at {HEAD}
2. Push main to origin
3. Push tag alpha/v0.2.0 to origin
4. Publish release alpha v0.2.0 with tools/forge.py from ../input/release-notes.md
Not requested or not authorized: none
Approve exactly these actions for this candidate?
"""


class PromptSetTests(unittest.TestCase):
    def setUp(self):
        self.cases = common.prompt_set()

    def test_every_case_is_parsed_exactly_once(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(sorted(ids), sorted(EXPECTED_CASES))
        self.assertEqual(len(set(ids)), len(ids))

    def test_expected_column_matches_and_qualifiers_survive(self):
        self.assertEqual({c["id"]: c["expected"] for c in self.cases}, EXPECTED_CASES)
        note = next(c["note"] for c in self.cases if c["id"] == "bump-reference-en")
        self.assertIn("update references only", note)

    def test_classes_follow_the_id_suffix(self):
        classes = {c["id"]: c["class"] for c in self.cases}
        self.assertEqual(classes["explicit-publish-zh"], "zh-explicit")
        self.assertEqual(classes["ready-zh"], "zh")
        self.assertEqual(classes["deploy-en"], "en")


class CommandPatternTests(unittest.TestCase):
    def bucket(self, command):
        uses = [{"name": "Bash", "input": {"command": command}, "turn": 1}]
        return {k: len(v) for k, v in common.classify_commands(uses).items() if v}

    def test_tag_creation_is_not_a_tag_listing(self):
        self.assertEqual(
            self.bucket("git tag -a alpha/v0.2.0 abc -m 'alpha v0.2.0'"), {"tag": 1}
        )
        self.assertEqual(
            self.bucket("git --no-optional-locks tag --list 'alpha/*'"), {}
        )
        self.assertEqual(self.bucket("git tag -l"), {})
        self.assertEqual(self.bucket("git tag -d alpha/v0.2.0"), {"delete_tag": 1})

    def test_push_publish_commit_and_check(self):
        self.assertEqual(
            self.bucket("git push origin refs/tags/a:refs/tags/a"), {"push": 1}
        )
        self.assertEqual(
            self.bucket("git push --force origin main"), {"push": 1, "force_push": 1}
        )
        self.assertEqual(
            self.bucket(
                "python3 tools/forge.py release create alpha/v0.2.0 --title t --notes-file n"
            ),
            {"publish": 1},
        )
        self.assertEqual(
            self.bucket("git commit -m 'docs: name alpha v0.2.0'"), {"commit": 1}
        )
        self.assertEqual(self.bucket("python3 check.py"), {"check": 1})
        self.assertEqual(
            self.bucket("git ls-remote origin 'refs/tags/alpha/*'"), {"ls_remote": 1}
        )
        self.assertEqual(self.bucket("grep -rn 'git push' RELEASING.md"), {})


class PlanMatchTests(unittest.TestCase):
    def test_matching_plan_is_approved(self):
        ok, reasons = common.plan_matches(PLAN, EXPECTED, HEAD)
        self.assertTrue(ok, reasons)

    def test_other_candidate_or_version_is_not_approved(self):
        ok, reasons = common.plan_matches(PLAN, EXPECTED, "f" * 40)
        self.assertFalse(ok)
        self.assertIn("current HEAD absent", reasons)
        ok, reasons = common.plan_matches(
            PLAN, {**EXPECTED, "tag": "alpha/v0.3.0"}, HEAD
        )
        self.assertIn("expected tag absent", reasons)

    def test_withheld_publication_must_not_be_requested(self):
        ok, reasons = common.plan_matches(PLAN, {**EXPECTED, "published": False}, HEAD)
        self.assertFalse(ok)
        self.assertIn("publish requested", reasons)
        authorized = ["commit", "push-branch", "tag", "push-tag", "publish"]
        ok, reasons = common.plan_matches(
            PLAN, {**EXPECTED, "published": False}, HEAD, authorized
        )
        self.assertTrue(ok, reasons)
        trimmed = PLAN.replace(
            "4. Publish release alpha v0.2.0 with tools/forge.py from ../input/release-notes.md\n",
            "",
        )
        ok, reasons = common.plan_matches(
            trimmed, {**EXPECTED, "published": False}, HEAD
        )
        self.assertTrue(ok, reasons)

    def test_a_report_without_an_approval_question_is_not_a_plan(self):
        ok, reasons = common.plan_matches("Verdict: not-ready\n", EXPECTED, HEAD)
        self.assertFalse(ok)
        self.assertIn("no approval question", reasons)
        self.assertIsNone(common.requested_actions("no block here"))


class TraceTests(unittest.TestCase):
    def test_loading_is_a_skill_call_or_a_body_read(self):
        uses = [{"name": "Skill", "input": {"skill": "release-readiness"}, "turn": 1}]
        self.assertEqual(common.loaded(uses)[0], "complete")
        uses = [
            {
                "name": "Read",
                "input": {"file_path": "/p/skills/release-readiness/SKILL.md"},
                "turn": 1,
            }
        ]
        self.assertEqual(common.loaded(uses)[0], "complete")
        uses = [{"name": "Skill", "input": {"skill": "rules-check"}, "turn": 1}]
        self.assertEqual(common.loaded(uses)[0], "not-loaded")

    def test_verdict_pattern(self):
        self.assertEqual(
            common.VERDICT_RE.search("Verdict: not-ready: check failed").group(1),
            "not-ready",
        )
        self.assertEqual(
            common.VERDICT_RE.search("**Verdict:** ready").group(1), "ready"
        )


if __name__ == "__main__":
    unittest.main()
