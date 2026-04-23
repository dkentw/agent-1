# Self-Learning AI Agent Design Specification

## 1. Overview

This document translates `SPEC.md` into an implementation-oriented design for a CLI-first self-learning AI agent. The agent runs primarily as an interactive terminal application similar in spirit to Claude Code CLI, with one-shot command support for automation.

The design prioritizes:

- a workspace-aware interactive CLI
- structured planning and execution
- explicit approvals for risky and high-privilege actions
- hard controls that prevent sensitive-data leakage
- inspectable local memory
- durable session logs
- incremental learning from feedback and outcomes

## 2. System Shape

The system is organized around a runtime loop shared by both interactive and one-shot modes.

```text
CLI / REPL
  -> Session Manager
  -> Context Loader
  -> Agent Loop
      -> Planner
      -> Tool Router
      -> Executor
      -> Observer
      -> Heartbeat
      -> Reflector
      -> Memory Service
  -> Renderer
  -> Session Logger
```

The CLI owns user interaction. The agent loop owns task execution. Tools are isolated behind schemas and permission checks. Memory and logs are local by default.

## 3. Recommended Implementation Stack

The initial implementation should use Python unless there is a strong reason to prefer TypeScript.

Recommended Python stack:

- CLI command framework: Typer
- Interactive prompt: prompt_toolkit
- Terminal rendering: Rich
- Config models: Pydantic
- Config format: YAML
- Structured storage: SQLite
- Session logs: JSONL
- Tests: pytest

Vector search can start with simple keyword or SQLite FTS search, then add embeddings later. This keeps the first build usable without forcing vector infrastructure too early.

## 4. Runtime Components

### 4.1 CLI Entry Point

Module: `agent/cli.py`

Responsibilities:

- parse top-level commands
- start interactive mode when `agent` is run without arguments
- route `agent chat` to the interactive REPL
- route `agent run "task"` to one-shot execution
- expose memory, feedback, eval, and config commands

Command surface:

```text
agent
agent chat
agent run "task"
agent memory list
agent memory search <query>
agent memory show <id>
agent memory delete <id>
agent feedback good "reason"
agent feedback bad "reason"
agent eval <scenario>
agent config show
agent config edit
```

### 4.2 Interactive REPL

Module: `agent/repl.py`

Responsibilities:

- maintain a persistent session until `/exit`
- render the workspace-aware prompt
- accept multi-line input and pasted code
- route slash commands
- stream agent progress
- handle `Ctrl+C` interruption
- prompt for approvals
- display diffs, plans, logs, and final summaries

Prompt format:

```text
agent:C:\Users\User\repos\project>
```

Slash commands:

```text
/help
/exit
/clear
/status
/plan
/memory
/memory search <query>
/permissions
/approve
/deny
/diff
/undo
/logs
/model
/config
```

The REPL should not directly perform agent work. It should create session events and call the agent runtime.

### 4.3 Session Manager

Module: `agent/session.py`

Responsibilities:

- create a session ID
- store current workspace path
- maintain conversation history
- track active task state
- track current loop state
- track current plan and completed steps
- track loaded memories
- coordinate cancellation and interruption
- expose session state to `/status`, `/plan`, `/memory`, and `/logs`

Session state should be explicit and serializable.

Suggested model:

```text
SessionState
  id
  workspace_path
  started_at
  mode
  active_task
  loop_state
  conversation
  current_plan
  loaded_memories
  pending_approval
  recent_tool_results
  pending_edits
  log_path
```

### 4.4 Workspace Detector

Module: `agent/workspace.py`

Responsibilities:

- identify Git repository root
- inspect Git status
- detect package manager
- detect language and framework hints
- detect common test commands
- identify important config files

Detection should be read-only.

Examples:

- `package.json` -> Node or TypeScript project
- `pyproject.toml` -> Python project
- `Cargo.toml` -> Rust project
- `go.mod` -> Go project
- `.git` -> Git workspace

### 4.5 Config Service

Module: `agent/config.py`

Responsibilities:

- load global and workspace config
- validate config with typed models
- expose permission policy
- expose memory policy
- expose model/provider settings

Config load order:

1. built-in defaults
2. user-level config
3. workspace `agent.yaml`
4. CLI flags

Example:

```yaml
permissions:
  shell:
    default: ask
    read_only: allow
  filesystem:
    read: allow
    write: ask
    delete: ask
  network:
    default: ask
memory:
  auto_write: true
  require_review_for_user_preferences: true
```

### 4.6 Agent Loop

Module: `agent/loop.py`

Responsibilities:

- receive a task request
- load context
- ask the planner for steps
- execute steps through the tool router
- observe results
- revise the plan when needed
- stop on completion, failure, interruption, or required user input
- maintain explicit loop state transitions
- cooperate with the heartbeat service
- emit structured progress events for the CLI renderer

The loop should be event-driven from the CLI perspective.

Event examples:

```text
task_started
context_loaded
plan_created
step_started
tool_requested
approval_required
tool_started
tool_finished
step_completed
plan_revised
task_completed
task_failed
memory_written
```

Loop states:

```text
idle
loading_context
planning
waiting_for_approval
executing_tool
observing
replanning
reflecting
writing_memory
completed
failed
cancelled
```

Core loop algorithm:

```text
set state loading_context
load workspace, config, tools, permissions, and memories

set state planning
create or revise plan

for each pending step:
  if cancellation requested:
    set state cancelled
    stop

  if approval is required:
    set state waiting_for_approval
    wait for approval decision

  set state executing_tool
  execute tool request

  set state observing
  interpret tool result

  if plan revision is needed:
    set state replanning
    revise plan

set state reflecting
reflect on task outcome

set state writing_memory
write approved useful memories

set state completed or failed
emit final summary
```

The loop should avoid hidden background autonomy. It may continue autonomously only within the active user-requested task and current permission policy.

### 4.7 Heartbeat Service

Module: `agent/heartbeat.py`

Responsibilities:

- emit liveness events while a task is active
- expose current loop state to the renderer
- include the active step, active tool, elapsed time, and cancellation status
- keep long-running shell commands and model calls visible
- support timeout warnings
- write sampled heartbeat events to the session log

Heartbeat event model:

```text
HeartbeatEvent
  session_id
  task_id
  loop_state
  active_step_id
  active_step_title
  active_tool
  started_at
  elapsed_ms
  cancellable
  cancellation_requested
  message
```

Default behavior:

- UI heartbeat interval: 1 second
- log heartbeat interval: 10 seconds
- timeout warning interval: configurable per tool
- heartbeat stops when the loop reaches completed, failed, or cancelled

The heartbeat service should be passive. It reports state owned by the session and loop; it should not make planning or tool decisions.

### 4.8 Planner

Module: `agent/planner.py`

Responsibilities:

- produce a short task plan
- classify steps by risk
- identify likely tools
- identify unknowns
- revise plans based on observations

Plan model:

```text
Plan
  id
  task
  steps
  status
  created_at
  updated_at

PlanStep
  id
  title
  rationale
  status
  expected_tools
  risk_level
```

The first planner can be rule-assisted and model-backed. It does not need complex autonomy in phase one.

### 4.9 Tool Router

Module: `agent/tool_router.py`

Responsibilities:

- register available tools
- validate tool inputs
- classify risk
- enforce permissions
- request approval when needed
- dispatch calls to tools
- normalize tool results

Tool call flow:

```text
ToolRequest
  -> validate
  -> classify risk
  -> check policy
  -> maybe request approval
  -> execute
  -> return ToolResult
```

### 4.10 Tools

Package: `agent/tools/`

Initial tools:

- `filesystem.py`: read, write, list, stat, diff
- `shell.py`: run commands with timeout and working directory
- `git.py`: status, diff, branch, log
- `tests.py`: run detected test commands
- `http.py`: optional network tool, disabled or ask-by-default

Tool result schema:

```text
ToolResult
  id
  tool_name
  input
  status
  stdout
  stderr
  artifacts
  started_at
  finished_at
  risk_level
  requires_approval
```

### 4.11 Permission Engine

Module: `agent/permissions.py`

Responsibilities:

- map tool requests to risk levels
- apply policy from config
- support approve once and approve similar
- log approval decisions
- deny dangerous actions by default when policy requires

Approval choices:

```text
approve once
always approve similar
deny
explain
```

Risk defaults:

- read-only local inspection: allow
- file writes: ask
- package installs: ask
- network calls: ask
- deletes: ask
- credential access: deny by default
- high-privilege commands: ask every time
- unknown risk: treat as high risk

The permission engine must never let broad approval bypass credential access, destructive actions, sensitive-data disclosure, or elevated-privilege commands.

### 4.12 Sensitive Data Guard

Module: `agent/sensitive_data.py`

Responsibilities:

- detect likely secrets in tool inputs and outputs
- redact secrets before logs, summaries, memory writes, model calls, or network calls
- block memory writes that contain secrets
- block network egress containing secrets unless explicitly approved
- mark known sensitive paths as high risk
- provide structured redaction metadata without storing secret values

Sensitive paths and patterns:

```text
.env
.env.*
*.pem
*.key
id_rsa
id_ed25519
credentials.json
*.p12
*.pfx
production.log
database dumps
```

Sensitive values:

```text
API keys
passwords
private keys
SSH keys
tokens
session cookies
database URLs
cloud credentials
personal data
customer data
```

Redaction format:

```text
[REDACTED_SECRET:type=api_key]
[REDACTED_SECRET:type=token]
[REDACTED_SECRET:type=private_key]
```

### 4.13 Observer

Module: `agent/observer.py`

Responsibilities:

- interpret tool results
- detect whether a step succeeded
- identify errors and likely causes
- extract useful evidence for the next planning turn
- summarize outputs for the session log and renderer

### 4.14 Reflector

Module: `agent/reflector.py`

Responsibilities:

- evaluate final task outcome
- identify reusable lessons
- propose memory writes
- avoid storing incidental or sensitive data
- call the sensitive data guard before proposing memory writes
- attach confidence and scope to proposed memories

Reflection should run at task end, not after every tiny action.

### 4.15 Memory Service

Module: `agent/memory.py`

Responsibilities:

- create local SQLite schema
- store memory records
- search memories
- update confidence and usage metadata
- delete memories
- provide memories to the context loader
- reject memory writes that contain raw secrets

Initial storage should use SQLite with FTS for search. Embedding-based retrieval can be added later behind the same interface.

Memory table fields:

```text
id
type
scope
content
summary
source_task_id
created_at
updated_at
confidence
relevance_score
reliability_score
last_used_at
use_count
tags
```

### 4.16 Logger

Module: `agent/logging.py`

Responsibilities:

- write JSONL session events
- record tool calls and results
- record approvals
- record sampled heartbeat events
- record memory reads and writes
- expose current log path to `/logs`

Logs should be append-only per session. All event payloads must pass through redaction before write. Raw secrets must never be logged.

### 4.17 Renderer

Module: `agent/rendering.py`

Responsibilities:

- format assistant messages
- format plan updates
- format tool calls
- format heartbeat status
- format approvals
- format diffs and summaries
- keep output compact and readable

The renderer should be replaceable so non-interactive output can stay clean.

## 5. Data Models

### 5.1 Task Request

```text
TaskRequest
  id
  input
  mode
  workspace_path
  created_at
```

### 5.2 Tool Request

```text
ToolRequest
  id
  tool_name
  args
  reason
  risk_level
  workspace_path
```

### 5.3 Approval Request

```text
ApprovalRequest
  id
  action_type
  command_or_path
  reason
  risk_level
  expected_effect
  choices
```

### 5.4 Memory Record

```text
MemoryRecord
  id
  type
  scope
  content
  summary
  source_task_id
  confidence
  reliability_score
  created_at
  updated_at
  tags
```

### 5.5 Loop State

```text
LoopState
  session_id
  task_id
  state
  active_step_id
  active_tool_call_id
  cancellation_requested
  started_at
  updated_at
```

### 5.6 Heartbeat Event

```text
HeartbeatEvent
  session_id
  task_id
  loop_state
  active_step_title
  active_tool
  elapsed_ms
  cancellable
  cancellation_requested
  message
```

## 6. Control Flow

### 6.1 Interactive Task Flow

```text
User enters prompt
  -> REPL creates TaskRequest
  -> Session Manager appends conversation turn
  -> Context Loader gathers workspace and memory context
  -> Planner creates plan
  -> Renderer shows plan
  -> Agent Loop executes steps
  -> Heartbeat emits liveness events while active
  -> Tool Router handles approvals and tools
  -> Observer interprets results
  -> Planner revises if needed
  -> Reflector proposes memory writes
  -> Memory Service stores allowed memories
  -> Renderer prints final summary
  -> REPL waits for next prompt
```

### 6.2 One-Shot Task Flow

```text
agent run "task"
  -> create temporary session
  -> run same agent loop
  -> print final summary
  -> exit with status code
```

Exit code guidance:

- `0`: task completed
- `1`: task failed
- `2`: user denied required approval
- `130`: interrupted

### 6.3 Approval Flow

```text
Tool request created
  -> permission engine classifies risk
  -> sensitive data guard classifies data exposure risk
  -> policy says approval required
  -> CLI renders approval prompt
  -> user chooses approve, approve similar, deny, or explain
  -> decision logged
  -> tool runs only if approved
```

### 6.4 Heartbeat Flow

```text
Task starts
  -> session stores task start time
  -> loop updates state on each transition
  -> heartbeat service emits UI event every second
  -> renderer updates compact status line
  -> logger records sampled heartbeat every 10 seconds
  -> heartbeat stops when task completes, fails, or is cancelled
```

Example rendered heartbeat:

```text
Running tests... 12s elapsed. Press Ctrl+C to interrupt.
```

## 7. Error Handling

The system should distinguish:

- user cancellation
- denied approval
- tool timeout
- missing heartbeat from active task
- tool execution failure
- invalid tool input
- model/provider failure
- memory store failure
- config validation failure

Failures should be rendered clearly and logged with structured metadata.

The agent should retry only when the retry has a specific reason, such as correcting a command path, using a detected package manager, or applying a failed test insight.

If an active task stops emitting heartbeat events unexpectedly, the CLI should mark the task as unhealthy, log the condition, and offer to interrupt or wait.

## 8. Security and Safety Design

Security is the highest-priority requirement. When security conflicts with convenience, security wins.

### 8.1 Hard Security Rules

- Never store secrets in memory.
- Never write raw secrets to logs.
- Never send sensitive data to external services without explicit file-specific or content-specific approval.
- Always ask before destructive actions.
- Always ask before network calls that include local content, logs, memory, command output, or source code.
- Always ask before package installs.
- Always ask before elevated-privilege commands.
- Always ask before credential access.
- Deny attempts to bypass approval gates.
- Treat unknown risk as high risk.
- Keep file edits scoped to the active workspace.
- Keep shell commands scoped to the active workspace unless explicitly approved.
- Support read-only inspection without prompts only when the action is low risk and does not target secret-bearing files.

### 8.2 High-Privilege Approval Gate

The following must always require explicit approval:

- administrator, root, sudo, or equivalent commands
- changing file permissions
- deleting or overwriting files
- modifying Git history
- installing dependencies
- running remote scripts
- accessing credential stores
- reading known secret-bearing files
- sending local data to a network service
- triggering paid API usage
- changing system configuration

Approval prompts must include:

- exact command or path
- data that may be exposed
- risk level
- expected effect
- whether the action is reversible
- one-time or persisted approval choice, where persisted approval is allowed

Persisted approvals are not allowed for credential access, destructive actions, sensitive-data disclosure, or elevated-privilege commands.

### 8.3 Sensitive Data Flow

All data that may leave a component boundary must pass through the sensitive data guard.

Protected boundaries:

- tool input
- tool output
- renderer summary
- session log
- memory write
- model/provider call
- network request
- evaluation artifact

Required behavior:

- redact before writing logs
- redact before memory storage
- redact before model calls when local content is included
- block network egress when secrets are detected
- record redaction metadata without recording the secret value

The first version should avoid autonomous background execution.

## 9. Testing Strategy

Unit tests:

- config loading and validation
- slash command parsing
- permission policy decisions
- sensitive-data detection and redaction
- memory CRUD
- workspace detection
- tool result normalization
- loop state transitions
- heartbeat event generation
- plan status transitions

Integration tests:

- one-shot task executes read-only flow
- interactive session preserves context
- active task emits heartbeat events
- approval required before file write
- denied approval stops tool execution
- raw secrets are not written to logs or memory
- high-privilege actions require approval
- memory created after task reflection
- later task retrieves relevant memory

Manual tests:

- start `agent` in a Git repo
- run `/status`
- ask it to inspect the repo
- interrupt a running command
- approve and deny sample actions
- inspect `/logs`

## 10. Design Decisions

- Use one runtime loop for both interactive and one-shot modes.
- Make loop states explicit and observable from the CLI.
- Use heartbeat events to keep long-running work inspectable.
- Treat the REPL as the default product surface.
- Start memory search with SQLite FTS before adding vector retrieval.
- Keep tools schema-based from the beginning.
- Require explicit approval for file writes, shell commands with side effects, and high-privilege instructions.
- Redact sensitive data before logs, memory, model calls, and network egress.
- Store session logs as JSONL to support debugging and evaluation.

## 11. Open Technical Decisions

- Which model provider should power planning and reflection?
- Should shell execution use direct subprocesses, a sandbox, or containers?
- Should persistent memory require review by default?
- Should file edits use patch application only, full-file writes, or both?
- Should the REPL support background tasks in a later version?
