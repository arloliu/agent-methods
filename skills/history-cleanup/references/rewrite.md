# Rewrite, verify, and publish

Use this procedure only after approval of the exact displayed plan,
or for a separately authorized publication request.

## Act after approval

Complete applicable repository-required precommit checks after approval, before creating the backup.
If a required check fails or cannot complete, report its actual status and stop before rewriting.
Then revalidate state, including any working files changed by those checks:

```sh
git --no-optional-locks status --porcelain=v1 --untracked-files=all
git --no-optional-locks branch --show-current
git --no-optional-locks rev-parse HEAD
git --no-optional-locks rev-parse <approved-base-ref>^{commit}
git --no-optional-locks merge-base --all <approved-base-ref> HEAD
```

Keep the displayed branch, HEAD, base ref, base-tip ID, and unique merge-base ID as the immutable approved record.
Compare each current value with that record using an executed equality predicate before creating the backup.
Observe the Git query and comparison results; every query and every predicate must succeed.
Printing values, matching trees, or asserting equality in prose does not establish these comparisons.
Stop on a failed query or unequal value, including a changed base commit with the same tree.
Do not replace approved values with current observations to make a comparison pass.
Re-inspect and obtain approval of an updated plan before proceeding after a mismatch.

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
git --no-optional-locks for-each-ref --format='%(refname) %(objectname)'
```

Before starting the approved rewrite operation, confirm that branch, HEAD, base, merge-base, and worktree are unchanged.
Confirm that the verified backup still resolves to the original HEAD.
Repeat the executed comparisons against the immutable approved record.
Also compare the backup commit ID with the approved HEAD.
Require successful queries and equality predicates immediately before starting the rewrite; otherwise stop.
Any intervening change triggers the same stop and re-inspection rule; a prior clean result is not sufficient.

Rewrite from the approved merge-base using a mechanism appropriate to the approved topology.
For a linear range, interactive rebase is suitable.
Pass `--no-update-refs` when starting any rebase to override `rebase.updateRefs=true`,
which could otherwise move the backup and other branches along with rewritten commits.
For example: `git rebase --interactive --no-update-refs <approved-merge-base>`.
If Git rejects that option, stop and select a supported strategy before rewriting.
When generating a todo for a linear rebase:

1. Derive the expected ordered `(action, source ID)` list from the approved groups and removals.
   Use recorded full IDs, or resolve abbreviations uniquely against the inventory.
2. Construct the complete replacement before emitting reordered instructions.
3. Have the sequence editor parse the completed replacement and compare it with that expected list before allowing replay.
   Require the approved actions and order, each retained source exactly once, and only approved omissions.
   Stop on a parse error or mismatch; validating the original input alone does not validate the replacement.

Perform only the approved picks, squashes/fixups, justified moves, subject edits, and explicitly approved removals.
Do not broaden the range or opportunistically clean unrelated history.
Resolve conflicts only when the resolution clearly preserves both the approved net change and grouping.
If a conflict requires a behavioral decision or changes the planned result, stop for user direction.

## Verify and stop

Verify the backup commit independently of tree equality:

```sh
git --no-optional-locks rev-parse <backup-branch>^{commit}
git --no-optional-locks for-each-ref --format='%(refname) %(objectname)'
```

The backup must still resolve to the recorded original HEAD commit ID.
Compare refs with the recorded snapshot: only the approved target branch may move;
all other refs must retain their names and object IDs, with no unexpected additions or deletions.
A moved backup is a verification failure even when its tree matches.

Compare the recorded original tree with both trees below:

```sh
git --no-optional-locks rev-parse HEAD^{tree}
git --no-optional-locks rev-parse <backup-branch>^{tree}
git --no-optional-locks diff --exit-code <backup-branch> HEAD
```

All tree IDs must match exactly; tree identity is primary and the diff is a secondary check.
Verify the history from the approved merge-base to rewritten HEAD against the inventory and plan:

- Expected commit count and resulting order/parent relationships.
- Every approved group exactly once, with its intended patch content.
- Preserved commits still independent and approved drops absent.
- Correct subjects and agreed attribution handling.
- No unapproved history changes, including outside the rewrite range.

Inspect resulting patches and dependencies, not only log subjects and counts.
Confirm the worktree is clean with `git --no-optional-locks status --porcelain=v1 --untracked-files=all`
and the rewrite operation has finished.
If any check fails, report failure, retain the backup, and stop for recovery direction.
Do not claim success, publish, or silently reset away the failed result.

Report:

List resulting commits in approved order with their group IDs, full object IDs, and subjects.
Compare these IDs with recorded Git output before sending the final response.
Complete every field below, retaining separate verification results when shortening the report.
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
Resulting history: <group; full commit ID; subject, in approved order; or unavailable>
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
