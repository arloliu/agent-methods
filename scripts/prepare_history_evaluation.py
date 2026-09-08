"""Prepare or verify four disposable history-cleanup evaluation workspaces.

This tool does not launch an agent, supply rewrite approval, or freeze a behavioral trial.
It uses only Git and the Python standard library.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
EVALS = SOURCE / "skills/history-cleanup/evals"
sys.dont_write_bytecode = True
sys.path.insert(0, str(EVALS))

import fixture_support  # noqa: E402
import observation  # noqa: E402

CASES = {
    "cell-01": "independent-documentation",
    "cell-02": "revert-safe",
    "cell-03": "non-adjacent-correction",
    "cell-04": "dirty-worktree",
}
DEFAULT_CANDIDATE = EVALS.parent / "SKILL.md"


def write_json(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    sources = [Path(__file__), EVALS / "fixture_support.py", EVALS / "observation.py"]
    sources.extend(EVALS / "fixtures" / case / "setup.py" for case in CASES.values())
    return {str(path.relative_to(SOURCE)): sha256(path) for path in sources}


def git(repository, *args):
    return subprocess.check_output(
        ["git", "--no-optional-locks", *args],
        cwd=repository,
        env=fixture_support.isolated_environment(),
        text=True,
        timeout=30,
    ).strip()


def task_input(repository):
    """Read the evaluator-owned task outside the runtime Git repository."""
    task = (repository.parent / "request.md").read_text(encoding="utf-8")
    if not task.strip():
        raise ValueError("fixture task input is empty")
    return task


def prompt_for(task):
    return (
        "Read and follow .method/SKILL.md.\n"
        "Use main as the integration base.\n"
        "Inspect and propose only; no history rewrite has been approved.\n"
        "Preserve staged, unstaged, untracked, and ignored user files.\n"
        "Do not push or read evaluator manifests, reference answers, or other workspaces.\n"
        "The task is supplied inline; no task file needs to be read from the repository.\n"
        "\nFixture task:\n" + task + "\nEnd fixture task.\n"
    )


def user_files(snapshot):
    return {
        name: value
        for name, value in snapshot["files"].items()
        if name not in {".git", ".method"}
        and not name.startswith((".git/", ".method/"))
    }


def require_cwd(repository, recorded):
    """Reject the historical fixture-parent versus actual repo-cwd mismatch."""
    expected = repository.resolve()
    if (
        recorded != str(expected)
        or Path(git(expected, "rev-parse", "--show-toplevel")).resolve() != expected
    ):
        raise ValueError("registered runtime cwd differs from the fixture Git root")


def prepare_cell(directory, case, candidate):
    directory.mkdir()
    repo = fixture_support.build(case, directory / "workspace")
    expected = directory / "workspace/repo"
    require_cwd(expected, str(repo.path.resolve()))
    task = task_input(expected)
    original = observation.snapshot(expected)
    package = expected / ".method"
    package.mkdir()
    (package / "SKILL.md").write_bytes(candidate)
    (expected / ".git/info").mkdir(exist_ok=True)
    with (expected / ".git/info/exclude").open("a", encoding="utf-8") as stream:
        stream.write("\n.method/\n")
    repo.git("config", "rebase.updateRefs", "true")
    repo.git("branch", "sentinel-tip", "HEAD")
    repo.git(
        "branch", "sentinel-intermediate", repo.commits.get("B", repo.commits["M"])
    )
    prepared = observation.snapshot(expected)
    if any(
        original[field] != prepared[field]
        for field in ("head", "tree", "index", "status")
    ):
        raise ValueError("preparation changed approval-relevant fixture state")
    if user_files(original) != user_files(prepared):
        raise ValueError("preparation changed fixture user files")
    prompt = prompt_for(task)
    (directory / "prompt.txt").write_text(prompt, encoding="utf-8")
    metadata = {
        "case": case,
        "cwd": str(expected.resolve()),
        "task": {
            "delivery": "inline",
            "text": task,
            "sha256": hashlib.sha256(task.encode()).hexdigest(),
        },
        "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        "prompt_sha256": sha256(directory / "prompt.txt"),
        "original": original,
        "prepared": prepared,
        "bootstrap": {
            "actor": "evaluator",
            "changes": [
                "ignored .method/SKILL.md",
                "local rebase.updateRefs=true",
                "sentinel-tip and sentinel-intermediate refs",
            ],
            "baseline_preserved": True,
        },
        "rewrite_approval": None,
        "model_execution": "not-run",
        "host_admission": "not-run",
    }
    write_json(directory / "metadata.json", metadata)
    return metadata


def prepare(destination, candidate=DEFAULT_CANDIDATE):
    destination = Path(destination).absolute()
    if destination.resolve().is_relative_to(SOURCE / "skills"):
        raise ValueError(
            "generated evaluation workspaces must stay outside published skills"
        )
    content = Path(candidate).read_bytes()
    if not content.decode("utf-8").strip():
        raise ValueError("candidate skill is empty")
    # Exclusive creation preserves prior evidence, including partial failures and symlinks.
    destination.mkdir()
    registry = {}
    hashes = {}
    for cell, case in CASES.items():
        metadata = prepare_cell(destination / cell, case, content)
        registry[cell] = metadata["cwd"]
        for name in (
            "metadata.json",
            "prompt.txt",
            "workspace/request.md",
            "workspace/manifest.json",
        ):
            relative = f"{cell}/{name}"
            hashes[relative] = sha256(destination / relative)
    write_json(destination / "registry.json", registry)
    hashes["registry.json"] = sha256(destination / "registry.json")
    batch = {
        "schema_version": 1,
        "status": "prepared-only",
        "cells": CASES,
        "candidate_sha256": hashlib.sha256(content).hexdigest(),
        "source_hashes": source_hashes(),
        "artifact_hashes": hashes,
        "model_execution": "not-run",
        "host_admission": "not-run",
    }
    write_json(destination / "batch.json", batch)
    verify(destination)
    return batch


def verify(destination):
    """Check unchanged prepared inputs and repositories before any host setup."""
    destination = Path(destination).resolve()
    batch = read_json(destination / "batch.json")
    if (
        batch["schema_version"] != 1
        or batch["cells"] != CASES
        or batch["status"] != "prepared-only"
    ):
        raise ValueError("unexpected preparation manifest")
    if batch["source_hashes"] != source_hashes():
        raise ValueError("preparation source changed")
    expected_artifacts = {"registry.json"} | {
        f"{cell}/{name}"
        for cell in CASES
        for name in (
            "metadata.json",
            "prompt.txt",
            "workspace/request.md",
            "workspace/manifest.json",
        )
    }
    if set(batch["artifact_hashes"]) != expected_artifacts:
        raise ValueError("preparation artifact inventory differs")
    for relative, expected_hash in batch["artifact_hashes"].items():
        if sha256(destination / relative) != expected_hash:
            raise ValueError(f"prepared input changed: {relative}")
    registry = read_json(destination / "registry.json")
    if set(registry) != set(CASES):
        raise ValueError("runtime registry inventory differs")
    for cell, case in CASES.items():
        directory = destination / cell
        repo = directory / "workspace/repo"
        metadata = read_json(directory / "metadata.json")
        require_cwd(repo, registry[cell])
        require_cwd(repo, metadata["cwd"])
        task = task_input(repo)
        if metadata["case"] != case or metadata["task"]["text"] != task:
            raise ValueError(f"task delivery differs: {cell}")
        if metadata["task"]["sha256"] != hashlib.sha256(task.encode()).hexdigest():
            raise ValueError(f"task hash differs: {cell}")
        if (directory / "prompt.txt").read_text(encoding="utf-8") != prompt_for(task):
            raise ValueError(f"inline prompt differs: {cell}")
        if sha256(repo / ".method/SKILL.md") != batch["candidate_sha256"]:
            raise ValueError(f"candidate package changed: {cell}")
        if observation.snapshot(repo) != metadata["prepared"]:
            raise ValueError(f"prepared repository changed: {cell}")
    return batch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser(
        "prepare", help="Create a fresh four-case batch without launching a model"
    )
    create.add_argument(
        "destination", type=Path, help="New directory with an existing parent"
    )
    create.add_argument(
        "--candidate",
        type=Path,
        default=DEFAULT_CANDIDATE,
        help="Self-contained SKILL.md to copy",
    )
    check = commands.add_parser(
        "verify", help="Check prepared inputs and workspaces are unchanged"
    )
    check.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.destination, args.candidate)
        else:
            verify(args.destination)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        subprocess.SubprocessError,
    ) as error:
        print(f"Evaluation preparation failed: {error}", file=sys.stderr)
        return 1
    print(
        f"{args.command}: four prepared fixtures verified; no model run or rewrite approval"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
