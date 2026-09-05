"""M forks to A and S1/S2; merge J records a real conflict resolution before C."""

REQUEST = "Squash the fixups before review, using main as the base."


def populate(repo):
    repo.start({"settings.py": "MODE = 'base'\n"})
    repo.commit(
        "A",
        "Add bounded retry",
        {
            "settings.py": "MODE = 'retry'\n",
            "retry.py": "def retries(value):\n    return min(value, 4)\n",
        },
    )
    repo.git("checkout", "-b", "topic", repo.commits["M"])
    repo.commit(
        "S1",
        "Add JSON log output",
        {
            "settings.py": "MODE = 'json'\n",
            "log_output.py": "import json\n\ndef render(value):\n    return json.dumps(value)\n",
        },
    )
    repo.commit(
        "S2",
        "Test JSON log output",
        {
            "check_logs.py": "from log_output import render\nassert render({'ok': True}) == '{\"ok\": true}'\n",
        },
    )
    repo.git("checkout", "feature")
    result = repo.run("git", "merge", "--no-ff", "--no-commit", "topic", check=False)
    if (
        result.returncode != 1
        or repo.git("diff", "--name-only", "--diff-filter=U") != "settings.py"
    ):
        raise ValueError("Expected the fixture's settings.py merge conflict")
    repo.commit("J", "Merge JSON output", {"settings.py": "MODE = 'retry-json'\n"})
    repo.commit(
        "C",
        "Correct retry cap",
        {
            "retry.py": "def retries(value):\n    return min(value, 3)\n",
            "check_retry.py": "from retry import retries\nassert retries(8) == 3\n",
        },
    )
