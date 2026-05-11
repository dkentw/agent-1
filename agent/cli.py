"""Command-line entry point for the self-learning agent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agent import __version__
from agent.config import AgentConfig, load_config
from agent.llm import LLMConfigurationError, LLMError, ModelService
from agent.logging import SessionLogger, log_session_started
from agent.memory import MemoryService
from agent.models import ModelRegistry
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
    parser.add_argument(
        "--model",
        default=None,
        help="Override the active model for this process.",
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

    model_parser = subcommands.add_parser("model", help="Inspect available and active models.")
    model_subcommands = model_parser.add_subparsers(dest="model_command")
    model_subcommands.add_parser("show", help="Show the configured active model.")
    model_subcommands.add_parser("list", help="List available registered models.")
    model_test = model_subcommands.add_parser("test", help="Send a test prompt to the active provider.")
    model_test.add_argument("prompt", help="Prompt to send to the model.")

    config_parser = subcommands.add_parser("config", help="Inspect configuration.")
    config_subcommands = config_parser.add_subparsers(dest="config_command")
    config_subcommands.add_parser("show", help="Show effective configuration.")
    config_subcommands.add_parser("edit", help="Print the config path to edit.")

    eval_parser = subcommands.add_parser("eval", help="Run evaluation scenarios.")
    eval_parser.add_argument(
        "scenario_or_cmd",
        nargs="?",
        default=None,
        metavar="SCENARIO",
        help="Scenario ID or path to .json file, or: list, scenarios, compare.",
    )
    eval_parser.add_argument(
        "extra",
        nargs="*",
        metavar="ARGS",
        help="Extra args (for compare: <run-id-a> <run-id-b>).",
    )
    eval_parser.add_argument(
        "--no-memory",
        action="store_true",
        dest="no_memory",
        help="Disable memory retrieval for this run.",
    )
    eval_parser.add_argument(
        "--compare",
        action="store_true",
        dest="compare_runs",
        help="Run with and without memory and compare results.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config(args.config)
    registry = ModelRegistry()

    if args.model and not registry.validate(args.model):
        print(f"Unknown model: {args.model}")
        return 1

    if args.command is None:
        return start_repl(config, model_override=args.model)

    if args.command == "chat":
        return start_repl(config, model_override=args.model)

    if args.command == "run":
        session = create_session(
            mode="one-shot",
            model_provider=config.models.provider,
            selected_model=args.model or config.models.default,
        )
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
        print(f"Model: {session.model_provider}/{session.selected_model}")
        print(f"Log: {session.log_path}")
        return 0

    if args.command == "memory":
        return handle_memory(args)

    if args.command == "feedback":
        return handle_feedback(args)

    if args.command == "model":
        return handle_model(args, config)

    if args.command == "config":
        return handle_config(args, config, Path(args.config))

    if args.command == "eval":
        return handle_eval(args, config)

    parser.print_help()
    return 0


def start_repl(config: AgentConfig, model_override: str | None = None) -> int:
    return run_repl(config, model_override=model_override)


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


def handle_model(args: argparse.Namespace, config: AgentConfig) -> int:
    registry = ModelRegistry()
    if args.model_command in {None, "show"}:
        print(f"provider: {config.models.provider}")
        print(f"default: {config.models.default}")
        print(f"planner: {config.models.planner}")
        print(f"reflector: {config.models.reflector}")
        print(f"remote_calls_enabled: {config.models.remote_calls_enabled}")
        print(f"approval_required: {config.models.approval_required}")
        return 0

    if args.model_command == "list":
        for model in registry.list_models(config.models.provider):
            print(f"{model.name} [{', '.join(model.roles)}]")
        return 0

    if args.model_command == "test":
        service = ModelService(config)
        try:
            response = service.generate(
                model=args.model or config.models.default,
                prompt=args.prompt,
                system_prompt="Reply briefly. This is a connectivity test.",
            )
        except (LLMConfigurationError, LLMError) as exc:
            print(str(exc))
            return 1
        print(f"provider: {response.provider}")
        print(f"model: {response.model}")
        if response.response_id:
            print(f"response_id: {response.response_id}")
        print(response.text)
        return 0

    print("Model commands: show, list")
    return 1


def handle_eval(args: argparse.Namespace, config: AgentConfig) -> int:
    from agent.eval.runner import EvalRunner
    from agent.eval.scenario import BUILTIN_SCENARIOS, resolve_scenario
    from agent.eval.store import EvalStore

    cmd = args.scenario_or_cmd

    if cmd is None:
        print("Usage: agent eval <scenario>  |  list  |  scenarios  |  compare <id-a> <id-b>")
        return 0

    if cmd == "scenarios":
        for s in BUILTIN_SCENARIOS:
            tags = f"  [{', '.join(s.tags)}]" if s.tags else ""
            print(f"{s.id:<24} {s.name}{tags}")
        return 0

    if cmd == "list":
        store = EvalStore()
        runs = store.list()
        if not runs:
            print("No evaluation runs stored.")
            return 0
        for run in runs:
            memory_label = "memory" if run.with_memory else "no-memory"
            rate = f"{run.completion_rate * 100:.0f}%"
            print(f"{run.run_id}  {run.scenario_id:<24} {memory_label:<10} {rate}  {run.started_at[:19]}")
        return 0

    if cmd == "compare":
        if len(args.extra) < 2:
            print("Usage: agent eval compare <run-id-a> <run-id-b>")
            return 1
        store = EvalStore()
        run_a = store.get(args.extra[0])
        run_b = store.get(args.extra[1])
        if run_a is None:
            print(f"Run not found: {args.extra[0]}")
            return 1
        if run_b is None:
            print(f"Run not found: {args.extra[1]}")
            return 1
        _print_comparison(run_a, run_b)
        return 0

    scenario = resolve_scenario(cmd)
    if scenario is None:
        print(f"Unknown scenario: {cmd}  (use 'agent eval scenarios' to list builtins)")
        return 1

    runner = EvalRunner(config)
    store = EvalStore()

    if args.compare_runs:
        print(f"Running scenario: {scenario.name} ({scenario.id})")
        print("Pass 1: without memory")
        run_no_mem = runner.run(scenario, with_memory=False)
        store.save(run_no_mem)
        print("Pass 2: with memory")
        run_mem = runner.run(scenario, with_memory=True)
        store.save(run_mem)
        _print_comparison(run_no_mem, run_mem)
        return 0

    with_memory = not args.no_memory
    print(f"Running scenario: {scenario.name} ({scenario.id})")
    run = runner.run(scenario, with_memory=with_memory)
    store.save(run)
    _print_run(run)
    return 0


def _print_run(run) -> None:
    from agent.eval.metrics import EvalRunMetrics

    memory_label = "with memory" if run.with_memory else "no memory"
    print(f"\n[{memory_label}]")
    for i, t in enumerate(run.task_metrics, 1):
        status = "ok" if t.completed else "fail"
        print(
            f"  task {i}/{run.tasks_total}: {t.task_input!r:<30}"
            f"  {status:<4}  steps {t.steps_completed}/{t.steps_total}"
            f"  {t.duration_seconds:.3f}s"
            f"  mem-hits={t.memory_hits}"
        )
    print(
        f"\n  completion   {run.tasks_completed}/{run.tasks_total}"
        f" ({run.completion_rate * 100:.0f}%)"
    )
    print(f"  tool failures     {run.total_tool_failures}")
    print(f"  approval prompts  {run.total_approval_prompts}")
    print(f"  memory hits       {run.total_memory_hits}")
    print(f"  memories learned  {run.total_memories_learned}")
    print(f"  total duration    {run.total_duration_seconds:.3f}s")
    print(f"\n  run id: {run.run_id}")


def _print_comparison(run_a, run_b) -> None:
    def _label(r) -> str:
        return "memory" if r.with_memory else "no-memory"

    print(f"\n{'metric':<24}  {_label(run_a):<12}  {_label(run_b):<12}")
    print("-" * 52)
    print(f"{'completion rate':<24}  {run_a.completion_rate * 100:>10.0f}%  {run_b.completion_rate * 100:>10.0f}%")
    print(f"{'tool failures':<24}  {run_a.total_tool_failures:>11}  {run_b.total_tool_failures:>11}")
    print(f"{'approval prompts':<24}  {run_a.total_approval_prompts:>11}  {run_b.total_approval_prompts:>11}")
    print(f"{'memory hits':<24}  {run_a.total_memory_hits:>11}  {run_b.total_memory_hits:>11}")
    print(f"{'memories learned':<24}  {run_a.total_memories_learned:>11}  {run_b.total_memories_learned:>11}")
    print(f"{'duration (s)':<24}  {run_a.total_duration_seconds:>11.3f}  {run_b.total_duration_seconds:>11.3f}")
    print(f"\n  {_label(run_a)} run: {run_a.run_id}")
    print(f"  {_label(run_b)} run: {run_b.run_id}")


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
        print("models:")
        print(f"  provider: {config.models.provider}")
        print(f"  default: {config.models.default}")
        print(f"  planner: {config.models.planner}")
        print(f"  reflector: {config.models.reflector}")
        print(f"  allow_task_override: {config.models.allow_task_override}")
        print(f"  remote_calls_enabled: {config.models.remote_calls_enabled}")
        print(f"  approval_required: {config.models.approval_required}")
        print(f"  api_key_env_var: {config.models.api_key_env_var}")
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
