"""Command-line entry point for the self-learning agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent import __version__
from agent.config import AgentConfig, load_config
from agent.logging import SessionLogger, log_session_started
from agent.memory import MemoryService
from agent.repl import run_repl
from agent.session import create_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent",
        description="CLI-first self-learning AI agent.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--config",
        default="agent.yaml",
        help="Path to the workspace config file.",
    )

    subcommands = parser.add_subparsers(dest="command")

    run_parser = subcommands.add_parser("run", help="Run a one-shot task.")
    run_parser.add_argument("task", help="Task to run.")

    subcommands.add_parser("chat", help="Start the interactive CLI session.")

    memory_parser = subcommands.add_parser("memory", help="Inspect local memory.")
    memory_subcommands = memory_parser.add_subparsers(dest="memory_command")
    memory_subcommands.add_parser("list", help="List stored memories.")
    memory_search = memory_subcommands.add_parser("search", help="Search memories.")
    memory_search.add_argument("query", help="Search query.")
    memory_show = memory_subcommands.add_parser("show", help="Show a memory record.")
    memory_show.add_argument("id", help="Memory ID.")
    memory_delete = memory_subcommands.add_parser("delete", help="Delete a memory record.")
    memory_delete.add_argument("id", help="Memory ID.")

    feedback_parser = subcommands.add_parser("feedback", help="Apply feedback to recent memories.")
    feedback_subcommands = feedback_parser.add_subparsers(dest="feedback_command")
    feedback_good = feedback_subcommands.add_parser("good", help="Mark recent memories as useful.")
    feedback_good.add_argument("reason", help="Reason for the feedback.")
    feedback_bad = feedback_subcommands.add_parser("bad", help="Mark recent memories as not useful.")
    feedback_bad.add_argument("reason", help="Reason for the feedback.")

    config_parser = subcommands.add_parser("config", help="Inspect configuration.")
    config_subcommands = config_parser.add_subparsers(dest="config_command")
    config_subcommands.add_parser("show", help="Show effective configuration.")
    config_subcommands.add_parser("edit", help="Print the config path to edit.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)

    if args.command is None:
        return start_repl(config)

    if args.command == "chat":
        return start_repl(config)

    if args.command == "run":
        session = create_session(mode="one-shot")
        logger = SessionLogger(session.log_path)
        log_session_started(logger, session)
        session.append_turn("user", args.task)
        logger.write(
            "task_received",
            {
                "session_id": session.id,
                "task": args.task,
                "loop_state": session.loop_state,
            },
        )
        print(f"Task received. Agent execution starts in Phase 4: {args.task}")
        print(f"Log: {session.log_path}")
        return 0

    if args.command == "memory":
        return handle_memory(args)

    if args.command == "feedback":
        return handle_feedback(args)

    if args.command == "config":
        return handle_config(args, config, Path(args.config))

    parser.print_help()
    return 0


def start_repl(config: AgentConfig) -> int:
    return run_repl(config)


def handle_memory(args: argparse.Namespace) -> int:
    memory_service = MemoryService()
    if args.memory_command is None:
        print("Memory commands: list, search, show, delete")
        return 0

    if args.memory_command == "list":
        records = memory_service.list()
        if not records:
            print("No memories stored.")
            return 0
        for record in records:
            print(f"{record.id} {record.summary}")
        return 0

    if args.memory_command == "search":
        records = memory_service.search(args.query)
        if not records:
            print("No memories found.")
            return 0
        for record in records:
            print(f"{record.id} {record.summary}")
        return 0

    if args.memory_command == "show":
        record = memory_service.get(args.id)
        if record is None:
            print(f"Memory not found: {args.id}")
            return 1
        print(f"id: {record.id}")
        print(f"type: {record.type}")
        print(f"scope: {record.scope}")
        print(f"summary: {record.summary}")
        print(f"content: {record.content}")
        print(f"source_task_id: {record.source_task_id}")
        print(f"confidence: {record.confidence}")
        print(f"reliability_score: {record.reliability_score}")
        print(f"use_count: {record.use_count}")
        print(f"tags: {', '.join(record.tags) if record.tags else ''}")
        return 0

    if args.memory_command == "delete":
        deleted = memory_service.delete(args.id)
        if not deleted:
            print(f"Memory not found: {args.id}")
            return 1
        print(f"Deleted memory: {args.id}")
        return 0

    print(f"Unknown memory command: {args.memory_command}")
    return 1


def handle_feedback(args: argparse.Namespace) -> int:
    memory_service = MemoryService()
    if args.feedback_command not in {"good", "bad"}:
        print('Feedback commands: good "reason", bad "reason"')
        return 0

    recent = memory_service.list(limit=5)
    if not recent:
        print("No recent memories available for feedback.")
        return 1

    updated = memory_service.apply_feedback(
        [record.id for record in recent],
        positive=args.feedback_command == "good",
    )
    print(
        f"Applied {args.feedback_command} feedback to {len(updated)} memory item(s): {args.reason}"
    )
    return 0


def handle_config(args: argparse.Namespace, config: AgentConfig, config_path: Path) -> int:
    if args.config_command == "show":
        print("permissions:")
        print(f"  shell.default: {config.permissions.shell.default}")
        print(f"  shell.read_only: {config.permissions.shell.read_only}")
        print(f"  filesystem.read: {config.permissions.filesystem.read}")
        print(f"  filesystem.write: {config.permissions.filesystem.write}")
        print(f"  filesystem.delete: {config.permissions.filesystem.delete}")
        print(f"  network.default: {config.permissions.network.default}")
        print(f"  high_privilege: {config.permissions.high_privilege}")
        print(f"  credential_access: {config.permissions.credential_access}")
        print("memory:")
        print(f"  auto_write: {config.memory.auto_write}")
        print(f"  require_review_for_user_preferences: {config.memory.require_review_for_user_preferences}")
        print(f"  block_secrets: {config.memory.block_secrets}")
        print("security:")
        print(f"  redact_logs: {config.security.redact_logs}")
        print(f"  redact_memory: {config.security.redact_memory}")
        print(f"  redact_model_calls: {config.security.redact_model_calls}")
        print(f"  redact_network: {config.security.redact_network}")
        print(f"  unknown_risk: {config.security.unknown_risk}")
        return 0

    if args.config_command == "edit":
        print(config_path)
        return 0

    print("Config commands: show, edit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
