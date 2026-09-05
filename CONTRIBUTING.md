# Contributing

Quality matters more than skill count.
A contribution should encode an engineering method that changes an agent's decisions in a useful, observable way.
Use the [quality bar](README.md#quality-bar) and [commit-squashing](skills/commit-squashing/SKILL.md) as references.

## Propose a method

Explain:

- What failure mode of a general-purpose coding agent does this solve?
- What expert procedure or judgment does it encode?
- What evidence does the agent need before making decisions?
- What operations could be destructive?
- Where are explicit user approval boundaries needed?
- What postcondition proves the task succeeded?
- How can the behavior be evaluated?

A proposal that cannot answer these questions probably needs a narrower purpose.
Avoid prompt collections, thin wrappers around obvious model capabilities, and unnecessary duplication.
Extend an existing method when it already owns the same decision process.

## Write portable instructions

Use a skill directory with `SKILL.md` and frontmatter containing `name` and `description`.
Keep the description specific enough to select the method for the right task.
Keep instructions concise enough to execute and explicit enough to preserve safety invariants.
Put substantial optional material in linked supporting files when it improves navigation.

Keep vendor-specific metadata, agent configuration, and personal installation paths out of portable skills.
New dependencies need a concrete justification; plain Markdown is enough for many methods.
Instructions must make external mutations visible and authorized.
Never weaken an approval or verification boundary to make a workflow shorter.

## Evaluate behavior

Add meaningful eval scenarios for every non-trivial skill and update them whenever behavior changes.
Use the [commit-squashing evals](skills/commit-squashing/evals/README.md) as the initial format.
Include realistic inputs, relevant evidence, a user request, expected behavior, and the failure the case detects.
Cover successful execution as well as ambiguity, adverse inputs, and stop conditions.
Evaluate decisions and observable postconditions, not exact wording.

When running a scenario, keep expected answers separate from the agent's inputs.
Use disposable local fixtures for destructive operations and record any approval supplied during the run.
Report what actually ran, what passed or failed, and what remains unevaluated.
A written scenario alone is not a passed behavioral test.

## Before submitting

Review every changed file for consistency with the method's evidence, approval, and verification rules.
Check relative links and frontmatter, proofread the Markdown, and remove boilerplate.
Use semantic line breaks: start each sentence on a new line and split long sentences at meaningful clause boundaries.
Run available linters and fix findings before committing; run `git diff --check` as a whitespace check.
Include validation results and remaining limitations in the contribution description.
Do not add attribution trailers to commit messages.
