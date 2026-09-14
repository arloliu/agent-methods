---
name: release-readiness
description: >
  Assess, prepare, or publish a software release bound to one candidate commit.
  Use when asked whether a repository or package is ready to release, which version to choose,
  to prepare release notes, create a version tag, or publish a release.
  Shows the exact release plan before consequential actions,
  executes only approved actions for a candidate judged ready,
  and verifies tag and publication state afterwards.
  Not for deployment, rollout monitoring, branch integration, or history cleanup.
---

# Release Readiness

Bind every claim, check result, release note, tag, and publication to one candidate commit.
Judge readiness from evidence that covers that exact candidate.
Execute only approved actions, only for a candidate judged ready,
and report preparation, tagging, pushing, publication, and verification as separate observed statuses.

## Invariants

- One candidate: every statement names the same full commit ID and tree ID.
  A changed candidate invalidates evidence, the plan, and any approval.
- Version references are updated and committed before tagging; the tagged tree already names the released version.
- Published tags are immutable: never delete, move, re-point, or force-push one.
  Correct a mistake with a new version.
- Preparation is not publication.
  Perform only the authorized actions and report each action's status from observed state.
- Evidence categories stay separate: automated checks, executed behavioral or model evaluations, and written scenarios.
  Failed, incomplete, unrun, and stale evidence remains visible.
- Required automated checks cover the final candidate: they ran on it,
  or an earlier run is retained with recorded evidence that the intervening change lies outside that check's inputs.
  Evaluation results from an earlier candidate are cited with that candidate and the difference,
  never as results for the final candidate.
- Authorization names the exact tag, commit, remote, release entry, and artifacts.
  Authority to prepare does not include authority to publish,
  and an earlier approval does not extend to a new candidate, version, remote, or channel.
- A `not-ready` verdict ends the run before any tag, push, or publication; authorization cannot override it.

## Establish scope, policy, and candidate

Read the repository's release instructions and package conventions before selecting a version or running any check.
Extract the scope rules, tag format, version rule, version reference locations, required checks and evaluations,
publication channel, and any product-readiness judgment the owners must supply.
Without a policy, use Semantic Versioning 2.0.0 and annotated tags, and state that choice.

State the requested outcome: assess, prepare, or publish.
List the actions the session authorizes: commit version references, create a tag, push the branch,
push the tag, or publish a release entry.
Artifact uploads, checksums, signatures, and registry publication are outside this method;
when the policy requires one, record it as an action the user must complete separately.
Treat an unclear request as an assessment.

Resolve the release scope from the request, the release instructions,
or a unique inference from existing tags and package manifests.
If the scope or tag convention stays ambiguous, stop and list the observed evidence for the user to choose;
never invent a convention.

Record the candidate with read-only Git queries:

```sh
git --no-optional-locks status --porcelain=v1 --untracked-files=all
git --no-optional-locks branch --show-current
git --no-optional-locks rev-parse HEAD HEAD^{tree}
git --no-optional-locks tag --list '<scope-prefix>*'
git --no-optional-locks rev-parse '<previous-tag>^{commit}'
```

The previous release is the highest version tag in scope, peeled to its commit.
Local tags can be stale: query `git ls-remote <remote> 'refs/tags/<scope-prefix>*'`
when existing authorization covers network access, and record which view was used.
With no tag in scope, use the policy's starting version and state that this is the first release.
Analyze a dirty worktree, but stop before preparation when the policy requires a committed candidate;
never stash, commit, or discard user changes to satisfy that gate.

## Map changes and propose the version

Inventory `<previous-release-commit>..HEAD` filtered to the scope's paths, reading patches rather than subjects.
Include shared material only when it changes the scope's delivered behavior, installation, or requirements.
Map each change to the public contract:
supported tasks and triggers, required inputs and dependencies, approval boundaries,
promised outputs, and supported environments, or the package type's equivalent.
Propose the increment from that mapping and the policy, and explain it.
Name breaking changes and migration steps explicitly, including during `0.y.z`.
Release notes describe the selected scope only.

## Inventory evidence

List every check and evaluation the policy requires.
For each, record the command, the commit or tree it covered, the exit status, and the outcome,
then classify it as covering the candidate, covering an earlier candidate, failed, incomplete, or unrun.
Query CI by the exact commit; a branch status is not evidence for the candidate.
Treat summaries and earlier claims as retrieval clues and read the actual results.
Run a check only within existing authorization and its side-effect limits;
otherwise record it as unrun with the command that would run it.
Stop before preparing references when a required check has failed on the candidate
or cannot be run or retrieved for it.

## Prepare version references and notes

Search the repository for the previous tag string and version string to find every location naming the current version;
do not trust a documented list alone.
Update each location and commit under the repository's ordinary commit authorization and message conventions.
When no reference needs updating, say so with the search evidence.

Draft the release notes with the scope, version, changes, compatibility impact, migration steps,
validation evidence by category, known limitations, and required human review.
When the policy stores a changelog entry in the repository, commit it with the version references;
name the exact source commit only in the external release entry or the tag message,
because a commit cannot contain its own ID.
Record the resulting commit as the final candidate.
Then re-run every required check whose inputs the edit could affect;
retain an earlier result only with recorded evidence that the changed paths lie outside that check's inputs,
and always re-run link, metadata, and whitespace checks after a documentation edit.

## Judge readiness

The verdict is `ready` only when all of these hold:

- The release scope and previous release are resolved unambiguously.
- The final candidate is committed and the worktree satisfies the policy.
- Every required check covers the final candidate and passed.
- Every required evaluation is satisfied for the final candidate,
  or disclosed in the notes as earlier, failed, incomplete, or unrun where the policy tolerates that.
- Version references and release notes name the proposed version and the final candidate.
- The proposed tag is unused in the local view and in the remote view when it is accessible.
- Any product-readiness judgment the policy requires has been supplied by the repository owners.
- Every action the policy requires is either a supported action in the plan
  or one the user has explicitly accepted completing separately.

Otherwise the verdict is `not-ready`, listing each unmet condition and what would satisfy it.
That verdict ends the run at the prepared state with no consequential action.

## Display the plan and obtain approval

Show the plan in this form, replacing only the placeholders:

```text
Release scope: <scope>
Previous release: <tag> at <full-hash>, or none
Final candidate: <branch> at <full-hash>, tree <tree-id>, worktree <clean | dirty: paths>
Proposed version: <tag>; <increment> because <contract reasoning>
Version references: <paths> updated in <full-hash>, or none required
Release notes: <path or location>; source commit <full-hash>
Verdict: <ready | not-ready: unmet conditions>
Checks covering the final candidate: <command; exit; outcome>
Evidence on earlier candidates, failed, incomplete, or unrun: <items, or none>
Remote view: <remote> branch tip <full-hash>; tag <unused | exists at full-hash | not queried>
Requested actions, in order:
1. Create annotated tag <tag> at <full-hash>
2. Push <branch> to <remote>, when publication requires it
3. Push tag <tag> to <remote>
4. Publish release <title> on <channel> from <notes>
Not requested or not authorized: <actions>
Approve exactly these actions for this candidate?
```

Approval covers only the displayed candidate, version, remote, notes, and action list;
any change requires a new plan and approval.
An assessment or preparation request ends here with status `prepared`.

## Execute approved actions

Proceed only with a `ready` verdict and approval of the displayed plan.
Immediately before each action, re-run the state queries
and compare them with the expected state for that step using executed equality checks.
At every step, HEAD and the tree equal the approved final candidate and the worktree is clean.
Before creating the tag, it is unused locally and remotely.
Before pushing the branch, the remote branch tip equals the value the plan assumed.
Before pushing the tag, the local tag resolves to the approved commit and the remote still lacks it.
Before publishing, the remote tag peels to the approved commit and the remote branch contains it.
Stop on any difference and present a new plan.

Execute in the approved order:

```sh
git tag -a '<tag>' <full-hash> -m '<title>'
git --no-optional-locks cat-file -t 'refs/tags/<tag>'
git --no-optional-locks rev-parse '<tag>^{commit}'
git push <remote> <full-hash>:refs/heads/<branch>
git push <remote> 'refs/tags/<tag>:refs/tags/<tag>'
git ls-remote <remote> 'refs/heads/<branch>' 'refs/tags/<tag>' 'refs/tags/<tag>^{}'
```

Publish the release entry with the channel's tool only when it is available and authorized,
naming the tag, title, and notes explicitly after confirming the tag exists on the remote.
Without an available authorized channel, stop after the tag push and report the entry as not published.
On any failure, stop at that step:
do not delete or move a pushed tag, do not retry with a force option, and do not roll back on your own.
Deleting a local tag that was never pushed is a new authorization question.

## Verify and report

Verify from observed state after the last executed action:
the local tag type and target, HEAD equal to that target,
the remote tag and its peeled target against the final candidate,
the release entry's tag, title, body, and draft or prerelease flags,
the version references in `git show '<tag>^{commit}:<path>'`,
every previously existing tag unchanged, and the remote branch containing the candidate.

Report the scope, previous release, final candidate, verdict, version reasoning,
and the evidence table with its categories.
Report `prepared`, `committed`, `tagged`, `branch pushed`, `tag pushed`, `published`, and `verified` separately,
each as observed, `not performed`, `not authorized`, or `failed`.
Never infer a status that was not observed.
State that a release does not establish reliable agent behavior, and name the human review the notes require.
