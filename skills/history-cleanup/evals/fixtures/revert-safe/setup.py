"""M -- A -- B -- R -- C: the experiment cancels without surviving dependencies."""

REQUEST = "Clean up the experiments and fixups before review; use main as the base."


def populate(repo):
    repo.start(
        {
            "log_time.py": "def timestamp():\n    return '2000-01-01T00:00:00'\n",
        }
    )
    repo.commit(
        "A",
        "Add experimental cache toggle",
        {
            "cache.py": "ENABLED = False\n",
            "check_cache.py": "from cache import ENABLED\nassert ENABLED is False\n",
        },
    )
    repo.commit(
        "B",
        "Fix log timestamp",
        {
            "log_time.py": "def timestamp():\n    return '2000-01-01T00:00:00Z'\n",
            "checks.py": "from log_time import timestamp\nassert timestamp().endswith('Z')\n",
        },
    )
    repo.commit(
        "R",
        'Revert "Add experimental cache toggle"',
        {
            "cache.py": None,
            "check_cache.py": None,
        },
    )
    repo.commit(
        "C",
        "Document timestamp timezone",
        {
            "timestamp.md": "Log timestamps use UTC with a trailing Z.\n",
        },
    )
