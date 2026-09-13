# Discovery evaluation

Test whether requests select [rules-check](../SKILL.md) without turning routine work into an audit.
These are written prompts; no model discovery results are claimed.
Use a fresh isolated profile and workspace per prompt, with a fixed skill catalog and source package hashes.
Expose only the description through normal discovery; explicit-name controls deliberately name the skill.
Keep this file, expected outcomes, and evaluator manifests inaccessible to the model.

Use the `ahead` fixture for branch prompts and `dirty` for working-change prompts.
Session prompts need task-specific operation evidence or a native setup sequence;
record which was used rather than pretending a fresh empty session tests history retrieval.
Negatives should receive the minimal corresponding workspace, including a harmless named lint command when needed.
Freeze repetitions, host/model, budgets and permissions before execution.

| ID | Prompt | Expected |
| --- | --- | --- |
| explicit-en | Use rules-check to review our current work and operations. | load |
| explicit-zh | 使用 rules-check 查核目前工作與操作紀錄。 | load |
| changes-en | Check whether my current changes violate this repository's agent rules. | load |
| changes-zh | 檢查目前 changes 有沒有違反這個 repo 的 agent rules。 | load |
| commits-en | I already made several commits. Check the local unpushed work against the repo instructions too. | load |
| commits-zh | 已經 commit 幾次了，幫我確認這批還沒 push 的工作有沒有違反 repo 規則。 | load |
| session-en | This session has become long. Verify whether you missed any required lint, tests, or approval steps. | load |
| session-zh | Context 已經很大了，查一下你這次有沒有漏掉規則要求的 lint、測試或批准。 | load |
| staged-en | Review only the staged changes for compliance with the applicable agent instructions. | load |
| base-zh | 以 main 為基準，查核整個 branch 的變更與 commit messages 是否符合 agent rules。 | load |
| bug-en | Review this function for an off-by-one bug. | skip |
| rules-edit-zh | 幫我修改 AGENTS.md，新增命名規範。 | skip |
| lint-en | Run python3 lint.py and tell me whether it passed. | skip |
| lint-zh | 執行 python3 lint.py，告訴我結果。 | skip |
| concept-en | Explain what an upstream branch is. | skip |
| history-zh | 列出目前 branch 最近五筆 commits。 | skip |

Record loading as complete, partial, not-loaded, or unobservable, citing the skill copy in the trace.
Record task behavior separately: correct audit scope for positives, and delivery of only requested work for negatives.
A verbal claim of skill use does not establish loading; a good audit does not erase a loading gap.
On eagerly injected hosts, selective discovery is unobservable rather than automatically successful.
Unnecessary loading and an actual unsolicited audit are distinct measurements.

Report natural-language positive loads, explicit-name controls, negative loads, and unsolicited audits separately.
Retain trace, final response, permissions, input hashes, and before/after state for every run.
Missing installation evidence or inaccessible trace makes discovery unobservable; preserve failures and denominators.
Score supplied-skill execution with the [rubric](behavioral-rubric.md), separately from discovery.
