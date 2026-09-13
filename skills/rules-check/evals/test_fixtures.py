"""Check real Git scope and generated evidence without evaluating an agent."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from build_fixture import CASES, Workspace, app, build


class FixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="rules-check-fixtures-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fixture(self, case):
        root = build(case, self.root / case)
        w = Workspace.__new__(Workspace)
        w.root = root
        w.repo = root / "repo"
        w.remote = root / "remote.git"
        w.template = root / "empty-template"
        # Reuse the isolated environment setup, without recreating fixture paths.
        helper_root = self.root / (case + "-environment")
        helper_root.mkdir()
        w.env = Workspace(helper_root).env
        manifest = json.loads((root / "manifest.json").read_text())
        evidence = json.loads((root / "input/operations.json").read_text())
        return w, manifest, evidence

    def test_every_case_builds_with_local_remote_and_valid_event_ids(self):
        for case in CASES:
            with self.subTest(case=case):
                w, manifest, evidence = self.fixture(case)
                self.assertEqual(w.git("rev-parse", "HEAD"), manifest["head"])
                self.assertEqual(w.git("remote", "get-url", "origin"), str(w.remote))
                events = manifest["all_events"]
                self.assertEqual(
                    [e["id"] for e in events], list(range(1, len(events) + 1))
                )
                self.assertIn("provenance", evidence)
                for event in events:
                    if event["kind"] == "commit":
                        self.assertEqual(
                            w.git("rev-parse", event["oid"] + "^{tree}"), event["tree"]
                        )

    def test_clean_worktree_still_has_two_commits_and_message_violation(self):
        w, manifest, _ = self.fixture("ahead")
        self.assertEqual(manifest["status"], "")
        self.assertEqual(w.git("rev-list", "--count", "@{upstream}..HEAD"), "2")
        self.assertEqual(w.git("show", "HEAD:app.py"), app(2).strip())
        self.assertEqual(w.git("show", manifest["first"] + ":app.py"), app(0).strip())
        self.assertIn("round 2", w.git("log", "--format=%B", "@{upstream}..HEAD"))
        self.assertNotIn("round 2", w.git("log", "--format=%s", "@{upstream}..HEAD"))

    def test_dirty_layers_do_not_cancel_staged_violation_or_hide_untracked_file(self):
        w, manifest, _ = self.fixture("dirty")
        self.assertEqual(w.git("show", ":app.py"), app(0).strip())
        self.assertEqual((w.repo / "app.py").read_text(), app(3))
        self.assertIn("MM app.py", manifest["status"])
        self.assertIn("?? extra.py", manifest["status"])
        self.assertIn("return 0", w.git("diff", "--cached"))
        self.assertIn("return 3", w.git("diff"))

    def test_missing_upstream_does_not_mean_no_commits(self):
        w, _, _ = self.fixture("no-upstream")
        result = w.run(["git", "rev-parse", "@{upstream}"], check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(w.git("rev-list", "--count", "main..HEAD"), "1")

    def test_divergence_contains_both_sides(self):
        w, manifest, _ = self.fixture("diverged")
        counts = w.git("rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        self.assertEqual(counts.split(), ["1", "1"])
        self.assertEqual(
            w.git("merge-base", "@{upstream}", "HEAD"), manifest["baseline"]
        )

    def test_cached_ahead_commit_can_already_be_on_remote(self):
        w, manifest, _ = self.fixture("stale-upstream")
        self.assertEqual(w.git("rev-list", "--count", "@{upstream}..HEAD"), "1")
        self.assertEqual(
            w.git("rev-parse", "refs/heads/feature", cwd=w.remote), manifest["head"]
        )
        self.assertNotEqual(w.git("rev-parse", "@{upstream}"), manifest["head"])

    def test_masked_component_failure_has_wrapper_success_before_commit(self):
        _, _, evidence = self.fixture("masked-failure")
        command = next(e for e in evidence["events"] if e["kind"] == "command")
        commit = next(e for e in evidence["events"] if e["kind"] == "commit")
        self.assertEqual(command["exit_code"], 0)
        self.assertIn("Required component exit: 3", command["stdout"])
        self.assertLess(command["id"], commit["id"])

    def test_late_lint_passes_but_does_not_precede_commit(self):
        _, _, evidence = self.fixture("late-check")
        events = evidence["events"]
        command = next(e for e in events if e["kind"] == "command")
        commit = next(e for e in events if e["kind"] == "commit")
        self.assertEqual(command["exit_code"], 0)
        self.assertEqual(command["files"], commit["files"])
        self.assertGreater(command["id"], commit["id"])

    def test_edit_after_lint_changes_inputs_without_changing_head(self):
        w, manifest, evidence = self.fixture("checked-then-edited")
        command = next(e for e in evidence["events"] if e["kind"] == "command")
        self.assertNotEqual(command["files"]["app.py"], manifest["files"]["app.py"])
        self.assertEqual(w.git("rev-parse", "HEAD"), manifest["first"])

    def test_markdown_edit_keeps_python_input_hashes(self):
        _, manifest, evidence = self.fixture("clean")
        command = next(e for e in evidence["events"] if e["kind"] == "command")
        for name in ("app.py", "lint.py"):
            self.assertEqual(command["files"][name], manifest["files"][name])
        self.assertNotEqual(
            command["files"]["README.md"], manifest["files"]["README.md"]
        )

    def test_missing_record_exposes_only_summary_not_hidden_events(self):
        _, manifest, evidence = self.fixture("missing-record")
        self.assertEqual(evidence["coverage"], "incomplete")
        self.assertEqual(evidence["events"], [])
        self.assertTrue(manifest["all_events"])

    def test_summary_points_to_recoverable_original_record_inside_inputs(self):
        w, manifest, summary = self.fixture("recoverable-record")
        self.assertEqual(summary["events"], [])
        inputs = w.root / "input"
        original_path = (inputs / summary["original_record"]).resolve()
        self.assertTrue(original_path.is_relative_to(inputs.resolve()))
        original = json.loads(original_path.read_text())
        self.assertEqual(original["events"], manifest["all_events"])
        command = next(e for e in original["events"] if e["kind"] == "command")
        commit = next(e for e in original["events"] if e["kind"] == "commit")
        self.assertEqual(command["exit_code"], 0)
        self.assertLess(command["id"], commit["id"])
        self.assertEqual(command["files"], commit["files"])

    def test_pending_check_has_staged_work_but_no_new_commit_or_lint(self):
        w, manifest, evidence = self.fixture("pending-check")
        self.assertEqual(w.git("rev-list", "--count", "@{upstream}..HEAD"), "0")
        self.assertEqual(manifest["head"], manifest["baseline"])
        self.assertEqual(w.git("show", ":app.py"), app(2).strip())
        self.assertEqual([e["kind"] for e in evidence["events"]], ["write", "stage"])
        self.assertEqual(w.git("diff"), "")

    def test_queries_with_no_optional_locks_preserve_index_and_files(self):
        w, manifest, _ = self.fixture("dirty")
        w.git("status", "--porcelain=v1", "--untracked-files=all")
        w.git("diff", "--cached")
        w.git("diff")
        w.git("log", "@{upstream}..HEAD", "--format=fuller")
        self.assertEqual(
            hashlib.sha256((w.repo / ".git/index").read_bytes()).hexdigest(),
            manifest["index_sha256"],
        )
        self.assertEqual(w.content(), manifest["files"])
        self.assertEqual(w.git("show-ref"), manifest["refs"])

    def test_builder_refuses_existing_destination_and_unknown_case(self):
        destination = self.root / "existing"
        destination.mkdir()
        marker = destination / "user-file"
        marker.write_text("keep")
        with self.assertRaises(FileExistsError):
            build("clean", destination)
        self.assertEqual(marker.read_text(), "keep")
        with self.assertRaises(ValueError):
            build("unknown", self.root / "unused")
        self.assertFalse((self.root / "unused").exists())

    def test_builder_ignores_inherited_git_routing_and_config(self):
        with patch.dict(
            "os.environ",
            {
                "GIT_DIR": str(self.root / "wrong-git"),
                "GIT_WORK_TREE": str(self.root / "wrong-tree"),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "commit.gpgsign",
                "GIT_CONFIG_VALUE_0": "true",
            },
        ):
            w, _, _ = self.fixture("clean")
        self.assertEqual(w.git("branch", "--show-current"), "feature")
        self.assertFalse((self.root / "wrong-git").exists())
        self.assertFalse((self.root / "wrong-tree").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
