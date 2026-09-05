"""Validate portable skill metadata and local Markdown link destinations."""

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml
from markdown_it import MarkdownIt

FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
MARKDOWN = MarkdownIt("commonmark").enable("table")


class UniqueSafeLoader(yaml.SafeLoader):
    """Reject ambiguous duplicate mapping keys while retaining safe YAML parsing."""

    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ValueError("frontmatter keys must be strings")
            if key in result:
                raise ValueError(f"duplicate frontmatter key: {key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def frontmatter(text):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter delimiter")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise ValueError("missing closing frontmatter delimiter")
    data = yaml.load("".join(lines[1:end]), Loader=UniqueSafeLoader)
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a mapping")
    return data, "".join(lines[end + 1 :])


def metadata_errors(data, directory):
    errors = []
    unknown = set(data) - FIELDS
    if unknown:
        errors.append(f"unsupported portable frontmatter fields: {sorted(unknown)}")
    name = data.get("name")
    if (
        not isinstance(name, str)
        or not 1 <= len(name) <= 64
        or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
    ):
        errors.append("name must be 1-64 lowercase letters/digits with single hyphens")
    if name != directory:
        errors.append("name must match the skill directory")
    for field, limit in (("description", 1024), ("compatibility", 500)):
        if field == "compatibility" and field not in data:
            continue
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            errors.append(
                f"{field} must be a nonempty string of at most {limit} characters"
            )
    for field in ("license", "allowed-tools"):
        if field in data and not isinstance(data[field], str):
            errors.append(f"{field} must be a string")
    if "metadata" in data:
        value = data["metadata"]
        if not isinstance(value, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()
        ):
            errors.append("metadata must map string keys to string values")
    return errors


def link_destinations(tokens):
    for token in tokens:
        if token.type == "link_open":
            yield token.attrGet("href")
        elif token.type == "image":
            yield token.attrGet("src")
        if token.children:
            yield from link_destinations(token.children)


def validate(root, files):
    """Check listed repository files without fetching URLs or executing skill code."""
    root = Path(root).resolve()
    files = {Path(name) for name in files}
    errors = []
    skill_dirs = {
        path.parts[1]
        for path in files
        if len(path.parts) >= 3 and path.parts[0] == "skills"
    }
    if not skill_dirs:
        errors.append("skills/: no skill artifacts found")
    for directory in sorted(skill_dirs):
        entry = Path("skills") / directory / "SKILL.md"
        if entry not in files:
            errors.append(f"{entry}: missing skill entrypoint")
    for relative in sorted(files):
        if relative.suffix.lower() != ".md":
            continue
        path = root / relative
        try:
            body = path.read_text(encoding="utf-8")
            if relative.name == "SKILL.md":
                data, body = frontmatter(body)
                errors.extend(
                    f"{relative}: {error}"
                    for error in metadata_errors(data, relative.parent.name)
                )
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            errors.append(f"{relative}: {exc}")
            continue
        for destination in link_destinations(MARKDOWN.parse(body)):
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(root):
                errors.append(f"{relative}: link escapes repository: {destination}")
                continue
            target_relative = target.relative_to(root)
            published = target_relative in files or (
                target.is_dir()
                and any(item.is_relative_to(target_relative) for item in files)
            )
            if not target.exists() or not published:
                errors.append(
                    f"{relative}: missing published link target: {destination}"
                )
    return errors


def main():
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    files = result.stdout.rstrip("\0").split("\0") if result.stdout else []
    errors = validate(root, files)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Skill frontmatter and Markdown local file targets passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
