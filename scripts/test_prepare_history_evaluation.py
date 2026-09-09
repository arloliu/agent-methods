"""Regression checks for portable fixture preparation and task delivery."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import prepare_history_evaluation as preparation


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="history-preparation-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.destination = self.root / "batch"

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(Path(preparation.__file__)), *map(str, args)],
            cwd=self.root,
            text=True,
            capture_output=True,
            timeout=30,
        )

    def test_cli_prepares_and_verifies_all_four_real_fixtures(self):
        result = self.cli("prepare", self.destination)
        self.assertEqual(result.returncode, 0, result.stderr)
        batch = preparation.read_json(self.destination / "batch.json")
        registry = preparation.read_json(self.destination / "registry.json")
        self.assertEqual(batch["model_execution"], "not-run")
        self.assertEqual(set(registry), set(preparation.CASES))
        for cell, case in preparation.CASES.items():
            with self.subTest(case=case):
                directory = self.destination / cell
                repo = directory / "workspace/repo"
                metadata = preparation.read_json(directory / "metadata.json")
                request = (directory / "workspace/request.md").read_text()
                self.assertEqual(registry[cell], str(repo.resolve()))
                self.assertEqual(metadata["cwd"], str(repo.resolve()))
                self.assertEqual(metadata["case"], case)
                self.assertEqual(metadata["task"]["text"], request)
                self.assertIn(
                    "Fixture task:\n" + request, (directory / "prompt.txt").read_text()
                )
                self.assertFalse((repo / "request.md").exists())
                self.assertEqual(
                    (repo / ".method/SKILL.md").read_bytes(),
                    preparation.DEFAULT_CANDIDATE.read_bytes(),
                )
                self.assertIsNone(metadata["rewrite_approval"])
                for field in ("head", "tree", "index", "status"):
                    self.assertEqual(
                        metadata["original"][field], metadata["prepared"][field]
                    )
                self.assertEqual(
                    preparation.user_files(metadata["original"]),
                    preparation.user_files(metadata["prepared"]),
                )
                self.assertFalse(
                    any(
                        "backup/history-cleanup/" in ref
                        for ref in metadata["prepared"]["refs"].splitlines()
                    )
                )
                if case == "dirty-worktree":
                    self.assertEqual(
                        metadata["prepared"]["status"],
                        " M client.py\nM  notes.md\n?? scratch.txt",
                    )
        before = {
            cell: preparation.observation.snapshot(Path(cwd))
            for cell, cwd in registry.items()
        }
        result = self.cli("verify", self.destination)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            before,
            {
                cell: preparation.observation.snapshot(Path(cwd))
                for cell, cwd in registry.items()
            },
        )

    def test_references_are_copied_and_all_package_changes_are_rejected(self):
        package = self.root / "candidate"
        (package / "references").mkdir(parents=True)
        entry = package / "SKILL.md"
        entry.write_text("Read references/rewrite.md after approval.\n")
        (package / "references/rewrite.md").write_text(
            "Stop when a required check fails.\n"
        )
        preparation.prepare(self.destination, entry)
        for cell in preparation.CASES:
            installed = (
                self.destination / cell / "workspace/repo/.method/references/rewrite.md"
            )
            self.assertEqual(
                installed.read_bytes(), (package / "references/rewrite.md").read_bytes()
            )
        method = self.destination / "cell-01/workspace/repo/.method"
        reference = method / "references/rewrite.md"
        original = reference.read_bytes()
        for change in ("changed", "missing", "extra"):
            with self.subTest(change=change):
                if change == "changed":
                    reference.write_text("Skip verification.\n")
                elif change == "missing":
                    reference.unlink()
                else:
                    (method / "extra.md").write_text("unexpected input\n")
                with self.assertRaisesRegex(ValueError, "candidate package changed"):
                    preparation.verify(self.destination)
                reference.write_bytes(original)
                (method / "extra.md").unlink(missing_ok=True)
        preparation.verify(self.destination)

    def test_self_contained_candidate_remains_supported(self):
        entry = self.root / "standalone.md"
        entry.write_text("Self-contained method.\n")
        batch = preparation.prepare(self.destination, entry)
        self.assertEqual(set(batch["candidate_files_sha256"]), {"SKILL.md"})
        preparation.verify(self.destination)
        for cell in preparation.CASES:
            installed = self.destination / cell / "workspace/repo/.method/SKILL.md"
            self.assertEqual(installed.read_bytes(), entry.read_bytes())

    def test_reference_outside_candidate_is_rejected_before_output_creation(self):
        package = self.root / "candidate"
        (package / "references").mkdir(parents=True)
        entry = package / "SKILL.md"
        entry.write_text("Example method.\n")
        outside = self.root / "outside.md"
        outside.write_text("External instructions.\n")
        outside_directory = self.root / "outside-directory"
        outside_directory.mkdir()
        link = package / "references/rewrite.md"
        for target in (outside, outside_directory):
            with self.subTest(target=target):
                link.symlink_to(target)
                with self.assertRaisesRegex(ValueError, "reference escapes"):
                    preparation.prepare(self.destination, entry)
                self.assertFalse(self.destination.exists())
                link.unlink()

    def test_existing_directory_and_symlinks_are_never_replaced(self):
        existing = self.root / "existing"
        existing.mkdir()
        sentinel = existing / "keep.txt"
        sentinel.write_text("user data")
        linked = self.root / "linked"
        linked.symlink_to(existing, target_is_directory=True)
        dangling = self.root / "dangling"
        dangling.symlink_to(self.root / "missing", target_is_directory=True)
        for destination in (existing, linked, dangling):
            with self.subTest(destination=destination):
                with self.assertRaises(FileExistsError):
                    preparation.prepare(destination)
        self.assertEqual(sentinel.read_text(), "user data")
        self.assertEqual(list(existing.iterdir()), [sentinel])
        self.assertTrue(linked.is_symlink())
        self.assertTrue(dangling.is_symlink())

    def test_missing_or_empty_candidate_creates_no_output(self):
        candidate = self.root / "candidate.md"
        with self.assertRaises(FileNotFoundError):
            preparation.prepare(self.destination, candidate)
        candidate.write_text(" \n")
        with self.assertRaisesRegex(ValueError, "candidate skill is empty"):
            preparation.prepare(self.destination, candidate)
        self.assertFalse(self.destination.exists())

    def test_missing_or_empty_task_stops_actual_preparation(self):
        original_build = preparation.fixture_support.build
        for missing in (True, False):
            with self.subTest(missing=missing):
                destination = self.root / str(missing)

                def build(case, path):
                    repo = original_build(case, path)
                    request = repo.root / "request.md"
                    if missing:
                        request.unlink()
                    else:
                        request.write_text(" \n")
                    return repo

                with patch.object(
                    preparation.fixture_support, "build", side_effect=build
                ):
                    with self.assertRaises((FileNotFoundError, ValueError)):
                        preparation.prepare(destination)
                self.assertTrue((destination / "cell-01/workspace/repo").is_dir())
                self.assertFalse((destination / "cell-01/prompt.txt").exists())
                self.assertFalse((destination / "batch.json").exists())

    def test_registry_must_name_actual_repo_even_after_hash_is_updated(self):
        preparation.prepare(self.destination)
        registry_path = self.destination / "registry.json"
        registry = preparation.read_json(registry_path)
        registry["cell-01"] = str(Path(registry["cell-01"]).parent)
        preparation.write_json(registry_path, registry)
        batch_path = self.destination / "batch.json"
        batch = preparation.read_json(batch_path)
        batch["artifact_hashes"]["registry.json"] = preparation.sha256(registry_path)
        preparation.write_json(batch_path, batch)
        with self.assertRaisesRegex(ValueError, "registered runtime cwd"):
            preparation.verify(self.destination)

    def test_changed_task_prompt_package_and_user_files_are_detected(self):
        preparation.prepare(self.destination)
        for name in (
            "workspace/request.md",
            "prompt.txt",
            "workspace/repo/.method/SKILL.md",
            "workspace/repo/retry.md",
        ):
            with self.subTest(name=name):
                path = self.destination / "cell-01" / name
                saved = path.read_bytes()
                path.write_bytes(saved + b"changed\n")
                with self.assertRaisesRegex(ValueError, "changed"):
                    preparation.verify(self.destination)
                path.write_bytes(saved)
        preparation.verify(self.destination)

    def test_changed_source_manifest_is_rejected(self):
        preparation.prepare(self.destination)
        path = self.destination / "batch.json"
        batch = preparation.read_json(path)
        batch["source_hashes"]["scripts/prepare_history_evaluation.py"] = "0" * 64
        preparation.write_json(path, batch)
        with self.assertRaisesRegex(ValueError, "preparation source changed"):
            preparation.verify(self.destination)

    def test_published_skill_directory_is_not_an_output_location(self):
        with self.assertRaisesRegex(ValueError, "outside published skills"):
            preparation.prepare(preparation.EVALS / "generated-trial")


if __name__ == "__main__":
    unittest.main(verbosity=2)
