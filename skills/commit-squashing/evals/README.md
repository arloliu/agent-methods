# Evaluating commit-squashing

These are human-readable behavioral scenarios for [commit-squashing](../SKILL.md).
The [fixtures](fixtures/) turn the base cases into reproducible local Git repositories.
The scripts use Python's standard library and Git; no packages or agent-specific runner are required.
The fixture tests check graphs and reference transformations, not whether an agent follows the skill.

[GitHub Actions](../../../.github/workflows/ci.yml) runs the suite on Linux and macOS with Python 3.10 and 3.14.
CI also checks Python lint and formatting using a pinned Ruff version.
It runs on pushes to `main`, pull requests, and manual dispatch.

## Test the fixtures

From the repository root:

```sh
python3 -B skills/commit-squashing/evals/test_fixtures.py
```

The script uses `unittest` and creates disposable repositories in the operating system's temporary directory.
It removes those repositories on completion and returns a nonzero exit status on failure.
Tests exercise real cherry-picks, squashes, a merge conflict and reconstruction, intermediate program checks,
tree identity including file modes, dirty index/worktree separation, base ambiguity, and reproducible commit IDs.
They also check that fixture generation refuses existing destinations and ignores inherited Git routing/configuration.
All reference transformations run only in repositories created by the test process.
The test script cannot rewrite a supplied repository.

Run one test with the standard `unittest` selector, for example:

```sh
python3 -B skills/commit-squashing/evals/test_fixtures.py FixtureTests.test_safe_revert_pair_can_be_removed
```

## Build a fixture for an agent

Each directory contains a `setup.py` with concrete file contents, commit construction, and a user request.
These are trusted repository scripts, not data files or package installers.
Use [build_fixture.py](build_fixture.py) to construct one:

```sh
python3 -B skills/commit-squashing/evals/build_fixture.py fixup-chain /tmp/commit-squashing-example
```

The destination must not exist, and its parent must already exist.
Paths containing spaces are supported when quoted by the shell.
An existing destination is never reused or deleted; a failed build can leave a partial directory for diagnosis.
Choose another destination for the next run.

The generated layout is:

```text
<destination>/
├── repo/             # agent workspace, containing a real .git directory
├── request.md        # user request to give the agent
├── manifest.json     # evaluator baseline: original hashes, tree, refs, and status
└── empty-template/   # empty Git template and disabled hook directory
```

Give the agent only `repo/`, the skill, and the text of `request.md`.
Keep the manifest, setup scripts, test source, and expected behavior outside its task context.
The manifest is the evaluator's baseline, not an approved rewrite plan or an instruction to the agent.
Fixture repositories have no remotes, backup refs, or expected-group labels.
The builder fixes author identity and timestamps, uses SHA-1 repositories,
and isolates Git configuration, templates, signing, and hooks for reproducible construction.
Generated commits belong only to the fixture; the source repository's history is untouched.

| Fixture | Scenario | Reference outcome or stopping condition |
| --- | --- | --- |
| `fixup-chain` | [Fixup chain](fixup-chain.md) | A+B+C+D form one group |
| `non-adjacent-correction` | [Non-adjacent correction](non-adjacent-correction.md) | A+C, then independent B |
| `revert-safe` | [Safe revert pair](revert-pair.md#safe-cancellation) | Remove A/R after approval; group B+C |
| `revert-dependent` | [Dependent revert pair](revert-pair.md#cancellation-with-a-dependent-intermediate-commit) | Removing A/R alone leaves B broken |
| `merge-boundary` | [Merge boundary](merge-boundary.md) | Require an explicitly approved parent map and merge strategy |
| `dirty-worktree` | [Dirty worktree](dirty-worktree.md) | Analyze committed A/B; preserve staged, unstaged, and untracked work |
| `independent-changes` | [Independent changes](independent-changes.md) | Preserve all three commits; no rewrite needed |
| `ambiguous-base` | [Ambiguous base](ambiguous-base.md) | Ask whether to use main or master before grouping |

Fixture paths use small Python examples; some differ from the conceptual paths in the scenario prose.
The graph and behavioral relationships are the contract.
Additional prose variants, including multiple authors, signatures, and stale approval, remain manual cases.

## Run a case

Build a fresh fixture for each trial, or construct a disposable repository for a prose-only variant.
Letters denote commits, `M` denotes the integration merge-base, and graph edges run from parent to child.
Unless a case says otherwise, use a clean attached feature branch, a user-supplied base at `M`,
one author, unsigned commits, plain sentence subjects, and no upstream or remote.

Give the agent the skill, repository, and user request.
Keep expected behavior and failure criteria in the evaluator's notes rather than the agent's task prompt.
Observe inspection and the displayed plan before providing any approval.
For execution checks, approve a specific displayed plan in the disposable repository and record that approval.
Never point an execution trial at a real shared branch or remote.

The tests include a deliberately invalid intermediate history for `revert-dependent`.
Its final tree matches even though its first surviving commit fails with a missing import.
They also demonstrate B+D as a possible alternative;
that does not authorize an agent to override the requested grouping.
Approval timing, appropriate clarification, and publication boundaries require transcript review.
A passing fixture suite is not a passed agent evaluation.

Record the case and variant, agent/tool version, inspected HEAD and tree IDs, observed plan, approvals,
commands or transcript, verification output, and pass/fail/not-run result with reasons.
Judge decisions and repository state rather than exact phrasing.

## Shared checks

Before approval, HEAD, refs, index, and working files must remain unchanged.
No fetch, backup creation, automatic stash, or history rewrite belongs in inspection.
In a proposal, account for every original commit with diff evidence or visible uncertainty.
The plan must expose its base, merge-base, tree, groups, resulting order, subjects, counts, and concerns.
An unresolved base or another earlier stop condition can prevent a complete proposal.

After an approved rewrite, require a verified backup at the original HEAD, exact tree identity,
an empty backup-to-HEAD diff, and history matching the approved groups and topology.
A failed or incomplete check must not be reported as success.
No case authorizes publication; rewrite reports must end with `Published: no`.

## Cases

| Case | Decision under evaluation |
| --- | --- |
| [Fixup chain](fixup-chain.md) | One behavior across implementation, repair, tests, and documentation; failed verification |
| [Non-adjacent correction](non-adjacent-correction.md) | Safe regrouping requires dependency evidence |
| [Independent changes](independent-changes.md) | Shared directories do not imply one rollback unit; authorship remains visible |
| [Revert pair](revert-pair.md) | Cancellation and independence are separate requirements |
| [Merge boundary](merge-boundary.md) | Complete inventory and explicit topology strategy |
| [Dirty worktree](dirty-worktree.md) | Analysis is allowed; mutation requires clean, revalidated state |
| [Ambiguous base](ambiguous-base.md) | Base selection requires evidence or user direction |
