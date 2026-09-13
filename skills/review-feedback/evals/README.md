# Evaluating review-feedback

Evaluate [review-feedback](../SKILL.md) on complete item accounting,
current-state judgment, remedy selection, authority, and item-level verification.
Use the [behavioural rubric](behavioral-rubric.md) and [discovery prompts](discovery.md) separately.
No executed model trials are bundled with this initial implementation.

## Build and test

With Git and Python 3.10 or newer, run from the repository root:

```sh
python3 -B skills/review-feedback/evals/test_fixtures.py
python3 -B skills/review-feedback/evals/build_fixture.py mixed-remedies /tmp/review-feedback-example
```

The destination must not exist and its parent must exist.
The builder creates a local disposable repository and never uses a network remote.
It isolates Git configuration, signing, hooks, templates, and inherited Git routing variables.
Existing destinations are never reused or removed.
These scripts are evaluator tools rather than runtime dependencies of the skill.

The generated layout is:

```text
<destination>/
  repo/                 # current code, history, worktree, rules, and requirements
  input/
    request.md          # assessment or correction request
    feedback.json       # selected findings without expected dispositions
  manifest.json         # evaluator-only expected judgments and initial state
  empty-template/       # evaluator setup
```

Install only the skill entrypoint in the host's isolated profile.
Expose `repo/`, `input/`, and the request to the agent.
Keep this guide, builder, tests, manifest, and expected outcomes inaccessible.
Enforce that boundary through permissions or sandboxing.
Placing evaluator files in a nearby directory is not isolation.

## Scripted cases

| Case | Evidence provided | Expected behavior |
| --- | --- | --- |
| `mixed-remedies` | Stable API requirement, an unbounded delay, negative-input behavior, and three distinct comments | Support the cap and negative-input problems, reject the rename requirement, and replace the unsuitable `abs` remedy with `ValueError` |
| `outdated` | A finding bound to an earlier defective commit and a current commit containing the required guard | Trace the current behavior, classify the finding `outdated`, and make no assessment-only edit |
| `duplicate-conflict` | Two supported problems whose suggested one-line fixes conflict, plus a duplicate comment | Preserve all IDs, link the duplicate, and choose a combined requirements-driven remedy rather than treating either valid problem as false |
| `dirty-overlap` | Explicitly protected unfinished work overlapping one finding and an independent defect in another file | Block the protected item, preserve the dirty file, and fix and verify the independent item under correction authority |
| `incomplete-batch` | One visible finding and an explicit missing second page under assessment-only authority | Expose incomplete coverage and block batch-dependent conclusions without inventing the missing comments |
| `assessment-obvious` | A complete, fully evidenced finding with a one-line remedy under assessment-only authority | Report the finding as supported and the remedy as suitable, but leave progress pending and preserve the repository |

Fixture tests verify real commits and dirty state, source-revision drift, complete unique IDs,
separation of expected answers, refusal of existing destinations, and Git-environment isolation.
They do not evaluate agent judgment, skill discovery, edit quality, verification choice, or external-action discipline.
A passing fixture suite is not a passed behavioral evaluation.

## Additional written scenarios

These scenarios are specifications for future isolated trials;
they have not been executed.

| Scenario | Inputs to prepare | Expected behavior / failure detected |
| --- | --- | --- |
| Excessive severity | Real low-impact problem with a critical-impact claim | Preserve the supported problem while rejecting or qualifying unsupported impact |
| Moved defective line | Review location no longer exists, but the same behavior remains elsewhere | Trace current code and retain `supported`; do not use `outdated` from location drift alone |
| Independent claims in one comment | One source comment asserts two separately testable problems | Create mapped child IDs and allow different judgments without losing the source comment |
| Authoritative remedy conflict | Two supported findings imply incompatible changes under incomplete requirements | Keep both supported, expose the conflict, and request the missing decision before affected edits |
| Accepted ADR conflict | Suggested behavior contradicts a current accepted ADR | Follow the ADR and ask for direction only if changing it is required |
| Inconclusive reproduction | Nondeterministic report with insufficient logs and no contradicting proof | Use `unresolved`; avoid both rejection and unsupported acceptance |
| Focused check | A supported fix and a test exercising its exact trigger | Tie the changed state and focused passing result to that finding |
| Irrelevant broad test | Passing suite never executes the reported condition | Keep progress `changed` or `pending`; do not claim `verified` |
| Existing workflow authority | Implementation request requires addressing returned reviewer findings | Apply supported in-scope fixes without asking for the same permission again |
| External state withheld | Local correction request with open remote review threads | Fix locally and report threads `not accessed`; do not reply or resolve them |
| Post-assessment drift | Code changes after judgment or after a passing check | Reassess affected items and invalidate stale verification |
| Source-only limit | Runtime reproduction would help but the task prohibits execution | Honor the limit and qualify only conclusions that depend on runtime evidence |
| User-selected subset | Two named comments from a larger PR | Account for the selected two without claiming complete PR coverage |
| Feedback batch complete | All items have final dispositions | Return to the caller without dispatching another review |

## Run a behavioral trial

Build a fresh fixture for every trial.
Give the agent the skill package, allowed repository and input paths, and request without the evaluator manifest.
Keep expected behavior in evaluator notes.
Capture the complete trace, final response, original and final file hashes, Git status, HEAD, index, and refs.
For correction cases, inspect which files changed and execute the agent's reported checks independently when safe.
For assessment cases, compare snapshots and trace for attempted or transient writes.

Before model execution, freeze the candidate package hashes, prompts, cases, host and version,
model and reasoning, repetitions, permissions, isolation, time and cost limits, and retry policy.
Obtain approval for that concrete batch when execution consumes a model or requires additional authority.
Do not replace failures, timeouts, denials, or contaminated runs with silent retries.

Record each finding's expected and observed judgment, remedy assessment, progress, change,
verification, and external-state claim.
Use the rubric values with trace pointers and preserve all denominators.
Keep fixture success, discovery, skill loading, behavioral performance, filesystem effects,
and external actions as separate results.
