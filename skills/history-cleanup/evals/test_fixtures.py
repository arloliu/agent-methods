"""Test fixture graphs and reference transformations, without invoking an agent."""

import importlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
support = importlib.import_module("fixture_support")


class FixtureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="history-cleanup-tests-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def fixture(self, name):
        return support.build(name, self.root / name)

    def check_program(self, repo, name="checks.py", succeeds=True):
        result = repo.run(sys.executable, "-B", name, check=False)
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0)
        return result

    def baseline(self, repo):
        return json.loads((repo.root / "manifest.json").read_text())

    def prepare_rewrite(self, repo):
        self.assertEqual(
            repo.git("status", "--porcelain=v1", "--untracked-files=all"), ""
        )
        repo.git("branch", "backup/fixture-original", self.baseline(repo)["head"])
        self.assertEqual(
            repo.git("rev-parse", "backup/fixture-original"),
            self.baseline(repo)["head"],
        )
        repo.git("checkout", "-b", "rewritten", repo.commits["M"])

    def group(self, repo, label, members):
        subject = repo.git("show", "-s", "--format=%s", repo.commits[members[0]])
        for member in members:
            repo.git("cherry-pick", "--no-commit", repo.commits[member])
        return repo.commit(label, subject)

    def assert_final_tree(self, repo, count):
        self.assertEqual(
            repo.git("rev-parse", "backup/fixture-original^{commit}"),
            self.baseline(repo)["head"],
        )
        self.assertEqual(
            repo.git("rev-parse", "HEAD^{tree}"), self.baseline(repo)["tree"]
        )
        self.assertEqual(
            repo.git("rev-parse", "backup/fixture-original^{tree}"),
            self.baseline(repo)["tree"],
        )
        self.assertEqual(
            repo.git("diff", "--exit-code", "backup/fixture-original", "HEAD"), ""
        )
        self.assertEqual(
            int(repo.git("rev-list", "--count", f"{repo.commits['M']}..HEAD")), count
        )
        self.assertEqual(
            repo.git("status", "--porcelain=v1", "--untracked-files=all"), ""
        )

    def test_all_graphs_have_expected_counts_and_parent_order(self):
        expected = {
            "fixup-chain": ("M", 4),
            "independent-documentation": ("M", 5),
            "non-adjacent-correction": ("M", 3),
            "revert-safe": ("M", 4),
            "revert-dependent": ("M", 4),
            "merge-boundary": ("M", 5),
            "dirty-worktree": ("M", 2),
            "independent-changes": ("M", 3),
            "ambiguous-base": ("O", 3),
        }
        self.assertEqual(set(support.cases()), set(expected))
        for name, (base, count) in expected.items():
            with self.subTest(case=name):
                repo = self.fixture(name)
                self.assertEqual(repo.git("branch", "--show-current"), "feature")
                self.assertEqual(repo.git("remote"), "")
                self.assertEqual(
                    int(repo.git("rev-list", "--count", f"{repo.commits[base]}..HEAD")),
                    count,
                )
                ordered = repo.git(
                    "rev-list", "--reverse", "--topo-order", "HEAD"
                ).splitlines()
                seen = set()
                for oid in ordered:
                    parents = repo.git("show", "-s", "--format=%P", oid).split()
                    self.assertTrue(set(parents) <= seen)
                    seen.add(oid)
                self.assertFalse((repo.path / "manifest.json").exists())
                self.assertFalse((repo.path / "request.md").exists())
                self.assertFalse(repo.git("for-each-ref", "refs/heads/backup"))

    def test_builds_are_reproducible(self):
        for case in support.cases():
            with self.subTest(case=case):
                first = support.build(case, self.root / (case + "-one"))
                second = support.build(case, self.root / (case + "-two"))
                self.assertEqual(self.baseline(first), self.baseline(second))

    def test_fixup_chain_squashes_to_one_behavior(self):
        repo = self.fixture("fixup-chain")
        self.check_program(repo)
        self.prepare_rewrite(repo)
        self.group(repo, "G", ["A", "B", "C", "D"])
        self.assert_final_tree(repo, 1)
        self.assertEqual(repo.git("show", "-s", "--format=%s"), "Add retry limit")
        self.check_program(repo)

    def test_fixup_regression_detects_original_bug(self):
        repo = self.fixture("fixup-chain")
        repo.git("checkout", "--detach", repo.commits["A"])
        repo.git("checkout", repo.commits["C"], "--", "checks.py")
        result = self.check_program(repo, succeeds=False)
        self.assertIn("AssertionError", result.stderr)

    def test_independent_documentation_has_separate_rollback_boundaries(self):
        repo = self.fixture("independent-documentation")
        self.check_program(repo)
        self.prepare_rewrite(repo)
        feature = self.group(repo, "G", ["A", "B", "C", "D"])
        self.check_program(repo)
        self.assertEqual(
            (repo.path / "endpoint.md").read_text(),
            "The default endpoint uses API v1.\n",
        )
        docs = self.group(repo, "DOCS", ["E"])
        self.assert_final_tree(repo, 2)
        self.assertEqual(repo.git("diff", "--name-only", feature, docs), "endpoint.md")
        self.assertEqual(
            repo.git("show", "-s", "--format=%s"),
            "Correct default endpoint documentation",
        )
        repo.git("revert", "--no-edit", docs)
        self.check_program(repo)
        repo.git("revert", "--no-edit", "HEAD")
        repo.git("revert", "--no-edit", feature)
        self.assertFalse((repo.path / "client/retry.py").exists())
        self.assertEqual(
            (repo.path / "endpoint.md").read_text(),
            "The default endpoint uses API v2.\n",
        )

    def rebase_with_update_refs_config(self, disable_updates):
        repo = self.fixture("fixup-chain")
        repo.git("config", "--local", "rebase.updateRefs", "true")
        repo.git("branch", "backup/fixture-original")
        repo.git("branch", "unrelated", repo.commits["B"])
        repo.git("tag", "original-tip")
        before = repo.git("for-each-ref", "--format=%(refname) %(objectname)")
        editor = repo.root / "sequence editor.py"
        editor.write_text(
            "import pathlib, sys\n"
            "todo = pathlib.Path(sys.argv[1])\n"
            "lines = todo.read_text().splitlines(keepends=True)\n"
            "picked = False\n"
            "for i, line in enumerate(lines):\n"
            "    if line.startswith('pick '):\n"
            "        if picked:\n"
            "            lines[i] = 'fixup ' + line[5:]\n"
            "        picked = True\n"
            "todo.write_text(''.join(lines))\n"
        )
        # Preserve non-pick commands so Git's generated update-ref commands run.
        repo.env["GIT_SEQUENCE_EDITOR"] = shlex.join([sys.executable, str(editor)])
        options = ["--no-update-refs"] if disable_updates else []
        repo.git("rebase", "--interactive", *options, repo.commits["M"])
        self.assertNotEqual(repo.git("rev-parse", "HEAD"), self.baseline(repo)["head"])
        self.assertEqual(repo.git("rev-list", "--count", "main..HEAD"), "1")
        self.assertEqual(
            repo.git("rev-parse", "HEAD^{tree}"), self.baseline(repo)["tree"]
        )
        self.assertEqual(
            repo.git("diff", "--exit-code", "backup/fixture-original", "HEAD"), ""
        )
        return repo, before

    def test_update_refs_moves_backup_despite_matching_trees(self):
        repo, before = self.rebase_with_update_refs_config(disable_updates=False)
        self.assertEqual(
            repo.git("rev-parse", "backup/fixture-original"),
            repo.git("rev-parse", "HEAD"),
        )
        self.assertNotEqual(repo.git("rev-parse", "unrelated"), repo.commits["B"])
        self.assertNotEqual(
            repo.git("for-each-ref", "--format=%(refname) %(objectname)"), before
        )
        with self.assertRaises(AssertionError):
            self.assert_final_tree(repo, 1)

    def test_no_update_refs_preserves_backup_and_other_refs(self):
        repo, before = self.rebase_with_update_refs_config(disable_updates=True)
        self.assert_final_tree(repo, 1)
        after = repo.git("for-each-ref", "--format=%(refname) %(objectname)")
        self.assertEqual(
            after,
            before.replace(
                "refs/heads/feature " + self.baseline(repo)["head"],
                "refs/heads/feature " + repo.git("rev-parse", "HEAD"),
            ),
        )
        self.check_program(repo)

    def test_explicit_status_exposes_config_hidden_untracked_work(self):
        repo = self.fixture("fixup-chain")
        repo.git("config", "--local", "status.showUntrackedFiles", "no")
        repo.write({"drafts/scratch.txt": "Uncommitted work.\n"})
        before = repo.git("show-ref")
        index = repo.git("write-tree")
        self.assertEqual(repo.git("status", "--short"), "")
        self.assertEqual(
            repo.git("status", "--porcelain=v1", "--untracked-files=all"),
            "?? drafts/scratch.txt",
        )
        self.assertEqual(repo.git("show-ref"), before)
        self.assertEqual(repo.git("write-tree"), index)
        self.assertEqual(
            (repo.path / "drafts/scratch.txt").read_text(), "Uncommitted work.\n"
        )

    def test_non_adjacent_correction_moves_without_its_neighbor(self):
        repo = self.fixture("non-adjacent-correction")
        self.prepare_rewrite(repo)
        self.group(repo, "GX", ["A", "C"])
        self.check_program(repo, "check_retry.py")
        self.assertFalse((repo.path / "log_output.py").exists())
        self.group(repo, "GY", ["B"])
        self.check_program(repo, "check_retry.py")
        self.check_program(repo, "check_logs.py")
        self.assert_final_tree(repo, 2)
        self.assertEqual(
            repo.git(
                "log", "--reverse", "--format=%s", f"{repo.commits['M']}..HEAD"
            ).splitlines(),
            ["Add bounded retry", "Add JSON log output"],
        )

    def test_safe_revert_pair_can_be_removed(self):
        repo = self.fixture("revert-safe")
        self.prepare_rewrite(repo)
        self.group(repo, "G", ["B", "C"])
        self.assert_final_tree(repo, 1)
        self.check_program(repo)
        self.assertFalse((repo.path / "cache.py").exists())

    def test_dependent_revert_pair_cancels_but_breaks_intermediate_commit(self):
        repo = self.fixture("revert-dependent")
        self.check_program(repo)
        before = repo.git(
            "diff", repo.commits["M"], repo.commits["A"], "--", "retry_limit.py"
        )
        reverse = repo.git(
            "diff", repo.commits["R"], repo.commits["B"], "--", "retry_limit.py"
        )
        self.assertEqual(before, reverse)
        self.prepare_rewrite(repo)
        self.group(repo, "GB", ["B"])
        result = self.check_program(repo, succeeds=False)
        self.assertIn("ModuleNotFoundError", result.stderr)
        self.assertIn("retry_limit", result.stderr)
        self.group(repo, "GD", ["D"])
        self.check_program(repo)
        # Final-tree equality cannot detect the broken intermediate GB commit.
        self.assert_final_tree(repo, 2)

    def test_changed_dependent_group_can_eliminate_the_dependency(self):
        repo = self.fixture("revert-dependent")
        self.prepare_rewrite(repo)
        self.group(repo, "G", ["B", "D"])
        self.assert_final_tree(repo, 1)
        self.check_program(repo)

    def test_merge_resolution_and_topology_survive_reference_reconstruction(self):
        repo = self.fixture("merge-boundary")
        parents = repo.git("show", "-s", "--format=%P", repo.commits["J"]).split()
        self.assertEqual(parents, [repo.commits["A"], repo.commits["S2"]])
        resolution = repo.git("show", f"{repo.commits['J']}:settings.py")
        for parent in parents:
            self.assertNotEqual(resolution, repo.git("show", f"{parent}:settings.py"))
        self.prepare_rewrite(repo)
        side = self.group(repo, "SIDE", ["S1", "S2"])
        self.check_program(repo, "check_logs.py")
        repo.git("checkout", "-b", "rebuilt", repo.commits["A"])
        result = repo.run("git", "merge", "--no-ff", "--no-commit", side, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(
            repo.git("diff", "--name-only", "--diff-filter=U"), "settings.py"
        )
        merged = repo.commit(
            "MERGED", "Merge JSON output", {"settings.py": resolution + "\n"}
        )
        self.assertEqual(
            repo.git("show", "-s", "--format=%P", merged).split(),
            [repo.commits["A"], side],
        )
        self.group(repo, "FINAL", ["C"])
        self.assert_final_tree(repo, 4)
        self.check_program(repo, "check_logs.py")
        self.check_program(repo, "check_retry.py")

    def test_dirty_worktree_separates_head_index_and_working_files(self):
        repo = self.fixture("dirty-worktree")
        original = self.baseline(repo)
        self.assertEqual(
            set(original["status"].splitlines()),
            {" M client.py", "M  notes.md", "?? scratch.txt"},
        )
        index = repo.git("write-tree")
        self.assertNotEqual(index, original["tree"])
        staged = repo.git("diff", "--cached", "--binary")
        unstaged = repo.git("diff", "--binary")
        scratch = (repo.path / "scratch.txt").read_bytes()
        self.assertIn("value=30", repo.git("show", "HEAD:client.py"))
        self.assertIn("value=60", (repo.path / "client.py").read_text())
        repo.git("log", "--format=fuller", "main..HEAD")
        repo.git("diff", "main", "HEAD")
        self.assertEqual(repo.git("rev-parse", "HEAD"), original["head"])
        self.assertEqual(repo.git("show-ref"), original["refs"])
        self.assertEqual(repo.git("write-tree"), index)
        self.assertEqual(repo.git("diff", "--cached", "--binary"), staged)
        self.assertEqual(repo.git("diff", "--binary"), unstaged)
        self.assertEqual((repo.path / "scratch.txt").read_bytes(), scratch)

    def test_independent_changes_remain_separate(self):
        repo = self.fixture("independent-changes")
        for program in ("check_retry.py", "check_timing.py", "check_endpoint.py"):
            self.check_program(repo, program)
        self.assertEqual(
            repo.git(
                "diff", "--name-only", repo.commits["M"], repo.commits["A"]
            ).splitlines(),
            ["check_retry.py", "client/session.py"],
        )
        self.assertEqual(
            repo.git(
                "diff", "--name-only", repo.commits["A"], repo.commits["B"]
            ).splitlines(),
            ["check_timing.py", "client/session.py"],
        )
        self.assertEqual(repo.git("rev-parse", "HEAD"), self.baseline(repo)["head"])
        self.prepare_rewrite(repo)
        self.group(repo, "TIMING", ["B"])
        self.check_program(repo, "check_timing.py")
        self.group(repo, "RETRY", ["A"])
        self.check_program(repo, "check_retry.py")
        self.group(repo, "ENDPOINT", ["C"])
        self.check_program(repo, "check_endpoint.py")
        self.assert_final_tree(repo, 3)

    def test_ambiguous_base_changes_the_selected_range(self):
        repo = self.fixture("ambiguous-base")
        self.assertEqual(repo.git("merge-base", "main", "HEAD"), repo.commits["N"])
        self.assertEqual(repo.git("merge-base", "master", "HEAD"), repo.commits["O"])
        self.assertNotEqual(repo.git("rev-parse", "main"), repo.commits["N"])
        self.assertEqual(repo.git("rev-list", "--count", "main..HEAD"), "2")
        self.assertEqual(repo.git("rev-list", "--count", "master..HEAD"), "3")
        self.assertEqual(repo.git("for-each-ref", "refs/remotes"), "")
        self.check_program(repo)

    def test_tree_identity_detects_content_and_mode_corruption(self):
        repo = self.fixture("fixup-chain")
        original = self.baseline(repo)["tree"]
        repo.git("update-index", "--chmod=+x", "client/retry.py")
        self.assertNotEqual(repo.git("write-tree"), original)
        repo.git("update-index", "--chmod=-x", "client/retry.py")
        self.assertEqual(repo.git("write-tree"), original)
        repo.write({"client/retry.py": "def attempts(limit):\n    return []\n"})
        repo.git("add", "client/retry.py")
        self.assertNotEqual(repo.git("write-tree"), original)

    def test_existing_destination_is_never_overwritten(self):
        destination = self.root / "existing"
        destination.mkdir()
        marker = destination / "keep.txt"
        marker.write_text("keep me")
        with self.assertRaises(FileExistsError):
            support.build("fixup-chain", destination)
        self.assertEqual(list(destination.iterdir()), [marker])
        self.assertEqual(marker.read_text(), "keep me")

    def test_invalid_case_does_not_create_a_destination(self):
        destination = self.root / "invalid"
        with self.assertRaises(ValueError):
            support.build("../fixup-chain", destination)
        self.assertFalse(destination.exists())

    def test_inherited_git_environment_cannot_redirect_fixture_writes(self):
        other = self.fixture("independent-changes")
        original = self.baseline(other)
        with patch.dict(
            os.environ,
            {
                "GIT_DIR": str(other.path / ".git"),
                "GIT_WORK_TREE": str(other.path),
                "GIT_INDEX_FILE": str(other.path / ".git" / "index"),
                "GIT_AUTHOR_NAME": "Unintended Author",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "commit.gpgSign",
                "GIT_CONFIG_VALUE_0": "true",
            },
        ):
            created = self.fixture("fixup-chain")
        self.assertEqual(created.git("show", "-s", "--format=%an"), "Fixture Author")
        self.assertEqual(other.git("rev-parse", "HEAD"), original["head"])
        self.assertEqual(other.git("show-ref"), original["refs"])
        self.assertEqual(
            other.git("status", "--porcelain=v1", "--untracked-files=all"),
            original["status"],
        )

    def test_cli_builds_and_rejects_reuse(self):
        destination = self.root / "cli fixture"
        command = [
            sys.executable,
            "-B",
            str(Path(__file__).with_name("build_fixture.py")),
            "fixup-chain",
            str(destination),
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        baseline = (destination / "manifest.json").read_bytes()
        again = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
        self.assertEqual(again.returncode, 1)
        self.assertEqual((destination / "manifest.json").read_bytes(), baseline)


if __name__ == "__main__":
    unittest.main(verbosity=2)
