# agent-methods

Battle-tested engineering methods packaged as portable Agent Skills.

This repository contains methods for coding agents that emphasize explicit reasoning workflows,
evidence-based decisions, safe handling of destructive operations, approval boundaries,
machine-verifiable postconditions, and portability across Agent Skills implementations.

## What belongs here

A skill belongs in this repository
when it encodes something a capable coding agent cannot be expected to perform consistently from generic instructions alone.
Quality matters more than skill count.

Good candidates include production debugging procedures, Git history transformations,
distributed-system reviews, migration procedures, incident investigation, compatibility analysis,
and operational safety workflows.
Each needs a concrete failure mode and a method for avoiding it.

Generic instructions such as “write good code,” “review code,” “explain code,” “write documentation,”
or “fix bugs” do not meet that bar on their own.
This is a collection of engineering methods, not a general prompt collection.

## First skill

[commit-squashing](skills/commit-squashing/SKILL.md) is the initial quality reference.
It groups branch history into the fewest coherent review and rollback units using patch and dependency evidence.
It requires approval of the exact plan, a backup branch, and verification that the final Git tree is unchanged.
Publishing requires separate authorization.

[Evaluation scenarios](skills/commit-squashing/evals/README.md) cover normal and adversarial histories.
Reproducible Git fixtures and a standard-library test script check the example histories and reference transformations.
Agent decisions and approval handling still require evaluating an actual run.

## Use and layout

Copy or install a skill directory using your Agent Skills-compatible tool's discovery mechanism.
The instructions assume access to the tools needed for the method; `commit-squashing` requires Git.
No particular agent, installer, or runtime is required by this repository.

```text
skills/<skill-name>/
├── SKILL.md
├── references/   # optional
├── scripts/      # optional
├── assets/       # optional
└── evals/        # repository-specific evaluation cases
```

`SKILL.md` contains portable discovery metadata and operational instructions.
Add supporting directories only when they serve the method.
`evals/` is this repository's convention for evaluating behavior, not a required runtime feature.

## Quality bar

Every skill needs:

1. A precise trigger description.
2. A clearly defined objective.
3. Explicit invariants where correctness or safety matters.
4. Evidence requirements for decisions.
5. Explicit authorization gates before destructive actions.
6. Deterministic or machine-verifiable postconditions where possible.
7. Clear stop conditions.
8. Minimal assumptions about the host agent.
9. No unnecessary vendor-specific behavior.
10. Eval cases covering normal and adversarial situations.

For methods that change state, prefer:

```text
Inspect → Reason → Plan → Approval → Act → Verify → Stop
```

The reasoning and safety boundaries matter more than the exact section headings.
See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution criteria.

## License

[Apache-2.0](LICENSE).
