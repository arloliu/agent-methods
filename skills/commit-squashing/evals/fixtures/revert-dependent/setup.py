"""M -- A -- B -- R -- D: cancellation hides B's temporary import dependency."""

REQUEST = (
    "Can the reverted experiment be removed while keeping B and D as separate review commits?\n"
    "B is 'Add bounded retry'; D is 'Inline retry cap'.\n"
    "Use main as the base."
)


def populate(repo):
    repo.start()
    repo.commit(
        "A",
        "Add retry cap helper",
        {
            "retry_limit.py": "def cap_retries(value):\n    return min(value, 3)\n",
        },
    )
    repo.commit(
        "B",
        "Add bounded retry",
        {
            "client.py": "from retry_limit import cap_retries\n\ndef retries(value):\n    return cap_retries(value)\n",
            "checks.py": "from client import retries\nassert retries(8) == 3\nassert retries(1) == 1\n",
        },
    )
    repo.commit("R", 'Revert "Add retry cap helper"', {"retry_limit.py": None})
    repo.commit(
        "D",
        "Inline retry cap",
        {
            "client.py": "def retries(value):\n    return min(value, 3)\n",
        },
    )
