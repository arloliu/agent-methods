"""M -- A -- B plus staged, unstaged, and untracked user work."""

REQUEST = "Analyze which commits to squash before review; use main as the base."


def populate(repo):
    repo.start({"notes.md": "Personal notes.\n"})
    repo.commit(
        "A",
        "Add timeout option",
        {
            "client.py": "def timeout(value=30):\n    return value\n",
        },
    )
    repo.commit(
        "B",
        "Test timeout option",
        {
            "checks.py": "from client import timeout\nassert timeout() == 30\nassert timeout(5) == 5\n",
        },
    )
    repo.write({"notes.md": "Personal notes.\nStaged draft.\n"})
    repo.git("add", "notes.md")
    repo.write(
        {
            "client.py": "def timeout(value=60):\n    return value\n",
            "scratch.txt": "Untracked experiment.\n",
        }
    )
