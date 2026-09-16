# agent-methods

**Give your coding agent a method you can review and a result you can verify.**

[![CI](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml/badge.svg)](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Portable Agent Skills for engineering tasks where judgment, safety, and proof matter.
Each skill tells the agent what evidence to gather, which decisions need your review,
when to stop for approval, and how to verify the final state.

We refine each method through an evidence loop:

`failure mode → explicit workflow → evaluation case → recorded result → revision`

Fixture tests, executed agent trials, and written scenarios remain separate,
so you can see what has been tested, what agents have demonstrated,
and what still lacks evidence.

Works with Claude Code, OpenCode, Codex, and agy.

Read the [development workflow](docs/development-workflow.md) for an integrated path from discovery to release.

[Skills](#skills) · [Install](#install) · [Evaluations](#evaluations) · [Releases](#releases) · [Contributing](#contributing)

## Skills

Each skill is independent:
its own workflow, its own evaluation suite, and its own release version.
Install only the ones you want.

| Skill | Use it when | Latest release |
| --- | --- | --- |
| [history-cleanup](#history-cleanup) | A branch's commit history needs grouping into reviewable commits before a pull request | `history-cleanup/v0.1.3` |
| [progress-check](#progress-check) | You need to know where a session stands and whether background work is still running or stuck | `progress-check/v0.2.0` |
| [release-readiness](#release-readiness) | You need to assess, prepare, or publish a release bound to one candidate commit | `release-readiness/v0.2.0` |
| [review-feedback](#review-feedback) | You need to assess supplied review findings and address the supported ones within the current task | `review-feedback/v0.1.0` |
| [rules-check](#rules-check) | You need to check local commits, uncommitted changes, and session operations against agent rules | `rules-check/v0.1.0` |

Every skill in this repository is built to the same [quality bar](#quality-bar) and carries the same kinds of [evidence](#evaluations).

## Install

You need **Git** and a coding agent with local skill support.
Python is needed only to run the evaluation fixtures.

Throughout this section, replace `<skill>` with the directory name of the skill you want:
`history-cleanup`, `progress-check`, `release-readiness`, `review-feedback`, or `rules-check`.
Repeat the commands for each skill.

### With Skills CLI

With Node.js 22.20.0 or newer and npm, run this from your target project:

```sh
npx skills add arloliu/agent-methods --skill <skill>
```

The default scope is the current project; add `--global` to install for your user account across projects.
When running interactively, choose your agent from the prompts.
For agy, use the [manual installation](#manually) instead.

Update a CLI-managed installation from the same project, adding `--global` if that is how you installed it:

```sh
npx skills update <skill>
```

The installation was checked with Skills CLI `1.5.23`.
See the [Skills CLI documentation](https://github.com/vercel-labs/skills#readme)
for agent selection and copy/symlink options.
Keep any local customizations before reinstalling; the CLI replaces existing skill files.
Start a new agent session in your target project afterwards.

### Manually

The commands below use a POSIX shell on macOS, Linux, or WSL and need no Node.js.

**1. Get the skills.**
This checkout follows `main` and picks up future updates when you run `git pull --ff-only`:

```sh
git clone https://github.com/arloliu/agent-methods.git
cd agent-methods
```

To pin a reviewed release instead, clone its tag; see [Releases](#releases) for the current tags:

```sh
git clone --branch <skill>/<version> --depth 1 https://github.com/arloliu/agent-methods.git
cd agent-methods && git rev-parse HEAD
```

A tag is specific to one skill, so a pinned checkout may not contain the others.

**2. Copy the skill into your agent's directory.**
These paths install for your user account, across projects:

| Agent | Copy command (run from the clone) | Invoke it with |
| --- | --- | --- |
| Claude Code | `mkdir -p ~/.claude/skills && cp -Ri skills/<skill> ~/.claude/skills/` | `/<skill>` |
| OpenCode | `mkdir -p ~/.config/opencode/skills && cp -Ri skills/<skill> ~/.config/opencode/skills/` | ask it to use the `<skill>` skill |
| Codex | `mkdir -p ~/.agents/skills && cp -Ri skills/<skill> ~/.agents/skills/` | `/skills`, or `$<skill>` in a prompt |
| agy | `mkdir -p ~/.gemini/config/skills && cp -Ri skills/<skill> ~/.gemini/config/skills/` | `/<skill>` |

The copy commands ask before replacing existing files, so local customizations are not overwritten silently.
OpenCode also discovers `~/.agents/skills/` and `~/.claude/skills/`, so an installation there can be reused.
On agy 1.2.2 the global configuration directory above is the location that registers;
a single named Markdown file under `~/.gemini/antigravity-cli/skills/` was not listed in testing,
and copying the whole directory keeps each skill's `references/` available.

To install for one project instead, copy the same directory to `.claude/skills/`, `.opencode/skills/`,
or `.agents/skills/` inside that repository, and commit it if your team should share it.

**3. Start a new agent session.**
If the skill is missing, check the path and directory name against the table above.

Manual installations do not update themselves.
Run `git pull --ff-only` in the clone, review the changes, and repeat the copy command.

See the agent documentation for details:
[Claude Code](https://code.claude.com/docs/en/skills),
[OpenCode](https://opencode.ai/docs/skills),
[Codex](https://learn.chatgpt.com/docs/build-skills),
[agy](https://www.antigravity.google/docs/cli/plugins/).

## history-cleanup

Prepare a history-cleanup proposal for human review before opening a pull request or merging a branch.
Read the [skill](skills/history-cleanup/SKILL.md).

### When to use it

- Your branch contains WIP, fixup, retry, or partial commits that obscure the final change.
- You want patches and dependencies to determine the commit groups,
  followed by your approval of the exact rewrite plan.

### What it does

- Proposes grouping related implementation, fixes, tests, and documentation into coherent commits.
- Uses patches and dependencies to decide what belongs together, including non-adjacent corrections.
- Keeps independent work separate and checks dependencies before removing revert pairs.
- Requires your approval of the exact rewrite plan, creates a backup, and verifies the final Git tree is unchanged.
- Treats pushing as a separate action requiring authorization.

### Example

For example, when the retry changes belong together and logging is independent:

```text
Before                          After
WIP: add retries                Add retries with tests
Add structured logging          Add structured logging
fixup! retry limit
Test retry edge cases
```

The grouping depends on the actual changes, not just these commit messages.

### Ask for it

Run the request in the repository whose branch you want to clean up:

- Recommended:

  ```text
  Use the history-cleanup skill to review this branch against main.
  Group related WIP commits and fixups into atomic commits.
  Show me the exact plan before rewriting anything.
  ```

- `Squash commits into fewer commits on this branch; use main as the base.`
- `Clean up this branch's commit history before review.`

Replace `main` with your intended integration base, such as `origin/main`.
Automatic selection depends on the host and model, so naming the skill makes it explicit.

### What to expect

1. **Inspect:** the agent reads the branch history, patches, dependencies, and working-tree state.
2. **Plan:** it accounts for every commit and proposes the resulting groups and order.
3. **Approve:** you review the exact plan before any history rewrite begins.
4. **Rewrite and verify:** it checks that the inspected state is unchanged, creates a backup, and applies the plan.
   It verifies both the final Git tree and the resulting commit structure.
5. **Report:** you get the outcome, verification results, and backup reference.
   Publishing requires separate authorization.

### Before you approve

Check whether each group has one coherent purpose,
whether every original commit is accounted for with its intended subject and order,
and which checks actually ran against which remain pending.

### Limits

The proposal aids your judgment; the agent can misgroup changes or omit required evidence.
A dirty worktree can be analyzed but must be clean before rewriting.
An unclear base or a merge requiring a topology decision may need your input.
If the history is already coherent, the correct outcome is to leave it alone.
Merely listing commits, explaining Git squash, or cleaning source files is outside this skill's purpose.

### Migrating from `commit-squashing`

Preserve local customizations, install `history-cleanup`, confirm it loads in a new session,
then remove the old installation from the same scope
so both are not discovered together.
Updating `history-cleanup` does not migrate an installation registered under the old name.

## progress-check

Check a session's real progress and the background work it started.
Read the [skill](skills/progress-check/SKILL.md).

### When to use it

- The agent started background jobs, subagents, monitors, or delegated runs,
  and you need to know what is still active.
- A session appears silent, stuck, or complete,
  and you want evidence before accepting that assessment or stopping anything.

### What it does

- Reconciles the accepted scope, the work record, and the runtime record with permitted evidence within a stated budget.
- Probes each background item within a bounded wait and classifies it with the evidence it cites;
  silence alone is never "stuck".
- Proposes stops only for evidenced candidates, names who can stop each one, and acts only on an approved list.
- Verifies each stop's postcondition and keeps unread failures from being reported as done.
- Works with any host through capability probing;
  a dated per-host reference covers Claude Code, Codex, OpenCode, agy, and Gemini CLI.

### Ask for it

Run the request in a session where background work exists:

- Recommended:

  ```text
  Use the progress-check skill: where are we, and is anything you started still running or stuck?
  ```

- `Where are we on this task, and is anything still running in the background?`
- `Check whether any background job, subagent, or watcher you started is stuck.`

### What to expect

1. **Inspect:** the agent states which capabilities its host exposes, rebuilds the accepted scope,
   and lists every background item it can account for, with the boundary of what it cannot see.
2. **Probe:** it checks each item within a bounded wait where the host permits, and reports the gaps it cannot observe;
   lifecycle, output activity, and expectations are recorded separately.
3. **Assess:** each item gets a class with cited evidence;
   unread results and running delegated runs block any "done" claim.
4. **Propose:** stop candidates appear with their mechanism, reason, affected descendants, and who can stop them.
   Nothing is stopped in the proposal turn.
5. **Act and verify:** after you approve the exact displayed operations, it revalidates each item,
   executes only the approved mechanism with its documented or explicitly unknown semantics,
   and reports the observed outcome, ending with `Stopped: <ids or none>`.

### Before you approve

Check that each stop candidate cites evidence rather than silence,
that the mechanism named matches what you expect it to do to child processes,
and that nothing you still need is on the list.

### Limits

The skill also asks the agent to record a handle, purpose, expected end, and output location
whenever it starts background work, so a later check has something to inventory.
Some hosts let only the user stop a background terminal;
the report then names the command and its side effects instead of asking.
Terminating arbitrary processes and cancelling external CI are outside its purpose.

## rules-check

Check current work and session operations against the applicable agent rules.
Read the [skill](skills/rules-check/SKILL.md).

### When to use it

- You want to review local commits and uncommitted work against repository or user-level agent rules.
- You need to check whether the session missed required lint, tests, approvals, or other workflow steps.

### What it does

- Includes local commits ahead of the confirmed upstream, staged and unstaged changes, and relevant untracked files.
- Reviews cumulative content, each selected commit message, and required workflow steps such as lint and approval.
- Re-reads applicable rules and actively seeks operation evidence instead of trusting a summary that checks passed.
- Separates confirmed violations, pending requirements, and facts it cannot verify.
  A later successful check cannot prove that a prerequisite happened before an earlier commit.

### Ask for it

- Recommended:

  ```text
  Use rules-check to check our current work against the agent rules.
  Include the commits I have not pushed and verify whether you missed required lint, tests, or approvals.
  ```

- `Check my current changes and unpushed commits against the agent rules, including any required steps we missed.`

Specify a base or range to review a different commit scope, or request staged-only review.

### What to expect

You receive a report naming the compared refs and commits, uncommitted scope, rule sources,
and operation evidence.
It separates concrete violations from remaining requirements and evidence gaps.
Missing upstream or divergent history requires a comparison decision; other independent checks can proceed.
The default commit set is based on locally cached refs, so it does not prove what is currently on the remote.
Incomplete session records limit historical verification; a clean worktree does not remove commits from review.
Existing authorization governs any follow-up checks, and inspection does not authorize fixes or publication.

### Validation status

The current evidence includes deterministic fixtures and written evaluation scenarios.
Model behavior, discovery, and native session-record retrieval have not yet been evaluated.
See the [evaluation guide](skills/rules-check/evals/README.md).

## review-feedback

Assess supplied code-review findings against the current code and accepted requirements,
then address supported findings when the current task authorizes correction.
Read the [skill](skills/review-feedback/SKILL.md).

### When to use it

- You have PR comments or a review report and need to determine which findings hold for the current code.
- You want supported findings fixed and verified within the requested scope.
- A reviewer returns findings during a workflow that already requires assessing or addressing them.

### What it does

- Accounts for every selected finding and checks each claim against current code and requirements.
- Judges the reported problem independently from its suggested remedy.
- Preserves stale findings, duplicates, conflicting recommendations, and missing evidence in a traceable ledger.
- Implements supported fixes when authorized and ties verification to each reviewed behavior.
- Keeps local technical resolution separate from replies, thread state, commits, pushes, and merges.

### Ask for it

- Recommended assessment request:

  ```text
  Use review-feedback to assess every finding in this report against the current code.
  Recommend what to do, but do not edit files.
  ```

- Recommended correction request:

  ```text
  Address these review comments with review-feedback.
  Fix and verify the supported findings within the current task scope.
  ```

- `The reviewer returned these findings; assess them before continuing the authorized implementation.`

### What to expect

The agent defines the selected feedback batch and binds it to the current branch, commit, diff, and working tree.
Every finding receives a judgment, a separate remedy assessment, a progress state, and supporting evidence.
Assessment-only requests leave supported changes pending.
Correction requests apply supported local fixes and report focused verification where authority and evidence permit.
External replies and thread resolution require separate authorization and observed external state.

### Validation status

The current evidence includes deterministic Git fixtures and written behavioral and discovery scenarios.
Model behavior and discovery have not yet been evaluated.
See the [evaluation guide](skills/review-feedback/evals/README.md).

## release-readiness

Assess, prepare, or publish a software release bound to one candidate commit.
Read the [skill](skills/release-readiness/SKILL.md).

### When to use it

- You want to know whether a repository or package is ready to release and which version it should get.
- You need release notes, version references, a tag, and a release entry that all describe the same commit.
- You want tagging and publication executed only for a candidate judged ready, and verified afterwards.

### What it does

- Reads the repository's release policy first, then resolves the scope, previous release, and candidate commit.
- Maps the change range to the public contract and proposes the version with compatibility and migration reasoning.
- Inventories required checks and evaluations, tying each result to the commit it covered
  and keeping failed, incomplete, unrun, and earlier-candidate evidence visible.
- Finds every version reference by searching, updates and commits them before tagging, and drafts the notes.
- Judges readiness, shows the exact plan, and executes only approved actions in order with pre-action state checks.
- Verifies the tag target, remote state, release entry, and tagged-tree references,
  and reports each status separately.

### Ask for it

Run the request in the repository you want to release:

- Recommended:

  ```text
  Use release-readiness to prepare the next alpha release.
  Propose the version, update the version references, and draft the notes.
  Show me the exact plan before creating or pushing anything.
  ```

- `Is this repository ready to release, and which version should it be?`
- `Publish alpha v0.2.0: push the tag and create the release from the prepared notes.`

State which actions you authorize: committing version references, tagging, pushing, and publishing are separate.

### What to expect

1. **Inspect:** the agent reads the release policy, records the candidate, resolves the previous release,
   and reads the change range.
2. **Reason:** it proposes the version from the contract mapping and inventories the evidence per commit.
3. **Prepare:** it updates version references, commits them, drafts the notes, and re-runs invalidated checks.
4. **Judge and plan:** it reports `ready` or `not-ready`,
   then shows the plan with the exact tag, commit, remote, and actions.
   A `not-ready` verdict ends the run; authorization does not override it.
5. **Execute and verify:** after you approve the displayed plan, it tags, pushes, and publishes in order,
   re-checking state before each step, then verifies the published state and reports each status separately.

### Before you approve

Check that the candidate commit is the one you reviewed, that the version matches the contract change,
that every required check names that commit, and that the action list contains only what you intend to authorize.

### Limits

Published tags are never moved; a mistake becomes a new version.
Registry publication, artifact uploads, checksums, and signing are outside this version;
the agent lists them as actions you complete separately and proceeds only if you accept that.
A release does not establish that agents follow the method reliably; review the cited evidence and notes yourself.
Deployment, rollout monitoring, branch integration, and history cleanup are outside its purpose.

### Validation status

The current evidence includes deterministic Git and forge fixtures, an end-state verifier,
and written behavioral and discovery scenarios.
On 2026-09-15, [Claude Code](skills/release-readiness/evals/trials/2026-09-15-claude-code.md) ran every fixture case once with Sonnet 5 and Haiku 4.5.
Every approved run passed the end-state verifier, and both models stopped on stale checks and conflicting tags.
Two Haiku gate slips led to wording corrections that re-ran clean.
Without the skill, Haiku published under a stale approval and Sonnet offered to delete a remote tag on the same fixtures.
The same batch ran 48 discovery runs per model.
The same record covers the skill's own `v0.1.0` release, performed with the method and self-reported.
See the [evaluation guide](skills/release-readiness/evals/README.md).

## Evaluations

Each skill carries three kinds of evidence, and they are never conflated:

- **Fixture tests** run in CI and check the machine-verifiable parts —
  fixture state, reference transformations, and trace verification.
- **Executed trials** are real agent runs against a fixture, recorded with host, model, date, and per-dimension results.
- **Written scenarios** are cases the method must handle, described but not yet run.

Run the fixture tests from the repository root with Git and Python 3.10 or newer:

| Skill | Command | What it covers |
| --- | --- | --- |
| history-cleanup | `python3 -B skills/history-cleanup/evals/test_fixtures.py` | fixup chains, non-adjacent corrections, safe and dependent revert pairs, merge boundaries, dirty worktrees, ambiguous bases |
| progress-check | `python3 -B skills/progress-check/evals/test_fixtures.py` | real worker processes, a held stdin writer, stopping one worker, liveness snapshots, and rejecting bad traces |
| release-readiness | `python3 -B skills/release-readiness/evals/test_fixtures.py` | version reasoning, stale references, checks on the parent, failing checks, existing and mismatched remote tags, stale approval, partial authorization, overstated notes, failed publication, and the end-state verifier |
| review-feedback | `python3 -B skills/review-feedback/evals/test_fixtures.py` | mixed findings, older revisions, duplicate and conflicting remedies, protected dirty work, incomplete batches, and assessment-only fixes |
| rules-check | `python3 -B skills/rules-check/evals/test_fixtures.py` | local ahead/divergent refs, staged/worktree separation, generated check evidence, timing, and stale results |

[CI](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml) runs these suites on Linux and macOS.
Evaluating an agent's judgment and approval handling needs an actual agent run, which the fixtures cannot do.

Per-skill evaluation guides:
[history-cleanup](skills/history-cleanup/evals/README.md) ·
[progress-check](skills/progress-check/evals/README.md),
with its [discovery prompt set](skills/progress-check/evals/discovery.md)
and [behavioural rubric](skills/progress-check/evals/behavioral-rubric.md).

For rules-check, see its [guide](skills/rules-check/evals/README.md),
[prompts](skills/rules-check/evals/discovery.md), and [rubric](skills/rules-check/evals/behavioral-rubric.md).

For review-feedback, see its [guide](skills/review-feedback/evals/README.md),
[prompts](skills/review-feedback/evals/discovery.md),
and [rubric](skills/review-feedback/evals/behavioral-rubric.md).

For release-readiness, see its [guide](skills/release-readiness/evals/README.md),
[prompts](skills/release-readiness/evals/discovery.md),
and [rubric](skills/release-readiness/evals/behavioral-rubric.md).

Executed trials are recorded under [trials/](skills/progress-check/evals/trials/), one file per date and host.
On 2026-09-12, [Claude Code](skills/progress-check/evals/trials/2026-09-12-claude-code.md) ran one behavioural trial each
with Sonnet 5 and Haiku 4.5 plus 54 discovery runs per model;
Sonnet passed 11 of 18 rubric dimensions and Haiku 2 of 18, and neither stopped anything without approval.
The same day, [Antigravity CLI](skills/progress-check/evals/trials/2026-09-12-agy.md) ran 54 discovery runs on each of two Gemini models;
all 48 positive prompts loaded the skill, and the behavioural trial could not be driven on that host.

For release-readiness, [Claude Code](skills/release-readiness/evals/trials/2026-09-15-claude-code.md) ran on 2026-09-15.
It covered fifteen fixture cases once each with Sonnet 5 and Haiku 4.5, a four-run follow-up batch, and 48 discovery runs per model.
Sonnet loaded the skill in 28 of 30 positive prompts and Haiku in 26 of 30; neither loaded it on a negative prompt.

## Releases

Skills are versioned and tagged independently as `<skill>/vMAJOR.MINOR.PATCH`;
the repository itself has no shared version.

| Skill | Latest | Tags |
| --- | --- | --- |
| history-cleanup | `history-cleanup/v0.1.3` | v0.1.0 … v0.1.3 |
| progress-check | `progress-check/v0.2.0` | v0.1.0, v0.2.0 |
| release-readiness | `release-readiness/v0.2.0` | v0.1.0, v0.2.0 |
| review-feedback | `review-feedback/v0.1.0` | v0.1.0 |
| rules-check | `rules-check/v0.1.0` | v0.1.0 |

A release is cut only when its evaluation evidence supports the claims in its notes.
See [RELEASING.md](RELEASING.md) for the process,
and [CONTRIBUTING.md](CONTRIBUTING.md) for what a change needs before it ships.

## Quality bar

Every skill in this repository is designed around:

- **A focused task:** clear triggers and a concrete objective.
- **Evidence before decisions:** explicit inputs and correctness invariants.
- **Your control:** approval boundaries before destructive actions and clear conditions for stopping.
- **Verifiable outcomes:** deterministic or machine-checkable postconditions where possible.
- **Portability:** minimal host assumptions and no unnecessary vendor-specific behavior.
- **Evaluation cases:** ordinary workflows, edge cases, and failures the method must avoid.

Skills guide an agent's behavior; they do not enforce permissions in the agent runtime.
Review the proposed actions and verification results as you work.

## Contributing

Have a repeatable method for a difficult engineering task?
Start with the failure it prevents, the evidence it needs, and how to verify its outcome.
Quality matters more than skill count.

Read the [contribution guide](CONTRIBUTING.md) to propose a method or improve an existing skill.

## License

[Apache-2.0](LICENSE).
