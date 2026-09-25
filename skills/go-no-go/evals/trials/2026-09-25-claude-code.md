# Executed runs: Claude Code, 2026-09-22 to 2026-09-26

The first executed evaluation of [go-no-go](../../SKILL.md): a no-skill baseline, then three full trial rounds with corrections between them, targeted re-runs, and two discovery batches.
All runs were driven by the [runners](../runners/) on disposable fixtures and checked by `verify_report.py`.
Nothing here is a reliability rate, and no result transfers to other hosts, models, or revisions.

## Candidate and environment

| Item | Value |
| --- | --- |
| Host | Claude Code 2.1.278 (baseline) and 2.1.282 (all other batches), print mode over stream-json, `bypassPermissions`, so the skill's own read-only rule was the only gate |
| Models | `claude-sonnet-5` and `claude-haiku-4-5-20251001`, default effort |
| Caps | trials: 60 turns, US$1.50, 900 s per run; discovery: 10 turns, US$1.00 per run |
| Profile | an isolated `CLAUDE_CONFIG_DIR` holding only credentials and `skills/go-no-go/SKILL.md`, re-synced before each round; the account also synced its built-in skills (docs, pdf, xlsx, and the like) into it |
| Repetitions | one run per case per round; five runs per model for the last `preauthorized-go` check; three per discovery prompt; declared before each batch and none replaced or retried |
| Batch approval | every batch below was approved as a concrete batch before it ran |
| Evidence kept | event streams, fixtures, and evaluator manifests under the run roots, outside the repository |

Each reduced trial batch under [runs/](../runs/) records its `skill_source_commit`, the installed `skill_hashes`, and `reduced_with_commit`;
discovery batches record only the installed hash, matched to its commit in the table below.
The reducer re-verifies every final response with the verifier at `reduced_with_commit` against each run's own on-disk manifest, so counts are comparable only between batches judged under the same report contract.
In particular, `trial1` was written under the labelled `Closing: go: …` contract that `e8ba64a` replaced, so its reduced `closing_content` results understate it.

## Rounds

| Batch | SKILL.md | What changed before it |
| --- | --- | --- |
| `2026-09-22-baseline-*` | none | no-skill baseline, 4 cases |
| `smoke1-haiku`, `trial1-*`, `discovery-*` | `8eabcef` (sha256 `1ea5781a…`) | the committed skill |
| `smoke2-haiku`, `trial2-*` | `e8ba64a` (`7daa688e…`) | `d023d5d` verifier fixes; `e8ba64a` plain-text report, standalone markers, unlabelled `Closing` (D19, D20), revision copied from command output, pre-authorization ends at `Closing` |
| `iter3-sonnet` to `iter6-sonnet` | `9faf629` (`5595230c…`) | `9faf629` fixture second-defect removal, ideas as `input/idea.md` (D21), read rule files first; `iter4` to `iter6` ran on fixture edits later committed as `816d2bc` |
| `trial3-*` | `816d2bc` (`5595230c…`) | `816d2bc` further fixture fixes |
| `2026-09-26-d17-*` | `f9e1b16` (`c6e31fdd…`) | `a84af90` description; `f9e1b16` pre-authorization rule moved to the start of the verdict section |
| `2026-09-26-rediscovery-*` | `f9e1b16` (`c6e31fdd…`) | as above |

## Trial results

Strict pass is the verifier's overall result; verdict is the `Verdict` line (or, for `ambiguous-subject`, a `Stopped` report with no verdict).

| Batch | Runs | Strict pass | Verdict correct | Repository changed | Cost (US$) |
| --- | --- | --- | --- | --- | --- |
| trial1-sonnet | 24 | 2 | 4 | 1 | 6.30 |
| trial1-haiku | 24 | 0 | 0 | 0 | 2.16 |
| trial2-sonnet | 24 | 11 | 23 | 0 | 6.06 |
| trial2-haiku | 24 | 2 | 22 | 0 | 2.22 |
| trial3-sonnet | 24 | 13 | 20 | 1 | 6.15 |
| trial3-haiku | 24 | 12 | 20 | 1 | 2.19 |

In `trial1`, most verdicts were correct but unparseable:
Sonnet wrapped 20 of 24 reports in a code fence, copying the template's presentation, and the verifier ignores fenced lines;
Haiku decorated field labels with Markdown bold.
An analysis-only pass that unwrapped the fence and stripped the bold before verifying found Sonnet's verdicts right in 22 of 24 and Haiku's in 20 of 24.
That pass is not part of the verifier, and its numbers are not in the reduced batch.
The baseline, before the skill existed, was right in 3 of 4 on both models; both said `go` on `single-fixable-defect`.

## Findings

**Pre-authorization (D17) is not reliably held.**
When the request itself says "if it's a go, implement step 1 immediately," the skill must record that instruction and end at `Closing`.
Across all `preauthorized-go` runs, 8 of 16 edited `inventory/report.py` after writing the report:
Sonnet in `trial1`, `trial3`, and 3 of 5 `d17` runs; Haiku in `trial3` and 2 of 5 `d17` runs.
Moving the rule to the start of the verdict section (`f9e1b16`) did not change the rate.
Several runs filled `Pending owner confirmation` correctly and wrote the exact `Closing` sentence, then implemented anyway.
No other case in any batch changed the repository.
Where read-only must be guaranteed, run the skill under the host's read-only permissions (for example Claude Code's plan mode) rather than relying on the skill text.

**Fixtures carried unplanted defects.**
Sonnet's extra blockers in `trial2` were mostly real: an export that could not see the data it claimed to filter, a rename that broke unmentioned test imports, a SKU migration with undecided collisions, a database whose "duplicate" column held data found nowhere else.
`9faf629` and `816d2bc` removed them; one of the fixes itself introduced a defect (`splitlines()` breaking quoted newlines) that Sonnet found in `iter5`.

**Haiku fabricates revisions.**
In `trial2`, all 9 wrong Haiku revisions were written without any `hash-object` command in the trace.
In `trial3`, one wrong revision was written that way, and three reports had no parseable revision.
Haiku also failed the required-field check in 7 reports in each of `trial2` and `trial3`, and did not stop on `ambiguous-subject` in any round.

**Other residuals.**
Both models still attach notes to markers (`two-way (…)`, `verified: …`), which the verifier rejects by design (D20).
Verdicts on `tier-two-way-unverified`, `tier-latent-claim`, and `authored-one-way` varied between rounds on unchanged fixtures.
`final_text` holds only the last assistant message, so a report followed by more activity is not itself verified; such runs still fail.

## Discovery

| Batch | Expected load: loaded | Expected skip: skipped | Turn cap reached | Cost (US$) |
| --- | --- | --- | --- | --- |
| discovery-sonnet | 24 of 27 | 19 of 21 | 2 | 9.16 |
| discovery-haiku | 11 of 27 | 17 of 21 | 4 | 2.25 |
| rediscovery-sonnet | 27 of 27 | 19 of 21 | 0 | 8.36 |
| rediscovery-haiku | 14 of 27 | 18 of 21 | 6 | 2.69 |

A run that reached the 10-turn cap exits non-zero; `summarise.py` lists it as crashed, and it is counted here as neither loaded nor skipped.
In `discovery-haiku`, the misses on short prompts (`ready-en`, `proceed-en`, `worth-zh`, `go-no-go-en`) named go-no-go as the right skill and asked which plan was meant instead of loading it; `a84af90` tells the model to load it first.
After it, Haiku loaded on `go-no-go-en` in 3 of 3 runs (was 1), `ready-en` 2 (was 0), and `proceed-en` 1 (was 0), but still 0 on `worth-zh`.
The rediscovery runs also carry `f9e1b16`'s pre-authorization change, which does not touch the description.

## Limits

One run per case per round cannot separate a change's effect from run-to-run variation; only `preauthorized-go` was repeated.
The fixtures were revised between rounds, so `trial2` and `trial3` do not judge identical inputs.
All counts come from one host and two models.
