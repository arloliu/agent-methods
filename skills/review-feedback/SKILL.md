---
name: review-feedback
description: >
  Assess supplied code-review findings against current code and accepted requirements,
  and address supported findings within existing task authorization.
  Use for review reports, PR comments, or reviewer results that a current workflow requires assessing or fixing.
  General code review and issue triage are outside its scope.
---

# Review Feedback

Determine what should happen to every supplied finding and why.
Judge the reported problem independently from its suggested remedy,
then make only the changes authorized by the current task.

## Establish the batch

State whether the requested outcome is assessment or correction.
A request to assess does not authorize edits;
a request to fix feedback authorizes ordinary local fixes within that feedback's established scope.
Existing implementation-and-correction authority carries through when a reviewer returns findings during that workflow.
When intent remains unclear, assess first and leave changes pending.

Define the selected batch before changing code.
Preserve source IDs and available author, location, timestamp, and thread state.
Assign report-only IDs when stable IDs are unavailable.
Split independent claims into child IDs while retaining their source-comment mapping.
Describe a user-selected subset as that subset rather than as the entire review.

Bind the review to the current state:

- branch, commit, diff, and working-tree state;
- current code and tests relevant to each claim;
- applicable repository instructions;
- the issue, specification, plan, ADR, or recorded decision when intent matters;
- authorization for local edits and for any external or Git action.

Missing optional metadata does not block a technically verifiable claim.
Stop dependent conclusions
when a missing part of the selected batch or an inaccessible revision could change the resolution plan.
After bounded retrieval attempts, request unavailable supplied feedback and report the evidence gap.

## Build the ledger first

Inventory every finding before implementing any of them.
Record duplicates, dependencies, and conflicts without merging away their source IDs.
For each claim, reconstruct the trigger, reported behavior, expected behavior, and asserted impact.
Trace moved or obsolete line references to the current behavior.

Record three separate conclusions per item.

| Dimension | Values |
| --- | --- |
| Judgment | `supported`: evidence establishes the problem; `unsupported`: evidence contradicts it or shows no requirement violation; `outdated`: the premise no longer applies or the current code already addresses it; `unresolved`: missing evidence or requirements prevent a defensible judgment |
| Remedy | Whether the suggestion fixes the supported problem without violating requirements or expanding scope; retain the problem judgment when choosing a different remedy |
| Progress | `pending`: action remains; `changed`: a relevant change lacks sufficient verification; `verified`: the problem is addressed and covered by relevant verification; `no-change`: evidence supports taking no action; `blocked`: a specific evidence, authority, preservation, or validation issue prevents action |

Both support and rejection require evidence;
an inconclusive reproduction remains `unresolved`.
Split a partly correct claim when unsupported severity or impact would otherwise hide the supported problem.
An obsolete line number alone is not `outdated` while the behavior remains defective.
A duplicate may share change and verification evidence with its canonical item,
but duplication alone does not resolve the underlying problem.
Keep two valid findings separate when their proposed remedies conflict.

## Assess, act, and verify

Test each claim against evidence that could support or contradict it.
Inspect relevant callers, tests, and history far enough to judge the supplied concern,
without expanding into a general review.
Reproduce behavior when needed and allowed.

Choose a next action for every item.
Assessment-only work ends with recommendations and supported items still `pending`.
For correction work, recheck affected code for drift.
Implement supported fixes that fit the accepted requirements and authorization.
Preserve user changes;
block an overlapping item when they cannot be preserved safely and continue independent items.
Ask for direction when resolution would change an accepted decision,
materially expand scope, or choose between conflicting authoritative requirements.

Use the smallest sufficient checks for the reviewed behavior and complete applicable repository checks.
Record each command, outcome, covered code state, and why it covers the claim.
Broad passing tests do not verify a condition they do not exercise.
Keep failed, unavailable, and insufficient checks visible.
If code changes after assessment or verification, reassess affected findings and invalidate stale results.

Before reporting, recheck the final diff, code state, and complete item inventory.
A validation failure prevents a resolution claim until an authorized correction and successful revalidation address it.

## Action boundaries

Inspection and classification are read-only.
Source-only and other execution limits remain controlling.
Verification that changes state requires applicable task authorization.
Posting replies, resolving or dismissing threads, committing, pushing, and merging are separate actions;
perform them only when the session authorizes the exact action and target.
Never infer external thread state from local code state.
Return control after this feedback batch rather than initiating another reviewer run.

## Report

Identify the selected batch, requested outcome, reviewed branch and commit,
and the working-tree diff covered by the conclusions.
Use compact prose for one item and a table for multiple items.
For every item, report:

- claim and source mapping;
- judgment with current-code and requirement evidence;
- remedy assessment and duplicate, dependency, or conflict relationships;
- progress and actual change or no-change reason;
- verification tied to the covered code state;
- observed external state, or `not accessed` / `not applicable`.

Completion requires every inventoried finding exactly once.
Every supported finding maps to a proposed action, an observed change, or an evidenced existing fix.
Keep unsupported, unresolved, and blocked items visible.
Distinguish assessment completion, implementation completion, technical resolution, and external thread state.
