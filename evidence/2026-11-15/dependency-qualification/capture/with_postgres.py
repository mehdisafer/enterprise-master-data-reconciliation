#!/usr/bin/env python3
"""Run a bounded command beside the isolated P02 PostgreSQL instance.

The execution host isolates loopback networking per exec invocation. Start the
database and its client command in this same process namespace. Secrets remain
in the local mode-0600 environment file and are never printed.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("provide a command after --")

    env = os.environ.copy()
    env.update(json.loads((ROOT / "secrets/environment.json").read_text()))
    env["PATH"] = env["P02_PG_BIN"] + ":" + env["PATH"]
    pg_ctl = str(Path(env["P02_PG_BIN"]) / "pg_ctl")
    data = str(ROOT / "pgdata")
    child: subprocess.Popen | None = None
    started = False

    def interrupted(signum, _frame):
        if child is not None and child.poll() is None:
            child.terminate()
        raise KeyboardInterrupt(f"signal {signum}")

    with (ROOT / "validation.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        try:
            startup = subprocess.run(
                [pg_ctl, "-D", data, "-l", str(ROOT / "postgres.log"), "-w", "-t", "20", "start"],
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=25,
            )
            if startup.returncode:
                print(startup.stdout + startup.stderr, file=sys.stderr)
                return startup.returncode
            started = True
            print("Isolated PostgreSQL started (17.12, TCP 127.0.0.1:55432).", flush=True)
            child = subprocess.Popen(command, env=env)
            return child.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            if child is not None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            print("Validation timeout; isolated PostgreSQL will be stopped.", file=sys.stderr)
            return 124
        except KeyboardInterrupt:
            if child is not None:
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            return 130
        finally:
            if started:
                stopped = subprocess.run(
                    [pg_ctl, "-D", data, "-m", "fast", "-w", "-t", "20", "stop"],
                    env=env,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=25,
                )
                if stopped.returncode:
                    print(stopped.stdout + stopped.stderr, file=sys.stderr)
                else:
                    print("Isolated PostgreSQL stopped cleanly.", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
