# agent-methods

**Give your coding agent a method you can review and a result you can verify.**

[![CI](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml/badge.svg)](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Portable Agent Skills for engineering work that needs careful judgment.
Install a skill in your coding agent, ask for the task, and follow a workflow with evidence, approval, and verification.

- **Review the plan:** understand proposed changes before approving destructive actions.
- **Check the result:** each method defines what success looks like and how to verify it.
- **Use your preferred agent:** installation instructions below cover Claude Code, OpenCode, Codex, and agy.

[Skills](#available-skills) · [Install](#install) · [Usage](#use-history-cleanup) · [Evaluations](#evaluations)

## Available skills

### [history-cleanup](skills/history-cleanup/SKILL.md)

**Prepare a history-cleanup proposal for human review.**
Use it before opening a pull request or merging a branch.

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

### [progress-check](skills/progress-check/SKILL.md)

**Check a session's real progress and the background work it started.**
Use it when you want to know where the work stands, whether anything is still running,
or whether a background shell, subagent, monitor, scheduled job, or delegated agent run is stuck.

- Reconciles the accepted scope, the work record, and the runtime record with permitted evidence within a stated budget.
- Probes each background item within a bounded wait and classifies it with the evidence it cites;
  silence alone is never "stuck".
- Proposes stops only for evidenced candidates, names who can stop each one, and acts only on an approved list.
- Verifies each stop's postcondition and keeps unread failures from being reported as done.
- Works with any host through capability probing;
  a dated per-host reference covers Claude Code, Codex, OpenCode, agy, and Gemini CLI.

## Install

You need **Git** and an installed coding agent with local skill support.
Python is only needed if you want to run the fixture tests.

### Install with Skills CLI

With Node.js 22.20.0 or newer and npm, run this from your target project:

```sh
npx skills add arloliu/agent-methods --skill history-cleanup
```

Use `--skill progress-check` for the progress-check skill, or repeat the command for each skill you want.

The default scope is the current project.
When running interactively, choose your agent from the prompts.
Add `--global` to install for your user account across projects.
For agy, use the [manual installation](#agy--antigravity-cli) below.

The installation was checked with Skills CLI `1.5.23`.
See the [Skills CLI documentation](https://github.com/vercel-labs/skills#readme) for agent selection and copy/symlink options.
Keep any local customizations before reinstalling or updating; the CLI replaces existing skill files.
Start a new agent session in your target project after installation.

To update a CLI-managed installation, run this from the same project:

```sh
npx skills update history-cleanup
```

Add `--global` when updating a user-level installation.

### Manual install

The commands below use a POSIX shell on macOS, Linux, or WSL and require no Node.js installation.

#### 1. Get the skills from main

This default checkout follows `main` and receives future main updates when you run `git pull --ff-only`.

```sh
git clone https://github.com/arloliu/agent-methods.git
cd agent-methods
```

#### Install the pinned history-cleanup v0.1.2 release instead

Use this checkout when you want the reviewed `history-cleanup/v0.1.2` release rather than future main updates.

```sh
git clone --branch history-cleanup/v0.1.2 --depth 1 https://github.com/arloliu/agent-methods.git
cd agent-methods
git rev-parse HEAD
# fa4d430205e9a6663a35f3e582d867430a210e07
```

This checkout remains on that release tag until you deliberately select another version.

#### 2. Install for your agent

Run **one** of the following blocks from the cloned repository.
These install for your user account, making the skill available across projects.
The commands show `history-cleanup`; replace it with `progress-check` to install that skill from a checkout that contains it.
The pinned `history-cleanup/v0.1.2` checkout does not include progress-check.
The copy commands ask before replacing existing files; keep any local customizations you need.

##### Claude Code

```sh
mkdir -p "$HOME/.claude/skills"
cp -Ri skills/history-cleanup "$HOME/.claude/skills/"
```

In Claude Code, invoke it with `/history-cleanup`.
See [Claude Code skill documentation](https://code.claude.com/docs/en/skills).

##### OpenCode

```sh
mkdir -p "$HOME/.config/opencode/skills"
cp -Ri skills/history-cleanup "$HOME/.config/opencode/skills/"
```

Ask OpenCode to use the `history-cleanup` skill.
OpenCode also discovers `~/.agents/skills/` and `~/.claude/skills/`, so an existing installation there can be reused.
See [OpenCode skill documentation](https://opencode.ai/docs/skills).

##### Codex

```sh
mkdir -p "$HOME/.agents/skills"
cp -Ri skills/history-cleanup "$HOME/.agents/skills/"
```

In Codex CLI or the IDE extension, select it through `/skills` or mention `$history-cleanup` in your prompt.
See [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills).

##### agy — Antigravity CLI

```sh
mkdir -p "$HOME/.gemini/antigravity-cli/skills"
cp -i skills/history-cleanup/SKILL.md "$HOME/.gemini/antigravity-cli/skills/history-cleanup.md"
```

This follows agy's documented CLI installation using a named Markdown file.
Each skill's `SKILL.md` operates on its own; progress-check's references add per-host detail and evaluation files are not required.
Launch `agy` and invoke `/history-cleanup`.
See [Antigravity CLI skill documentation](https://www.antigravity.google/docs/cli/plugins/).

#### Install for one project instead

Use the following locations inside the repository where you want to use the skill.
Copy the skill directory for Claude Code, OpenCode, and Codex; for agy, copy `SKILL.md` to the named file.
The paths show `history-cleanup`; `progress-check` installs at the same locations under its own name.
You can commit the installation to share it with your team.

| Agent | Project installation path |
| --- | --- |
| Claude Code | `.claude/skills/history-cleanup/SKILL.md` |
| OpenCode | `.opencode/skills/history-cleanup/SKILL.md` |
| Codex | `.agents/skills/history-cleanup/SKILL.md` |
| agy CLI | `.agents/skills/history-cleanup.md` |

These paths follow the agent documentation linked above.
Start a new agent session in your target repository after installation.
If the skill is missing, check the installation path and filename against the instructions for your agent.

#### Update a manual installation

For the default main checkout, run `git pull --ff-only` in your `agent-methods` clone.
Review the changes, then repeat your agent's copy command.
For a pinned release checkout, choose and verify a newer release tag.
Then repeat the copy command instead of pulling main.
Installed copies do not update automatically in either case.

#### Migrate from commit-squashing

If you installed the former `commit-squashing` skill, preserve any local customizations first.
Install `history-cleanup` using the instructions above and confirm it is available in a new agent session.
Then remove the old `commit-squashing` installation from the same scope and agent location
so both versions are not discovered together.
For CLI-managed installations, use the CLI's `remove` command for the old skill name;
for manual installations, remove only the old skill directory (or agy's old `commit-squashing.md` file).
Updating `history-cleanup` does not migrate an installation registered under the old name.

## Use history-cleanup

Open the repository whose branch you want to clean up, then send your agent:

```text
Use the history-cleanup skill to review this branch against main.
Group related WIP commits and fixups into atomic commits.
Show me the exact plan before rewriting anything.
```

Replace `main` with your intended integration base, such as `origin/main`.

The skill's description also covers ordinary requests without its name, such as:

- "Squash commits into fewer commits on this branch; use main as the base."
- "Clean up this branch's commit history before review; use main as the base."
- "把這個分支的 WIP commits 和 fixups 整理成幾個合理的提交，以 main 為基準。"

These requests should select the same workflow, including its approval and verification steps.
Automatic selection depends on the host and model; naming `history-cleanup` makes the intended skill explicit.
Merely listing commits, explaining Git squash, or cleaning source files is outside this skill's purpose.
The [discovery evaluation](skills/history-cleanup/evals/discovery.md) covers both matching and non-matching prompts.
Those scenarios are separate from the automated fixture tests.

**What to expect:**

1. **Inspect:** the agent reads the branch history, patches, dependencies, and working-tree state.
2. **Plan:** it accounts for every commit and proposes the resulting groups and order.
3. **Approve:** you review the exact plan before any history rewrite begins.
4. **Rewrite and verify:** it checks that the inspected state is unchanged, creates a backup, and applies the plan.
   It verifies both the final Git tree and the resulting commit structure.
5. **Report:** you get the outcome, verification results, and backup reference.
   Publishing requires separate authorization.

Before approving, check:

- Whether each group has one coherent purpose, including the reasoning for keeping or separating documentation.
- Whether every original commit is accounted for, with the intended resulting subjects and order.
- Which checks actually ran, which remain pending, and how the backup and rewritten history will be verified.

The proposal is an aid to your judgment; the agent can misgroup changes or omit required evidence and steps.
A dirty worktree can be analyzed, but must be clean before rewriting.
An unclear base or a merge requiring a topology decision may need your input.
If the history is already coherent, the correct outcome may be to leave it as it is.

## Use progress-check

In a session where background work exists, send your agent:

```text
Use the progress-check skill: where are we, and is anything you started still running or stuck?
```

The skill's description also covers ordinary requests without its name, such as:

- "Where are we on this task, and is anything still running in the background?"
- "Check whether any background job, subagent, or watcher you started is stuck."
- "現在進度到哪了？有沒有背景工作還在跑？"

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

The description also asks the agent to record a handle, purpose, expected end, and output location
whenever it starts background work, so a later check has something to inventory.
Some hosts let only the user stop a background terminal;
the report then names the command and its side effects instead of asking.
The [evaluation guide](skills/progress-check/evals/README.md) describes the fixture contract and trial protocol;
the fixture workers, harness, and trace verifier are tested in CI, while agent trials remain manual.

## Quality bar

Every skill is designed around:

- **A focused task:** clear triggers and a concrete objective.
- **Evidence before decisions:** explicit inputs and correctness invariants.
- **Your control:** approval boundaries before destructive actions and clear conditions for stopping.
- **Verifiable outcomes:** deterministic or machine-checkable postconditions where possible.
- **Portability:** minimal host assumptions and no unnecessary vendor-specific behavior.
- **Evaluation cases:** ordinary workflows, edge cases, and failures the method must avoid.

Skills guide an agent's behavior; they do not enforce permissions in the agent runtime.
Review the proposed actions and verification results as you work.

## Evaluations

The history-cleanup suite includes reproducible Git fixtures for:

- Fixup chains and non-adjacent corrections.
- Safe and dependent revert pairs.
- Merge boundaries and dirty worktrees.
- Independent changes and ambiguous bases.

Run the fixture tests from this repository's root with Git and Python 3.10 or newer:

```sh
python3 -B skills/history-cleanup/evals/test_fixtures.py
```

[CI](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml) runs the fixtures on Linux and macOS.
The tests check fixture histories and reference transformations.
Evaluating an agent's decisions and approval handling requires an actual agent run.
See the [evaluation guide](skills/history-cleanup/evals/README.md) to build a fixture and assess a run.

The progress-check suite has a machine-checked fixture layer and written trial material:
a [discovery prompt set](skills/progress-check/evals/discovery.md),
a [fixture contract and trial protocol](skills/progress-check/evals/README.md),
and a [behavioural rubric](skills/progress-check/evals/behavioral-rubric.md).
Its tests start real worker processes, hold a stdin writer open, stop one worker, and reject bad traces:

```sh
python3 -B skills/progress-check/evals/test_fixtures.py
```

Executed trials are recorded under [evals/trials](skills/progress-check/evals/trials/2026-09-12-claude-code.md):
on 2026-09-12, one behavioural trial each on Claude Code with Sonnet 5 and Haiku 4.5, and 54 discovery runs per model.
Sonnet passed 11 of 18 rubric dimensions and Haiku 2 of 18; neither stopped anything without approval.

## Contributing

Have a repeatable method for a difficult engineering task?
Start with the failure it prevents, the evidence it needs, and how to verify its outcome.
Quality matters more than skill count.

Read the [contribution guide](CONTRIBUTING.md) to propose a method or improve an existing skill.

## License

[Apache-2.0](LICENSE).
