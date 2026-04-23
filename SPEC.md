# Self-Learning AI Agent Specification

## 1. Purpose

Build a self-learning AI agent whose default input interface is a command-line interface (CLI). The agent should accept user tasks, plan work, execute approved actions, observe results, learn from outcomes, and use that learning to improve future task performance.

## 2. Goals

- Provide a CLI-first user experience for one-shot and interactive agent usage.
- Support task planning, execution, observation, reflection, and memory.
- Treat security, privacy, and user approval as hard product requirements.
- Store reusable lessons from successes, failures, and user feedback.
- Retrieve relevant memories before and during future tasks.
- Keep learning inspectable, correctable, and safe.
- Require explicit approval for risky, destructive, costly, sensitive, or high-privilege actions.
- Maintain an audit trail of agent decisions, tool calls, and outcomes.

## 3. Non-Goals

- Full autonomy without user control.
- Hidden or irreversible learning.
- Storing secrets, credentials, private keys, or sensitive tokens in memory.
- Replacing explicit tests and evaluation with vague self-assessment.
- Building a graphical interface in the initial version.

## 4. Primary Interface

The default interface is an interactive CLI similar in spirit to Claude Code CLI. The product should feel like a terminal-native agent that can stay inside a workspace, understand project context, stream progress, request approvals, edit files, run commands, and maintain a persistent conversation with the user.

### 4.1 CLI Commands

```text
agent run "task"
agent
agent chat
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

### 4.2 Modes

- Interactive default mode: `agent` starts a persistent workspace-aware CLI session.
- Explicit interactive mode: `agent chat` starts the same persistent CLI session.
- One-shot mode: `agent run "task"` executes a single task and exits.
- Evaluation mode: `agent eval <scenario>` runs a predefined benchmark task.

### 4.3 CLI Requirements

- Display the current task, active plan, and next action clearly.
- Ask for confirmation before risky actions.
- Allow the user to interrupt, revise, or stop a task.
- Show concise summaries by default, with verbose logs available.
- Persist session logs for later review.

### 4.4 Interactive CLI Experience

The interactive CLI must be a first-class experience, not a thin wrapper around one-shot execution.

Requirements:

- Starting `agent` with no subcommand opens an interactive session in the current working directory.
- The session keeps conversational context until the user exits.
- The agent detects the current workspace, project files, Git state, package manager, and available test commands.
- The CLI streams the agent's progress while it works.
- The CLI shows tool activity in a compact, readable form, such as file reads, edits, shell commands, test runs, and memory lookups.
- The user can continue giving instructions after each result without restarting the agent.
- The user can interrupt an active task with `Ctrl+C` and choose whether to stop, revise, or continue.
- The user can approve or deny risky actions inline.
- The user can inspect planned edits before they are applied when the action is medium or high risk.
- The user can ask follow-up questions about previous commands, outputs, files, and decisions from the same session.
- The agent should preserve useful session context without forcing the user to repeat project details.
- The interface should remain usable in plain terminals without requiring a GUI.

### 4.5 Interactive Commands

Inside the interactive CLI, slash commands should provide fast control over the session.

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

Command behavior:

- `/help` shows available commands.
- `/exit` ends the session.
- `/clear` clears visible conversation context while preserving persistent memory.
- `/status` shows workspace, model, permission mode, active task, and Git state.
- `/plan` shows the current plan and completed steps.
- `/memory` shows memories used in the current session.
- `/permissions` shows the current approval policy.
- `/diff` shows pending or recently applied file changes.
- `/undo` reverts the last agent-applied file edit when possible.
- `/logs` opens or prints the current session log path.

### 4.6 Interactive Prompt Behavior

The CLI prompt should make the current workspace obvious.

Example:

```text
agent:C:\Users\User\repos\project>
```

The prompt should support:

- multi-line user input
- pasted code blocks
- command history
- basic autocomplete for slash commands
- clear rendering of assistant responses, tool calls, approvals, and final summaries
- heartbeat status updates while long-running tasks are active

### 4.7 Approval UX

When approval is required, the CLI should show:

- action type
- exact command or file path
- reason for the action
- risk level
- expected effect
- available choices

Example:

```text
Approval required: run shell command
Command: npm install
Risk: medium
Reason: dependencies are missing for the requested test run.

[a] approve once  [s] always approve similar  [d] deny  [e] explain
```

Approval decisions should be logged.

## 5. Core Architecture

The agent is built around a loop with the following components:

```text
User Input
  -> Context Loader
  -> Planner
  -> Executor
  -> Observer
  -> Reflector
  -> Memory Writer
  -> Response Generator
```

### 5.1 Context Loader

Responsibilities:

- Parse the user request.
- Load project configuration.
- Retrieve relevant memories.
- Load available tools and permissions.
- Build the initial task context.

### 5.2 Planner

Responsibilities:

- Decompose the user request into concrete steps.
- Identify dependencies, risks, and unknowns.
- Decide when to ask the user for clarification.
- Revise the plan based on observations.

### 5.3 Executor

Responsibilities:

- Select and invoke tools.
- Enforce permission and safety rules.
- Capture structured tool outputs.
- Retry or route errors back to the planner when appropriate.

### 5.4 Observer

Responsibilities:

- Normalize outputs from tools.
- Detect success, failure, partial completion, and unexpected state.
- Record relevant environment changes.
- Produce evidence for reflection and memory.

### 5.5 Reflector

Responsibilities:

- Evaluate whether the task was completed.
- Identify useful lessons from the task.
- Distinguish reusable learning from incidental details.
- Propose memory writes with confidence scores.

### 5.6 Memory Writer

Responsibilities:

- Store approved or automatically eligible memories.
- Avoid storing secrets or sensitive data.
- Deduplicate similar memories.
- Attach metadata such as source task, confidence, timestamp, and scope.

## 6. Agent Loop

For each task:

1. Accept input from the interactive CLI or one-shot command.
2. Load configuration, permissions, tools, and relevant memories.
3. Generate an initial plan.
4. Execute the next safe step.
5. Observe tool output and environment changes.
6. Update the plan if needed.
7. Continue until the task succeeds, fails, or needs user input.
8. Reflect on the result.
9. Store useful, specific, reusable memories.
10. Return a concise final summary to the user.

### 6.1 Loop States

The agent loop should expose explicit task states so the CLI can render progress and recover from interruptions.

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

### 6.2 Heartbeat

The agent must emit heartbeat events during active work so the interactive CLI can show that the agent is still alive, what it is waiting on, and how long the current step has been running.

Heartbeat requirements:

- emit at a fixed interval while a task is active
- include session ID, task ID, loop state, active step, active tool, elapsed time, and cancellation status
- continue during long-running shell commands and model calls when possible
- stop when the task reaches completed, failed, or cancelled
- write heartbeat events to the session log at a lower frequency than UI updates to avoid noisy logs
- allow the user to interrupt the active task from the CLI

Example heartbeat event:

```text
type: heartbeat
session_id: session_123
task_id: task_456
state: executing_tool
active_step: Run tests
active_tool: shell
elapsed_ms: 12000
cancellable: true
```

## 7. Memory System

### 7.1 Storage

The MVP should use local storage:

- SQLite for structured memory records.
- A vector index for semantic search.
- JSONL session logs for auditability.

Candidate vector stores:

- SQLite vector extension
- LanceDB
- Chroma

### 7.2 Memory Types

- User preferences
- Project facts
- Successful strategies
- Failed attempts
- Tool usage patterns
- Error resolutions
- Evaluation outcomes

### 7.3 Memory Fields

Each memory record should contain:

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

### 7.4 Memory Scoring

Memory retrieval should consider:

- semantic relevance
- recency
- reliability
- scope match
- prior usefulness
- user approval

### 7.5 Memory Safety

The agent must not store:

- API keys
- passwords
- private keys
- session cookies
- authentication tokens
- personal data unless explicitly allowed

The CLI must provide memory inspection and deletion commands.

## 8. Tool System

Tools should be schema-defined and return structured results.

### 8.1 Initial Tools

- Shell command tool
- File read tool
- File write tool
- Directory listing tool
- Git tool
- Test runner tool
- HTTP/search tool, optional for MVP

### 8.2 Tool Result Schema

```text
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

### 8.3 Risk Levels

- Low: read-only operations, local inspection.
- Medium: file edits, package installs, network calls.
- High: deletion, credential access, external side effects, costly API usage.

High-risk operations must require explicit user approval.

## 9. Learning Mechanisms

### 9.1 Short-Term Learning

Within a session, the agent should adapt based on:

- command failures
- test failures
- user corrections
- discovered project conventions
- tool availability

### 9.2 Long-Term Learning

Across sessions, the agent should store:

- reusable project conventions
- reliable fixes for recurring errors
- user preferences
- known tool commands
- successful strategies

### 9.3 Feedback Learning

The CLI should allow feedback:

```text
agent feedback good "Used the right test command"
agent feedback bad "Do not run formatter on the whole repo"
```

Feedback should influence memory confidence and future planning.

### 9.4 Evaluation Learning

The agent should run benchmark scenarios and compare results over time.

Tracked metrics:

- task completion rate
- retries per task
- user interventions
- tool failures
- test pass rate
- memory retrieval usefulness
- time to completion

## 10. Safety and Permissions

Security is the most important requirement. The agent must default to protecting user data, local files, credentials, source code, and environment details from accidental exposure.

### 10.1 Hard Security Rules

These rules are non-negotiable:

- Sensitive data must not leak to external systems, model providers, logs, memory, telemetry, or network tools.
- Secrets must never be stored in memory, session summaries, evaluation results, or reusable learning records.
- High-privilege instructions must always require explicit user approval before execution.
- Destructive actions must always require explicit user approval before execution.
- Network egress must always be classified for sensitive-data risk before execution.
- The agent must deny or redact any action that would expose secrets unless the user explicitly approves the exact disclosure.
- Approval must be action-specific; broad approval must never silently permit credential access, destructive actions, or sensitive-data exfiltration.
- If risk classification is uncertain, the action must be treated as high risk.

Sensitive data includes:

- API keys
- passwords
- private keys
- SSH keys
- tokens
- session cookies
- credential files
- `.env` values
- personal data
- proprietary source code or private repository contents when sent outside the local machine
- database dumps
- production logs containing user or customer data

High-privilege instructions include:

- deleting, overwriting, or moving files
- changing file permissions
- installing packages
- running scripts from the network
- modifying Git history
- accessing credential stores
- reading secret-bearing files
- sending local files, logs, source code, or command output to external services
- changing system configuration
- running commands with elevated privileges
- spending API credits or triggering paid external actions

### 10.2 Approval Requirements

The agent must ask for approval before:

- deleting files
- overwriting large or sensitive files
- installing dependencies
- making network calls
- accessing credentials
- sending data to external services
- spending API credits
- performing irreversible operations
- reading files that are likely to contain secrets
- sending any local file content, terminal output, memory content, or logs to a remote service
- running commands with administrator, root, sudo, or equivalent elevated privileges

The agent should support configurable policies in `agent.yaml`.

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

### 10.3 Sensitive Data Controls

The agent must implement sensitive-data controls before any memory write, log write, tool call, model call, or network call.

Required controls:

- scan tool inputs and outputs for common secret patterns
- redact detected secrets from logs and UI summaries
- block memory writes containing secrets
- block network calls containing secrets unless explicitly approved
- warn before reading known sensitive files such as `.env`, private keys, credential stores, and production dumps
- preserve local-only processing when possible
- record that redaction occurred without recording the secret value

Redaction format:

```text
[REDACTED_SECRET:type=api_key]
[REDACTED_SECRET:type=token]
[REDACTED_SECRET:type=private_key]
```

### 10.4 Approval Logging

Approval logs must include:

- action type
- target command or path
- risk level
- reason
- decision
- timestamp
- whether the approval was one-time or persisted for similar actions

Approval logs must not include raw secret values.

### 10.5 Default Deny Cases

The agent must deny by default:

- requests to reveal stored secrets
- requests to bypass approval gates
- requests to disable security logging
- requests to exfiltrate credentials
- requests to run unknown remote scripts with elevated privileges
- requests to persist secrets into memory
- requests to send private files to external services without explicit file-specific approval

## 11. Logging and Audit Trail

Each session should produce a JSONL log containing:

- task ID
- user input
- loaded memories
- generated plans
- tool calls
- tool results
- approval prompts
- final result
- reflection
- memory writes

Logs should be human-inspectable and suitable for evaluation.

Logs must be redacted before write. Raw secrets must never be written to logs.

## 12. Suggested Tech Stack

### 12.1 Python Option

- CLI: Typer
- Interactive prompt: prompt_toolkit
- Terminal rendering: Rich
- Storage: SQLite
- Vector search: LanceDB, Chroma, or SQLite vector extension
- Config: Pydantic and YAML
- Tests: pytest

### 12.2 TypeScript Option

- CLI: Commander
- Interactive prompt: Ink, Clack, or readline/prompts
- Terminal rendering: Ink, consola, or picocolors
- Storage: SQLite
- Vector search: LanceDB or local embedding index
- Config: Zod and YAML
- Tests: Vitest

## 13. Proposed Project Structure

```text
self_learning_agent/
  agent/
    cli.py
    repl.py
    heartbeat.py
    loop.py
    planner.py
    executor.py
    observer.py
    reflector.py
    memory.py
    config.py
    logging.py
    tools/
      shell.py
      filesystem.py
      git.py
      tests.py
      http.py
  data/
    memory.sqlite
    sessions/
  evals/
    scenarios.yaml
  tests/
    test_loop.py
    test_memory.py
    test_tools.py
  agent.yaml
  README.md
```

## 14. MVP Requirements

The first usable version must:

- Accept CLI tasks with `agent run "task"`.
- Start an interactive CLI with `agent`.
- Support `agent chat` as an alias for interactive mode.
- Maintain session context across multiple user turns.
- Provide slash commands for session control.
- Generate and display a task plan.
- Run the task through an explicit agent loop with observable states.
- Execute safe shell and filesystem tools.
- Ask before risky actions.
- Enforce hard security rules and high-privilege approval gates.
- Stream progress and tool activity in the terminal.
- Emit heartbeat status while active work is running.
- Record structured observations.
- Summarize the final result.
- Store useful memories locally.
- Retrieve relevant memories in future runs.
- Provide memory list, search, show, and delete commands.
- Write session logs.

## 15. Milestones

### Milestone 1: CLI Skeleton

- Create CLI entry point.
- Add config loading.
- Add one-shot mode.
- Add interactive REPL mode as the default when running `agent`.
- Add slash command parsing.
- Add basic logging.

### Milestone 2: Tool Runtime

- Add shell and filesystem tools.
- Add structured tool result schema.
- Add approval prompts.
- Add risk classification.
- Add sensitive-data redaction for tool inputs, outputs, logs, memory, and network calls.
- Add default-deny handling for secrets and high-privilege actions.

### Milestone 3: Agent Loop

- Add planner.
- Add executor.
- Add observer.
- Add explicit loop states.
- Add heartbeat event emission.
- Add final response generation.
- Support plan revision after failures.

### Milestone 4: Memory

- Add SQLite memory store.
- Add memory CRUD commands.
- Add semantic retrieval.
- Add memory scoring.
- Add memory safety filters.
- Block memory writes that contain secrets or sensitive data.

### Milestone 5: Reflection and Learning

- Add task reflection.
- Add automatic memory proposals.
- Add feedback commands.
- Add memory confidence updates.

### Milestone 6: Evaluation

- Add benchmark scenario format.
- Add evaluation runner.
- Track metrics over time.
- Compare runs with and without memory retrieval.

## 16. Acceptance Criteria

- A user can run `agent` from a project directory and enter an interactive session.
- The interactive session preserves context across follow-up prompts.
- Slash commands such as `/help`, `/status`, `/plan`, and `/exit` work.
- A user can run `agent run "summarize this repo"` from the CLI.
- The agent creates a visible plan before acting.
- The agent exposes observable loop states during task execution.
- The agent uses read-only tools without unnecessary prompts.
- The agent asks before file writes, deletes, network calls, or package installs.
- The agent requires approval before any high-privilege instruction.
- The agent redacts secrets before logging, memory writes, model calls, or network calls.
- The agent denies attempts to store or exfiltrate secrets by default.
- The agent streams command execution and file activity clearly in the terminal.
- The CLI shows heartbeat status for long-running work.
- The agent logs all actions in a session file.
- The agent stores at least one reusable memory after a successful task.
- A later task retrieves and uses that memory.
- The user can inspect and delete memories.
- Evaluation scenarios produce repeatable metrics.

## 17. Open Design Questions

- Should memory writes be automatic by default or require review?
- Which vector store should be used for the MVP?
- Should tool execution run in a sandboxed subprocess, container, or both?
- Which model provider should power planning and reflection?
- Should the agent support multiple workspaces in the first version?
- How strict should approval policies be by default?
