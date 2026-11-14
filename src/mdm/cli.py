"""Bounded operator commands. stdout contains structured results, never secrets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mdm.service import Service
from mdm.telemetry import correlated_operation


@correlated_operation("cli.command")
def main(argv=None):
    parser = argparse.ArgumentParser(prog="mdm")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("migrate", "check", "quality"):
        sub.add_parser(name)
    for name in ("demo", "snapshot"):
        command = sub.add_parser(name)
        command.add_argument("--output", type=Path)
    command = sub.add_parser("consume")
    command.add_argument("--consumer", default="reporting")
    command.add_argument("--limit", type=int, default=10000)
    command = sub.add_parser("run")
    command.add_argument("--input", type=Path, required=True, help="JSON object with all three ERP keys; null means unavailable")
    command.add_argument("--run-key", required=True)
    command.add_argument("--mode", choices=["deterministic", "hybrid"], default="hybrid")
    command = sub.add_parser("benchmark")
    command.add_argument("--size", type=int, default=1000)
    command.add_argument("--output", type=Path)
    command.add_argument("--database", action="store_true", help="also ingest and consolidate into an EMPTY dedicated database")
    args = parser.parse_args(argv)
    try:
        if args.command == "benchmark":
            from mdm.benchmark import benchmark
            result = benchmark(args.size, database=args.database)
        else:
            service = Service()
            if args.command == "migrate":
                result = service.db.migrate()
            elif args.command == "demo":
                from mdm.demo import demonstrate
                result = demonstrate(service)
            elif args.command == "run":
                from mdm.domain import SourceRecord
                from mdm.pipeline import run
                manifest = json.loads(args.input.read_text())
                sources = {key: None if rows is None else [SourceRecord.model_validate(row) for row in rows] for key, rows in manifest.items()}
                result = run(service, sources, run_key=args.run_key, mode=args.mode)
            elif args.command == "consume":
                result = service.consume(args.consumer, limit=args.limit)
            else:
                result = getattr(service, args.command)()
        text = json.dumps(result, indent=2, default=str, sort_keys=True)
        if getattr(args, "output", None):
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n")
            print(json.dumps({"output": str(args.output), "command": args.command}))
        else:
            print(text)
        if args.command == "check" and not result["passed"]:
            raise SystemExit(1)
    except (ValueError, PermissionError, KeyError) as exc:
        # Validation messages never include connection strings or raw SQL.
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
