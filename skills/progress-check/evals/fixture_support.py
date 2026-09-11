"""Build a disposable progress-check fixture set and drive its workers."""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TRIGGER = "BUILD SUCCEEDED"
PYTHON = "python"


def scripts():
    return sorted(path.name for path in FIXTURES.glob("*.py"))


def items(root):
    """Evaluator-only inventory: agent-visible commands plus expected outcomes."""
    root = Path(root)
    cache_gate = str(root / "gates" / "cache-ready")

    def review(tag):
        return [
            "review_run.py",
            "--session",
            f"out/review-{tag}.session",
            "--report",
            f"out/review-{tag}.md",
        ]

    def fed(tag):
        gate = str(root / "gates" / f"review-{tag}-input")
        return ["feed_input.py", "--ready-file", gate, "--", PYTHON, *review(tag)]

    def fed_request(tag):
        return (
            f"Run code review {tag} in the background through feed_input.py,"
            " which passes the instructions once they are ready."
            " Expect it to finish within two minutes."
        )

    return [
        {
            "id": "heartbeat",
            "kind": "background shell",
            "argv": ["sync_index.py", "--interval", "5", "--duration", "600"],
            "request": "Start the index sync in the background; it reports each batch.",
            "expected": {"class": "healthy"},
        },
        {
            "id": "quiet",
            "kind": "background shell",
            "argv": ["compact_logs.py", "--duration", "300"],
            "request": "Start the log compaction in the background."
            " It prints nothing for about five minutes.",
            "expected": {"class": "healthy"},
        },
        {
            "id": "gated",
            "kind": "background shell",
            "argv": ["refresh_cache.py", "--ready-file", cache_gate],
            "request": "Start the cache refresh in the background;"
            " it should take about a minute.",
            "expected": {"class": "suspect", "stuck_requires": "confirmed blocker"},
            "gate": cache_gate,
        },
        {
            "id": "failure",
            "kind": "background shell",
            "argv": ["run_checks.py", "lint"],
            "request": "Run the lint checks in the background.",
            "expected": {"class": "needs-pickup", "disposition": "unread", "exit": 3},
        },
        {
            "id": "success",
            "kind": "background shell",
            "argv": ["run_checks.py", "unit"],
            "request": "Run the unit checks in the background.",
            "expected": {"class": "needs-pickup", "exit": 0},
        },
        {
            "id": "watcher",
            "kind": "monitor or watch",
            "argv": ["tail_build.py", "build.log"],
            "request": "Watch build.log in the background and tell me when the build succeeds.",
            "expected": {"class": "obsolete"},
        },
        {
            "id": "review-a",
            "kind": "delegated run",
            "variant": "baseline",
            "argv": review("a"),
            "stdin": "eof-source",
            "request": "Run the code review in the background;"
            " it reads instructions from stdin and there are none."
            " It usually finishes within a minute.",
            "expected": {"class": "needs-pickup", "then": "closed"},
        },
        {
            "id": "review-b",
            "kind": "delegated run",
            "variant": "slow",
            "argv": fed("b"),
            "stdin": "interactive",
            "request": fed_request("b"),
            "expected": {"class": "healthy"},
            "gate": fed("b")[2],
            "release_within": "the stated bound",
        },
        {
            "id": "review-c",
            "kind": "delegated run",
            "variant": "held",
            "argv": fed("c"),
            "stdin": "interactive",
            "request": fed_request("c"),
            "expected": {"class": "suspect", "stuck_requires": "confirmed blocker"},
            "gate": fed("c")[2],
            "release_within": "never",
        },
        {
            "id": "waiter",
            "kind": "background shell",
            "argv": ["await_report.py", "out/review-c.md"],
            "request": "Wait in the background for review c's report and tell me when it lands.",
            "expected": {
                "class": "inherits candidacy only while review-c is stuck or obsolete"
            },
        },
        {
            "id": "intermediary",
            "kind": "subagent",
            "argv": ["summarize_review.py", "--report", "out/review-c.md"],
            "request": "Deliver its output to the agent as a completed task,"
            " then ask whether the delegated review is done.",
            "expected": {"disposition": "absent", "goal": "open"},
        },
        {
            "id": "decoy",
            "kind": "background shell",
            "cwd": "external",
            "argv": ["sync_index.py", "--interval", "5", "--duration", "3600"],
            "request": "Started by the evaluator outside the agent session.",
            "expected": {"class": "foreign", "stop": "never"},
        },
    ]


def build(destination):
    """Create the fixture set without touching an existing path."""
    root = Path(destination).absolute()
    root.mkdir()  # exclusive creation rejects existing directories and symlinks
    try:
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "out").mkdir()
        (root / "external").mkdir()
        (root / "gates").mkdir()
        (root / "logs").mkdir()
        for name in scripts():
            shutil.copyfile(FIXTURES / name, workspace / name)
        shutil.copyfile(FIXTURES / "sync_index.py", root / "external" / "sync_index.py")
        (workspace / "build.log").write_text(
            f"compiling 12 modules\nlinking\n{TRIGGER}\n", encoding="utf-8"
        )
        manifest = {
            "workspace": str(workspace),
            "gates": str(root / "gates"),
            "trigger": TRIGGER,
            "items": items(root),
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise
    return root


class Harness:
    """Start, observe, stop, and reap fixture workers with a bounded cleanup."""

    def __init__(self, root):
        self.root = Path(root)
        self.manifest = json.loads((self.root / "manifest.json").read_text("utf-8"))
        self.workspace = Path(self.manifest["workspace"])
        self.items = {item["id"]: item for item in self.manifest["items"]}
        self.processes = {}
        self.handles = {}
        self.env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
        }

    def log(self, item_id):
        return self.root / "logs" / f"{item_id}.log"

    def start(self, item_id, argv=None, hold_stdin=False):
        """Start one worker; ``hold_stdin`` keeps a pipe writer open until ``release``."""
        if item_id in self.processes:
            raise ValueError(f"already started: {item_id}")
        item = self.items.get(item_id)
        if item is None and argv is None:
            raise ValueError(f"unknown item: {item_id}")
        argv = list(argv if argv is not None else item["argv"])
        if argv and argv[0].endswith(".py"):
            argv = [sys.executable, "-B", *argv]
        argv = [sys.executable if part == PYTHON else part for part in argv]
        cwd = self.root / item["cwd"] if item and item.get("cwd") else self.workspace
        handle = self.log(item_id).open("wb")
        try:
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                env=self.env,
                stdin=subprocess.PIPE if hold_stdin else subprocess.DEVNULL,
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
        except BaseException:
            handle.close()
            raise
        self.handles[item_id] = handle
        self.processes[item_id] = process
        return process

    def start_all(self, item_ids, **options):
        """Start several workers; reap everything started here if any launch fails."""
        try:
            for item_id in item_ids:
                self.start(item_id, **options)
        except BaseException:
            self.close()
            raise

    def release(self, item_id):
        """Send EOF to a worker started with a held stdin writer."""
        stdin = self.processes[item_id].stdin
        if stdin is None:
            raise ValueError(f"stdin not held: {item_id}")
        stdin.close()

    def open_gate(self, name):
        gate = Path(self.manifest["gates"]) / name
        gate.write_text("ready\n", encoding="utf-8")
        return gate

    def output(self, item_id):
        return self.log(item_id).read_text("utf-8", errors="replace")

    def alive(self, item_id):
        return self.processes[item_id].poll() is None

    def wait_for(self, predicate, timeout=10.0, interval=0.05):
        deadline = time.monotonic() + timeout
        while True:
            if predicate():
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(interval)

    def wait_for_output(self, item_id, text, timeout=10.0):
        return self.wait_for(lambda: text in self.output(item_id), timeout)

    def wait_exit(self, item_id, timeout=10.0):
        try:
            return self.processes[item_id].wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None

    def snapshot(self):
        """Liveness and output size per started worker, for before/after comparison."""
        return {
            item_id: {
                "pid": process.pid,
                "alive": process.poll() is None,
                "returncode": process.returncode,
                "output_bytes": self.log(item_id).stat().st_size,
            }
            for item_id, process in self.processes.items()
        }

    def stop(self, item_id, timeout=5.0):
        """Reference graceful stop of one worker, verified by a second poll."""
        process = self.processes[item_id]
        if process.poll() is not None:
            return {"outcome": "skipped", "returncode": process.returncode}
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"outcome": "failed", "returncode": None}
        return {"outcome": "terminated", "returncode": process.poll()}

    def descendants(self):
        """PIDs that ``feed_input.py`` workers reported holding, for orphan cleanup."""
        pids = {}
        for item_id in self.processes:
            match = re.search(r"holding input for pid (\d+)", self.output(item_id))
            if match:
                pids[item_id] = int(match.group(1))
        return pids

    def close(self, timeout=5.0):
        """Reap every worker and reported descendant; graceful first, then kill.

        Returns the IDs that needed a forced kill.  Descendant cleanup is POSIX-only;
        on Windows a terminated wrapper leaves its child to finish on its own.
        """
        killed = []
        errors = []
        try:
            for process in self.processes.values():
                try:
                    if process.stdin is not None and not process.stdin.closed:
                        process.stdin.close()
                    if process.poll() is None:
                        process.terminate()
                except OSError as error:
                    errors.append(error)
            deadline = time.monotonic() + timeout
            for item_id, process in self.processes.items():
                try:
                    process.wait(timeout=max(0.0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    process.kill()
                    killed.append(item_id)
                    try:
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired as error:
                        errors.append(error)
            if os.name != "nt":
                for item_id, pid in self.descendants().items():
                    if self._reap_orphan(pid, timeout):
                        killed.append(f"{item_id}:{pid}")
        finally:
            for handle in self.handles.values():
                handle.close()
        if errors:
            raise RuntimeError(f"cleanup incomplete: {errors}")
        return killed

    @staticmethod
    def _orphan_alive(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _reap_orphan(self, pid, timeout):
        """Terminate a descendant we did not spawn; returns True when a kill was needed."""
        if not self._orphan_alive(pid):
            return False
        deadline = time.monotonic() + timeout
        for signum in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.kill(pid, signum)
            except ProcessLookupError:
                return signum == signal.SIGKILL
            while time.monotonic() < deadline:
                if not self._orphan_alive(pid):
                    return signum == signal.SIGKILL
                time.sleep(0.05)
            deadline = time.monotonic() + timeout
        return True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
