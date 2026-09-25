"""Test the go-no-go runner helpers without starting an agent session."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "runners"))
import reduce_runs  # noqa: E402
import score_trial  # noqa: E402
import summarise  # noqa: E402
from common import (  # noqa: E402
    REPO,
    case_ids,
    final_text,
    loaded,
    prompt_set,
    refuse_git_tree,
    required_path,
    resolve_profile,
    select,
    tool_uses,
)

EVENTS = [
    {"type": "system", "subtype": "init"},
    {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "text", "text": "Reading the plan."},
                {
                    "type": "tool_use",
                    "name": "Read",
                    "input": {"file_path": "docs/plan.md"},
                },
            ]
        },
    },
    {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "Verdict: go"}]},
    },
    {"type": "result", "subtype": "success", "total_cost_usd": 0.1},
]


class RunnerHelperTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="go-no-go-runners-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_final_text_is_the_last_assistant_text_block(self):
        self.assertEqual(final_text(EVENTS), "Verdict: go")
        self.assertEqual(final_text([]), "")

    def test_tool_uses_lists_calls_in_order(self):
        self.assertEqual(
            tool_uses(EVENTS),
            [{"name": "Read", "input": {"file_path": "docs/plan.md"}}],
        )

    def test_case_ids_split_and_trim(self):
        self.assertEqual(
            case_ids("sound-plan, missing-symbol,"), {"sound-plan", "missing-symbol"}
        )
        self.assertEqual(case_ids(""), set())

    def test_paths_are_required_and_never_inside_a_checkout(self):
        with self.assertRaises(SystemExit):
            required_path("the run root", None, "GO_NO_GO_UNSET_VARIABLE")
        with self.assertRaises(SystemExit):
            refuse_git_tree("the run root", REPO / "tmp" / "runs")
        self.assertEqual(
            refuse_git_tree("the run root", self.root / "runs"), self.root / "runs"
        )

    def test_loaded_detects_a_skill_call_or_a_body_read(self):
        skill_call = [
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Skill",
                            "input": {"skill": "go-no-go"},
                        }
                    ]
                },
            }
        ]
        self.assertEqual(loaded(tool_uses(skill_call))[0], "complete")
        self.assertEqual(loaded(tool_uses(EVENTS))[0], "not-loaded")

    def test_prompt_set_parses_the_discovery_table(self):
        rows = prompt_set()
        ids = {row["id"] for row in rows}
        self.assertIn("explicit-en", ids)
        self.assertIn("write-plan-en", ids)
        expected = {row["id"]: row["expected"] for row in rows}
        self.assertEqual(expected["explicit-en"], "load")
        self.assertEqual(expected["write-plan-en"], "skip")

    def test_select_filters_by_case_id_and_rejects_unknown_ones(self):
        rows = prompt_set()
        chosen = select(rows, {"explicit-en"})
        self.assertEqual([row["id"] for row in chosen], ["explicit-en"])
        with self.assertRaises(SystemExit):
            select(rows, {"no-such-case"})

    def test_baseline_profile_needs_credentials_and_must_not_hold_the_skill(self):
        profile = self.root / "profile"
        profile.mkdir()
        with self.assertRaises(SystemExit):
            resolve_profile(str(profile), with_skill=False)
        (profile / ".credentials.json").write_text("{}", encoding="utf-8")
        self.assertEqual(resolve_profile(str(profile), with_skill=False), profile)
        with self.assertRaises(SystemExit):
            resolve_profile(str(profile), with_skill=True)
        skill = profile / "skills" / "go-no-go"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("", encoding="utf-8")
        with self.assertRaises(SystemExit):
            resolve_profile(str(profile), with_skill=False)
        self.assertEqual(resolve_profile(str(profile), with_skill=True), profile)


class ResultProcessingTests(unittest.TestCase):
    """Batch dispatch and scoring must key off explicit shape, not the first record."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="go-no-go-results-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_summarise_uses_arm_not_the_first_record_shape(self):
        batch = {
            "arm": "skill",
            "results": [
                {"case": "a-crashed-first", "error": "boom"},
                {
                    "case": "sound-plan",
                    "loaded": "complete",
                    "final_text": "Verdict: go",
                    "verifier": {"pass": True, "checks": {}},
                    "cost_usd": 0.1,
                },
            ],
        }
        path = self.root / "results.json"
        path.write_text(json.dumps(batch), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sys.argv = ["summarise.py", str(path)]
            summarise.main()
        printed = out.getvalue()
        self.assertIn("ERROR boom", printed)
        self.assertIn("verifier=pass", printed)
        self.assertNotIn("Traceback", printed)

    def test_summarise_refuses_a_baseline_batch_instead_of_misrouting(self):
        batch = {"arm": "baseline", "results": [{"case": "sound-plan", "score": {}}]}
        path = self.root / "results.json"
        path.write_text(json.dumps(batch), encoding="utf-8")
        sys.argv = ["summarise.py", str(path)]
        with self.assertRaises(SystemExit):
            summarise.main()

    def test_discovery_does_not_score_a_crashed_run_as_pass(self):
        # `not-loaded` against `expected="skip"` is exactly the combination the old
        # loaded-only heuristic scored "pass" -- the crash must preempt that, not agree with it.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            summarise.discovery(
                [
                    {
                        "case": "write-plan-en",
                        "rep": 1,
                        "expected": "skip",
                        "returncode": 1,
                        "loaded": "not-loaded",
                        "tool_names": [],
                    }
                ],
                detail=False,
            )
        printed = out.getvalue()
        self.assertIn("CRASHED", printed)
        self.assertNotIn("skip    pass", printed)

    def test_reduce_runs_leaves_baseline_records_unrestated_but_restates_skill_records(
        self,
    ):
        from build_fixture import build

        fixture = build("sound-plan", self.root / "sound-plan")
        evaluator = self.root.parent / (self.root.name + "-evaluator")
        evaluator.mkdir(parents=True)
        (evaluator / "sound-plan.json").write_text(
            (fixture / "manifest.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        manifest = json.loads((fixture / "manifest.json").read_text(encoding="utf-8"))
        text = (
            f"Subject: {manifest['subject']['path']} at blob {manifest['subject']['revision']}; "
            f"revision {manifest['subject']['revision']}\nVerdict: go\n"
        )

        baseline_entry = {"case": "sound-plan", "arm": "baseline", "final_text": text}
        result = reduce_runs.restate_verifier(dict(baseline_entry), self.root)
        self.assertEqual(result, baseline_entry)
        self.assertNotIn("verifier", result)

        skill_entry = {"case": "sound-plan", "arm": "skill", "final_text": text}
        restated = reduce_runs.restate_verifier(dict(skill_entry), self.root)
        self.assertIn("verifier", restated)

    def test_score_trial_counts_errored_runs_separately_from_dimensions(self):
        batch = {
            "model": "test-model",
            "results": [
                {"case": "a-crashed", "error": "boom"},
                {
                    "case": "sound-plan",
                    "loaded": "complete",
                    "final_text": "Verdict: go",
                    "verifier": {
                        "pass": True,
                        "checks": {"verdict": {"pass": True, "observed": "go"}},
                    },
                },
            ],
        }
        path = self.root / "results.json"
        path.write_text(json.dumps(batch), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            score_trial.main([str(path)])
        printed = out.getvalue()
        self.assertIn("scheduled=2, errored=1", printed)
        self.assertIn("ERROR boom", printed)


if __name__ == "__main__":
    unittest.main()
