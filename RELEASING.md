# Release policy

Version and release each skill independently.
Users install individual methods, and each method has its own compatibility contract and evaluation evidence.
Each skill release is also recorded in a dated repository snapshot,
which labels the whole catalog at that commit and is not a compatibility version.
Repository maintenance without a skill release is not tagged.

## Names and release scope

- Tag: `<skill-name>/v<major>.<minor>.<patch>`, for example `history-cleanup/v0.1.0`.
- Release title: `<skill-name> v<major>.<minor>.<patch>`, for example `history-cleanup v0.1.0`.
- Use the skill's directory and frontmatter name as `<skill-name>`.
- Start a new skill at `0.1.0`; the first history-cleanup release uses `history-cleanup/v0.1.0`.
- Repository snapshot tag: `v<YYYY>.<MM>.<DD>.<N>`, for example `v2026.09.19.1`.
- Repository snapshot release title: `agent-methods v<YYYY>.<MM>.<DD>.<N>`, for example `agent-methods v2026.09.19.1`.

[Repository snapshots](#repository-snapshots) defines the date and sequence fields.

A Git tag identifies an entire repository commit.
Its skill prefix defines the release's scope; other skills at that commit do not acquire that version.
When releasing several skills from one commit, create a separate tag and release for each.
Use the tag as the authoritative version identifier without requiring a duplicate version field in `SKILL.md`.
Keep published tags and versioned artifacts immutable; issue a new version for corrections.

## Choose the version

Use [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).
For a skill, the public contract covers task triggers and scope, required inputs and dependencies,
approval boundaries, promised outputs, and supported installation and execution environments.
Describe compatibility changes against that contract rather than the number of edited lines.

For stable versions starting at `1.0.0`:

| Change | Version increment |
| --- | --- |
| Compatible correction to instructions or supporting artifacts that restores the existing contract | Patch |
| Compatible addition to supported tasks, inputs, outputs, or environments | Minor |
| Incompatible change to the public contract, including a skill rename or new required dependency | Major |

During `0.y.z`, use patch releases for compatible corrections.
Use minor releases for new capabilities or breaking changes.
Identify breaking changes and migration steps explicitly even before `1.0.0`.
Release `1.0.0` when the documented contract is intended to be stable.
Version numbers express contract evolution; evaluation results separately describe observed model reliability.

Bump only affected skills.
Changes limited to repository CI, contributor guidance, or evaluation tooling do not require a skill release
unless they change its delivered method, installation, or public contract.
If shared material changes a skill's delivered behavior or requirements, include that skill in the release scope.

## Repository snapshots

A snapshot labels the catalog at the commit where skills were released.
It does not follow Semantic Versioning, because the repository has no single public contract to version.
Skill tags remain the authoritative versions; a snapshot adds a dated name and a manifest of skill releases.

- Give every commit that receives at least one skill tag exactly one snapshot tag, and tag no other commit.
  Releasing several skills from one commit produces one snapshot.
  Changes limited to repository CI, contributor guidance, or evaluation tooling produce no snapshot.
- `<YYYY>.<MM>.<DD>` is the UTC+8 calendar date on which the snapshot tag is created,
  with a four-digit year and two-digit month and day.
  Take it from `TZ=Asia/Taipei date +%Y.%m.%d`, whatever the machine's own time zone.
  `<N>` counts the snapshots created on that date, starts at 1, and is not padded.
  Take the next `<N>` from the highest existing number for that date in the local and remote tag lists, plus one.
  Never reuse a number, even if a tag was removed.
- List snapshot tags with `git tag --list 'v[0-9][0-9][0-9][0-9].*'`.
  Skill names contain no `.`, so this pattern never matches a skill tag.
  Order snapshots by date, then `<N>`.
- Write the release notes as a manifest.
  Give the exact source commit, then a table listing every skill in the repository with its latest released tag,
  marked as new in this snapshot or released earlier.
  Link each skill's release notes instead of repeating them.
- A snapshot names released versions only.
  Its commit may contain unreleased changes to skills that were not part of this release.
  Install or pin one skill by its own tag.
- Do not record a snapshot tag in tracked files.
  The tagged tree cannot name a tag that does not exist yet, and a published tag cannot be amended afterwards.
  README links to the Releases page instead.
- Publish the snapshot release last and mark it as the repository's latest release.
  Mark skill releases published on GitHub as not latest, so that Latest names the snapshot.

## Prepare and verify a release

1. Identify the affected skill, its previous release tag if any, and the proposed version.
   Review changes since that tag and explain the version increment using the rules above.
2. Prepare release notes with the skill name, version, exact source commit, changes, compatibility impact,
   migration steps when needed, validation evidence, and known limitations.
3. Run applicable repository linters, artifact and link checks, relevant automated tests, and `git diff --check`.
   Record commands and outcomes, and resolve failures before tagging.
4. Tie evaluation claims to the candidate actually evaluated, including model and environment where relevant.
   Distinguish automated fixture checks, executed model evaluations, and written scenarios.
   Report failed, incomplete, and unrun evaluations explicitly.
   Earlier candidates' results do not establish the released candidate's reliability.
5. Update every place in the repository that names the skill's current version, and commit that change.
   Today that is `README.md`: the skill table's "Latest release" column, and the Releases table's "Latest" and "Tags" columns.
   Do this before tagging, not after.
   A tag is immutable and points at a tree, so a tag created over a stale README names the previous version forever,
   and the fix can only land on the branch afterwards.
   Search for the previous tag string rather than trusting this list, since a new reference may have been added since.
6. Confirm the tag name is unused and targets the exact source commit described in the notes.
   That commit is the one whose checks passed and whose README names the version being released.
   Complete publication within the user's authorized scope,
   then verify the published tag target, the release contents, and that the repository's version references match.
7. When the release includes a skill tag, prepare the repository snapshot from the same verified commit.
   Choose the next `<N>`, draft the manifest, and list the snapshot tag as its own action in the release plan.
   Creating or publishing it needs the same approval as any other tag or release.
   Create it only after the skill tags exist, then verify its target commit,
   that its manifest matches the skill tags, and that it is the latest release.

A release does not establish that every agent follows the method reliably.
State the intended use and human review requirements alongside the observed evaluation limits.
Report preparation, tagging, and publication status separately so unfinished publication is visible.
