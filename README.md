# Self-Learning AI Agent

CLI-first self-learning AI agent. The current repository has completed Phase 8: better interactive behavior.

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
- core model registry and selection state
- `agent model show`
- `agent model list`
- `agent model test "prompt"`
- `--model <name>` process override
- `/setup-pin`, `/model`, `/model list`, `/model use <name>`, `/model test <prompt>`, `/model key setup`, `/model key unlock`, `/model key clear`, and `/model <name>`
- multiline input continuation with trailing `\`
- recent input history via `/history`
- slash-command suggestion for near matches
- follow-up file reuse such as `read it again`
- cancellation-request status on `Ctrl+C`
- compact tool rendering through `agent/rendering.py`
- `/cancel` to cancel pending approval or active task state
- broader follow-ups such as `show the diff`, `undo that`, and `run that again`
- safe default config loading
- default `agent.yaml`
- starter tests
- development status tracking

Not implemented yet:

- review-required user preference memories
- planner and reflector integration with provider-backed model calls

## Requirements

- Python 3.11 or newer
- pytest for tests

The current runtime still uses only the Python standard library.

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
Slash commands are now organized under [agent/commands](C:\Users\User\repos\agent-1\agent\commands) as plugin-style components loaded by a central registry, instead of a single hardcoded dispatch block in the REPL. Command-family behavior is further split into [agent/commands/services.py](C:\Users\User\repos\agent-1\agent\commands\services.py), so `Repl` mainly coordinates terminal I/O. Phase 8 now also includes a cancellable `shell.run` runtime path, richer session references for follow-ups such as `run that test again`, `run that command again`, and `open that again`, extracted control/edit command services for approval and diff flows, a dedicated secure prompt service for credential input, duplicate-heartbeat suppression for longer-running tasks, richer live heartbeat rendering with step, tool, elapsed time, and cancel hints, and a task interaction service that owns task-start, plan/summary, heartbeat, approval, tool-result, and memory-notification orchestration.

`/status` now includes detected project context such as Git state, package manager, languages, likely test commands, and important files.

Supported slash commands:

```text
/help
/exit
/clear
/setup-pin
/status
/plan
/permissions
/approve
/deny
/diff
/undo
/memory
/feedback
/history
/model
/cancel
/logs
```

`/permissions` shows the current policy, and the REPL now has approval-state handling for non-read-only actions.
`/plan` shows the current plan, and normal task prompts now go through a visible plan before read-only execution.
Heartbeat status is emitted during active work and is visible in both task output and `/status`.
Write tasks now preview a diff before approval. `/diff` shows the pending or last applied diff, and `/undo` restores the last agent-applied edit.
Memories are stored locally in SQLite. `/memory` shows loaded memories for the current task, `/memory search <query>` searches stored memories, and `agent memory ...` provides top-level CRUD commands.
Successful tasks now write safe reflected memories for reusable workspace facts such as package manager, test commands, and frequently inspected files. `agent feedback good "reason"` and `agent feedback bad "reason"` update recent memory confidence, while `/feedback` applies the same scoring to the current task memories in the REPL.
The agent now has a core model component with a typed model config, a local registry of supported models, session-level model selection, a provider adapter interface in `agent/llm.py`, and an OpenAI Responses adapter. Remote model calls are still disabled by default until you opt in through config.

## LLM Setup

Enable remote model calls in `agent.yaml`:

```yaml
models:
  provider: openai
  default: gpt-5.4-mini
  planner: gpt-5.4-mini
  reflector: gpt-5.4-mini
  remote_calls_enabled: true
  api_key_env_var: OPENAI_API_KEY
```

You can still set the API key in PowerShell for the current session:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
```

Persist it for future PowerShell sessions:

```powershell
setx OPENAI_API_KEY "your_api_key_here"
```

Or set it from inside the REPL with a local credential store:

```text
/setup-pin
/model key setup
```

The REPL setup flow is now split:
1. `/setup-pin` creates the single global credential-store PIN
2. `/model key setup` stores a provider API key using that existing PIN

Behavior:
- the API key is stored locally in `data/credentials.sqlite`
- the PIN is a single global PIN for the whole local credential store
- the PIN is stored only as a hash
- the API key is stored encrypted
- the secret and PIN are not written to the session log
- `/model key setup` requires an existing PIN and does not create one implicitly
- the stored key is unlocked for the current REPL session after setup
- later credential setup reuses the same existing PIN instead of creating a new one per provider

On later sessions:

```text
/model key unlock
```

That asks for the same global credential-store PIN and unlocks the stored API key for model calls in the current session.

Then use:

```powershell
uv run python -m agent.cli model test "hello"
uv run python -m agent.cli --model gpt-5.4 run "summarize this repo"
```

Inside the REPL:

```text
/model
/model list
/model use gpt-5.4
/setup-pin
/model key setup
/model key unlock
/model test hello
```

Model prompts pass through the model-call redaction path before leaving the machine.

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
