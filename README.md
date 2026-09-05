# agent-methods

**Give your coding agent a method you can review and a result you can verify.**

[![CI](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml/badge.svg)](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

Portable Agent Skills for engineering work that needs careful judgment.
Install a skill in your coding agent, ask for the task, and follow a workflow with evidence, approval, and verification.

- **Review the plan:** understand proposed changes before approving destructive actions.
- **Check the result:** each method defines what success looks like and how to verify it.
- **Use your preferred agent:** installation instructions below cover Claude Code, OpenCode, Codex, and agy.

[Skills](#available-skills) · [Install](#install) · [Usage](#use-commit-squashing) · [Evaluations](#evaluations)

## Available skills

### [commit-squashing](skills/commit-squashing/SKILL.md)

**Turn WIP commits and fixups into a history that is easier to review and revert.**
Use it before opening a pull request or merging a branch.

- Groups related implementation, fixes, tests, and documentation into coherent commits.
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

## Install

You need **Git** and an installed coding agent with local skill support.
The commands below use a POSIX shell on macOS, Linux, or WSL.
Python is only needed if you want to run the fixture tests.

### 1. Get the skills

```sh
git clone https://github.com/arloliu/agent-methods.git
cd agent-methods
```

### 2. Install for your agent

Run **one** of the following blocks from the cloned repository.
These install for your user account, making the skill available across projects.
The copy commands ask before replacing existing files; keep any local customizations you need.

#### Claude Code

```sh
mkdir -p "$HOME/.claude/skills"
cp -Ri skills/commit-squashing "$HOME/.claude/skills/"
```

In Claude Code, invoke it with `/commit-squashing`.
See [Claude Code skill documentation](https://code.claude.com/docs/en/skills).

#### OpenCode

```sh
mkdir -p "$HOME/.config/opencode/skills"
cp -Ri skills/commit-squashing "$HOME/.config/opencode/skills/"
```

Ask OpenCode to use the `commit-squashing` skill.
OpenCode also discovers `~/.agents/skills/` and `~/.claude/skills/`, so an existing installation there can be reused.
See [OpenCode skill documentation](https://opencode.ai/docs/skills).

#### Codex

```sh
mkdir -p "$HOME/.agents/skills"
cp -Ri skills/commit-squashing "$HOME/.agents/skills/"
```

In Codex CLI or the IDE extension, select it through `/skills` or mention `$commit-squashing` in your prompt.
See [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills).

#### agy — Antigravity CLI

```sh
mkdir -p "$HOME/.gemini/antigravity-cli/skills"
cp -i skills/commit-squashing/SKILL.md "$HOME/.gemini/antigravity-cli/skills/commit-squashing.md"
```

This follows agy's documented CLI installation using a named Markdown file.
The current skill is self-contained; its evaluation files are not required to use it.
Launch `agy` and invoke `/commit-squashing`.
See [Antigravity CLI skill documentation](https://www.antigravity.google/docs/cli/plugins/).

### Install for one project instead

Use the following locations inside the repository where you want to use the skill.
Copy the skill directory for Claude Code, OpenCode, and Codex; for agy, copy `SKILL.md` to the named file.
You can commit the installation to share it with your team.

| Agent | Project installation path |
| --- | --- |
| Claude Code | `.claude/skills/commit-squashing/SKILL.md` |
| OpenCode | `.opencode/skills/commit-squashing/SKILL.md` |
| Codex | `.agents/skills/commit-squashing/SKILL.md` |
| agy CLI | `.agents/skills/commit-squashing.md` |

These paths follow the agent documentation linked above.
Start a new agent session in your target repository after installation.
If the skill is missing, check the installation path and filename against the instructions for your agent.

### Update an installation

Run `git pull --ff-only` in your `agent-methods` clone, review the changes, and repeat your agent's copy command.
Installed copies do not update automatically.

## Use commit-squashing

Open the repository whose branch you want to clean up, then send your agent:

```text
Use the commit-squashing skill to review this branch against main.
Group related WIP commits and fixups into atomic commits.
Show me the exact plan before rewriting anything.
```

Replace `main` with your intended integration base, such as `origin/main`.

**What to expect:**

1. **Inspect:** the agent reads the branch history, patches, dependencies, and working-tree state.
2. **Plan:** it accounts for every commit and proposes the resulting groups and order.
3. **Approve:** you review the exact plan before any history rewrite begins.
4. **Rewrite and verify:** it checks that the inspected state is unchanged, creates a backup, and applies the plan.
   It verifies both the final Git tree and the resulting commit structure.
5. **Report:** you get the outcome, verification results, and backup reference.
   Publishing requires separate authorization.

A dirty worktree can be analyzed, but must be clean before rewriting.
An unclear base or a merge requiring a topology decision may need your input.
If the history is already coherent, the correct outcome may be to leave it as it is.

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

The commit-squashing suite includes reproducible Git fixtures for:

- Fixup chains and non-adjacent corrections.
- Safe and dependent revert pairs.
- Merge boundaries and dirty worktrees.
- Independent changes and ambiguous bases.

Run the fixture tests from this repository's root with Git and Python 3.10 or newer:

```sh
python3 -B skills/commit-squashing/evals/test_fixtures.py
```

[CI](https://github.com/arloliu/agent-methods/actions/workflows/ci.yml) runs the fixtures on Linux and macOS.
The tests check fixture histories and reference transformations.
Evaluating an agent's decisions and approval handling requires an actual agent run.
See the [evaluation guide](skills/commit-squashing/evals/README.md) to build a fixture and assess a run.

## Contributing

Have a repeatable method for a difficult engineering task?
Start with the failure it prevents, the evidence it needs, and how to verify its outcome.
Quality matters more than skill count.

Read the [contribution guide](CONTRIBUTING.md) to propose a method or improve an existing skill.

## License

[Apache-2.0](LICENSE).
