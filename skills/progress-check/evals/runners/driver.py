"""Drive a multi-turn Claude Code print-mode session over stream-json for evaluation trials.

Usage: driver.py <cwd> <model> <log-path> <profile> [<turn text> ...]

The profile is the isolated CLAUDE_CONFIG_DIR, falling back to $TRIAL_PROFILE.
There is no default: a trial that silently ran against the user's own profile would
carry their hooks, plugins, and skills into the measurement.
"""

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import refuse_git_tree, required_path  # noqa: E402


def now():
    return datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3] + "Z"


def resolve_profile(argument=None):
    """The isolated Claude Code profile; required, credentialed, outside any checkout."""
    profile = refuse_git_tree(
        "the trial profile",
        required_path("the trial profile", argument, "TRIAL_PROFILE"),
    )
    if not (profile / ".credentials.json").exists():
        raise SystemExit(f"the trial profile has no .credentials.json: {profile}")
    return profile


class Session:
    """One Claude Code print-mode process; a reader thread logs every event as it arrives.

    Claude Code runs idle turns of its own when a background task completes, so a
    ``result`` event is matched to a user turn by position: the replayed user message
    marks where the turn was accepted, and a turn already in progress at that point is
    skipped before the caller's result is taken.
    """

    def __init__(self, cwd, model, log_path, config_dir, extra=()):
        self.cwd = Path(cwd)
        self.model = model
        self.log = Path(log_path).open("a", encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        self.config_dir = Path(config_dir)
        env["CLAUDE_CONFIG_DIR"] = str(self.config_dir)
        cmd = [
            "claude",
            "-p",
            "--model",
            model,
            "--verbose",
            "--replay-user-messages",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--permission-mode",
            "bypassPermissions",
            *extra,
        ]
        self.process = subprocess.Popen(
            cmd,
            cwd=str(self.cwd),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=open(str(log_path) + ".stderr", "ab"),
            text=True,
            bufsize=1,
        )
        self.session_id = None
        self.turn = 0
        self.events = []
        self.lock = threading.Condition()
        self.closed = False
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        for line in self.process.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            event["_time"] = now()
            event["_turn"] = self.turn
            with self.lock:
                self.log.write(json.dumps(event, ensure_ascii=False) + "\n")
                self.log.flush()
                self.events.append(event)
                self.session_id = event.get("session_id", self.session_id)
                self.lock.notify_all()
            self.summarise(event)
        with self.lock:
            self.closed = True
            self.lock.notify_all()

    def note(self, text):
        line = {"type": "evaluator", "time": now(), "text": text}
        with self.lock:
            self.log.write(json.dumps(line, ensure_ascii=False) + "\n")
            self.log.flush()
        print(f"[{now()}] {text}", flush=True)

    @staticmethod
    def _is_replay(event, text):
        if event.get("type") != "user":
            return False
        content = event["message"].get("content")
        if isinstance(content, str):
            return content == text
        return any(
            b.get("type") == "text" and b.get("text") == text for b in content or []
        )

    def send(self, text, timeout=900):
        """Send one user turn and block until this turn's result event arrives."""
        self.turn += 1
        self.note(f"turn {self.turn} user: {text}")
        message = {
            "type": "user",
            "message": {"role": "user", "content": [{"type": "text", "text": text}]},
        }
        with self.lock:
            sent_at = len(self.events)
        self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + timeout

        def wait_for(predicate):
            with self.lock:
                while not predicate():
                    if self.closed or time.monotonic() > deadline:
                        return False
                    self.lock.wait(timeout=1.0)
                return True

        replay = [None]

        def replayed():
            for i in range(sent_at, len(self.events)):
                if self._is_replay(self.events[i], text):
                    replay[0] = i
                    return True
            return False

        if not wait_for(replayed):
            self.note("no replay of the user message; returning what arrived")
            return self.events[sent_at:]
        # Was another turn in progress when the message was accepted?
        last_result = max(
            [i for i in range(replay[0]) if self.events[i].get("type") == "result"],
            default=-1,
        )
        in_progress = any(
            self.events[i].get("type") == "assistant"
            for i in range(last_result + 1, replay[0])
        )
        # Claude Code merges a queued message into a turn already in progress, so the next
        # result after the replay covers this message either way.
        needed = 1
        if in_progress:
            self.note("another turn was in progress; this message was merged into it")

        def done():
            return (
                sum(
                    1
                    for i in range(replay[0] + 1, len(self.events))
                    if self.events[i].get("type") == "result"
                )
                >= needed
            )

        if not wait_for(done):
            self.note("turn timeout")
        with self.lock:
            results = [
                i
                for i in range(replay[0] + 1, len(self.events))
                if self.events[i].get("type") == "result"
            ]
            first = replay[0] + 1
            last = (
                results[needed - 1] + 1 if len(results) >= needed else len(self.events)
            )
            return self.events[first:last]

    def summarise(self, event):
        kind = event.get("type")
        if kind == "assistant":
            for block in event["message"].get("content", []):
                if block.get("type") == "tool_use":
                    inp = json.dumps(block.get("input"), ensure_ascii=False)
                    print(
                        f"  [{event['_time']}] tool_use {block['name']} {inp[:220]}",
                        flush=True,
                    )
                elif block.get("type") == "text":
                    print(
                        f"  [{event['_time']}] text: {block['text'][:300].replace(chr(10), ' | ')}",
                        flush=True,
                    )
        elif kind == "user":
            content = event["message"].get("content")
            blocks = content if isinstance(content, list) else []
            for block in blocks:
                if block.get("type") == "tool_result":
                    body = block.get("content")
                    text = (
                        body
                        if isinstance(body, str)
                        else json.dumps(body, ensure_ascii=False)
                    )
                    print(
                        f"  [{event['_time']}] tool_result {text[:160].replace(chr(10), ' | ')}",
                        flush=True,
                    )
                elif block.get("type") == "text":
                    print(
                        f"  [{event['_time']}] user-event: {block['text'][:200].replace(chr(10), ' | ')}",
                        flush=True,
                    )
            if isinstance(content, str):
                print(
                    f"  [{event['_time']}] user-event: {content[:200].replace(chr(10), ' | ')}",
                    flush=True,
                )
        elif kind == "result":
            print(
                f"  [{event['_time']}] result turns={event.get('num_turns')} cost={event.get('total_cost_usd')} stop={event.get('stop_reason')}",
                flush=True,
            )
        elif kind == "system" and event.get("subtype") == "init":
            print(
                f"  init model={event.get('model')} tools={len(event.get('tools', []))} skills={event.get('skills') or event.get('slash_commands')}",
                flush=True,
            )

    def final_text(self, turn_events):
        texts = []
        for event in turn_events:
            if event.get("type") == "assistant":
                for block in event["message"].get("content", []):
                    if block.get("type") == "text":
                        texts.append(block["text"])
        return texts[-1] if texts else ""

    def close(self):
        try:
            self.process.stdin.close()
            self.process.wait(timeout=30)
        except Exception:
            self.process.kill()
        self.reader.join(timeout=5)
        self.log.close()


def snapshot(label, patterns, out_dir):
    """Record the process table rows matching the fixture, for liveness comparison."""
    ps = subprocess.run(
        ["ps", "-eo", "pid,ppid,pgid,lstart,etime,stat,args"],
        capture_output=True,
        text=True,
    ).stdout
    rows = [
        line
        for line in ps.splitlines()[1:]
        if any(p in line for p in patterns)
        and "driver.py" not in line
        and "grep" not in line
    ]
    path = Path(out_dir) / f"snapshot-{label}.txt"
    path.write_text(f"# {now()} {label}\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"[{now()}] snapshot {label}: {len(rows)} rows", flush=True)
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    cwd, model, log = sys.argv[1:4]
    session = Session(
        cwd, model, log, resolve_profile(sys.argv[4] if len(sys.argv) > 4 else None)
    )
    for turn in sys.argv[5:]:
        session.send(turn)
    session.close()
