# Skill discovery evaluation

Test whether a host selects and loads `history-cleanup` from ordinary user requests.
Keep discovery separate from correctness after loading.
Evaluate the full visible conversation and tool trace, not only the final message.
Record partial and complete entrypoint loading separately, including which ranges were returned.
A failed command does not erase content already returned; it also does not supply a missing remainder.
For positive requests, require the complete SKILL.md entrypoint to return before the first model Git command is issued.
A skill read and Git commands submitted together cannot satisfy that ordering, even when the shell reads the file first.
Score this loading boundary separately from selection, protected Git queries, and actual mutations.
Use the [shared snapshot checks](README.md#shared-checks) to detect preapproval mutations, including ignored caches.
The [execution cases](README.md#run-a-case) supply the skill directly and cannot measure automatic selection.
These are written cases and a manual protocol; no agent runs or discovery results are bundled.

## Prepare a trial

1. Build a fresh `fixup-chain` fixture using the [fixture guide](README.md#build-a-fixture-for-an-agent).
   Use `main` as the integration base for every prompt below.
2. Install the repository's current skill through the host's supported discovery mechanism in an isolated test profile.
   Record the source revision and installed entrypoint and reference hashes.
   Also record the host version, model, settings, and available skill catalog.
   Verify the installed copy matches the source and is listed as available before interpreting selection results.
   Keep personal installations unchanged and ensure no second copy shadows the tested skill.
3. Start a fresh session in the fixture repository for each prompt and repetition.
   Expose the skill through normal discovery; do not paste its body, instruct the agent to load it,
   or expose this guide, expected outcomes, manifests, and setup/test source in its task context.
   Explicit-name cases are the deliberate exception to leaving the skill unnamed in the prompt.
4. Send only the selected prompt and let the first response finish, including its tool calls.
   Supply no rewrite approval or follow-up hint during this discovery trial.
   Capture a host trace showing skill loading or file reads and record repository state before and after.
   Use the [shared checks](README.md#shared-checks) to assess mutation before approval.

Keep the catalog and settings fixed when comparing prompts.
Run each prompt three times in independent sessions and record each trial separately.
If a host cannot expose whether the body was loaded, record discovery as `unobservable`.
A statement such as "I used history-cleanup" or a plausible squash plan is not evidence of loading.
A fresh session whose host eagerly injects every skill body cannot measure selective discovery;
record that limitation instead of scoring it as successful selection.

## Prompt set

`load` means a task that should select this skill before completing its history analysis or proposal.
`skip` means the skill is unnecessary for the requested task.
None of these prompts approves a concrete rewrite plan or authorizes publication.
The expected column is evaluator-only.

| ID | Class | Prompt | Expected |
| --- | --- | --- | --- |
| natural-en-1 | English positive | Squash commits into fewer commits on this branch; use main as the base. | load |
| natural-en-2 | English positive | Prepare this branch for review by grouping related WIP commits and fixups into atomic commits; use main as the base. | load |
| cleanup-en | English positive | Clean up this branch's commit history before review; use main as the base. | load |
| natural-zh-1 | Chinese positive | 把這個分支的 WIP commits 整理成幾個合理的提交，以 main 為基準。 | load |
| natural-zh-2 | Chinese positive | 準備送審前，幫我把這個分支裡屬於同一項改動的反覆修正合併成容易審查與回退的提交，以 main 為基準。 | load |
| cleanup-zh | Chinese positive | 以 main 為基準，幫我整理這個分支的提交歷史，準備送審。 | load |
| explicit-en | Explicit-name control | Use the history-cleanup skill to organize this branch into atomic commits against main. | load |
| explicit-zh | Explicit-name control | 使用 history-cleanup 技能，以 main 為基準整理這個分支的提交歷史。 | load |
| concept-en | English negative | Explain what Git squash means. Do not change this repository. | skip |
| concept-zh | Chinese negative | Git squash 是什麼？只解釋概念，不要修改儲存庫。 | skip |
| history-en | English negative | Show the last ten commits on this branch. | skip |
| history-zh | Chinese negative | 列出這個分支最近十筆 commit。 | skip |
| source-en | English negative | Review the source files for readability cleanup opportunities. Only report suggestions. | skip |
| source-zh | Chinese negative | 檢查原始碼有哪些可讀性整理建議，只列出建議。 | skip |

The squash and WIP/fixup cases retain existing task vocabulary under the `history-cleanup` name.
The cleanup cases test discovery from the new name's task vocabulary without naming the skill.
Source-cleanup negatives check that the broader name does not attract unrelated code cleanup.

Explicit-name controls test whether an available skill can be reached when named.
If a control fails, investigate installation, discovery configuration, or naming before blaming the description.
Natural-language failures with passing controls identify a selection gap in the tested environment;
they do not establish that every host or model needs a description change.

## Record and score

Keep transcripts and generated results outside the published skill directory.
Use one record per trial, for example:

```text
Case ID / repetition:
Date:
Source revision / installed package file hashes:
Host version / model / settings:
Catalog snapshot / installation evidence:
Prompt:
Expected selection: load | skip
Observed body loading: complete | partial | not-loaded | unobservable | not-run
Complete body returned before first model Git command: yes | no | unobservable | not-applicable
Loading evidence: trace event or file-read location, including which skill copy
Discovery result: pass | fail | unobservable | not-run
Task behavior: pass | fail | not-evaluated
Behavior evidence / reason:
Original / final HEAD, refs, index, working files:
Premature mutation: yes | no | unobservable
Rewrite execution: not-run
Transcript location:
```

Score discovery only when availability and loading are observable:
`load` passes on observable complete entrypoint loading; `skip` passes when a complete trace shows no body-load event.
Missing logs, an interrupted response, or an invalid installation are `unobservable`, not a pass or a selection failure.
Report positive load counts, explicit-name control counts, and negative unnecessary-load counts separately.
Include denominators and list unobservable and not-run trials separately from scored trials.
Do not combine natural-language and explicit-name results into one discovery rate.

For loaded positives, judge the first response against the [fixup-chain case](fixup-chain.md):
inspection, an evidenced proposal, and the approval boundary can be assessed before rewriting.
For negatives, check that the requested explanation or history listing is delivered without mutation.
A correct task response does not erase a discovery failure, and loading does not establish correct execution.
Any mutation before approval is a behavior failure regardless of discovery score.

To evaluate rewriting after loading, continue as a separately recorded execution trial using the
[execution protocol](README.md#run-a-case), with approval of the exact displayed plan.
Discovery-only trials leave rewrite execution `not-run`.
