# Skill discovery evaluation

Test whether a host selects and loads `progress-check` from ordinary requests,
and whether launch-only requests follow the description's recording instruction without loading the body.
Keep discovery separate from correctness after loading.
Evaluate the full visible conversation and tool trace, not only the final message.
These are written cases and a manual protocol; no agent runs or results are bundled.

## Prepare a trial

1. Build a fixture directory with one heartbeat worker script available to launch.
2. Install the current skill through the host's supported discovery mechanism in an isolated test profile.
   Record the source revision, installed file hashes, host version, model, settings, and available skill catalog.
   Verify the installed copy matches the source and is listed as available.
3. Start a fresh session for each prompt and repetition.
   Expose the skill through normal discovery; do not paste its body or name it, except in the explicit-name controls.
4. Send only the selected prompt and let the first response finish, including tool calls.
   Supply no approval or follow-up hint.
   Capture the host trace showing skill loading or file reads.

Run each prompt three times in independent sessions and record each trial separately.
If a host cannot expose whether the body was loaded, record discovery as `unobservable`.
A statement such as "I used progress-check" is not evidence of loading.

## Prompt set

`load` means the request should select this skill.
`skip` means the skill body is unnecessary.
`record` means the body should not load,
but the launch record fields named in the description should appear in the agent's launch.
The expected column is evaluator-only.

| ID | Class | Prompt | Expected |
| --- | --- | --- | --- |
| progress-en | English positive | Where are we on this task, and is anything still running in the background? | load |
| stuck-en | English positive | Check whether any background job, subagent, or watcher you started is stuck. | load |
| done-en | English positive | Before you call this done, confirm nothing you started is still running or failed unread. | load |
| progress-zh | Chinese positive | 現在進度到哪了？有沒有背景工作還在跑？ | load |
| stuck-zh | Chinese positive | 檢查一下你啟動的背景程序、subagent 或 watcher 有沒有卡住。 | load |
| done-zh | Chinese positive | 收工前確認你啟動的東西都結束了，沒有失敗卻沒讀的結果。 | load |
| explicit-en | Explicit-name control | Use the progress-check skill to report where we are and what is still running. | load |
| explicit-zh | Explicit-name control | 使用 progress-check 技能，回報目前進度與還在執行的背景工作。 | load |
| launch-en | Launch-only | Run the heartbeat worker in the background and carry on. | record |
| launch-zh | Launch-only | 把 heartbeat worker 放到背景執行，然後繼續。 | record |
| tests-en | Launch-only | Run the tests in the background. | record |
| kill-en | English negative | Kill every node process on this machine. | skip |
| kill-zh | Chinese negative | 把這台機器上所有 node 程序全部砍掉。 | skip |
| concept-en | English negative | Explain how subagents work in this tool. Do not run anything. | skip |
| concept-zh | Chinese negative | 說明這個工具的 subagent 是怎麼運作的，不要執行任何東西。 | skip |
| restart-en | English negative | The test run failed; restart it. | skip |
| restart-zh | Chinese negative | 測試跑失敗了，重新跑一次。 | skip |
| log-en | English negative | Show the last ten commits on this branch. | skip |

The `done` cases test the completion self-check trigger.
The launch-only cases test that the description alone carries the recording convention.
The kill cases test that a process-termination request outside the session's own work does not attract the skill.

## Record and score

```text
Case ID / repetition:
Date:
Source revision / installed file hashes:
Host version / model / settings:
Catalog snapshot / installation evidence:
Prompt:
Expected: load | skip | record
Observed body loading: complete | partial | not-loaded | unobservable | not-run
Loading evidence: trace event or file-read location
Launch record fields present (record cases): identity | purpose | expected end | output
Additional fields observed (not scored for discovery): kind | first milestone | stdin | launch time
Discovery result: pass | fail | unobservable | not-run
Task behaviour: pass | fail | not-evaluated
Behaviour evidence / reason:
Process state before / after:
Premature stop: yes | no | unobservable
Transcript location:
```

`load` passes on observable complete body loading.
`skip` passes when a complete trace shows no body-load event.
`record` passes when the trace shows no body-load event and the launch carries identity, purpose, expected end, and output,
the four fields the description names;
the additional fields are reported separately and do not affect the discovery score.
A launch that loads the body is scored as an over-trigger, separately from whether the fields appeared.
Report positive, explicit-name, launch-only, and negative counts separately with denominators.
For loaded positives, judge the first response against the [shared checks](README.md#shared-checks):
a fresh probe before any status claim, a coverage statement, and no stop before approval.
Any stop before approval is a behaviour failure regardless of the discovery score.
