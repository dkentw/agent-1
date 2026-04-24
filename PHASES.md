# Self-Learning AI Agent Implementation Phases

## Phase 0: Project Foundation

Goal: create the repository structure, tooling, and baseline conventions.

Deliverables:

- project package skeleton
- dependency manager setup
- test runner setup
- lint or formatting command
- initial `agent.yaml`
- README with local development instructions

Suggested files:

```text
agent/
  __init__.py
  cli.py
  config.py
tests/
  test_config.py
agent.yaml
README.md
```

Exit criteria:

- tests run successfully
- `agent --help` displays top-level CLI help
- config loads from defaults and `agent.yaml`

## Phase 1: Interactive CLI Skeleton

Goal: make `agent` open a persistent terminal session.

Deliverables:

- `agent` starts the interactive REPL by default
- `agent chat` aliases the same REPL
- `agent run "task"` supports one-shot mode
- workspace-aware prompt
- slash command parser
- basic session state
- JSONL session log file

Required slash commands:

```text
/help
/exit
/clear
/status
/logs
```

Exit criteria:

- user can start and exit the REPL
- `/status` shows workspace path and session ID
- `/logs` shows the current log path
- conversation turns are recorded in session state

## Phase 2: Workspace Detection

Goal: make the agent aware of the current project.

Deliverables:

- Git root detection
- Git status summary
- language and package manager detection
- test command detection
- important file detection
- workspace context model

Exit criteria:

- `/status` shows Git state when inside a repo
- detected package manager appears in session context
- read-only detection does not require approval

## Phase 3: Tool Runtime and Permissions

Goal: add safe, structured tool execution with hard approval gates.

Deliverables:

- tool request and result schemas
- tool registry
- filesystem read/list/stat tools
- shell command tool
- Git status/diff tools
- permission engine
- sensitive-data guard
- approval prompt UI
- approval logging
- redaction before logs, memory writes, model calls, and network calls

Default policy:

- allow read-only file and Git inspection
- ask before shell commands with side effects
- ask before file writes
- ask before network calls
- ask before deletes
- always ask before high-privilege instructions
- deny credential access by default
- treat unknown risk as high risk

Exit criteria:

- read-only tools run without approval
- risky actions show an approval prompt
- high-privilege instructions always show an approval prompt
- denied approvals prevent execution
- raw secrets are redacted before logging
- network egress containing secrets is blocked by default
- tool calls are logged as structured JSONL events

## Phase 4: Basic Agent Loop

Goal: connect user tasks to planning and tool execution.

Deliverables:

- task request model
- planner interface
- plan and plan step models
- explicit loop state model
- executor loop
- observer result interpretation
- renderer for plan and progress events
- final task summary

Required REPL commands:

```text
/plan
/permissions
```

Exit criteria:

- user can ask a simple repo-inspection task
- agent creates and displays a plan
- agent exposes current loop state
- agent executes read-only steps
- agent summarizes the result
- `/plan` shows current and completed steps

## Phase 4.5: Heartbeat and Liveness

Goal: keep long-running agent work visible and interruptible.

Deliverables:

- heartbeat service
- heartbeat event model
- UI heartbeat renderer
- sampled heartbeat logging
- timeout warning support
- unhealthy task detection
- cancellation flag checked by the agent loop

Exit criteria:

- active tasks emit heartbeat events at a fixed interval
- long-running shell commands show elapsed time
- session logs include sampled heartbeat events
- `Ctrl+C` can request cancellation while heartbeat is active
- missing heartbeat is treated as an unhealthy active task

## Phase 5: File Editing and Diff UX

Goal: support controlled workspace edits.

Deliverables:

- file write tool
- patch or diff generation
- pending edit preview
- `/diff` command
- basic `/undo` support for last agent-applied edit
- edit approval flow

Required REPL commands:

```text
/diff
/undo
```

Exit criteria:

- agent can propose a file edit
- user can inspect the diff before approval
- approved edit is applied and logged
- denied edit is not applied
- last edit can be undone when possible

## Phase 6: Local Memory MVP

Goal: add inspectable local memory and retrieval.

Deliverables:

- SQLite schema
- memory CRUD service
- memory CLI commands
- memory slash commands
- keyword or SQLite FTS search
- memory retrieval during context loading
- memory usage logging

Required commands:

```text
agent memory list
agent memory search <query>
agent memory show <id>
agent memory delete <id>
/memory
/memory search <query>
```

Exit criteria:

- memories can be created, listed, searched, shown, and deleted
- relevant memories are loaded into task context
- session logs show which memories were used

## Phase 7: Reflection and Self-Learning

Goal: store useful lessons from completed tasks.

Deliverables:

- reflection service
- memory proposal model
- sensitive data filter
- automatic memory writes for safe project facts
- review-required memory writes for user preferences
- feedback commands
- confidence and reliability updates

Required commands:

```text
agent feedback good "reason"
agent feedback bad "reason"
```

Exit criteria:

- successful tasks can produce memory proposals
- unsafe memory content is rejected
- raw secrets cannot be stored in memory
- user feedback updates memory confidence
- later tasks can use memories from earlier tasks

## Phase 8: Better Interactive Behavior

Goal: make the REPL feel like a durable coding-agent interface.

Deliverables:

- model selection UX polish
- streaming progress events
- compact tool activity rendering
- multi-line input support
- command history
- autocomplete for slash commands
- `Ctrl+C` task interruption flow
- follow-up question support using session context
- heuristic-only follow-up resolution for executable actions

Exit criteria:

- long-running work streams progress
- interrupted tasks can stop cleanly
- follow-up prompts can refer to previous commands or files
- ambiguous executable follow-ups do not guess and require explicit user input
- plain terminal usage remains clear

## Phase 9: Evaluation Harness

Goal: measure whether learning improves task performance.

Deliverables:

- scenario format
- evaluation runner
- repeatable test workspace fixtures
- metrics storage
- comparison of runs with and without memory retrieval

Metrics:

- completion rate
- retries per task
- user interventions
- approval denials
- tool failures
- test pass rate
- memory retrieval usefulness
- time to completion

Exit criteria:

- `agent eval <scenario>` runs a predefined task
- evaluation results are stored
- repeated runs can be compared

## Phase 10: Hardening and Release Readiness

Goal: prepare the agent for regular local use.

Deliverables:

- stronger config validation
- improved error messages
- shell timeout controls
- workspace path enforcement
- credential storage migration to a standard keychain or audited AEAD-backed store
- argv-based shell execution path for the default runner
- security regression tests
- secret redaction regression tests
- high-privilege approval regression tests
- log rotation or cleanup
- documentation
- installation instructions
- end-to-end tests for core flows

Exit criteria:

- clean install works from README instructions
- core flows pass tests
- safety prompts are consistent
- security hard rules are covered by tests
- raw secrets do not appear in logs, memory, or evaluation artifacts
- logs and memories are inspectable
- the agent is usable as a daily interactive CLI assistant
- residual hardening items are tracked and addressed before release

## Suggested MVP Boundary

The MVP should include Phases 0 through 6, including Phase 4.5.

MVP capabilities:

- `agent` opens an interactive CLI
- `agent run "task"` works
- workspace detection works
- read-only tools work
- approval prompts work
- high-privilege approval gates work
- sensitive-data redaction works
- basic planning and summaries work
- heartbeat status works for active tasks
- file edits can be previewed and approved
- memory CRUD and retrieval work
- session logs are written

Self-learning is meaningfully useful after Phase 7.

The Claude Code-style interactive experience becomes credible after Phase 8.

## Cross-Cutting: Model Runtime

This is a core component rather than a late add-on.

Required foundation:

- typed model config in `agent.yaml`
- model registry and validation
- session-level active model state
- process-level model override
- CLI and REPL model inspection
- redaction and approval boundary before any remote model call

Provider-backed planning and reflection should build on this foundation instead of making direct ad hoc API calls.
