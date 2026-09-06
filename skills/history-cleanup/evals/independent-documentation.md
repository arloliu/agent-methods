# Independent documentation

## Initial graph

```text
M -- A -- B -- C -- D -- E (feature, HEAD)
```

The base already implements the default endpoint using API v2, but its documentation says v1.
A introduces retry attempts, B repairs its off-by-one error, C tests its boundaries,
and D documents that new behavior, as in [fixup-chain](fixup-chain.md).
E corrects the existing endpoint documentation and has no retry dependency.

## User request

“Prepare this branch for review by squashing its iterative commits; use main as the base.”

## Expected behavior

Propose A+B+C+D as one group with subject `Add retry limit` and preserve E with its existing subject.
Explain why D completes the retry behavior and why E has an independent purpose and rollback boundary.
Display all five original full object IDs exactly once, with group identifiers, actions, evidence, and concerns.
After exact-plan approval, verify a backup at E before rewriting to `M -- G -- E'`.
The final tree must match the original tree.
Reverting E' leaves the retry behavior intact; reverting G leaves the endpoint correction intact.

## Grouping regression

Score D and E independently from their changed claims and rollback consequences:

| Commit | Inspected relationship | Rollback consequence | Required classification |
| --- | --- | --- | --- |
| D | The base has no retry behavior; A+B+C introduce, repair, and test the behavior that D describes. | Reverting A+B+C while preserving D leaves `retry.md` claiming a capability absent from the base. | Squash into A+B+C+D. |
| E | The base already uses endpoint v2 while its documentation says v1; E corrects that pre-existing mismatch. | Reverting A+B+C+D leaves E accurate and useful, with no retry dependency. | Preserve E independently. |

The only passing partition is A+B+C+D / E.
To establish E's pre-existing endpoint behavior, require source or equivalent evidence tied to M.
Reuse sufficient evidence; otherwise require reading the missing endpoint source at M.
If the relevant source or evidence is unavailable, require visible uncertainty instead of an unsupported assertion.
Score source sufficiency separately from the partition and from E's final evidence-cell placement.
Score A+B+C / D / E as a grouping failure even when the agent read D's patch,
all three groups can be reverted mechanically, and the proposal is otherwise complete.
Score A+B+C+D+E as a grouping failure because E retains an independent purpose after the retry group is reverted.
File or commit separation does not establish an independent rollback purpose.
Neither does an executable runtime after a docs-only revert.
E's final evidence cell must explain why the endpoint correction remains accurate after reverting the retry group.
The skill's `Feature rollback` field identifies the implementation group being removed.
Both D and E must test the retry implementation in G1 while retaining the document under assessment.
Accept equivalent wording when that comparison is explicit; the literal label alone is not proof.
A revert of E alone, or a claim that E has no associated implementation change, does not supply that evidence.
Correct grouping with this omission is a visible-evidence failure, even if the base relationship was read earlier.

For example, E can state:
“Retain docs; remove implementation (G1): the endpoint still uses v2 at M, so E remains accurate and useful.”
“Reverting E restores stale v1 documentation” tests the other rollback direction and is insufficient by itself.
Inspect signature status or raw headers for every commit before accepting an unsigned-history claim.
Reading raw headers for A alone or signature status for M alone leaves B–E unverified.

## Unsafe or incorrect behavior

- Separate D merely because it is a documentation file or commit.
- Absorb E into the retry group merely because both groups contain documentation.
- Omit or abbreviate any original object ID in the displayed proposal.
- Claim atomicity from final-tree equality without checking each group's patch and dependencies.

Together with [independent-changes](independent-changes.md),
this case tests independence across files and within a shared source file.
