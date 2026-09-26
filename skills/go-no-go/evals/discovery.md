# Discovery evaluation

Test whether requests select [go-no-go](../SKILL.md) for a go/no-go judgment on a plan or an idea.
Writing or revising a plan, interviewing the user for requirements, reviewing code, and release
judgments should remain outside it.
Executed results are in the [2026-09-25 trial record](trials/2026-09-25-claude-code.md).

Use a fresh isolated profile and workspace per prompt with fixed skill package hashes.
Expose only the description through normal discovery; explicit-name controls deliberately name
the skill.
Keep expected outcomes and evaluator artifacts inaccessible to the model.
Freeze the host, model, repetitions, budgets, permissions, and input fixture before execution.

| ID | Prompt | Expected |
| --- | --- | --- |
| explicit-en | Use the go-no-go skill on the plan in `docs/plan.md`. | load |
| explicit-zh | 用 go-no-go 這個 skill 幫我看看 `docs/plan.md` 這份計畫。 | load |
| go-no-go-en | Go or no-go on this plan? | load |
| ready-en | Is this design ready to implement? | load |
| ready-zh | 這個計畫可以開始做了嗎？ | load |
| worth-zh | 這個想法值得做嗎？ | load |
| proceed-en | Should we proceed with this proposal? | load |
| commit-en | Give me a go or no-go before I commit to the plan in `docs/plan.md`. | load |
| boundary-look-en | Can you take a look at this plan for me? | load; confirms whether a verdict is wanted before judging |
| write-plan-en | Write a plan to add a `--low-stock` filter to the stock report. | skip |
| grill-en | Grill me on this design -- poke holes in it. | skip |
| review-pr-en | Review this PR for correctness and style. | skip |
| release-zh | 這個版本可以發布了嗎？ | skip |
| brainstorm-en | Brainstorm some ideas for improving the stock report. | skip |
| explain-plan-zh | 幫我解釋一下這份計畫在做什麼。 | skip |
| requirements-en | Interview me about what this feature actually needs to do. | skip |

Record loading as complete, partial, not-loaded, or unobservable with trace evidence.
Score requested behavior separately: a positive must stay read-only and end with a report rather
than starting implementation (no discovery prompt pre-authorizes a step), and a negative must not fabricate a verdict, a blocker, or a
report template.
On eagerly injected hosts, selective discovery is unobservable rather than automatically
successful.

Report natural-language positives, explicit controls, negatives, and unsolicited actions
separately.
Retain the trace, final response, permissions, and input hashes for every run.
A verbal claim of skill use does not establish loading.
Score supplied-skill behavior with the [rubric](behavioral-rubric.md), separately from discovery.
