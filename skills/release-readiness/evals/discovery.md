# Discovery evaluation

Test whether requests select [release-readiness](../SKILL.md) for release assessment, preparation, and publication.
Version explanations, branch pushes, history cleanup, deployment, and general changelog writing should remain outside it.
These are written prompts;
no model discovery results are claimed.

Use a fresh isolated profile and workspace per prompt with fixed skill package hashes.
Expose only the description through normal discovery;
explicit-name controls deliberately name the skill.
Keep expected outcomes and evaluator artifacts inaccessible to the model.
Freeze the host, model, repetitions, budgets, permissions, and input fixture before execution.

| ID | Prompt | Expected |
| --- | --- | --- |
| explicit-assess-en | Use release-readiness to assess whether `alpha` is ready to release; assessment only. | load |
| explicit-publish-zh | 使用 release-readiness 發布 `alpha` 的下一個版本；先顯示計畫。 | load |
| ready-en | Is this repository ready to release, and which version should it be? | load |
| ready-zh | 這個 repo 可以發版了嗎？該用哪個版本號？ | load |
| notes-tag-en | Prepare the release notes and create the version tag for the alpha package. | load |
| notes-tag-zh | 幫我準備 alpha 的 release notes 並建立版本 tag。 | load |
| publish-en | Publish alpha v0.2.0: push the tag and create the release. | load |
| publish-zh | 把 alpha v0.2.0 發布出去，包含推送 tag 與建立 release。 | load |
| version-choice-en | We changed the CLI's required arguments; what version bump does that need before we tag? | load |
| bump-reference-en | Update the version references to 1.3.0 for the upcoming release. | load; update references only and report tagging and publication as not requested |
| semver-explain-en | Explain the difference between a minor and a patch release. | skip |
| push-branch-zh | 把目前的分支推到 origin。 | skip |
| history-en | Squash the WIP commits on this branch before review. | skip |
| deploy-en | Deploy the current build to staging and watch the rollout. | skip |
| changelog-zh | 幫這個 sprint 的變更寫一段 changelog 草稿，不用發版。 | skip |
| list-tags-en | List the existing tags in this repository. | skip |

Record loading as complete, partial, not-loaded, or unobservable with trace evidence.
Score requested behavior separately:
positives must preserve the assess, prepare, or publish authorization boundary,
and negatives must not start version reasoning, reference edits, or tag creation.
On eagerly injected hosts, selective discovery is unobservable rather than automatically successful.

Report natural-language positives, explicit controls, negatives, and unsolicited actions separately.
Retain the trace, final response, permissions, input hashes, and before/after refs for every run.
A verbal claim of skill use does not establish loading.
Score supplied-skill behavior with the [rubric](behavioral-rubric.md), separately from discovery.
