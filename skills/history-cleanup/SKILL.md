---
name: history-cleanup
description: >
  Clean up a Git branch's commit history while preserving its final tree.
  Use when asked to squash commits into fewer commits, clean up branch history,
  or group related WIP commits, fixups, partial changes, retries, and reverts
  into atomic review and rollback units before review, merge, or publication.
  Not for merely listing history, explaining Git concepts, or cleaning source files.
---

# History Cleanup

Propose the fewest atomic commits that accurately represent a branch's work.
The user reviews the proposal's evidence, grouping, and checks before approving a rewrite.
An atomic commit is one coherent change a reviewer can understand independently,
forming a meaningful review and rollback unit that can be reverted without unintentionally undoing unrelated work.
Do not minimize commit count at the expense of reviewability, dependency correctness, attribution, or rollback safety.

## Invariants

The rewrite may change commit boundaries, subjects, justified ordering, and commit IDs.
It must not change the final Git tree:

```text
original HEAD^{tree} == rewritten HEAD^{tree}
```

The net `<merge-base>..HEAD` change is the source of truth.
Tree equality proves the final snapshot is unchanged; it does not prove that intermediate groups are atomic.
Verify both the tree and the approved grouping.

Inspection and planning are read-only.
Never rewrite until the user explicitly approves the exact displayed plan.
Rewriting requires a clean worktree, unchanged inspected branch/base/HEAD, and a verified local backup branch.
Publishing is separate: do not push automatically or force-push without authorization for the exact remote and branch.
Use `--force-with-lease` when authorized; never silently substitute unconditional `--force`.

## Inspect

- Use read-only Git queries and file reads; use `git --no-optional-locks` so status does not write index metadata.
- Batch independent queries when the host preserves complete output and each command's exit status.
- Reuse recorded inventory and patches during planning; re-read missing evidence or changed state.
  Reuse never replaces the state and backup revalidation required before rewriting.
- Read repository instructions and configuration to identify required checks;
  identifying them does not authorize execution.
- Defer validation commands that may create caches, bytecode, reports, or build output until after approval.
  Test runners, syntax compilation, and formatter checks are not automatically free of side effects.
- Keep generated and ignored files intact; do not delete outputs or weaken the approval gate to hide a mutation.

Record repository state and the original tree ID:

```sh
git --no-optional-locks status --porcelain=v1 --untracked-files=all
git branch --show-current
git rev-parse HEAD HEAD^{tree}
```

Record the upstream when present, or `none`.
A dirty worktree or detached HEAD may still be analyzed and planned.
Report those conditions; require a clean worktree and an explicitly agreed branch attachment before rewriting.
Do not automatically stash, discard, or commit uncommitted changes to satisfy the gate.
If HEAD does not resolve to a commit, report that there is no history to squash and stop.

Choose the integration base in this order:

1. The user-supplied base.
2. An unambiguous configured remote default branch from existing local repository state.
3. Local `main` or `master` when exactly one is plausible.
4. Otherwise, ask the user to choose before proposing a rewrite base.

Do not fetch merely to discover the base unless requested.
Do not mistake the current branch's upstream for the integration base.
If a user-supplied base does not resolve, report the error and request direction instead of silently falling back.
Record the base ref and its resolved commit ID, then resolve the fork point:

```sh
git rev-parse <base-ref>^{commit}
git merge-base --all <base-ref> HEAD
```

Require exactly one merge-base.
If none exists, stop rather than silently using `--root`.
If multiple merge-bases exist, request direction rather than selecting one arbitrarily.
Distinguish the base ref, such as `origin/main`, from the merge-base commit.
The merge-base defines the inventory range and rewrite boundary; the base tip does not.

Inventory every commit in `<merge-base>..HEAD` oldest first, with parents before children:

```sh
git rev-list --reverse --topo-order <merge-base>..HEAD
```

For each commit collect its full hash, parents, author, subject, changed paths, diff summary, and merge status.
Record relevant attribution and signature concerns, including signatures that rewriting would invalidate or remove.
Read complete individual patches, including merge resolutions relative to their parents, and the complete net patch.
A stat or path summary is insufficient;
recover abbreviated IDs and filtered or truncated patch content before reasoning:

```sh
git --no-optional-locks diff <merge-base> <original-head>
```

Do not infer grouping from subjects, filenames, timestamps, or adjacency alone.
Inspection ends only when every commit has an understood purpose or a documented uncertainty.
If the range is empty, report that there is nothing to squash and stop.

## Reason about atomic groups

Group by behavioral cohesion and diff/dependency evidence.
Keep implementation, completing tests, and required documentation together when they form one review and rollback unit.
For each documentation change, identify its changed claims and the behavior they describe.
From the inspected patches, consider retaining the documentation while reverting the associated implementation change:
if its claims would describe a capability or contract no longer present, group it with that implementation.
Preserve documentation separately only with evidence that it retains an accurate, useful purpose without that change
and can itself be reverted without undoing the implementation's purpose.
Support claims of pre-existing behavior with source or equivalent evidence tied to the merge-base.
Reuse sufficient evidence; otherwise read the missing source at the merge-base.
If the relevant source or evidence is unavailable, make that uncertainty visible.
Do not treat the behavior as established.
A separate file or a mechanically clean revert does not establish independent purpose.
Keep unrelated refactors, dependencies, generated artifacts, configuration, delivery changes,
and standalone documentation separate unless evidence proves they are integral to the same behavior.

Subjects such as `fixup!`, `squash!`, `WIP`, `oops`, `fix tests`, `retry`, and `cleanup` are investigation hints.
The diff decides.
A non-adjacent correction may join an earlier commit only when they form one atomic behavior,
intervening commits remain independent, and dependency ordering remains correct.
Do not reorder for aesthetics.

A reverted commit and its revert are drop candidates only when their combined surviving effect is empty
and later history does not depend on either commit.
Check dependent commits between the pair as well as after the revert.
Patch cancellation alone is insufficient evidence.

Surface meaningful attribution loss from grouping different authors as an open concern.
Do not invent attribution trailers.
Follow established repository conventions when preservation is appropriate, respecting any prohibition on trailers.
If attribution cannot be preserved under those conventions, request direction before rewriting the affected group.

Preserve the repository's commit-message convention, using surrounding history as evidence.
Do not introduce Conventional Commits, scopes, issue prefixes, or another style unless history demonstrates it
or the user explicitly requests it.
Preserved commits keep their subjects.
For a squashed group, retain the earliest useful subject if it still describes the result accurately;
otherwise propose the smallest necessary improvement.

Treat merge commits as hard boundaries.
Identify every merge and do not group across it or combine independent parent histories.
Explain that ordinary interactive rebase may flatten topology.
Require explicit approval of a merge-aware rewrite strategy for any range containing a merge.
Do not recreate or restructure merges without explicit direction.

Check proposed groups in their resulting order for coherent purpose, required dependencies, and rollback boundaries.
Every original commit must belong to exactly one group or be a drop candidate.
Record unresolved intent, dependencies, attribution, signatures, or topology as visible concerns.
Resolve any concern that prevents a concrete safe transformation before acting.

## Display the plan and obtain approval

Show inspected state:

```text
Branch: <branch, or detached>
Inspected HEAD: <full-hash>
Base ref: <base-ref>
Base tip: <full-hash>
Merge-base: <full-hash>
Original commits: <count>
Proposed commits: <count>
Upstream: <remote/branch or none>
```

Table every original commit oldest first with these columns:

| Resulting subject | Commits | Action | Diff evidence | Open concern |
| --- | --- | --- | --- | --- |
| `<group subject>` | `<full original commit object ID, without abbreviation or ellipsis>` → `<group ID>` | `<action>` | `<patch/dependency evidence; for documentation: Claim: what it describes; Feature rollback (<feature group>): what remains if that feature group is reverted>` | `<concern or none>` |

Use one row per original commit, oldest first, with its full object ID and an explicit resulting group identifier.
Use the repository's full object IDs; do not assume a particular hash algorithm or length.
Repeat the group's proposed subject for its members and separately list the resulting group order.
For merges, also show the planned parent relationships and rewrite strategy.
Counts include every commit in the selected range, including merges and side-branch commits.

Allowed proposal actions:

- `squash`: members become one atomic commit.
- `preserve`: the commit stays independent with its existing subject; its ID may change if its parent changes.
- `drop candidate`: proposed removal, with an empty resulting subject.
  Never label it simply `drop` before approval.

Give concrete patch/dependency evidence for every decision and make uncertainty visible.
Show any required authorship or message-body preservation as part of the plan.
If every commit is preserved and no transformation is needed, report the unchanged inventory and stop.
Do not request rewrite approval or create a backup for a no-op.
Check the final user-visible proposal against the recorded evidence before requesting approval:

- Complete the state, every table column, and all closing fields, using `none` for absent concerns.
- Every original full ID must appear exactly once in the table;
  compare all displayed IDs, including the closing tree, with Git output.
- Each documentation evidence cell must include its claim and rollback consequences.
  Name the feature group under `Feature rollback (<feature group>)`.
  Explain whether retained documentation stays accurate and useful after that implementation is reverted.
  Reverting the document alone or removing it with the feature does not answer this comparison.
- When shortening prose, retain that evidence and all five closing steps;
  tool output or earlier commentary cannot fill omissions.
- Before approval, report each executed validation check's command, observed exit code, and relevant outcome.
- Identify required checks still not-run or incomplete; inspection results do not establish that those checks passed.

For a rewrite proposal, reproduce this closing template in full, replacing only its plan-specific placeholders.
Keep all five numbered steps and their verification objects, as required by [Act after approval](#act-after-approval):

```text
Base: <base-ref> at merge-base <full-hash>
Original commits: <count>
Resulting commits: <count>
Final tree will be required to match: <recorded original tree ID, copied exactly>
Checks run: <command; observed exit code; outcome, or none run>
Checks pending: <required check; not-run or incomplete; reason, or none>
After approval:
1. Complete applicable required precommit checks; stop if any fail or cannot complete.
2. Revalidate the approved branch, HEAD, base tip, merge-base, and clean worktree; confirm no history operation is in progress.
3. Create a new local backup at the original HEAD, verify its commit ID, and record the ref snapshot.
4. Reconfirm unchanged state and backup identity, then perform only the approved rewrite.
5. Verify final tree, backup commit, other refs, grouping, subjects, clean worktree, and completed rewrite operation.

Approve this squash plan and history rewrite?
```

Approval applies only to this displayed plan, including any proposed removals and merge strategy.
Any material change to groups, subjects, order, base, attribution, or strategy requires a new plan and approval.

## Act after approval

Complete applicable repository-required precommit checks after approval, before creating the backup.
If a required check fails or cannot complete, report its actual status and stop before rewriting.
Then revalidate state, including any working files changed by those checks:

```sh
git status --porcelain=v1 --untracked-files=all
git branch --show-current
git rev-parse HEAD
git rev-parse <approved-base-ref>^{commit}
git merge-base --all <approved-base-ref> HEAD
```

Require a clean worktree, the approved branch, original HEAD, unchanged base tip, and the same single merge-base.
Confirm no merge, rebase, cherry-pick, or other history operation is already in progress.
If inspected state differs, stop and re-inspect; obtain approval of an updated plan before acting.

Create a new local backup branch at the original HEAD, for example:

```text
backup/history-cleanup/<branch>-<YYYYMMDD-HHMMSS>-<short-head>
```

Choose a valid unused ref name; never overwrite an existing backup.
Verify that it resolves to the original HEAD and record its exact name.
Stop if backup creation or verification fails; do not rely solely on reflog recovery.
Record the ref names and object IDs after creating the backup:

```sh
git for-each-ref --format='%(refname) %(objectname)'
```

Before starting the approved rewrite operation, confirm that branch, HEAD, base, merge-base, and worktree are unchanged.
Confirm that the verified backup still resolves to the original HEAD.
Any intervening change triggers the same stop and re-inspection rule; a prior clean result is not sufficient.

Rewrite from the approved merge-base using a mechanism appropriate to the approved topology.
For a linear range, interactive rebase is suitable.
Pass `--no-update-refs` when starting any rebase to override `rebase.updateRefs=true`,
which could otherwise move the backup and other branches along with rewritten commits.
For example: `git rebase --interactive --no-update-refs <approved-merge-base>`.
If Git rejects that option, stop and select a supported strategy before rewriting.
Perform only the approved picks, squashes/fixups, justified moves, subject edits, and explicitly approved removals.
Do not broaden the range or opportunistically clean unrelated history.
Resolve conflicts only when the resolution clearly preserves both the approved net change and grouping.
If a conflict requires a behavioral decision or changes the planned result, stop for user direction.

## Verify and stop

Verify the backup commit independently of tree equality:

```sh
git rev-parse <backup-branch>^{commit}
git for-each-ref --format='%(refname) %(objectname)'
```

The backup must still resolve to the recorded original HEAD commit ID.
Compare refs with the recorded snapshot: only the approved target branch may move;
all other refs must retain their names and object IDs, with no unexpected additions or deletions.
A moved backup is a verification failure even when its tree matches.

Compare the recorded original tree with both trees below:

```sh
git rev-parse HEAD^{tree}
git rev-parse <backup-branch>^{tree}
git diff --exit-code <backup-branch> HEAD
```

All tree IDs must match exactly; tree identity is primary and the diff is a secondary check.
Verify the history from the approved merge-base to rewritten HEAD against the inventory and plan:

- Expected commit count and resulting order/parent relationships.
- Every approved group exactly once, with its intended patch content.
- Preserved commits still independent and approved drops absent.
- Correct subjects and agreed attribution handling.
- No unapproved history changes, including outside the rewrite range.

Inspect resulting patches and dependencies, not only log subjects and counts.
Confirm the worktree is clean with `git status --porcelain=v1 --untracked-files=all`
and the rewrite operation has finished.
If any check fails, report failure, retain the backup, and stop for recovery direction.
Do not claim success, publish, or silently reset away the failed result.

Report:

Give each check a status with its command, observed exit code, and relevant output:
`passed` (completed successfully), `failed` (observed failure), `not-run` (not executed),
or `incomplete` (blocked or insufficient evidence).
A missing executable, blocked command, or empty test collection cannot establish that required tests passed.
For compound commands, inspect each required component's result; a final exit zero cannot erase an earlier failure.
Record behavioral validation, tree identity, backup identity, other refs, and grouping verification separately.
None substitutes for another, and an unexecuted check has no invented result.

```text
Rewrite: passed | failed | not-run | incomplete
Behavioral validation: passed | failed | not-run | incomplete
Tree identity: passed | failed | not-run | incomplete
Original tree: <tree-id>
Rewritten tree: <tree-id, or unavailable>
Resulting commits: <count>
Backup branch: <backup-branch, or not created>
Backup identity: passed | failed | not-run | incomplete
Other refs: passed | failed | not-run | incomplete
Grouping verification: passed | failed | not-run | incomplete
Published: no
```

If verification cannot run, report it as incomplete with the failing check rather than inventing tree values.
Then stop.

## Publishing on a separate request

Rewrite approval does not authorize publication.
On a separate publishing request, identify the exact remote and destination branch,
determine whether the branch may be shared, and explain that commit IDs changed.
Obtain explicit authorization for that target before force-pushing.
Refresh remote state where appropriate and inspect the expected destination tip so the lease is meaningful.
If remote state changed unexpectedly, stop; do not simply refresh the lease and overwrite it.
Use an explicit destination and expected remote object ID, for example:

```sh
git push --force-with-lease=refs/heads/<branch>:<expected-remote-oid> <remote> HEAD:refs/heads/<branch>
```

Never silently fall back to unconditional `--force` after a rejected lease.
