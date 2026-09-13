"""Test the review-feedback evaluation fixtures."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fixture import CASES, build  # noqa: E402


class FixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="review-feedback-fixtures-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fixture(self, case):
        root = build(case, self.root / case)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        feedback = json.loads(
            (root / "input/feedback.json").read_text(encoding="utf-8")
        )
        return root, manifest, feedback

    def git(self, root, *args):
        return subprocess.check_output(
            ["git", "--no-optional-locks", *args],
            cwd=root / "repo",
            text=True,
        ).rstrip()

    def test_every_case_has_unique_traceable_items_and_separate_expectations(self):
        for case in CASES:
            with self.subTest(case=case):
                root, manifest, feedback = self.fixture(case)
                ids = [finding["id"] for finding in feedback["findings"]]
                self.assertEqual(ids, manifest["finding_ids"])
                self.assertEqual(len(ids), len(set(ids)))
                self.assertEqual(set(ids), set(manifest["expected"]))
                self.assertFalse(
                    any("expected" in finding for finding in feedback["findings"])
                )
                self.assertFalse((root / "input/manifest.json").exists())
                self.assertFalse((root / "repo/manifest.json").exists())
                self.assertEqual(self.git(root, "rev-parse", "HEAD"), manifest["head"])

    def test_mixed_case_separates_problem_and_remedy_judgments(self):
        _, manifest, feedback = self.fixture("mixed-remedies")
        self.assertEqual(manifest["expected"]["RF-1"]["judgment"], "supported")
        self.assertEqual(manifest["expected"]["RF-2"]["judgment"], "unsupported")
        self.assertEqual(manifest["expected"]["RF-3"]["remedy"], "unsuitable")
        self.assertIn("accepted public API name", feedback["findings"][1]["claim"])

    def test_empty_template_excludes_host_git_template_contents(self):
        root, _, _ = self.fixture("mixed-remedies")
        self.assertFalse((root / "repo/.git/description").exists())
        self.assertFalse((root / "repo/.git/hooks").exists())

    def test_outdated_case_binds_feedback_to_an_older_revision(self):
        root, manifest, feedback = self.fixture("outdated")
        source = feedback["findings"][0]["source_commit"]
        self.assertNotEqual(source, manifest["head"])
        current = (root / "repo/parser.py").read_text(encoding="utf-8")
        self.assertIn("if parsed < 0", current)
        self.assertNotIn("if parsed < 0", self.git(root, "show", f"{source}:parser.py"))

    def test_duplicate_case_preserves_each_source_id_and_relationship(self):
        _, manifest, feedback = self.fixture("duplicate-conflict")
        self.assertEqual(
            [item["id"] for item in feedback["findings"]], ["RF-20", "RF-21", "RF-22"]
        )
        self.assertEqual(
            manifest["expected"]["RF-22"]["relationship"], "duplicate of RF-20"
        )
        self.assertNotEqual(
            manifest["expected"]["RF-20"]["remedy"],
            manifest["expected"]["RF-21"]["remedy"],
        )

    def test_dirty_case_exposes_only_the_overlapping_user_file_as_dirty(self):
        root, manifest, _ = self.fixture("dirty-overlap")
        self.assertEqual(manifest["status"], " M limits.py")
        self.assertEqual(self.git(root, "status", "--porcelain=v1"), " M limits.py")
        self.assertIn(
            "return name", (root / "repo/labels.py").read_text(encoding="utf-8")
        )
        self.assertIn(
            "DEFAULT_MAX_RETRIES", (root / "repo/limits.py").read_text(encoding="utf-8")
        )

    def test_incomplete_batch_declares_the_missing_boundary(self):
        _, manifest, feedback = self.fixture("incomplete-batch")
        self.assertFalse(feedback["complete"])
        self.assertEqual(feedback["missing"], ["page 2 of 2 is unavailable"])
        self.assertNotIn("suggested_remedy", feedback["findings"][0])
        self.assertEqual(manifest["expected"]["RF-40"]["remedy"], "not provided")
        self.assertEqual(manifest["authorization"], "assessment-only")

    def test_assessment_only_case_keeps_an_obvious_supported_fix_pending(self):
        root, manifest, feedback = self.fixture("assessment-obvious")
        self.assertTrue(feedback["complete"])
        self.assertEqual(manifest["authorization"], "assessment-only")
        self.assertEqual(manifest["expected"]["RF-50"]["judgment"], "supported")
        self.assertEqual(
            manifest["expected"]["RF-50"]["action"], "leave pending without edits"
        )
        self.assertIn(
            "return value\n", (root / "repo/labels.py").read_text(encoding="utf-8")
        )

    def test_builder_refuses_reuse_and_unknown_cases(self):
        destination = self.root / "existing"
        destination.mkdir()
        with self.assertRaises(FileExistsError):
            build("mixed-remedies", destination)
        with self.assertRaises(ValueError):
            build("no-such-case", self.root / "unused")
        self.assertFalse((self.root / "unused").exists())

    def test_inherited_git_configuration_cannot_redirect_commits(self):
        other, manifest, _ = self.fixture("mixed-remedies")
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
            created, _, _ = self.fixture("outdated")
        self.assertEqual(
            self.git(created, "show", "-s", "--format=%an"), "Fixture Author"
        )
        self.assertEqual(self.git(other, "rev-parse", "HEAD"), manifest["head"])


if __name__ == "__main__":
    unittest.main()
