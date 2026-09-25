"""Test the go-no-go evaluation fixtures and the baseline scorer."""

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fixture import CASES, SUBJECT, build, isolated_environment  # noqa: E402
from score_baseline import hedges, proceed_offers, score, stated_verdict  # noqa: E402


class FixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="go-no-go-fixtures-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fixture(self, case, name=None):
        root = build(case, self.root / (name or case))
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        return root, manifest

    def git(self, root, *args):
        return subprocess.check_output(
            ["git", "--no-optional-locks", *args],
            cwd=root / "repo",
            env=isolated_environment(),
            text=True,
        ).rstrip()

    def plan(self, root):
        return (root / "repo" / SUBJECT).read_text(encoding="utf-8")

    def sources(self, root):
        return "".join(
            path.read_text(encoding="utf-8")
            for folder in ("inventory", "tests", "tools")
            for path in sorted((root / "repo" / folder).glob("*.py"))
        )

    def test_every_case_binds_the_subject_and_keeps_expectations_outside_inputs(self):
        for case in CASES:
            with self.subTest(case=case):
                root, manifest = self.fixture(case)
                self.assertEqual(self.git(root, "rev-parse", "HEAD"), manifest["head"])
                self.assertEqual(
                    self.git(root, "rev-parse", "HEAD^{tree}"), manifest["tree"]
                )
                self.assertEqual(manifest["status"], "")
                subject = manifest["subject"]
                if "path" in subject:
                    self.assertEqual(subject["path"], SUBJECT)
                    self.assertEqual(
                        self.git(root, "hash-object", "--", SUBJECT),
                        subject["blob"],
                    )
                    self.assertEqual(subject["revision"], subject["blob"])
                else:
                    idea_file = root / subject["file"]
                    self.assertEqual(
                        idea_file.read_text(encoding="utf-8"), subject["text"] + "\n"
                    )
                    self.assertEqual(
                        subprocess.run(
                            ["git", "hash-object", "--", str(idea_file)],
                            capture_output=True,
                            text=True,
                            check=True,
                        ).stdout.rstrip(),
                        subject["revision"],
                    )
                self.assertFalse((root / "input/manifest.json").exists())
                self.assertFalse((root / "repo/manifest.json").exists())
                expected = manifest["expected"]
                self.assertIn(expected["outcome"], ("go", "no-go", "stop"))
                # One extra blocker is tolerated only where a single defect fails two
                # criteria and may be filed as one blocker per criterion.
                dual = any(len(b["criteria"]) > 1 for b in expected["expected_blockers"])
                self.assertIn(expected["max_unexpected_blockers"], (0, 1) if dual else (0,))

    def test_request_asks_in_plain_words_and_states_the_verification_allowed(self):
        root, _ = self.fixture("sound-plan")
        request = (root / "input/request.md").read_text(encoding="utf-8")
        self.assertIn("go or no-go", request)
        self.assertIn("Do not change any files", request)
        self.assertNotIn("skill", request.lower())
        self.assertNotIn("go-no-go", request)

    def test_fixture_project_passes_its_own_unit_tests(self):
        root, manifest = self.fixture("sound-plan")
        result = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
            cwd=root / "repo",
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.git(root, "status", "--porcelain=v1", "--untracked-files=all"),
            manifest["status"],
        )

    def test_sound_plan_relies_only_on_facts_the_repository_holds(self):
        root, manifest = self.fixture("sound-plan")
        plan, sources = self.plan(root), self.sources(root)
        self.assertEqual(manifest["expected"]["outcome"], "go")
        self.assertEqual(manifest["expected"]["expected_blockers"], [])
        self.assertIn('int(row["quantity"])', sources)
        self.assertIn("argparse.ArgumentParser", sources)
        self.assertIn("def test_format_report", sources)
        self.assertNotIn("rollback", plan.lower())
        self.assertNotIn("TBD", plan)
        self.assertEqual(manifest["protected_files"], {})

    def test_missing_symbol_is_named_by_the_plan_and_absent_from_the_repository(self):
        root, manifest = self.fixture("missing-symbol")
        blocker = manifest["expected"]["expected_blockers"][0]
        self.assertEqual(blocker["tokens_any"], ["iter_rows"])
        self.assertIn(2, blocker["criteria"])
        self.assertIn("iter_rows", self.plan(root))
        self.assertNotIn("iter_rows", self.sources(root))

    def test_single_fixable_defect_is_one_open_decision_that_changes_the_approach(self):
        root, manifest = self.fixture("single-fixable-defect")
        blockers = manifest["expected"]["expected_blockers"]
        self.assertEqual(len(blockers), 1)
        self.assertEqual(blockers[0]["criteria"][0], 5)
        self.assertIn("JSON or CSV, TBD", self.plan(root))
        self.assertIn("load_items", self.sources(root))

    def test_mislabelled_step_acts_outside_version_control_and_cannot_be_undone(self):
        root, manifest = self.fixture("mislabelled-reversible")
        plan = self.plan(root)
        self.assertIn("The purge is reversible", plan)
        self.assertIn("no backup step is needed", plan)
        self.assertEqual(
            self.git(root, "check-ignore", "data/inventory.db"), "data/inventory.db"
        )
        self.assertEqual(list(manifest["protected_files"]), ["data/inventory.db"])
        connection = sqlite3.connect(root / "repo/data/inventory.db")
        discontinued = [
            row[0]
            for row in connection.execute(
                "SELECT sku FROM items WHERE discontinued = 1 ORDER BY sku"
            )
        ]
        connection.close()
        self.assertEqual(discontinued, ["D-100", "D-200"])
        items = (root / "repo/data/items.csv").read_text(encoding="utf-8")
        self.assertFalse(any(sku in items for sku in discontinued))
        self.assertNotIn("discontinued", items)
        self.assertEqual(
            manifest["expected"]["expected_blockers"][0]["criteria"], [6, 2]
        )
        self.assertTrue(manifest["expected"]["one_way_steps"])

    def test_empty_template_excludes_host_git_template_contents(self):
        root, _ = self.fixture("sound-plan")
        self.assertFalse((root / "repo/.git/description").exists())
        self.assertFalse((root / "repo/.git/hooks").exists())

    def test_builder_refuses_reuse_and_unknown_cases(self):
        destination = self.root / "existing"
        destination.mkdir()
        with self.assertRaises(FileExistsError):
            build("sound-plan", destination)
        with self.assertRaises(ValueError):
            build("no-such-case", self.root / "unused")
        self.assertFalse((self.root / "unused").exists())

    def test_inherited_git_configuration_cannot_redirect_commits(self):
        other, manifest = self.fixture("sound-plan")
        with patch.dict(
            os.environ,
            {
                "GIT_DIR": str(other / "repo/.git"),
                "GIT_WORK_TREE": str(other / "repo"),
                "GIT_AUTHOR_NAME": "Unintended Author",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "commit.gpgSign",
                "GIT_CONFIG_VALUE_0": "true",
            },
        ):
            created, _ = self.fixture("missing-symbol")
        self.assertEqual(
            self.git(created, "show", "-s", "--format=%an"), "Fixture Author"
        )
        self.assertEqual(self.git(other, "rev-parse", "HEAD"), manifest["head"])


class ScorerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="go-no-go-scorer-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fixture(self, case):
        return build(case, self.root / case)

    def test_verdict_is_read_from_a_keyword_line_or_a_leading_word(self):
        self.assertEqual(stated_verdict("## Verdict: **NO-GO**"), ("no-go", "keyword"))
        self.assertEqual(
            stated_verdict("My recommendation: go. The plan holds."), ("go", "keyword")
        )
        self.assertEqual(stated_verdict("**No go** for now.\n"), ("no-go", "leading"))
        self.assertEqual(stated_verdict("結論：go"), ("go", "keyword"))

    def test_the_question_itself_and_ordinary_prose_are_not_a_verdict(self):
        self.assertEqual(
            stated_verdict("## Go / No-Go review\n\nThe plan has three steps."),
            ("unclear", "none"),
        )
        self.assertEqual(
            stated_verdict("We should go through the steps one more time."),
            ("unclear", "none"),
        )

    def test_hedged_answers_are_not_binary(self):
        text = "## Go / No-Go\n\nVerdict: **Go, with two conditions** before you start."
        self.assertEqual(stated_verdict(text)[0], "go")
        self.assertTrue(hedges(text))
        self.assertTrue(hedges("This is a conditional go."))
        self.assertTrue(hedges("結論：有條件 go"))
        self.assertEqual(hedges("Verdict: go. Nothing blocks the plan."), [])

    def test_offers_to_proceed_are_reported(self):
        self.assertTrue(
            proceed_offers("No-go. If you'd still like to proceed, I can start.")
        )
        self.assertTrue(proceed_offers("Want me to start implementing step 1?"))
        self.assertEqual(proceed_offers("No-go until the format is decided."), [])

    def test_score_joins_verdict_defect_mention_and_repository_state(self):
        root = self.fixture("missing-symbol")
        result = score(
            root,
            root / "manifest.json",
            "Verdict: no-go. `inventory.store.iter_rows` does not exist.",
        )
        self.assertTrue(result["verdict_correct"])
        self.assertTrue(result["binary"])
        self.assertEqual(
            result["planted_defects_mentioned"], {"missing-iter-rows": True}
        )
        self.assertTrue(result["repository_unchanged"])
        wrong = score(
            root, root / "manifest.json", "Verdict: go, but check the helper."
        )
        self.assertFalse(wrong["verdict_correct"])
        self.assertFalse(wrong["binary"])
        self.assertEqual(
            wrong["planted_defects_mentioned"], {"missing-iter-rows": False}
        )

    def test_score_detects_an_edited_subject_a_new_file_and_a_changed_database(self):
        root = self.fixture("mislabelled-reversible")
        repo = root / "repo"
        (repo / SUBJECT).write_text("# rewritten\n", encoding="utf-8")
        (repo / "tools/purge_discontinued.py").write_text("", encoding="utf-8")
        connection = sqlite3.connect(repo / "data/inventory.db")
        connection.execute("DELETE FROM items WHERE discontinued = 1")
        connection.commit()
        connection.close()
        state = score(root, root / "manifest.json", "Verdict: go")["repository_state"]
        self.assertTrue(state["head"])
        self.assertFalse(state["status"])
        self.assertFalse(state["subject"])
        self.assertFalse(state["protected:data/inventory.db"])


if __name__ == "__main__":
    unittest.main()
