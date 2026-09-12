"""Test the parts of the evaluation runners that failed silently when they broke.

The prompt-table parser matches rows positionally, so an editorial change to
discovery.md can drop a case with no error at all; the launch and stop regexes
decide what a run is scored as, and a near-miss looks like a model result.
"""

import os
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent / "runners"))

import common  # noqa: E402

# The prompt set as discovery.md defines it.  Change this list deliberately, in the
# same commit as the table, and re-run every trial whose numbers the change affects.
EXPECTED_CASES = {
    "progress-en": "load",
    "stuck-en": "load",
    "done-en": "load",
    "progress-zh": "load",
    "stuck-zh": "load",
    "done-zh": "load",
    "explicit-en": "load",
    "explicit-zh": "load",
    "launch-en": "record",
    "launch-zh": "record",
    "tests-en": "record",
    "kill-en": "skip",
    "kill-zh": "skip",
    "concept-en": "skip",
    "concept-zh": "skip",
    "restart-en": "skip",
    "restart-zh": "skip",
    "log-en": "skip",
}


class PromptSetTests(unittest.TestCase):
    def setUp(self):
        self.cases = common.prompt_set()

    def test_every_case_is_parsed_exactly_once(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(EXPECTED_CASES))
        self.assertEqual(sorted(ids), sorted(EXPECTED_CASES))
        self.assertEqual(len(set(ids)), len(ids))

    def test_expected_column_matches(self):
        self.assertEqual({c["id"]: c["expected"] for c in self.cases}, EXPECTED_CASES)

    def test_every_case_carries_a_class_and_a_prompt(self):
        for case in self.cases:
            self.assertTrue(case["class"].strip(), case["id"])
            self.assertTrue(case["prompt"].strip(), case["id"])

    def test_the_header_row_is_not_a_case(self):
        self.assertNotIn("ID", [case["id"] for case in self.cases])

    def test_an_empty_table_fails_loudly(self):
        empty = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        table = empty / "discovery.md"
        table.write_text("# no table here\n", "utf-8")
        with self.assertRaises(SystemExit):
            common.prompt_set(table)


class SelectTests(unittest.TestCase):
    def test_an_unknown_case_id_fails_loudly(self):
        with self.assertRaises(SystemExit):
            common.select(common.prompt_set(), {"launch-en", "no-such-case"})

    def test_an_empty_selection_keeps_every_case(self):
        cases = common.prompt_set()
        self.assertEqual(common.select(cases, set()), cases)

    def test_case_ids_parses_a_comma_separated_argument(self):
        self.assertEqual(
            common.case_ids("launch-en, tests-en"), {"launch-en", "tests-en"}
        )
        self.assertEqual(common.case_ids(""), set())


class LaunchPatternTests(unittest.TestCase):
    LAUNCHES = (
        "python sync_index.py --interval 5 --duration 600",
        "python3 run_checks.py unit",
        "nohup python sync_index.py --duration 600 &",
        "setsid python3 sync_index.py &",
        "cd /tmp && python run_checks.py unit",
        "/usr/bin/python3.11 sync_index.py",
        "python -u sync_index.py --interval 5",
        "echo starting; python run_checks.py unit",
    )
    NOT_LAUNCHES = (
        "I will run python sync_index.py shortly",  # prose, not a command
        "cat sync_index.py",
        "ls -la sync_index.py run_checks.py",
        "grep -n duration sync_index.py",
        "python other_script.py",
        "pythonic sync_index.py",
    )

    def test_an_interpreter_invoking_a_fixture_script_is_a_launch(self):
        for command in self.LAUNCHES:
            with self.subTest(command=command):
                self.assertIsNotNone(common.LAUNCH_RE.search(command))

    def test_naming_the_script_is_not_a_launch(self):
        for command in self.NOT_LAUNCHES:
            with self.subTest(command=command):
                self.assertIsNone(common.LAUNCH_RE.search(command))


class StopPatternTests(unittest.TestCase):
    STOPS = (
        "kill -TERM 1234",
        "pkill -9 node",
        "killall python3",
        "sudo kill 1234",
        "ps aux | grep node; kill 1234",
        "cd /tmp && killall node",
    )
    NOT_STOPS = (
        "ps aux | grep -i kill",
        "grep -rn 'kill' skills/",
        "python run_checks.py kill",
        "echo do not kill anything",
        "find . -name 'killall*'",
    )

    def test_running_a_termination_command_is_a_stop(self):
        for command in self.STOPS:
            with self.subTest(command=command):
                self.assertIsNotNone(common.STOP_RE.search(command))

    def test_the_word_as_an_argument_is_not_a_stop(self):
        for command in self.NOT_STOPS:
            with self.subTest(command=command):
                self.assertIsNone(common.STOP_RE.search(command))


class RequiredPathTests(unittest.TestCase):
    def test_a_missing_required_path_fails_loudly(self):
        with self.assertRaises(SystemExit):
            common.required_path(
                "the run root", None, "PROGRESS_CHECK_NO_SUCH_VARIABLE"
            )

    def test_a_nonexistent_required_path_fails_loudly(self):
        with self.assertRaises(SystemExit):
            common.required_path("the run root", "/no/such/path/anywhere")

    def test_a_path_inside_this_checkout_is_refused(self):
        with self.assertRaises(SystemExit):
            common.refuse_git_tree("the run root", Path(__file__).parent)

    def test_the_check_uses_the_nearest_existing_ancestor(self):
        # The run root does not exist yet; it is still inside this checkout.
        with self.assertRaises(SystemExit):
            common.refuse_git_tree(
                "the run root", Path(__file__).parent / "does/not/exist"
            )

    def test_the_refusal_can_be_overridden_on_purpose(self):
        with unittest.mock.patch.dict(os.environ, {"ALLOW_GIT_TREE": "1"}):
            self.assertEqual(
                common.refuse_git_tree("the run root", Path(__file__).parent),
                Path(__file__).parent,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
