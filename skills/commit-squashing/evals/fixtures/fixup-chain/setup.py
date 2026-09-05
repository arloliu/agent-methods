"""M -- A -- B -- C -- D: implementation, correction, tests, and documentation."""

REQUEST = "Prepare this branch for review by squashing its iterative commits; use main as the base."


def populate(repo):
    repo.start()
    repo.commit(
        "A",
        "Add retry limit",
        {
            "client/retry.py": "def attempts(limit):\n    return list(range(limit + 2))\n",
        },
    )
    repo.commit(
        "B",
        "WIP",
        {
            "client/retry.py": "def attempts(limit):\n    return list(range(limit + 1))\n",
        },
    )
    repo.commit(
        "C",
        "fix tests",
        {
            "checks.py": "from client.retry import attempts\nassert attempts(0) == [0]\nassert attempts(2) == [0, 1, 2]\n",
        },
    )
    repo.commit(
        "D",
        "Document retry limit",
        {
            "retry.md": "The retry limit excludes the initial attempt.\nZero disables retries.\n",
        },
    )
