# Reduced run summaries

One JSON file per executed discovery batch, holding every number the
[trial records](../trials/) cite and every response in full.
They exist so a recorded count can be recomputed rather than taken on trust:
`runners/summarise_discovery.py` and `runners/score_over_trigger.py` read the same fields from the batch they came from.

Each file carries the batch name, the run count, the installed skill file hashes, and one entry per run with
its case, class, expected result, model, timings, body-load verdict and evidence, tool names, shell commands,
launches, stop calls, denials, and `final_text` in full.
Launch-only runs also carry an `over_trigger` object with the two signals
[discovery.md](../discovery.md#over-trigger-on-the-launch-only-cases) defines.

What is not here: the full event streams, each run's isolated `HOME`, and the host transcripts.
Those stay outside the repository.
The batches' `results.json` files are not committed either, because they record this machine's directory layout.

`runners/reduce_runs.py` writes these files and rewrites machine-specific text to placeholders:
`<run-root>`, `<repo>`, `<home>`, `<tmp>`, `<scratch>`, `<host>`, `<user>`,
and `<id-N>` for each host-assigned conversation or task identifier.
The identifiers are numbered per run, so a response that refers back to its own task still reads correctly,
and no identifier can be matched across runs.
