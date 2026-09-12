# agent-methods

**Give your coding agent a method you can review and a result you can verify.**

[![CI](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml/badge.svg)](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Portable Agent Skills for engineering work that needs careful judgment.
Install a skill in your coding agent, ask for the task, and follow a workflow with evidence, approval, and verification.

- **Review the plan:** understand proposed changes before approving destructive actions.
- **Check the result:** each method defines what success looks like and how to verify it.
- **Use your preferred agent:** Claude Code, OpenCode, Codex, and agy are covered below.

[Skills](#skills) · [Install](#install) · [Evaluations](#evaluations) · [Releases](#releases) · [Contributing](#contributing)

## Skills

Each skill is independent:
its own workflow, its own evaluation suite, and its own release version.
Install only the ones you want.

| Skill | Use it when | Latest release |
| --- | --- | --- |
| [history-cleanup](#history-cleanup) | A branch's commit history needs grouping into reviewable commits before a pull request | `history-cleanup/v0.1.3` |
| [progress-check](#progress-check) | You need to know where a session stands and whether background work is still running or stuck | `progress-check/v0.1.0` |

Every skill in this repository is built to the same [quality bar](#quality-bar) and carries the same kinds of [evidence](#evaluations).

## Install

You need **Git** and a coding agent with local skill support.
Python is needed only to run the evaluation fixtures.

Throughout this section, replace `<skill>` with the directory name of the skill you want:
`history-cleanup` or `progress-check`.
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

**Prepare a history-cleanup proposal for human review**, before opening a pull request or merging a branch.
Read the [skill](skills/history-cleanup/SKILL.md).

- Proposes grouping related implementation, fixes, tests, and documentation into coherent commits.
- Uses patches and dependencies to decide what belongs together, including non-adjacent corrections.
- Keeps independent work separate and checks dependencies before removing revert pairs.
- Requires your approval of the exact rewrite plan, creates a backup, and verifies the final Git tree is unchanged.
- Treats pushing as a separate action requiring authorization.

For example, when the retry changes belong together and logging is independent:

```text
Before                          After
WIP: add retries                Add retries with tests
Add structured logging          Add structured logging
fixup! retry limit
Test retry edge cases
```

The grouping depends on the actual changes, not just these commit messages.

**Ask for it** in the repository whose branch you want to clean up:

```text
Use the history-cleanup skill to review this branch against main.
Group related WIP commits and fixups into atomic commits.
Show me the exact plan before rewriting anything.
```

Replace `main` with your intended integration base, such as `origin/main`.
Ordinary requests reach the same workflow without naming the skill —
"Squash commits into fewer commits on this branch; use main as the base",
"Clean up this branch's commit history before review", or
"把這個分支的 WIP commits 和 fixups 整理成幾個合理的提交，以 main 為基準。"
Automatic selection depends on the host and model, so naming the skill makes it explicit.

**What to expect:**

1. **Inspect:** the agent reads the branch history, patches, dependencies, and working-tree state.
2. **Plan:** it accounts for every commit and proposes the resulting groups and order.
3. **Approve:** you review the exact plan before any history rewrite begins.
4. **Rewrite and verify:** it checks that the inspected state is unchanged, creates a backup, and applies the plan.
   It verifies both the final Git tree and the resulting commit structure.
5. **Report:** you get the outcome, verification results, and backup reference.
   Publishing requires separate authorization.

**Before you approve,** check whether each group has one coherent purpose,
whether every original commit is accounted for with its intended subject and order,
and which checks actually ran against which remain pending.

**Limits.**
The proposal aids your judgment; the agent can misgroup changes or omit required evidence.
A dirty worktree can be analyzed but must be clean before rewriting.
An unclear base or a merge requiring a topology decision may need your input.
If the history is already coherent, the correct outcome is to leave it alone.
Merely listing commits, explaining Git squash, or cleaning source files is outside this skill's purpose.

**Migrating from `commit-squashing`:** preserve local customizations, install `history-cleanup`,
confirm it loads in a new session, then remove the old installation from the same scope
so both are not discovered together.
Updating `history-cleanup` does not migrate an installation registered under the old name.

## progress-check

**Check a session's real progress and the background work it started.**
Read the [skill](skills/progress-check/SKILL.md).

- Reconciles the accepted scope, the work record, and the runtime record with permitted evidence within a stated budget.
- Probes each background item within a bounded wait and classifies it with the evidence it cites;
  silence alone is never "stuck".
- Proposes stops only for evidenced candidates, names who can stop each one, and acts only on an approved list.
- Verifies each stop's postcondition and keeps unread failures from being reported as done.
- Works with any host through capability probing;
  a dated per-host reference covers Claude Code, Codex, OpenCode, agy, and Gemini CLI.

**Ask for it** in a session where background work exists:

```text
Use the progress-check skill: where are we, and is anything you started still running or stuck?
```

Ordinary requests reach it without naming the skill —
"Where are we on this task, and is anything still running in the background?",
"Check whether any background job, subagent, or watcher you started is stuck", or
"現在進度到哪了？有沒有背景工作還在跑？"

**What to expect:**

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

**Before you approve,** check that each stop candidate cites evidence rather than silence,
that the mechanism named matches what you expect it to do to child processes,
and that nothing you still need is on the list.

**Limits.**
The skill also asks the agent to record a handle, purpose, expected end, and output location
whenever it starts background work, so a later check has something to inventory.
Some hosts let only the user stop a background terminal;
the report then names the command and its side effects instead of asking.
Terminating arbitrary processes and cancelling external CI are outside its purpose.

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

[CI](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml) runs both suites on Linux and macOS.
Evaluating an agent's judgment and approval handling needs an actual agent run, which the fixtures cannot do.

Per-skill evaluation guides:
[history-cleanup](skills/history-cleanup/evals/README.md) ·
[progress-check](skills/progress-check/evals/README.md),
with its [discovery prompt set](skills/progress-check/evals/discovery.md)
and [behavioural rubric](skills/progress-check/evals/behavioral-rubric.md).

Executed trials are recorded under [trials/](skills/progress-check/evals/trials/), one file per date and host.
On 2026-09-12, [Claude Code](skills/progress-check/evals/trials/2026-09-12-claude-code.md) ran one behavioural trial each
with Sonnet 5 and Haiku 4.5 plus 54 discovery runs per model;
Sonnet passed 11 of 18 rubric dimensions and Haiku 2 of 18, and neither stopped anything without approval.
The same day, [Antigravity CLI](skills/progress-check/evals/trials/2026-09-12-agy.md) ran 54 discovery runs on each of two Gemini models;
all 48 positive prompts loaded the skill, and the behavioural trial could not be driven on that host.

## Releases

Skills are versioned and tagged independently as `<skill>/vMAJOR.MINOR.PATCH`;
the repository itself has no shared version.

| Skill | Latest | Tags |
| --- | --- | --- |
| history-cleanup | `history-cleanup/v0.1.3` | v0.1.0 … v0.1.3 |
| progress-check | `progress-check/v0.1.0` | v0.1.0 |

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
