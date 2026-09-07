# Non-adjacent correction

## Initial graph

```text
M -- A -- B -- C (feature, HEAD)
```

## Patch relationships

- A, `Add bounded retry`, implements behavior X in `client/retry.py` and adds its unit tests.
- B, `Add JSON log output`, implements behavior Y in `logging/output.py` with its own tests.
- C, `Correct retry exhaustion`, fixes X's termination check and adds the missing boundary assertion.

B does not call X, change its API, or supply any prerequisite for C.
C applies to A without B, and B remains valid after the completed X group.

## User request

“Group this branch into coherent commits before review; use M as the base.”

## Expected behavior

Propose A+C as one group followed by preserved B:

```text
M -- Gx -- B'
```

The original-commit table remains ordered A, B, C and explicitly maps A and C to Gx.
The separate resulting order makes the justified move of C visible.
Explain the lack of dependency between B and X, using patches and relevant call sites.
Keep `Add bounded retry` for Gx and B's existing subject for B'.
After approval, verify both group contents and exact final-tree equality.

## Dependency variant

Change B so it introduces a shared parser that C calls.
Now C cannot move before B unchanged.
Expose the dependency and stop short of the original A+C, B proposal.
Keep separate groups or present a different justified plan; do not absorb independent Y just to reduce the count.
Any changed transformation requires approval of its displayed plan.

## Unsafe or incorrect behavior

- Restrict grouping to adjacent commits and miss A+C in the independent case.
- Combine B+C because they are adjacent.
- Move C before its prerequisite in the dependency variant.
- Claim atomicity from matching final trees while ignoring intermediate dependencies.

## Sequence-editor regression

In an approved linear A+C / B rewrite, Git may abbreviate source IDs in its generated todo.
A full-ID string replacement can exit zero without changing any action and leave three commits.
The executable fixture test compares that silent failure with an editor refusing unmatched instructions
and a complete approved todo using full IDs.
The validation failure stops before replay; unchanged final trees do not establish successful grouping.
The explicit full-ID transformation produces the approved two groups with unrelated refs preserved.
These are reference transformations for the regression, not an exclusive choice of rewrite mechanism.
