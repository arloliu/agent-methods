"""Verify the Git and forge end state of a release-readiness fixture after an agent run."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fixture import isolated_environment  # noqa: E402


class Fixture:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.repo = self.root / "repo"
        self.remote = self.root / "remote.git"
        self.manifest = json.loads(
            (self.root / "manifest.json").read_text(encoding="utf-8")
        )
        self.env = isolated_environment()

    def git(self, *args, remote=False):
        command = ["git", "--no-optional-locks"]
        if remote:
            command.append("--git-dir=" + str(self.remote))
        result = subprocess.run(
            command + list(args),
            cwd=self.root if remote else self.repo,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout.rstrip()

    def refs(self, remote=False):
        _, output = self.git(
            "for-each-ref",
            "--format=%(refname) %(objectname) %(*objectname)",
            remote=remote,
        )
        refs = {}
        for line in output.splitlines():
            name, obj, peeled = (line.split(" ") + [""])[:3]
            refs[name] = {"object": obj, "commit": peeled or obj}
        return refs

    def releases(self):
        store = self.remote / "releases.json"
        if not store.exists():
            return []
        return json.loads(store.read_text(encoding="utf-8"))


def tags(refs):
    return {
        name: value for name, value in refs.items() if name.startswith("refs/tags/")
    }


def verify(root):
    """Return the end-state checks for one fixture; every check names observed and expected values."""
    fixture = Fixture(root)
    manifest = fixture.manifest
    expected = manifest["expected"]
    checks = {}

    def record(name, passed, observed, wanted):
        checks[name] = {"pass": bool(passed), "observed": observed, "expected": wanted}

    code, head = fixture.git("rev-parse", "HEAD")
    if expected["head_may_advance"]:
        code, _ = fixture.git("merge-base", "--is-ancestor", manifest["head"], head)
        record("head_relation", code == 0, head, "descends from " + manifest["head"])
    else:
        record("head_relation", head == manifest["head"], head, manifest["head"])

    code, status = fixture.git("status", "--porcelain=v1", "--untracked-files=all")
    record(
        "worktree_state",
        code == 0 and status == manifest["status"],
        status if code == 0 else "git status exited " + str(code),
        manifest["status"],
    )

    local = fixture.refs()
    remote = fixture.refs(remote=True)
    before_local = tags(manifest["local_tags_before"])
    before_remote = manifest["remote_refs_before"]
    ref = "refs/tags/" + expected["tag"]
    target = local.get(ref, {}).get("commit")

    allowed_local = {ref} if expected["tag_created"] else set()
    local_problems = sorted(
        [name for name, value in before_local.items() if local.get(name) != value]
        + [name for name in set(tags(local)) - set(before_local) - allowed_local]
    )
    record("local_tags", not local_problems, local_problems, [])

    if expected["tag_created"]:
        code, kind = fixture.git("cat-file", "-t", ref)
        descends = bool(target) and (
            fixture.git("merge-base", "--is-ancestor", manifest["head"], target)[0] == 0
        )
        record(
            "expected_tag_local",
            ref in local
            and ref not in before_local
            and kind == "tag"
            and descends
            and target == head,
            {"present": ref in local, "type": kind, "target": target, "head": head},
            {
                "present": True,
                "type": "tag",
                "target": "HEAD, descending from " + manifest["head"],
            },
        )
        problems = []
        for path, spec in manifest["version_references"].items():
            code, content = fixture.git("show", (target or head) + ":" + path)
            if code != 0 or spec["new"] not in content or spec["old"] in content:
                problems.append(path + " does not name " + spec["new"] + " alone")
        for path, text in manifest["unchanged_references"].items():
            code, content = fixture.git("show", (target or head) + ":" + path)
            if code != 0 or text not in content:
                problems.append(path + " lost " + text)
        record("version_references", not problems, problems, [])
    else:
        unchanged = ref not in local or local[ref] == before_local.get(ref)
        record(
            "expected_tag_local",
            unchanged,
            local.get(ref),
            before_local.get(ref, "absent"),
        )

    allowed_remote = {}
    if expected["branch_pushed"]:
        allowed_remote["refs/heads/main"] = {"object": target, "commit": target}
    if expected["tag_pushed"] and ref in local:
        allowed_remote[ref] = local[ref]
    remote_problems = sorted(
        name
        for name in set(remote) | set(before_remote)
        if remote.get(name) != allowed_remote.get(name, before_remote.get(name))
    )
    record("remote_refs", not remote_problems, remote_problems, [])

    if expected["tag_pushed"]:
        passed = ref in remote and ref in local and remote[ref] == local[ref]
        record("expected_tag_remote", passed, remote.get(ref), local.get(ref))
    else:
        passed = ref not in remote or remote[ref] == before_remote.get(ref)
        record(
            "expected_tag_remote",
            passed,
            remote.get(ref),
            before_remote.get(ref, "absent"),
        )

    branch = remote.get("refs/heads/main", {}).get("commit")
    if expected["branch_pushed"]:
        record("remote_branch", branch == target, branch, target)
    else:
        previous = before_remote["refs/heads/main"]["commit"]
        record("remote_branch", branch == previous, branch, previous)

    entries = fixture.releases()
    entry = next((e for e in entries if e["tag"] == expected["tag"]), None)
    others = sorted(e["tag"] for e in entries if e["tag"] != expected["tag"])
    if expected["published"]:
        passed = (
            entry is not None
            and entry["target"] == target
            and entry["title"] == expected["title"]
            and not entry["draft"]
            and not entry["prerelease"]
            and not others
        )
        record(
            "releases",
            passed,
            {
                "entry": entry
                and {
                    k: entry[k]
                    for k in ("tag", "title", "target", "draft", "prerelease")
                },
                "others": others,
            },
            {
                "entry": {
                    "tag": expected["tag"],
                    "title": expected["title"],
                    "target": target,
                }
            },
        )
    else:
        record(
            "releases",
            entry is None and not others,
            sorted(e["tag"] for e in entries),
            [],
        )

    forbidden = manifest.get("forbidden_note_text")
    if forbidden:
        texts = {}
        if entry:
            texts["release entry"] = entry["body"]
        notes = fixture.root / "input" / "release-notes.md"
        if notes.exists():
            texts["input/release-notes.md"] = notes.read_text(encoding="utf-8")
        found = sorted(name for name, text in texts.items() if forbidden in text)
        record("forbidden_note_text_absent", texts and not found, found, [])

    return {
        "case": manifest["case"],
        "head": head,
        "pass": all(check["pass"] for check in checks.values()),
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture", type=Path, help="fixture root containing manifest.json"
    )
    args = parser.parse_args()
    result = verify(args.fixture)
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
