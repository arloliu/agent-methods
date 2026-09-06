# Repository instructions

Preserve the portable Agent Skills philosophy and the [quality bar](README.md#quality-bar).
Read [history-cleanup](skills/history-cleanup/SKILL.md) as the initial quality reference
when creating or changing a skill.

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

## Git conventions

Use [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) for every repository commit,
including merge, revert, and squash commit messages.
Write subjects as `<type>[optional scope][!]: <description>`, using a lowercase type and a concise description.
Use `feat` for new capabilities and `fix` for corrections;
use `docs`, `refactor`, `test`, `ci`, `build`, `perf`, `style`, `chore`, or `revert` when appropriate.
Scopes are optional and should name the affected skill or repository area.
Mark breaking changes with `!` before the colon or a `BREAKING CHANGE:` footer, and explain the incompatibility.
Separate an optional body or footer from the preceding section with a blank line.

Before any commit, run available linters and fix linting issues.
Also run `git diff --check`.
Never add `Co-Authored-By` or any other attribution trailers to Git commit messages.
