# Reduced run summaries

One JSON file per executed batch, holding every number the [trial records](../trials/) cite and every final response in full, so a recorded count can be recomputed rather than taken on trust.
`runners/summarise.py <batch>.json` reprints a batch's per-case table, and `runners/score_trial.py <batch>.json` reprints the machine-checkable rubric dimensions for a trial batch.

Each file carries its batch header (model, arm, host version, `skill_source_commit`, installed `skill_hashes`, caps) and `reduced_with_commit`, the commit whose verifier restated it.
Each trial entry carries the case, request, loading state and evidence, tool names, turn and cost totals, the final response, and the verifier output.
Each discovery entry carries the prompt, expected result, repetition, loading verdict and evidence, tool names, turn and cost totals, and the final response.
The two `2026-09-22-baseline-*` files are the no-skill arm, scored by `score_baseline.py`'s prose heuristics rather than the verifier.

What is not here: the full event streams, the fixtures, the evaluator manifests, and the host transcripts.
Those stay outside the repository, and the batches' raw `results.json` files are not committed because they record this machine's directory layout.

`runners/reduce_runs.py` writes these files and rewrites machine-specific text to placeholders:
`<run-root>`, `<evaluator-root>`, `<repo>`, `<home>`, `<tmp>`, `<scratch>`, `<host>`, `<user>`, and `<id-N>` for each host-assigned identifier, numbered per run.
It re-verifies each skill-arm final response with the current verifier against the run's own on-disk manifest, so a verifier fix applies to earlier batches;
results are comparable only between batches judged under the same report contract.
