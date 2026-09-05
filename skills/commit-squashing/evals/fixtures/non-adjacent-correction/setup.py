"""M -- A -- B -- C: a correction to X follows independent behavior Y."""

REQUEST = "Group this branch into coherent commits before review; use main as the base."


def populate(repo):
    repo.start()
    repo.commit(
        "A",
        "Add bounded retry",
        {
            "client/retry.py": "def attempts(limit):\n    return list(range(limit + 2))\n",
            "check_retry.py": "from client.retry import attempts\nassert attempts(2)[0] == 0\n",
        },
    )
    repo.commit(
        "B",
        "Add JSON log output",
        {
            "log_output.py": "import json\n\ndef render(message):\n    return json.dumps({'message': message})\n",
            "check_logs.py": "import json\nfrom log_output import render\nassert json.loads(render('ok')) == {'message': 'ok'}\n",
        },
    )
    repo.commit(
        "C",
        "Correct retry exhaustion",
        {
            "client/retry.py": "def attempts(limit):\n    return list(range(limit + 1))\n",
            "check_retry.py": "from client.retry import attempts\nassert attempts(2)[0] == 0\nassert attempts(0) == [0]\n",
        },
    )
