"""O -- N forks to main at L and feature at A/B; master forks from O at K."""

REQUEST = "Squash this branch into atomic commits before review."


def populate(repo):
    repo.start(label="O")
    repo.commit("N", "Add compatibility setting", {"compat.py": "LEGACY = True\n"})
    repo.git("branch", "--force", "main", repo.commits["N"])
    repo.git("checkout", "main")
    repo.commit(
        "L",
        "Document integration branch",
        {"integration.md": "Integrate new changes here.\n"},
    )
    repo.git("checkout", "-b", "master", repo.commits["O"])
    repo.commit(
        "K",
        "Document maintenance branch",
        {"maintenance.md": "Maintain older releases here.\n"},
    )
    repo.git("checkout", "feature")
    repo.commit("A", "Add retry limit", {"retry.py": "LIMIT = 4\n"})
    repo.commit(
        "B",
        "Correct retry limit",
        {
            "retry.py": "LIMIT = 3\n",
            "checks.py": "from retry import LIMIT\nassert LIMIT == 3\n",
        },
    )
