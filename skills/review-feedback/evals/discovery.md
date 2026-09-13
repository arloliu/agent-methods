# Discovery evaluation

Test whether requests select [review-feedback](../SKILL.md) for supplied findings.
General review, debugging, and unrelated implementation should remain outside feedback processing.
These are written prompts;
no model discovery results are claimed.

Use a fresh isolated profile and workspace per prompt with fixed skill package hashes.
Expose only the description through normal discovery;
explicit-name controls deliberately name the skill.
Keep expected outcomes and evaluator artifacts inaccessible to the model.
Freeze the host, model, repetitions, budgets, permissions, and input fixture before execution.

| ID | Prompt | Expected |
| --- | --- | --- |
| explicit-assess-en | Use review-feedback to assess the findings in `input/feedback.json`; do not edit. | load |
| explicit-fix-zh | 使用 review-feedback 處理 `input/feedback.json`，修正成立的項目並驗證。 | load |
| report-assess-en | Check which findings in this review report are correct and recommend what to do. | load |
| report-assess-zh | 檢查這份 review report 每一項是否成立，只做評估。 | load |
| comments-fix-en | Address these PR comments and verify the supported local fixes. | load |
| comments-fix-zh | 處理這批 PR comments，成立的問題請修正並驗證。 | load |
| incoming-fix-en | The reviewer returned these findings during the implementation; assess and address them before continuing. | load |
| incoming-assess-zh | Review workflow 剛回傳 findings；依目前只讀任務判斷哪些成立。 | load |
| subset-en | Review only comments RF-2 and RF-4 from the supplied report. | load |
| review-en | Review this branch against main and find bugs. | skip |
| old-report-zh | 先完成目前功能；旁邊有一份舊 review report 不用處理。 | skip |
| debug-en | Diagnose why this parser throws on empty input. | skip |
| issue-triage-en | Triage these open issues and assign priorities. | skip |
| implement-zh | 實作新的 retry policy。 | skip |
| review-end-en | Produce a code review report for this diff and stop when the report is complete. | skip |

## Reviewer-result continuations

Drive these as multi-event sessions rather than rewriting the incoming result as another user prompt.
Install the skill before the initial task,
then deliver the reviewer payload through the host's tool-result or agent-result channel.
Do not insert a user message between the initial task and the result.

| ID | Initial user task | Incoming non-user event | Expected |
| --- | --- | --- | --- |
| result-correction-en | Implement the requested change, run the assigned reviewer, and address supported findings before finishing. | Reviewer result containing two findings with stable IDs | load on result; assess both; apply only supported in-scope fixes under the existing correction authority |
| result-assessment-en | Review this branch and validate the assigned reviewer's findings; assessment only. | Review-tool result containing one supported and one unsupported finding | load on result; assess both; leave the supported fix pending |

Record the initial authorization, event role, event order, and absence of an intervening user turn.
A standalone user prompt that describes returned findings does not satisfy either continuation case.

Record loading as complete, partial, not-loaded, or unobservable with trace evidence.
Score requested behavior separately:
positives must preserve assessment versus correction authority,
and negatives must not start an unsolicited feedback ledger or fix loop.
On eagerly injected hosts, selective discovery is unobservable rather than automatically successful.

Report natural-language positives, explicit controls, negatives, and unsolicited actions separately.
Report reviewer-result continuation separately from direct-prompt discovery.
Retain the trace, final response, permissions, input hashes, and before/after state for every run.
A verbal claim of skill use does not establish loading.
Score supplied-skill behavior with the [rubric](behavioral-rubric.md), separately from discovery.
