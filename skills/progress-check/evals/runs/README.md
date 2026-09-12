# Reduced run summaries

One JSON file per executed discovery batch, holding every number the
[trial records](../trials/) cite and every response in full.
They exist so a recorded count can be recomputed rather than taken on trust.
`runners/summarise_discovery.py <batch>.json` reads one directly and reprints the per-class counts the records cite.
It buckets by prompt class rather than by case, which is enough for these batches:
a `restart-cc-*` batch holds `restart-en` alone under "English negative" and `restart-zh` alone under "Chinese negative",
so the per-case splits in the records read straight off its output.
`runners/score_over_trigger.py` needs the event streams, which are not committed,
so each launch-only entry carries its verdict instead.

Each file carries the batch name, the run count, the installed skill file hashes, and one entry per run with
its case, class, expected result, model, timings, body-load verdict and evidence, tool names, shell commands,
launches, stop calls, denials, and `final_text` in full.
Launch-only runs also carry an `over_trigger` object with the two signals
[discovery.md](../discovery.md#over-trigger-on-the-launch-only-cases) defines.

The six `2026-09-12-restart-cc-*` batches are 36 runs, not 24.
The `-outside` and `-inrepo` pairs are the re-run's two conditions;
the `-outside-allowed` pair is a control run under a second profile that also allows `run_checks.py`,
and the [record](../trials/2026-09-12-claude-code.md#restart-re-run) says what it controls for.

What is not here: the full event streams, each run's isolated `HOME`, and the host transcripts.
Those stay outside the repository.
The batches' `results.json` files are not committed either, because they record this machine's directory layout.

`runners/reduce_runs.py` writes these files and rewrites machine-specific text to placeholders:
`<run-root>`, `<repo>`, `<home>`, `<tmp>`, `<scratch>`, `<host>`, `<user>`,
and `<id-N>` for each host-assigned conversation or task identifier.
The identifiers are numbered per run, so a response that refers back to its own task still reads correctly,
and no identifier can be matched across runs.
