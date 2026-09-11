# Classification examples

Companion to the class table in [SKILL.md](../SKILL.md#class).
Each example names the evidence that decides the class;
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

A delegated run is an external agent CLI or an asynchronous remote task.
Its output is sparse and its duration long, so the generic rules would misclassify it.

Startup unconfirmed:

- The first milestone is a marker that shows initialization passed,
  such as a session file plus the first substantive output line, or the first outbound request.
  A banner printed before the CLI reads its input is not a milestone; it precedes the most common startup blocker.
- The bound is a baseline from this session when the same command ran before, else the wrapper's documented startup time,
  else a 60-second heuristic threshold.
  The threshold prompts a review; it does not establish failure on its own.
- Missing or inaccessible marker evidence leaves startup `unconfirmed` or `unobservable`; it is not a missed milestone.
- Missed milestone plus confirmed blocker is `stuck`.
  Confirmation means the CLI's documented behaviour for that state, thread-level evidence,
  or a controlled intervention on that process.
  An open stdin, a wait state, a missing session file, and zero CPU across two samples are compatible observations;
  together they name a suspected blocker and support only `suspect`.
  Unknown launch time makes the breach `unverified`.
- A deadline beyond the remaining budget is reported as `startup pending, deadline <time>`.

Startup confirmed:

- Silence never yields `suspect`.
- `suspect` needs an exceeded stated budget (wrapper timeout or user budget) and no activity on any observed signal;
  name the signals that could not be observed.
- The item still blocks a completion claim while it runs.
- A stop discards partial work and spent tokens; the proposal says so.

Baseline record: run identity, marker observed, observed duration,
comparability limits (same model, same input size, same host),
and the bound you chose, kept separate.

## Waiters and inheritance

A waiter is an item whose sole recorded, current purpose is to wait on, poll, or watch one other item.
When that item is `stuck` or `obsolete`, the waiter may inherit candidacy, one level only,
labelled "candidate because waiting solely on <class> <item>".
Inheritance never overrides ownership, terminal-result precedence, observability, the `long-lived` exclusion, or approved scope.
It keeps its own lifecycle, ownership, and stop path;
each operation is approved separately, and both identities and the dependency are revalidated immediately before action.
A waiter with any separate purpose (recovery, reporting, a second target) is assessed on its own.
A replacement waiter armed after a breached expectation inherits nothing from an earlier proposal or approval.

## Result disposition

Compare accessible result content and referenced deliverables with the accepted request:

| Disposition | Meaning |
| --- | --- |
| `present` | the requested deliverable is accessible and matches the request in kind; correctness is a separate judgement |
| `partial` | some of the requested content exists |
| `absent` | the result is accessible and the deliverable is not in it, for example a report that says it is still waiting |
| `unverified` | the result or its referenced artifact is not accessible from this session |

A host status of `completed` says nothing about disposition.
An item reported complete without its deliverable has disposition `absent`;
its handling may close after assessment while the goal stays open.

## Stop path examples

| Host situation | Stop path |
| --- | --- |
| Task stop tool available for background shells | `native` |
| Only a user command that stops every terminal | `user-only`; list all running terminals and the enumeration caveat |
| No host mechanism; process detached by this session with a recorded PID and start time | `os`, graceful signal first |
| Native stop attempted and failed | report `failed`; no `os` escalation |
| Parent subagent with children of unknown count | displayed, marked not executable until the scope is bounded |
