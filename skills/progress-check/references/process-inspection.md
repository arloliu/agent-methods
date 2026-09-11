# Process inspection

Read-only operating-system recipes for when the host exposes no probe for an item,
and the identity checks required before an `os` stop.
Every recipe is a hint; choose the command that fits your shell and permissions.
Findings from the process table are `foreign` unless matched to a launch record.
"Session shell" means the shell your tool calls run in (`$$` in POSIX shells, `$PID` in PowerShell).

## Ownership

Match a process to a launch record by PID and start time; ancestry alone is unreliable.

Linux:

```sh
ps -o pid,ppid,pgid,sid,lstart,etime,stat,args --ppid $$
pgrep -P $$
cat /proc/<pid>/stat        # field 4 ppid, 5 pgrp, 6 session, 22 start time in clock ticks
```

macOS (BSD `ps`, no `/proc`, `--ppid` unsupported):

```sh
ps -axo pid,ppid,pgid,sess,lstart,etime,stat,command | awk '$2 == <parent>'
pgrep -P $$
```

Windows (PowerShell; `wmic` is removed on current releases):

```powershell
Get-CimInstance Win32_Process | Where-Object ParentProcessId -eq $PID |
  Select-Object ProcessId, ParentProcessId, CreationDate, CommandLine
Get-Process -Id <pid> | Select-Object Id, StartTime, CPU, Path
```

Pitfalls:

- Orphans are reparented to PID 1, `launchd`, or a subreaper when their parent exits,
  so a parent chain breaks after a wrapper returns;
  process group and session IDs survive longer.
- `setsid` starts a new session; `nohup` only ignores hangup and `disown` only removes job control.
  Inspect the actual process group and session IDs rather than inferring them from the launch wrapper;
  find detached processes by command line, working directory, and start time.
- Windows never reparents; a parent ID may name a dead or reused PID, so compare creation dates.
- PIDs are reused on every platform; always pair a PID with its start time.

## Progress versus a hung process

Take two samples a few seconds apart and compare; a single sample shows nothing.

Linux:

```sh
awk '{print $14 + $15}' /proc/<pid>/stat     # CPU ticks; repeat after a pause
ps -o stat,wchan:32 -p <pid>                  # state and kernel wait channel
ls /proc/<pid>/fd | wc -l                     # open descriptors
ss -tnp | grep "pid=<pid>,"                   # sockets
stat -c '%s %Y' <output-file>                 # size and modification time
```

macOS:

```sh
ps -o stat,time,wchan -p <pid>; sleep 5; ps -o time -p <pid>
lsof -p <pid> | wc -l
sample <pid> 5                                # user-level stacks, no root needed
```

Windows:

```powershell
$p = Get-Process -Id <pid>; $c1 = $p.CPU; Start-Sleep 5; $p.Refresh(); $p.CPU - $c1
(Get-Item <output-file>).Length; (Get-Item <output-file>).LastWriteTime
```

States on Linux and macOS: `R` running, `S` interruptible sleep, `D` uninterruptible I/O, `T` stopped, `Z` zombie.

Startup-blocked signature, common for delegated CLIs launched with an inherited open stdin:
descriptor 0 is a pipe or socket, the wait channel is a read or futex wait,
no output after a banner, no session or output file created, and zero CPU delta across samples.
Each of these is also consistent with a healthy wait, so together they support `suspect` with a named suspected blocker;
`stuck` needs the CLI's documented behaviour for that state,
thread-level evidence, or a controlled intervention on that process.

Pitfalls:

- A healthy wait on network, a lock, stdin, or a child shows zero CPU and state `S`, the same as a hang;
  combine CPU delta, output growth, child count changes, socket state, and the process's own log.
- Rising CPU with no output can be a busy loop.
- A process stuck in `D` cannot be interrupted by any signal.
- Windows `Responding` reflects only a window message pump; it is always true for console programs.
- Intervals under a few seconds miss slow but live workers.

## Zombies and orphans

`Z` or `defunct` means the process already exited; only its exit status remains until the parent reaps it.
Signals do nothing; reporting it as hung is wrong.
Orphans keep running normally under their new parent.
Windows has no zombies; a process object lingers only while a handle is open.

## Graceful stop and verification

Confirm PID and start time against the launch record immediately before signalling,
and confirm the target's process group is not the session shell's group by querying it.

Linux and macOS:

```sh
kill -TERM <pid>
sleep 5; kill -0 <pid> 2>/dev/null && echo alive
kill -TERM -- -<pgid>            # whole group: every member session-owned and approved, group not your own
```

`kill -0` sends nothing: exit 0 means the process exists and is signalable;
`No such process` means gone or invisible from this namespace;
`Operation not permitted` means it exists and is not yours.
Killing by name or pattern (`pkill -f`) matches other users' and sessions' processes; never use it.

Windows:

```powershell
taskkill /PID <pid>              # close request; console programs may ignore it
taskkill /PID <pid> /T           # include the child tree
Wait-Process -Id <pid> -Timeout 10
Get-Process -Id <pid> -ErrorAction SilentlyContinue   # $null means gone
```

`Stop-Process` is forceful; it has no graceful form.
`taskkill /F` is the forced form.
Forced termination is a new proposal.

A successful signal call, or disappearance from a sandboxed process table, does not establish termination;
re-probe, compare the start time if a PID reappears, and verify children separately.
A remaining check-then-signal race exists on every platform; record it as a limitation rather than a verified absence.

## Sandboxes

| Symptom | Meaning |
| --- | --- |
| `kill -0` exits 0 | exists, signalable |
| `No such process` or `Get-Process` error | gone, or invisible from this PID namespace |
| `Operation not permitted` or `Access is denied` | exists; blocked by ownership or policy |
| listed by `ps` but the signal fails | policy block; report to the user instead of retrying |

Inside a PID namespace, `not found` is ambiguous; `/proc/1/comm` not naming an init system suggests you are inside one.
Sandboxed shells often lack `pstree`, `lsof`, and `ss`; fall back to `/proc` reads or plain `ps`.
