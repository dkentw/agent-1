# Self-Learning AI Agent

CLI-first self-learning AI agent. The current repository is in Phase 7: reflection and self-learning.

## Current State

Implemented:

- Python package skeleton
- CLI entry point
- interactive REPL skeleton
- slash commands: `/help`, `/exit`, `/clear`, `/status`, `/logs`
- session state
- JSONL session logging
- one-shot task receipt logging
- workspace detection
- Git status summary in `/status`
- package manager detection
- language detection
- likely test command detection
- important file detection
- tool request and result models
- read-only filesystem tools
- read-only Git tools
- permission policy engine
- approval flow hooks
- task and plan models
- visible task planning
- explicit loop-state transitions
- minimal read-only task execution loop
- heartbeat event model
- heartbeat rendering in the REPL
- sampled heartbeat logging
- latest-heartbeat status reporting
- file write tool
- diff preview before approval
- pending edit tracking
- `/diff` for pending or last applied edits
- `/undo` for the last agent-applied edit
- SQLite-backed local memory store
- memory CRUD service
- `agent memory list/search/show/delete`
- `/memory` and `/memory search <query>`
- memory retrieval during task setup
- memory usage logging
- reflection-driven safe memory writing
- recent-memory feedback scoring
- `agent feedback good|bad "reason"`
- `/feedback good|bad <reason>`
- safe default config loading
- default `agent.yaml`
- starter tests
- development status tracking

Not implemented yet:

- review-required user preference memories

## Requirements

- Python 3.11 or newer
- pytest for tests

The Phase 6 code intentionally uses only the Python standard library at runtime.

## Install for Development

Using `uv`:

```powershell
uv run --extra dev pytest
```

Using `pip`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Run

Show CLI help:

```powershell
agent --help
```

Or without installing the script globally:

```powershell
uv run python -m agent.cli --help
```

Start the interactive CLI skeleton:

```powershell
agent
```

The prompt uses the current folder name:

```text
agent-1 > 
```

The full workspace path remains available through `/status`.
The interactive CLI uses a restrained ANSI color style inspired by Claude Code and Codex: cyan headings, green commands/workspace names, gray metadata, and yellow warnings.

`/status` now includes detected project context such as Git state, package manager, languages, likely test commands, and important files.

Supported slash commands:

```text
/help
/exit
/clear
/status
/plan
/permissions
/approve
/deny
/diff
/undo
/memory
/feedback
/logs
```

`/permissions` shows the current policy, and the REPL now has approval-state handling for non-read-only actions.
`/plan` shows the current plan, and normal task prompts now go through a visible plan before read-only execution.
Heartbeat status is emitted during active work and is visible in both task output and `/status`.
Write tasks now preview a diff before approval. `/diff` shows the pending or last applied diff, and `/undo` restores the last agent-applied edit.
Memories are stored locally in SQLite. `/memory` shows loaded memories for the current task, `/memory search <query>` searches stored memories, and `agent memory ...` provides top-level CRUD commands.
Successful tasks now write safe reflected memories for reusable workspace facts such as package manager, test commands, and frequently inspected files. `agent feedback good "reason"` and `agent feedback bad "reason"` update recent memory confidence, while `/feedback` applies the same scoring to the current task memories in the REPL.

Run the one-shot placeholder:

```powershell
agent run "summarize this repo"
```

Show effective config:

```powershell
agent config show
```

## Test

```powershell
pytest
```

Or with `uv`:

```powershell
uv run --extra dev pytest
```

## Security Defaults

The default config is intentionally conservative:

- shell side effects require approval
- file writes and deletes require approval
- network calls require approval
- high-privilege actions require approval
- credential access is denied
- logs, memory, model calls, and network calls must be redacted
- unknown risk is treated as high risk
