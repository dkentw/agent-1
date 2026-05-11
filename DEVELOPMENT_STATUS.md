# Self-Learning AI Agent Development Status

## Status Summary

Current status: Phase 9 completed.

The project now contains product requirements, technical design, implementation phases, this development tracker, the Phase 0 Python package foundation, the Phase 1 interactive CLI skeleton, the Phase 2 workspace detection layer, the Phase 3 tool runtime and permission layer, the Phase 4 basic agent loop, the Phase 4.5 heartbeat and liveness layer, the Phase 5 file editing and diff UX, the Phase 6 local memory MVP, the Phase 7 reflection and self-learning layer, and a core model registry and selection component.

## Source Documents

- `SPEC.md`: product specification and hard requirements
- `DESIGN_SPEC.md`: technical design and architecture
- `PHASES.md`: phased implementation plan
- `DEVELOPMENT_STATUS.md`: current development status and progress tracker

## Current Priorities

1. Keep security rules explicit and testable.
2. Build the interactive CLI as the default product surface.
3. Implement safe tool execution with approval gates before advanced autonomy.
4. Add heartbeat and observable loop states early.
5. Add memory only after logging, redaction, and permissions are reliable.

## Phase Progress

| Phase | Name | Status | Notes |
| --- | --- | --- | --- |
| 0 | Project Foundation | Completed | Package skeleton, config, CLI, tests, default config, README, and `.gitignore` have been added. CLI help and tests pass through `uv`. |
| 1 | Interactive CLI Skeleton | Completed | `agent` and `agent chat` start the REPL, `agent run` records a one-shot task, slash commands work, session state exists, and JSONL logs are written. |
| 2 | Workspace Detection | Completed | Sessions detect Git state, package manager, languages, likely test commands, and important files. `/status` surfaces workspace context. |
| 3 | Tool Runtime and Permissions | Completed | Added tool request/result models, read-only filesystem and Git tools, risk classification, permission decisions, approval state, and REPL permission commands. |
| 4 | Basic Agent Loop | Completed | Added task and plan models, explicit loop states, rule-based planning, observer, visible plan rendering, `/plan`, and read-only loop execution. |
| 4.5 | Heartbeat and Liveness | Completed | Added heartbeat monitor, heartbeat events, REPL heartbeat rendering, sampled heartbeat logs, and basic unhealthy-task detection. |
| 5 | File Editing and Diff UX | Completed | Added file write support, diff preview before approval, pending edit state, `/diff`, `/undo`, and edit approval flow. |
| 6 | Local Memory MVP | Completed | Added SQLite memory service, CLI memory CRUD, REPL memory commands, retrieval during task setup, and memory usage logging. |
| 7 | Reflection and Self-Learning | Completed | Added reflection service, safe memory proposals, memory confidence updates, top-level feedback commands, and REPL feedback for current task memories. |
| 8 | Better Interactive Behavior | Completed | Added multiline continuation, compact rendering, `/history`, `/cancel`, slash-command suggestions, richer follow-up reuse, heuristic-only executable follow-up resolution, live heartbeat rendering, and closed the `run_repl` boundary decision. |
| 9 | Evaluation Harness | Completed | Added scenario format, eval runner, temp workspace fixtures, SQLite metrics store, and CLI eval commands with comparison support. |
| 10 | Hardening and Release Readiness | Not started | Add regression tests, documentation, install flow, cleanup. |

## Completed Work

- Created product specification in `SPEC.md`.
- Added Claude Code-style interactive CLI requirements.
- Added technical design in `DESIGN_SPEC.md`.
- Added implementation phases in `PHASES.md`.
- Added explicit agent loop states.
- Added heartbeat and liveness requirements.
- Added hard security rules.
- Added sensitive-data redaction and default-deny requirements.
- Added mandatory high-privilege approval requirements.
- Started Phase 0 project foundation.
- Added Python package skeleton in `agent/`.
- Added CLI entry point in `agent/cli.py`.
- Added safe config loading in `agent/config.py`.
- Added default config in `agent.yaml`.
- Added starter tests in `tests/`.
- Added development README.
- Started and completed Phase 1 interactive CLI skeleton.
- Added session state in `agent/session.py`.
- Added JSONL logging in `agent/logging.py`.
- Added REPL command handling in `agent/repl.py`.
- Wired `agent` and `agent chat` to the REPL.
- Updated `agent run` to create a one-shot session log.
- Added Phase 1 REPL tests.
- Started and completed Phase 2 workspace detection.
- Added workspace detection in `agent/workspace.py`.
- Attached workspace context to each session.
- Added workspace context to session start logs.
- Updated `/status` to show Git, package manager, languages, tests, and important files.
- Added Phase 2 workspace tests.
- Started and completed Phase 3 tool runtime and permissions.
- Added tool models in `agent/tool_models.py`.
- Added permission policy logic in `agent/permissions.py`.
- Added read-only filesystem and Git tools in `agent/tools/`.
- Added tool routing in `agent/tool_router.py`.
- Added pending approval and recent tool result tracking to sessions.
- Added `/permissions`, `/approve`, and `/deny` handling in the REPL.
- Added Phase 3 tool and approval tests.
- Started and completed Phase 4 basic agent loop.
- Added task and plan models in `agent/planner.py`.
- Added observation helpers in `agent/observer.py`.
- Added the minimal agent loop in `agent/loop.py`.
- Added loop-state transitions and visible plan rendering to the REPL.
- Added `/plan` command support.
- Added Phase 4 loop and plan tests.
- Started and completed Phase 4.5 heartbeat and liveness.
- Added heartbeat service in `agent/heartbeat.py`.
- Added heartbeat tracking to sessions.
- Added heartbeat emission from the agent loop.
- Added heartbeat rendering and heartbeat log events in the REPL.
- Added heartbeat tests.
- Started and completed Phase 5 file editing and diff UX.
- Added file write and preview diff support in `agent/tools/filesystem.py`.
- Added diff preview support to approval requests.
- Added pending edit and last applied edit tracking to sessions.
- Added `/diff` and `/undo` handling in the REPL.
- Added Phase 5 edit-flow tests.
- Started and completed Phase 6 local memory MVP.
- Added SQLite memory service in `agent/memory.py`.
- Added top-level CLI memory commands.
- Added `/memory` and `/memory search` in the REPL.
- Added memory retrieval during task setup in the agent loop.
- Added memory usage logging and Phase 6 memory tests.
- Started and completed Phase 7 reflection and self-learning.
- Added the reflection service in `agent/reflector.py`.
- Added a minimal sensitive-data memory filter in `agent/sensitive_data.py`.
- Added safe automatic memory writes for workspace facts and successful file interactions.
- Added memory upsert and feedback score updates in `agent/memory.py`.
- Added `agent feedback good|bad "reason"` commands.
- Added `/feedback good|bad <reason>` in the REPL.
- Added Phase 7 reflection and feedback tests.
- Added typed model config and default model settings.
- Added a local model registry in `agent/models.py`.
- Added session-level active model tracking.
- Added `agent model show`, `agent model list`, and `--model <name>`.
- Added `/model`, `/model list`, and `/model <name>` in the REPL.
- Added model config, CLI, and REPL tests.
- Added the provider adapter interface and model service in `agent/llm.py`.
- Added the first provider-backed adapter using the OpenAI Responses API.
- Added `agent model test "prompt"` and `/model test <prompt>`.
- Added env-var API key loading through `models.api_key_env_var`.
- Added local credential storage in `agent/credentials.py`.
- Added `/model key setup`, `/model key unlock`, `/model key clear`, and hashed-PIN credential protection.
- Updated credential handling to use one global credential-store PIN for all stored provider keys.
- Split PIN initialization into a dedicated `/setup-pin` command so credential setup only uses an existing PIN.
- Refactored slash commands into plugin-style command components under `agent/commands/` with a shared registry.
- Moved command-family behavior out of `Repl` into `agent/commands/services.py` for help, status, memory, and model flows.
- Added cancellable `shell.run` execution, richer session references for follow-up resolution, and extracted control/edit command services.
- Moved secure credential prompt handling out of `Repl` into a dedicated command service and suppressed duplicate heartbeat lines.
- Moved follow-up resolution out of `Repl` into a dedicated service and broadened it to file/task/shell/test references.
- Moved task/approval/display orchestration out of `Repl` into a dedicated task interaction service.
- Added model-call redaction before provider requests.
- Started Phase 8 better interactive behavior.
- Added multiline input continuation in the REPL.
- Added compact REPL rendering in `agent/rendering.py`.
- Added `/history` for recent input history.
- Added `/cancel` for pending approval or active task state.
- Added slash-command suggestions for near matches.
- Added follow-up reuse such as `read it again`, `show the diff`, `undo that`, and `run that again`.
- Added cancellation-request tracking on `Ctrl+C` and loop cancellation exits.
- Added Phase 8 REPL tests for the new interaction patterns.
- Added richer live heartbeat rendering so long-running work shows compact state, step, tool, elapsed time, and cancel hints in both the main task flow and `/status`.

## Active Work

Active implementation work: none. Phase 9 complete. Next work is Phase 10 hardening.

## Next Implementation Steps

1. Start Phase 10: stronger config validation, improved error messages, shell timeout controls.
2. Integrate provider-backed model calls into planner and reflector behind the existing adapter boundary.
3. Harden credential storage by moving away from the current custom local crypto scheme.
4. Replace `shell=True` with an argv-based shell runner where possible.

## MVP Scope

The MVP includes Phases 0 through 6, including Phase 4.5.

MVP must include:

- interactive CLI started by `agent`
- one-shot mode with `agent run "task"`
- workspace detection
- safe read-only tools
- explicit approval prompts
- high-privilege approval gates
- sensitive-data redaction
- observable agent loop states
- heartbeat status for active tasks
- previewable file edits
- local memory CRUD and retrieval
- session logs

## Security Status

Security status: design defined, not implemented.

Required before any meaningful tool execution:

- sensitive-data guard
- secret pattern detection
- redaction before log writes
- redaction before memory writes
- redaction before model calls
- redaction before network calls
- default-deny for credential access
- explicit approval for high-privilege instructions
- approval logging without secret values

## Known Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Sensitive data leakage | Critical | Implement redaction and egress checks before memory, logs, model calls, and network calls. |
| Overbroad approvals | High | Do not allow persisted approvals for credentials, destructive actions, sensitive disclosure, or elevated privileges. |
| Tool execution side effects | High | Start with read-only tools and require approval for writes, deletes, installs, network, and elevated commands. |
| Memory pollution | Medium | Store only specific, reusable, non-sensitive memories with confidence and scope. |
| Hidden long-running work | Medium | Add heartbeat and explicit loop states before complex tool execution. |
| Poor interactive UX | Medium | Make the REPL the default surface and test it manually in real terminals. |

## Open Decisions

| Decision | Status | Notes |
| --- | --- | --- |
| Implementation language | Decided for Phase 0 | Python skeleton has been created. This can still be revisited before deeper implementation if needed. |
| Model provider | Open | Needed for planner and reflector implementation. |
| Memory search backend | Open | Start with SQLite FTS; embeddings can be added later. |
| Shell isolation model | Open | Decide between direct subprocess, sandboxed subprocess, or container. |
| File edit strategy | Open | Decide between patch-only edits, full-file writes, or both. |
| Memory write policy | Open | Decide whether automatic memory writes require review by default. |
| Follow-up resolution for executable actions | Decided | Keep it heuristic-only. Model-backed interpretation may exist later only as a non-executing suggestion layer. |
| `run_repl` terminal loop boundary | Decided | Keep the terminal loop in `agent/repl.py` rather than moving it to a thinner CLI session runner. |
| Credential storage backend | Tracked | Replace the custom PIN-based crypto with a standard keychain or audited AEAD-backed store. |
| Shell execution boundary | Tracked | Replace `shell=True` with argv-based execution for the default path when practical. |

## Change Log

| Date | Change |
| --- | --- |
| 2026-04-23 | Created initial product spec. |
| 2026-04-23 | Added interactive CLI requirements inspired by Claude Code CLI. |
| 2026-04-23 | Added design spec and implementation phases. |
| 2026-04-23 | Added agent loop states and heartbeat requirements. |
| 2026-04-23 | Added hard security rules, sensitive-data controls, and high-privilege approval gates. |
| 2026-04-23 | Added development status tracker. |
| 2026-04-23 | Started Phase 0 and added the initial Python package foundation. |
| 2026-04-23 | Completed Phase 0 verification: CLI help works and 5 tests pass through `uv run --extra dev pytest`. |
| 2026-04-23 | Completed Phase 1 verification: interactive CLI skeleton and 11 tests pass through `uv run --extra dev pytest`. |
| 2026-04-23 | Completed Phase 2 verification: workspace detection and 16 tests pass through `uv run --extra dev pytest`. |
| 2026-04-23 | Completed Phase 3 verification: tool runtime and permissions with 22 passing tests through `uv run --extra dev pytest`. |
| 2026-04-23 | Completed Phase 4 verification: basic agent loop with 26 passing tests through `uv run --extra dev pytest`. |
| 2026-04-23 | Completed Phase 4.5 verification: heartbeat and liveness with 28 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Completed Phase 5 verification: file editing and diff UX with 34 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Completed Phase 6 verification: local memory MVP with 39 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Completed Phase 7 verification: reflection and self-learning with 45 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Added core model registry and selection support with 49 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Started Phase 8 interactive-behavior work with multiline input, history, command suggestions, follow-up file reuse, and 55 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Extended Phase 8 with compact rendering, `/cancel`, broader follow-up resolution, and loop cancellation exits with 60 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Added the LLM adapter interface, OpenAI provider adapter, env-var API key loading, and model test commands with 66 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Added local credential storage with hashed PIN protection and slash-command key setup/unlock flow with 72 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Updated credential setup to use one global PIN for all stored provider keys with 74 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Split global PIN initialization into `/setup-pin` and kept `/model key setup` focused on provider credentials. |
| 2026-04-24 | Refactored REPL slash commands into plugin-style modules under `agent/commands/`. |
| 2026-04-24 | Moved command-family behavior out of `Repl` into dedicated command services while keeping the REPL as the I/O and loop coordinator. |
| 2026-04-24 | Added cancellable `shell.run`, session reference tracking for richer follow-ups, and extracted control/edit command services with 78 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Moved secure prompt handling into a dedicated service and suppressed duplicate heartbeat lines with 79 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Moved follow-up resolution into a dedicated service and broadened it to file/task/shell/test references with 81 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Moved task/approval/display orchestration into a dedicated task interaction service with 81 passing tests through `uv run --extra dev pytest`. |
| 2026-04-24 | Added richer live heartbeat rendering for long-running work, including compact progress summaries in task output and `/status`. |
| 2026-04-24 | Decided that follow-up resolution stays heuristic-only for executable actions. |
| 2026-04-24 | Decided that the `run_repl` terminal loop stays in `agent/repl.py`, closing the remaining Phase 8 boundary decision. |
| 2026-04-24 | Tracked credential storage and shell execution hardening items as explicit next-step work. |
| 2026-05-11 | Completed Phase 9 evaluation harness: scenario format, EvalRunner with auto-approving EvalToolRouter, temp workspace fixtures, SQLite metrics store, and CLI eval commands with 120 passing tests. |
