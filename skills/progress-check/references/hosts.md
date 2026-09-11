# Host mechanisms

Known mechanisms per host as of 2026-09-11, from vendor documentation, source, and one live session per marked row.
The live tool list of your session is authoritative; a mechanism listed here may be renamed, gated, or absent.
"model" means callable by the agent; "user" means a command or view only the user can invoke.
Record `supported`, `user-only`, or `unavailable` per capability and kind from what you can actually call.

## Capability table

| Capability | Claude Code | Codex CLI | OpenCode | Antigravity CLI (agy) | Gemini CLI |
| --- | --- | --- | --- | --- | --- |
| Launch background shell | model: shell tool with a background option; returns task ID and output file | model: PTY exec tool; returns a session ID | none in core; agent must detach the process itself and keep a log file | model: run command tool with async and persistent options | model: shell tool with a background flag; returns PIDs |
| Enumerate shells | no model list; launch records and a task directory listing; user `/tasks` | no model list; user `/ps` | none; process table only | model: task management list; user `/tasks` with start times | model: list background processes; user `/shells` |
| Probe shell | model: non-blocking task output call; output-file metadata | model: empty stdin write polls with a mandatory wait of at least 5 s | log file plus process table | model: task status | model: read background output by PID |
| Stop shell | model: task stop | **user-only**: `/stop` stops every terminal; sandbox blocks signals | `os`: signal by PID, no sandbox | model: task kill | user-only: `/shells` |
| Launch subagent | model: agent tool; returns agent ID | model: spawn agent tool | model: task tool; background mode gated by an environment flag | model: invoke subagent tool | blocking call; nothing to inventory |
| Enumerate agents | model: list agents | model: list agents (newer tool set; default availability unverified) | none; local HTTP API when the server port is known | model: manage subagents list; user `/agents` | n/a |
| Probe or stop agent | model: task output and task stop | model: wait, close, interrupt | HTTP session read and abort when the port is known | model: send message (not read-only) and manage subagents kill | n/a |
| Scheduled job or monitor | model: cron list and delete; monitor tool; artifact watch status and unwatch | none in CLI | none | model: schedule tool | none |
| Activity timestamp | none first-class; output-file modification time; agent transcript metadata | none; recent output lines only | session update time via API | user `/tasks` start time; tool output unverified | history start and end times; exposure unverified |
| Exit and resume | background shells and monitors are not restored; scheduled jobs restored within 7 days | shutdown terminates terminals; an interrupted turn does not; resume restores transcript only | in-memory registry; restart interrupts work; orphans reported | headless exit leaves daemons running; interactive behaviour undocumented | history in memory; undocumented |
| Sandbox effect on `ps` and signals | depends on configuration | PID namespace and seatbelt: cannot see or signal host processes or other terminals | none | Linux namespaces hide host processes; seatbelt on macOS | container modes isolate PIDs |
| Anti-polling guidance | none | polling is the designed probe | task prompt forbids polling background tasks; consume notifications | anti-polling reminders removed in 1.1.13 | none |

## Notes per host

### Claude Code

- An agent task's output handle is a symlink to its transcript; read metadata only (existence, size, modification time).
  A blocking output call on an agent task returns the transcript and spends the whole timeout; use a non-blocking call.
- Completed task rows leave the user's task view after about 30 seconds;
  the completion notification is the durable signal.
- The task directory under the session's scratch area lists candidate handles but over-includes persisted tool outputs;
  it is an enumeration aid, not a registry.

### Codex CLI

- Keep every PTY session ID from the exec tool's result; there is no way to recover a forgotten one.
- An empty stdin write is the probe; its minimum wait counts against the observation budget.
- `/stop` is global.
  When proposing it as a user action, state that it stops every terminal
  and that your list of running terminals may be incomplete;
  direct the user to `/ps` first.
- Sandboxed shells cannot see the host process table; treat `not found` as `unverified`.
- The CLI reads additional prompt text from stdin until EOF when stdin is not a terminal;
  launch it with an empty EOF source when delegating from another agent.

### OpenCode

- No background shell exists in core; a detached process is only as observable as the log file you gave it.
- Background subagents deliver completion as an injected message; the task prompt forbids polling them.
- The local HTTP API (session children, session status, abort) is reachable only when the server port is known,
  for example under `opencode serve --port`.
- The job registry is in memory; a restart interrupts live work.

### Antigravity CLI (agy)

- Task and subagent management tools give list, status, and kill from the model side.
- Sending a message to a subagent is an intervention, not a read-only probe.
- Killing a parent subagent can stop child threads and the background tasks they own; bound the scope before proposing.
- Skill installation may use a flat `<name>.md` file; this SKILL.md is self-sufficient without its references.

### Gemini CLI

- Background shells can be listed and read from the model side; stopping is user-only through `/shells`.
- Subagent calls block, so there is nothing to inventory while they run.

## Sources

- Claude Code: interactive mode, sub-agents, tools reference, scheduled tasks, workflows, sessions, and hooks documentation;
  a live session on 2026-09-11.
- Codex CLI: config reference, slash commands, subagents, and sandboxing documentation;
  `codex-rs` tool specifications;
  issues on background terminals.
- OpenCode: tools, agents, server, and skills documentation;
  `opencode` tool sources;
  release notes and issues on background subagents.
- Antigravity CLI: hooks, subagents, CLI commands, sandbox, plugins documentation and the CLI changelog.
- Gemini CLI: shell tool, subagents, session management, sandbox documentation and the background process tools source.
