# Reduced run summaries

One JSON file per executed batch, holding every number the [trial records](../trials/) cite
and every final response in full, so a recorded count can be recomputed rather than taken on trust.
`runners/summarise.py <batch>.json` reprints a batch's per-case table,
and `runners/score_trial.py <batch>.json` reprints the machine-checkable rubric dimensions for a trial batch.

Each trial entry carries the case, model, request, authorization, expected outcome, the plan-match decision
and its reasons, whether the evaluator approved, the trace analysis (loading, tool names, classified commands,
consequential commands before approval, statuses named), turn and cost totals, both final responses,
and the end-state verifier output.
Each discovery entry carries the case, expected result, repetition, loading verdict and evidence,
tool names, shell commands, consequential commands, turn and cost totals, and the final response.

What is not here: the full event streams, the fixtures and their bare remotes, the evaluator manifests,
and the host transcripts.
Those stay outside the repository, and the batches' raw `results.json` files are not committed
because they record this machine's directory layout.

`runners/reduce_runs.py` writes these files and rewrites machine-specific text to placeholders:
`<run-root>`, `<evaluator-root>`, `<repo>`, `<home>`, `<tmp>`, `<scratch>`, `<host>`, `<user>`,
and `<id-N>` for each host-assigned identifier, numbered per run.
It also recomputes each trial's stated verdict from the final responses with the current pattern.
