"""M -- A -- B -- C: three independent changes, including same-file edits."""

REQUEST = "Reduce this branch to the fewest atomic commits; use main as the base."


def populate(repo):
    shared = (
        "\n\ndef retry_count():\n    return RETRIES\n"
        "\n\ndef request_name():\n    return 'request'\n\n\n"
    )
    repo.start(
        {
            "client/session.py": "RETRIES = 4\n" + shared + "TIMING = False\n",
            "client/endpoint.py": "def parse(value):\n    result = value.strip()\n    return result\n",
        }
    )
    repo.commit(
        "A",
        "Fix retry exhaustion",
        {
            "client/session.py": "RETRIES = 3\n" + shared + "TIMING = False\n",
            "check_retry.py": "from client.session import RETRIES\nassert RETRIES == 3\n",
        },
    )
    repo.commit(
        "B",
        "Add request timing",
        {
            "client/session.py": "RETRIES = 3\n" + shared + "TIMING = True\n",
            "check_timing.py": "from client.session import TIMING\nassert TIMING is True\n",
        },
    )
    repo.commit(
        "C",
        "Simplify endpoint parsing",
        {
            "client/endpoint.py": "def parse(value):\n    return value.strip()\n",
            "check_endpoint.py": "from client.endpoint import parse\nassert parse(' localhost ') == 'localhost'\n",
        },
    )
