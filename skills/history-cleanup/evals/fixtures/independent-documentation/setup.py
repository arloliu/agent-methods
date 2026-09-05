"""M -- A -- B -- C -- D -- E: retry feature plus unrelated endpoint documentation."""

REQUEST = "Prepare this branch for review by squashing its iterative commits; use main as the base."


def populate(repo):
    repo.start(
        {
            "client/endpoint.py": 'DEFAULT_ENDPOINT = "https://api.example.invalid/v2"\n',
            "endpoint.md": "The default endpoint uses API v1.\n",
        }
    )
    repo.commit(
        "A",
        "Add retry limit",
        {
            "client/retry.py": "def attempts(limit):\n    return list(range(limit + 2))\n"
        },
    )
    repo.commit(
        "B",
        "WIP",
        {
            "client/retry.py": "def attempts(limit):\n    return list(range(limit + 1))\n"
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
            "retry.md": "The retry limit excludes the initial attempt.\nZero disables retries.\n"
        },
    )
    repo.commit(
        "E",
        "Correct default endpoint documentation",
        {"endpoint.md": "The default endpoint uses API v2.\n"},
    )
