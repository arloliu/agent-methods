# Classification examples

Worked examples for the class table in [SKILL.md](../SKILL.md#class); the rules live there.
Each example names the evidence that decides the outcome;
without that evidence, reapply the ordered conditions with what remains rather than keeping the class.

## Precedence in practice

| Situation | Evidence | Class |
| --- | --- | --- |
| A test runner started by this session exited 3 ten minutes ago; nobody read its output | launch record; host status `completed(3)`; no read in the conversation | `needs-pickup`, disposition `unread` |
| The same runner, output read, failure recorded, fix not yet made | disposition recorded | `closed`; goal stays open with a failed required outcome |
| A watcher tails a build log for "BUILD SUCCEEDED"; the build finished and the line already appeared | launch record; delivered notification with the line | `obsolete` |
| A process found in the process table with a similar command line and no launch record | no spawn evidence | `foreign`, ownership `unverified` |
| A subagent whose host status is `running`; its transcript metadata cannot be read in this sandbox | capability `unavailable` for probe | `unobservable` |
| A background shell with a 2-minute expectation, silent for 20 minutes, no CPU delta across two samples, reading a pipe whose writer supplies neither data nor EOF | breached expectation; blocker confirmed by the writer's state and the process's documented waiting behaviour | `stuck` |
| The same shell with the same observations but no evidence about the writer | breached expectation; suspected blocker named | `suspect` |
| The same shell, silent for 20 minutes, but the process table is not readable | breached expectation; no diagnosis | `suspect` |
| A dev server started for manual testing, running for an hour | no natural end | `healthy`, flag `long-lived` |
| A remote task returned as a handle, no status capability | capability `unavailable` | `unobservable` |

## Delegated runs

| Situation | Evidence | Outcome |
| --- | --- | --- |
| A delegated CLI launched 30 seconds ago printed its banner; no session file yet; no baseline this session | 60-second heuristic bound not reached; banner is not the milestone | `healthy`, startup unconfirmed |
| The same CLI three minutes later: descriptor 0 is an inherited open pipe, zero CPU delta across two samples, no session file; its documentation says it reads stdin until EOF when stdin is not a terminal | breached bound; blocker confirmed by documented behaviour for the observed state | `stuck` |
| The same observations without the documented behaviour | breached bound; suspected blocker named (open stdin, zero CPU) | `suspect` |
| The same observations with an unknown launch time | breach `unverified` | `suspect` at most |
| The same command ran earlier this session and reached its first output in 45 seconds | baseline recorded with comparability limits (same model, input size, host), separate from the chosen bound | bound taken from the baseline, not the heuristic |
| Session file present, first substantive output two minutes ago, nothing since; wrapper timeout 20 minutes | startup confirmed; stated budget not exceeded | `healthy`; still blocks a completion claim |
| Startup confirmed, wrapper timeout exceeded, no output change, no CPU delta; sockets not readable in this sandbox | exceeded budget; no activity on observed signals; unobserved signal named | `suspect` |
| Startup deadline at 09:41; the remaining budget ends at 09:40 | deadline beyond budget | `startup pending, deadline 09:41` |

## Waiters and inheritance

| Situation | Evidence | Outcome |
| --- | --- | --- |
| A watcher tails the output file of a `stuck` delegated run and has no other recorded purpose | sole dependency in its launch record | candidate, "candidate because waiting solely on stuck <item>", with its own stop path and approval |
| The same watcher while the delegated run is `suspect` | target class below the threshold | not a candidate |
| A watcher that also restarts the run on failure | separate recovery purpose | assessed on its own |
| A monitor waiting on that watcher | second level | not a candidate |
| A watcher re-armed after the first one's expectation was breached | replacement waiter | recorded with its dependency; inherits no earlier proposal or approval |
| The watcher is `foreign` or flagged `long-lived` | exclusion applies | never a candidate |

## Result disposition

| Disposition | Meaning |
| --- | --- |
| `present` | the requested deliverable is accessible and matches the request in kind; correctness is a separate judgement |
| `partial` | some of the requested content exists |
| `absent` | the result is accessible and the deliverable is not in it, for example a report that says it is still waiting |
| `unverified` | the result or its referenced artifact is not accessible from this session |

## Stop path examples

| Host situation | Stop path |
| --- | --- |
| Task stop tool available for background shells | `native` |
| Only a user command that stops every terminal | `user-only`; list all running terminals and the enumeration caveat |
| No host mechanism; process detached by this session with a recorded PID and start time | `os`, graceful signal first |
| Native stop attempted and failed | report `failed`; no `os` escalation |
| Parent subagent with children of unknown count | displayed, marked not executable until the scope is bounded |
