"""Build disposable Git repositories for the checked-in evaluation cases."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def isolated_environment():
    """Ignore inherited Git routing, identity, configuration, and signing state."""
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_TERMINAL_PROMPT="0",
        GIT_EDITOR="true",
        GIT_SEQUENCE_EDITOR="true",
        LC_ALL="C",
        TZ="UTC",
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


class Repository:
    """Git operations scoped to a newly created fixture directory."""

    def __init__(self, root):
        self.root = Path(root).absolute()
        # Exclusive creation rejects existing directories, including symlinks.
        self.root.mkdir()
        self.path = self.root / "repo"
        self.path.mkdir()
        self.empty = self.root / "empty-template"
        self.empty.mkdir()
        self.env = isolated_environment()
        self.commits = {}
        self.sequence = 0
        self.git(
            "init",
            "--template=" + str(self.empty),
            "--object-format=sha1",
            "-b",
            "main",
        )
        for key, value in {
            "user.name": "Fixture Author",
            "user.email": "fixture@example.invalid",
            "commit.gpgSign": "false",
            "tag.gpgSign": "false",
            "core.hooksPath": str(self.empty),
            "core.autocrlf": "false",
            "core.filemode": "true",
            "core.logAllRefUpdates": "true",
        }.items():
            self.git("config", "--local", key, value)

    def run(self, *args, check=True):
        return subprocess.run(
            args,
            cwd=self.path,
            env=self.env,
            text=True,
            capture_output=True,
            check=check,
            timeout=30,
        )

    def git(self, *args):
        return self.run("git", *args).stdout.rstrip("\n")

    def write(self, files):
        for name, content in files.items():
            path = self.path / name
            if content is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")

    def commit(self, label, subject, files=None):
        if label in self.commits:
            raise ValueError(f"Duplicate commit label: {label}")
        self.write(files or {})
        self.git("add", "--all")
        self.sequence += 1
        date = f"{946684800 + self.sequence} +0000"
        self.env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
        self.git("commit", "--no-gpg-sign", "-m", subject)
        self.commits[label] = self.git("rev-parse", "HEAD")
        return self.commits[label]

    def start(self, files=None, label="M"):
        self.commit(
            label, "Start example project", files or {"README.md": "Example project.\n"}
        )
        self.git("checkout", "-b", "feature")


def cases():
    return sorted(path.parent.name for path in FIXTURES.glob("*/setup.py"))


def build(case, destination):
    """Create a fixture and evaluator manifest without touching an existing path."""
    if case not in cases():
        raise ValueError(f"Unknown fixture: {case}")
    spec = importlib.util.spec_from_file_location(
        "fixture_setup", FIXTURES / case / "setup.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repo = Repository(destination)
    module.populate(repo)
    manifest = {
        "case": case,
        "commits": repo.commits,
        "head": repo.git("rev-parse", "HEAD"),
        "tree": repo.git("rev-parse", "HEAD^{tree}"),
        "branch": repo.git("branch", "--show-current"),
        "status": repo.git("status", "--short"),
        "refs": repo.git("show-ref"),
    }
    (repo.root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (repo.root / "request.md").write_text(module.REQUEST + "\n", encoding="utf-8")
    return repo
