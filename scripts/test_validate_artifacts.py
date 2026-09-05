"""Exercise malformed metadata and real Markdown link handling in isolation."""

import tempfile
import unittest
from pathlib import Path

from validate_artifacts import validate


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="agent-methods-artifacts-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.files = set()
        self.skill = "skills/example/SKILL.md"
        self.write(
            self.skill, "---\nname: example\ndescription: Do useful work.\n---\n"
        )

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.files.add(name)

    def check(self):
        return validate(self.root, self.files)

    def test_valid_portable_metadata_and_folded_description(self):
        self.write(
            self.skill,
            "---\nname: example\ndescription: >\n  Do useful work\n  when requested.\n"
            "license: Apache-2.0\nmetadata:\n  version: '1'\n---\n# Example\n",
        )
        self.assertEqual(self.check(), [])

    def test_rejects_missing_malformed_duplicate_and_nonmapping_frontmatter(self):
        cases = (
            "# No frontmatter\n",
            "---\nname: example\n",
            "---\nname: [broken\n---\n",
            "---\n- example\n---\n",
            "---\nname: example\nname: other\ndescription: Work.\n---\n",
            "---\nname: example\ndescription: Work.\nmetadata:\n  x: a\n  x: b\n---\n",
        )
        for text in cases:
            with self.subTest(text=text):
                self.write(self.skill, text)
                self.assertTrue(self.check())

    def test_rejects_invalid_required_fields_and_vendor_metadata(self):
        cases = (
            "name: example",
            "description: Work.",
            "name: other\ndescription: Work.",
            "name: Example\ndescription: Work.",
            "name: example--bad\ndescription: Work.",
            "name: " + "a" * 65 + "\ndescription: Work.",
            "name: example\ndescription: false",
            "name: example\ndescription: '   '",
            "name: example\ndescription: " + "x" * 1025,
            "name: example\ndescription: Work.\ndisable-model-invocation: true",
            "name: example\ndescription: Work.\nmetadata:\n  version: 1",
        )
        for data in cases:
            with self.subTest(data=data):
                self.write(self.skill, "---\n" + data + "\n---\n")
                self.assertTrue(self.check())

    def test_requires_entrypoint(self):
        self.files.remove(self.skill)
        self.write("skills/example/evals/case.md", "A case.\n")
        self.assertIn("missing skill entrypoint", "\n".join(self.check()))

    def test_rejects_missing_inline_reference_image_and_table_targets(self):
        cases = (
            "[missing](missing.md)",
            "[missing][ref]\n\n[ref]: missing.md",
            "![image](missing.png)",
            "| Link |\n| --- |\n| [missing](missing.md) |",
        )
        for body in cases:
            with self.subTest(body=body):
                self.write("README.md", body)
                self.assertIn("missing published link target", "\n".join(self.check()))

    def test_resolves_relative_encoded_and_parenthesized_destinations(self):
        self.write("docs/My Guide.md", "[skill](../skills/example/SKILL.md)")
        self.write("docs/guide(v2).md", "A guide.")
        self.write(
            "README.md",
            "[one](docs/My%20Guide.md#heading)\n"
            "[two](<docs/My Guide.md>)\n"
            "[three](docs/guide(v2).md)\n"
            "[folder](docs/)\n[reference][guide]\n\n"
            "[guide]: docs/guide(v2).md\n",
        )
        self.assertEqual(self.check(), [])

    def test_ignores_code_external_urls_and_fragment_only_links(self):
        self.write(
            "README.md",
            "`[sample](missing.md)`\n\n```md\n[sample](missing.md)\n```\n\n"
            "[web](https://example.invalid/missing)\n"
            "[cdn](//example.invalid/missing)\n[anchor](#heading)\n"
            "[email](mailto:example@example.invalid)\n",
        )
        self.assertEqual(self.check(), [])

    def test_rejects_unpublished_and_outside_targets(self):
        (self.root / "ignored.md").write_text("Not published.")
        for target in ("ignored.md", "../outside.md", "/etc/hosts"):
            with self.subTest(target=target):
                self.write("README.md", f"[target]({target})")
                self.assertTrue(self.check())

    def test_rejects_deleted_tracked_target(self):
        self.write("docs/guide.md", "A guide.")
        (self.root / "docs/guide.md").unlink()
        self.write("README.md", "[guide](docs/guide.md)")
        self.assertTrue(self.check())


if __name__ == "__main__":
    unittest.main(verbosity=2)
