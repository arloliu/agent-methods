# Repository instructions

Preserve the portable Agent Skills philosophy and the [quality bar](README.md#quality-bar).
Read [commit-squashing](skills/commit-squashing/SKILL.md) as the initial quality reference when creating or changing a skill.

- Add methods with concrete procedural value; do not bulk-create generic skills.
- Introduce dependencies only with strong justification.
- Keep `SKILL.md` concise enough to operate and explicit enough to be safe.
- Add or update evals whenever behavior changes.
- Preserve evidence requirements, explicit approval gates, verification boundaries, and stop conditions.
  Never weaken approval or verification merely to simplify a skill.
- Keep portable skill frontmatter free of agent/vendor-specific metadata
  unless the repository deliberately adopts a standard requiring it.
- Keep personal paths, local tool configuration, and generated artifacts out of published skill directories.
- Verify links, frontmatter, and consistency between instructions and evals.
  Distinguish written scenarios from executed evaluations when reporting validation.

Before any commit, run available linters and fix linting issues.
Also run `git diff --check`.
Never add `Co-Authored-By` or any other attribution trailers to Git commit messages.
