from __future__ import annotations

from pathlib import Path

from agent.llm import LLMConfigurationError, LLMError
from agent.tool_models import PendingEdit
from agent.style import Style, paint


class CoreCommandService:
    def __init__(self, repl):
        self.repl = repl

    def write_help(self) -> None:
        self.repl.write(paint("Commands", Style.bold, Style.cyan, enabled=self.repl.color))
        for command in self.repl.command_registry.items():
            styled_command = paint(command.name.ljust(10), Style.green, enabled=self.repl.color)
            self.repl.write(f"  {styled_command} {command.description}")

    def clear_context(self) -> None:
        self.repl.session.clear_visible_context()
        self.repl.write(
            paint("cleared", Style.green, enabled=self.repl.color)
            + " visible conversation context."
        )
        self.repl.logger.write("context_cleared", {"session_id": self.repl.session.id})

    def write_logs_path(self) -> None:
        self.repl.write(paint(str(self.repl.session.log_path), Style.gray, enabled=self.repl.color))


class StatusCommandService:
    def __init__(self, repl):
        self.repl = repl

    def write_status(self) -> None:
        self.repl.write(paint("Status", Style.bold, Style.cyan, enabled=self.repl.color))
        self.write_status_row("session", self.repl.session.id)
        self.write_status_row("prompt", self.repl.session.prompt.strip())
        self.write_status_row("workspace", str(self.repl.session.workspace_path))
        self.write_status_row("mode", self.repl.session.mode)
        self.write_status_row("provider", self.repl.session.model_provider)
        self.write_status_row("model", self.repl.session.selected_model)
        self.write_status_row("loop", self.repl.session.loop_state)
        self.write_status_row("cancel", str(self.repl.session.cancellation_requested).lower())
        self.write_status_row("task", self.repl.session.active_task or "none")
        self.write_status_row("log", str(self.repl.session.log_path))
        self.write_status_row("credential", self.repl.config.permissions.credential_access)
        self.write_status_row("risk", self.repl.config.security.unknown_risk)
        self.write_workspace_status()
        if self.repl.session.pending_approval:
            self.write_status_row("approval", self.repl.session.pending_approval.action_type)
        if self.repl.session.pending_edit:
            self.write_status_row("pending_edit", self.repl.session.pending_edit.path)
        if self.repl.session.last_applied_edit:
            self.write_status_row("last_edit", self.repl.session.last_applied_edit.path)
        if self.repl.session.current_plan:
            self.write_status_row("plan", self.repl.session.current_plan.status)
        if self.repl.session.loaded_memories:
            self.write_status_row("memories", str(len(self.repl.session.loaded_memories)))
        if self.repl.session.learned_memories:
            self.write_status_row("learned", str(len(self.repl.session.learned_memories)))
        if self.repl.session.latest_heartbeat:
            self.write_status_row("heartbeat", self.repl.describe_heartbeat(self.repl.session.latest_heartbeat))
        if self.repl.session.references.last_active_path:
            self.write_status_row("last_path", self.repl.session.references.last_active_path)

    def write_workspace_status(self) -> None:
        workspace = self.repl.session.workspace_context
        if workspace is None:
            return
        self.write_status_row("git", workspace.git.status_summary)
        if workspace.git.branch:
            self.write_status_row("branch", workspace.git.branch)
        if workspace.git.root:
            self.write_status_row("git_root", str(workspace.git.root))
        self.write_status_row("package", workspace.package_manager or "none")
        self.write_status_row("languages", ", ".join(workspace.languages) or "none")
        self.write_status_row("tests", ", ".join(workspace.test_commands) or "none")
        self.write_status_row("files", ", ".join(workspace.important_files) or "none")

    def write_status_row(self, label: str, value: str) -> None:
        styled_label = paint(label.rjust(10), Style.gray, enabled=self.repl.color)
        self.repl.write(f"  {styled_label}  {value}")

    def write_permissions(self) -> None:
        self.repl.write(paint("Permissions", Style.bold, Style.cyan, enabled=self.repl.color))
        self.write_status_row("shell", self.repl.config.permissions.shell.default)
        self.write_status_row("fs.read", self.repl.config.permissions.filesystem.read)
        self.write_status_row("fs.write", self.repl.config.permissions.filesystem.write)
        self.write_status_row("fs.delete", self.repl.config.permissions.filesystem.delete)
        self.write_status_row("network", self.repl.config.permissions.network.default)
        self.write_status_row("high_priv", self.repl.config.permissions.high_privilege)
        self.write_status_row("creds", self.repl.config.permissions.credential_access)

    def write_plan(self) -> None:
        plan = self.repl.session.current_plan
        if plan is None:
            self.repl.write(paint("No active plan.", Style.gray, enabled=self.repl.color))
            return
        self.repl.render_plan(plan)


class MemoryCommandService:
    def __init__(self, repl):
        self.repl = repl

    def write_history(self) -> None:
        if not self.repl.session.input_history:
            self.repl.write(paint("No input history.", Style.gray, enabled=self.repl.color))
            return
        self.repl.write(paint("History", Style.bold, Style.cyan, enabled=self.repl.color))
        start = max(1, len(self.repl.session.input_history) - 9)
        for index, entry in enumerate(self.repl.session.input_history[-10:], start=start):
            self.repl.write(f"  {paint(str(index).rjust(2), Style.gray, enabled=self.repl.color)}  {entry}")

    def write_loaded_memories(self) -> None:
        if not self.repl.session.loaded_memories:
            self.repl.write(paint("No loaded memories.", Style.gray, enabled=self.repl.color))
            return
        self.repl.write(paint("Loaded memories", Style.bold, Style.cyan, enabled=self.repl.color))
        for record in self.repl.session.loaded_memories:
            self.repl.write(f"  {paint(record.id, Style.green, enabled=self.repl.color)} {record.summary}")

    def write_memory_search(self, query: str) -> None:
        if not query:
            self.repl.write(paint("Usage: /memory search <query>", Style.gray, enabled=self.repl.color))
            return
        records = self.repl.memory_service.search(query, limit=10)
        if not records:
            self.repl.write(paint("No memories found.", Style.gray, enabled=self.repl.color))
            return
        self.repl.write(paint("Memory search", Style.bold, Style.cyan, enabled=self.repl.color))
        for record in records:
            self.repl.write(f"  {paint(record.id, Style.green, enabled=self.repl.color)} {record.summary}")

    def apply_feedback(self, argument: str) -> None:
        action, _, reason = argument.partition(" ")
        action = action.strip().lower()
        reason = reason.strip()
        if action not in {"good", "bad"}:
            self.repl.write(paint("Usage: /feedback good|bad <reason>", Style.gray, enabled=self.repl.color))
            return
        target_ids = [record.id for record in (self.repl.session.learned_memories or self.repl.session.loaded_memories)]
        if not target_ids:
            self.repl.write(paint("No task memories available for feedback.", Style.gray, enabled=self.repl.color))
            return
        updated = self.repl.memory_service.apply_feedback(target_ids, positive=action == "good")
        self.repl.logger.write(
            "feedback_applied",
            {
                "session_id": self.repl.session.id,
                "task_id": self.repl.session.current_task_id,
                "action": action,
                "reason": reason,
                "memory_ids": target_ids,
            },
        )
        self.repl.write(
            paint("feedback", Style.cyan, enabled=self.repl.color)
            + f" applied to {len(updated)} memory item(s)."
        )


class ModelCommandService:
    def __init__(self, repl):
        self.repl = repl

    def handle_command(self, argument: str) -> None:
        action = argument.strip()
        if not action or action == "show":
            self.write_model_status()
            return
        if action == "list":
            self.write_model_list()
            return
        if action == "key setup":
            self.start_key_setup()
            return
        if action == "key unlock":
            self.start_key_unlock()
            return
        if action == "key clear":
            deleted = self.repl.credential_store.delete(self.repl.session.model_provider)
            self.repl.unlocked_model_api_key = None
            self.repl.write(
                paint("credential", Style.cyan, enabled=self.repl.color)
                + (" cleared." if deleted else " not found.")
            )
            return
        if action == "key status":
            self.write_key_status()
            return
        if action.startswith("use "):
            action = action.removeprefix("use ").strip()
        if action.startswith("test "):
            self.test_active_model(action.removeprefix("test ").strip())
            return
        self.select_model(action)

    def write_model_status(self) -> None:
        self.repl.write(paint("Model", Style.bold, Style.cyan, enabled=self.repl.color))
        self.repl.status_commands.write_status_row("provider", self.repl.session.model_provider)
        self.repl.status_commands.write_status_row("active", self.repl.session.selected_model)
        self.repl.status_commands.write_status_row("planner", self.repl.config.models.planner)
        self.repl.status_commands.write_status_row("reflector", self.repl.config.models.reflector)
        self.repl.status_commands.write_status_row("remote", str(self.repl.config.models.remote_calls_enabled).lower())
        self.repl.status_commands.write_status_row("api_key_env", self.repl.config.models.api_key_env_var)
        self.repl.status_commands.write_status_row("stored_key", str(self.repl.credential_store.has_credential(self.repl.session.model_provider)).lower())
        self.repl.status_commands.write_status_row("unlocked", str(self.repl.unlocked_model_api_key is not None).lower())

    def write_model_list(self) -> None:
        self.repl.write(paint("Models", Style.bold, Style.cyan, enabled=self.repl.color))
        for model in self.repl.model_registry.list_models(self.repl.session.model_provider):
            self.repl.write(f"  {paint(model.name, Style.green, enabled=self.repl.color)} [{', '.join(model.roles)}]")

    def write_key_status(self) -> None:
        self.repl.write(paint("Credential", Style.bold, Style.cyan, enabled=self.repl.color))
        self.repl.status_commands.write_status_row("provider", self.repl.session.model_provider)
        self.repl.status_commands.write_status_row("stored", str(self.repl.credential_store.has_credential(self.repl.session.model_provider)).lower())
        self.repl.status_commands.write_status_row("unlocked", str(self.repl.unlocked_model_api_key is not None).lower())

    def select_model(self, action: str) -> None:
        if not self.repl.config.models.allow_task_override:
            self.repl.write(paint("Model override disabled.", Style.yellow, enabled=self.repl.color))
            return
        if not self.repl.model_registry.validate(action):
            self.repl.write(paint("Unknown model.", Style.yellow, enabled=self.repl.color) + f" {action}")
            return
        self.repl.session.selected_model = action
        self.repl.logger.write(
            "model_selected",
            {
                "session_id": self.repl.session.id,
                "provider": self.repl.session.model_provider,
                "model": self.repl.session.selected_model,
            },
        )
        self.repl.write(
            paint("model", Style.cyan, enabled=self.repl.color)
            + f" set to {self.repl.session.selected_model}."
        )

    def test_active_model(self, prompt: str) -> None:
        if not prompt:
            self.repl.write(paint("Usage: /model test <prompt>", Style.gray, enabled=self.repl.color))
            return
        try:
            response = self.repl.model_service.generate(
                model=self.repl.session.selected_model,
                prompt=prompt,
                system_prompt="Reply briefly. This is a connectivity test.",
                api_key_override=self.repl.unlocked_model_api_key,
            )
        except (LLMConfigurationError, LLMError) as exc:
            self.repl.write(paint(str(exc), Style.yellow, enabled=self.repl.color))
            return
        self.repl.logger.write(
            "model_test",
            {
                "session_id": self.repl.session.id,
                "provider": response.provider,
                "model": response.model,
                "response_id": response.response_id,
            },
        )
        self.repl.write(paint("model", Style.cyan, enabled=self.repl.color) + f" {response.provider}/{response.model}")
        self.repl.write(response.text)

    def start_key_setup(self) -> None:
        from agent.repl import SecurePromptState

        if not self.repl.credential_store.has_pin():
            self.repl.write(
                paint("PIN not configured.", Style.yellow, enabled=self.repl.color)
                + " Run "
                + paint("/setup-pin", Style.green, enabled=self.repl.color)
                + " first."
            )
            return
        self.repl.secure_prompt_state = SecurePromptState(
            mode="setup_api_key",
            provider=self.repl.session.model_provider,
        )
        self.repl.write(paint("credential", Style.cyan, enabled=self.repl.color) + " Enter API key for the active provider.")
        self.repl.write(paint("note", Style.gray, enabled=self.repl.color) + " This input will not be logged.")

    def start_pin_setup(self) -> None:
        from agent.repl import SecurePromptState

        if self.repl.credential_store.has_pin():
            self.repl.write(paint("PIN already configured.", Style.yellow, enabled=self.repl.color))
            return
        self.repl.secure_prompt_state = SecurePromptState(mode="setup_global_pin", provider="")
        self.repl.write(paint("credential", Style.cyan, enabled=self.repl.color) + " Create the global credential PIN code.")
        self.repl.write(paint("note", Style.gray, enabled=self.repl.color) + " This input will not be logged.")

    def start_key_unlock(self) -> None:
        from agent.repl import SecurePromptState

        if not self.repl.credential_store.has_credential(self.repl.session.model_provider):
            self.repl.write(paint("No stored credential for provider.", Style.gray, enabled=self.repl.color))
            return
        self.repl.secure_prompt_state = SecurePromptState(
            mode="unlock_pin",
            provider=self.repl.session.model_provider,
        )
        self.repl.write(paint("credential", Style.cyan, enabled=self.repl.color) + " Enter PIN to unlock the stored API key.")
        self.repl.write(paint("note", Style.gray, enabled=self.repl.color) + " This input will not be logged.")


class ControlCommandService:
    def __init__(self, repl):
        self.repl = repl

    def cancel_active_work(self):
        from agent.repl import ReplResult

        if self.repl.secure_prompt_state is not None:
            self.repl.secure_prompt_state = None
            self.repl.write(paint("Cancelled.", Style.yellow, enabled=self.repl.color))
            return ReplResult()
        had_pending_approval = self.repl.session.pending_approval is not None
        if self.repl.session.pending_approval:
            self.repl.session.pending_approval = None
            self.repl.session.pending_edit = None
        if (
            not had_pending_approval
            and self.repl.session.current_plan is None
            and self.repl.session.loop_state in {"idle", "completed", "failed", "cancelled"}
        ):
            self.repl.write(paint("No active task to cancel.", Style.gray, enabled=self.repl.color))
            return ReplResult()
        self.repl.session.cancellation_requested = True
        if self.repl.session.current_plan is not None:
            self.repl.session.current_plan.status = "cancelled"
        self.repl.set_loop_state("cancelled")
        self.repl.write(paint("Cancelled.", Style.yellow, enabled=self.repl.color))
        self.repl.logger.write(
            "task_cancelled",
            {
                "session_id": self.repl.session.id,
                "task_id": self.repl.session.current_task_id,
                "loop_state": self.repl.session.loop_state,
            },
        )
        return ReplResult()

    def resolve_pending_approval(self, approved: bool):
        from agent.repl import ReplResult

        approval = self.repl.session.pending_approval
        if approval is None:
            self.repl.write(paint("No pending approval.", Style.gray, enabled=self.repl.color))
            return ReplResult()

        self.repl.logger.write(
            "approval_decision",
            {
                "session_id": self.repl.session.id,
                "approval_id": approval.id,
                "decision": "approved" if approved else "denied",
                "action_type": approval.action_type,
                "target": approval.command_or_path,
                "risk_level": approval.risk_level,
            },
        )

        self.repl.session.pending_approval = None
        if not approved:
            self.repl.session.pending_edit = None
            self.repl.write(paint("Denied.", Style.yellow, enabled=self.repl.color))
            return ReplResult()

        result = self.repl.tool_router.execute(
            approval.tool_request,
            is_cancelled=lambda: self.repl.session.cancellation_requested,
        )
        self.repl.capture_applied_edit(result)
        if self.repl.session.current_plan is None:
            self.repl.handle_tool_result(result)
            return ReplResult()

        self.repl.agent_loop.resume_after_approval(
            session=self.repl.session,
            result=result,
            on_tool_result=self.repl.handle_tool_result,
            on_summary=self.repl.render_summary,
            on_state_change=self.repl.set_loop_state,
            on_heartbeat=self.repl.handle_heartbeat,
            on_memories_learned=self.repl.handle_learned_memories,
        )
        return ReplResult()


class EditCommandService:
    def __init__(self, repl):
        self.repl = repl

    def write_diff(self) -> None:
        if self.repl.session.pending_edit:
            self.repl.write(paint("Pending diff", Style.bold, Style.cyan, enabled=self.repl.color))
            self.repl.write(self.repl.session.pending_edit.diff.rstrip() or "(no visible diff)")
            return
        if self.repl.session.last_applied_edit:
            self.repl.write(paint("Last applied diff", Style.bold, Style.cyan, enabled=self.repl.color))
            self.repl.write(self.repl.session.last_applied_edit.diff.rstrip() or "(no visible diff)")
            return
        self.repl.write(paint("No diff available.", Style.gray, enabled=self.repl.color))

    def undo_last_edit(self):
        from pathlib import Path
        from agent.repl import ReplResult

        edit = self.repl.session.last_applied_edit
        if edit is None:
            self.repl.write(paint("No applied edit to undo.", Style.gray, enabled=self.repl.color))
            return ReplResult()

        path = Path(edit.path)
        if not path.is_absolute():
            path = self.repl.session.workspace_path / path
        path.write_text(edit.previous_content, encoding="utf-8")
        self.repl.logger.write(
            "edit_undone",
            {
                "session_id": self.repl.session.id,
                "path": edit.path,
            },
        )
        self.repl.write(paint("Undo applied.", Style.green, enabled=self.repl.color))
        self.repl.session.last_applied_edit = None
        return ReplResult()


class SecurePromptService:
    def __init__(self, repl):
        self.repl = repl

    def handle_input(self, stripped: str):
        from agent.repl import ReplResult

        state = self.repl.secure_prompt_state
        if state is None:
            return ReplResult()
        if state.mode == "setup_global_pin":
            state.pin_value = stripped
            state.mode = "setup_global_pin_confirm"
            self.repl.write(paint("credential", Style.cyan, enabled=self.repl.color) + " Confirm the PIN code.")
            return ReplResult()
        if state.mode == "setup_global_pin_confirm":
            if stripped != state.pin_value:
                self.repl.secure_prompt_state = None
                self.repl.write(paint("PIN confirmation mismatch.", Style.yellow, enabled=self.repl.color))
                return ReplResult()
            self.repl.credential_store.set_pin(state.pin_value)
            self.repl.secure_prompt_state = None
            self.repl.logger.write("pin_configured", {"session_id": self.repl.session.id})
            self.repl.write(paint("credential", Style.cyan, enabled=self.repl.color) + " PIN configured.")
            return ReplResult()
        if state.mode == "setup_api_key":
            state.secret_value = stripped
            state.mode = "setup_pin"
            self.repl.write(paint("credential", Style.cyan, enabled=self.repl.color) + " Enter the existing credential PIN code.")
            return ReplResult()
        if state.mode == "setup_pin":
            state.pin_value = stripped
            try:
                self.repl.credential_store.store_credential(state.provider, state.secret_value, state.pin_value)
            except ValueError as exc:
                self.repl.secure_prompt_state = None
                self.repl.write(paint(str(exc), Style.yellow, enabled=self.repl.color))
                return ReplResult()
            self.repl.unlocked_model_api_key = state.secret_value
            self.repl.secure_prompt_state = None
            self.repl.logger.write(
                "credential_stored",
                {
                    "session_id": self.repl.session.id,
                    "provider": state.provider,
                },
            )
            self.repl.write(paint("credential", Style.cyan, enabled=self.repl.color) + " stored and unlocked.")
            return ReplResult()
        if state.mode == "unlock_pin":
            try:
                self.repl.unlocked_model_api_key = self.repl.credential_store.unlock_credential(state.provider, stripped)
            except ValueError as exc:
                self.repl.secure_prompt_state = None
                self.repl.write(paint(str(exc), Style.yellow, enabled=self.repl.color))
                return ReplResult()
            self.repl.secure_prompt_state = None
            self.repl.logger.write(
                "credential_unlocked",
                {
                    "session_id": self.repl.session.id,
                    "provider": state.provider,
                },
            )
            self.repl.write(paint("credential", Style.cyan, enabled=self.repl.color) + " unlocked.")
            return ReplResult()
        return ReplResult()


class FollowUpService:
    def __init__(self, repl):
        self.repl = repl

    def resolve(self, stripped: str):
        from agent.repl import ReplResult

        lowered = stripped.lower().strip()
        if lowered in {"show the diff", "show diff", "show last diff", "diff that"}:
            self.repl.edit_commands.write_diff()
            return ReplResult()
        if lowered in {"undo that", "undo last edit", "revert that"}:
            return self.repl.edit_commands.undo_last_edit()
        if lowered in {"run that again", "do that again", "repeat that"} and self.repl.session.active_task:
            return self._run_task(self.repl.session.active_task)
        if lowered in {"run that test again", "repeat that test"} and self.repl.session.references.last_test_command:
            return self._run_task("run tests again")
        if lowered in {"run that command again", "repeat that command"} and self.repl.session.references.last_shell_command:
            command = self.repl.session.references.last_shell_command
            return self._run_task(f'run "{command}"')
        if lowered in {"read that again", "open that again", "show that file again"} and self.repl.session.references.last_active_path:
            path = self.repl.session.references.last_active_path
            return self._run_task(f'read "{path}"')
        return None

    def _run_task(self, task_input: str):
        from agent.repl import ReplResult

        self.repl.write(paint("task", Style.cyan, enabled=self.repl.color) + " received.")
        self.repl.agent_loop.run_task(
            session=self.repl.session,
            task_input=task_input,
            on_plan=self.repl.render_plan,
            on_tool_result=self.repl.handle_tool_result,
            on_approval=self.repl.prompt_approval,
            on_summary=self.repl.render_summary,
            on_state_change=self.repl.set_loop_state,
            on_heartbeat=self.repl.handle_heartbeat,
            on_memories_loaded=self.repl.handle_loaded_memories,
            on_memories_learned=self.repl.handle_learned_memories,
        )
        return ReplResult()


class TaskInteractionService:
    def __init__(self, repl):
        self.repl = repl

    def start_task(self, task_input: str):
        from agent.repl import ReplResult

        self.repl.logger.write(
            "task_received",
            {
                "session_id": self.repl.session.id,
                "task": task_input,
                "loop_state": self.repl.session.loop_state,
            },
        )
        self.repl.write(paint("task", Style.cyan, enabled=self.repl.color) + " received.")
        self.repl.agent_loop.run_task(
            session=self.repl.session,
            task_input=task_input,
            on_plan=self.repl.render_plan,
            on_tool_result=self.repl.handle_tool_result,
            on_approval=self.repl.prompt_approval,
            on_summary=self.repl.render_summary,
            on_state_change=self.repl.set_loop_state,
            on_heartbeat=self.repl.handle_heartbeat,
            on_memories_loaded=self.repl.handle_loaded_memories,
            on_memories_learned=self.repl.handle_learned_memories,
        )
        return ReplResult()

    def render_plan(self, plan) -> None:
        self.repl.write(paint("Plan", Style.bold, Style.cyan, enabled=self.repl.color))
        self.repl.status_commands.write_status_row("status", plan.status)
        for index, step in enumerate(plan.steps, start=1):
            title = paint(f"{index}. {step.title}", Style.green, enabled=self.repl.color)
            self.repl.write(f"  {title}")
            self.repl.status_commands.write_status_row("tool", step.tool_name)
            self.repl.status_commands.write_status_row("step", step.status)
            self.repl.status_commands.write_status_row("why", step.rationale)

    def render_summary(self, summary: str) -> None:
        self.repl.write(paint("Summary", Style.bold, Style.cyan, enabled=self.repl.color))
        self.repl.write(summary)

    def set_loop_state(self, state: str) -> None:
        self.repl.session.loop_state = state
        if state in {"completed", "failed", "cancelled", "idle"}:
            self.repl.session.cancellation_requested = False
            self.repl._last_heartbeat_line = None
        self.repl.logger.write(
            "loop_state_changed",
            {
                "session_id": self.repl.session.id,
                "state": state,
            },
        )

    def handle_heartbeat(self, event) -> None:
        self.repl.session.latest_heartbeat = event
        heartbeat_line = self.repl.renderer.render_heartbeat(event)
        if (
            heartbeat_line != self.repl._last_heartbeat_line
            or event.log_to_file
            or event.loop_state in {"completed", "failed", "cancelled"}
            or event.unhealthy
        ):
            self.repl.write(heartbeat_line)
            self.repl._last_heartbeat_line = heartbeat_line
        if event.log_to_file:
            self.repl.logger.write(
                "heartbeat",
                {
                    "session_id": event.session_id,
                    "task_id": event.task_id,
                    "loop_state": event.loop_state,
                    "active_step_title": event.active_step_title,
                    "active_tool": event.active_tool,
                    "elapsed_ms": event.elapsed_ms,
                    "cancellable": event.cancellable,
                    "message": event.message,
                    "unhealthy": event.unhealthy,
                },
            )

    def prompt_approval(self, approval) -> None:
        self.repl.session.pending_approval = approval
        self.repl.session.references.last_approval_target = approval.command_or_path
        if approval.action_type == "filesystem.write":
            self.repl.session.pending_edit = PendingEdit(
                path=approval.command_or_path,
                diff=approval.preview_diff,
                previous_content=str(approval.tool_request.args.get("__previous_content", "")),
                new_content=str(approval.tool_request.args.get("content", "")),
                tool_request=approval.tool_request,
            )
        self.repl.write(paint("Approval required", Style.yellow, Style.bold, enabled=self.repl.color))
        self.repl.status_commands.write_status_row("action", approval.action_type)
        self.repl.status_commands.write_status_row("target", approval.command_or_path)
        self.repl.status_commands.write_status_row("risk", approval.risk_level)
        self.repl.status_commands.write_status_row("reason", approval.reason)
        self.repl.status_commands.write_status_row("effect", approval.expected_effect)
        self.repl.write(
            paint("/approve", Style.green, enabled=self.repl.color)
            + " or "
            + paint("/deny", Style.yellow, enabled=self.repl.color)
        )
        if approval.preview_diff:
            self.repl.write(paint("Preview diff", Style.bold, Style.cyan, enabled=self.repl.color))
            self.repl.write(approval.preview_diff.rstrip() or "(no visible diff)")
        self.repl.logger.write(
            "approval_required",
            {
                "session_id": self.repl.session.id,
                "approval_id": approval.id,
                "action_type": approval.action_type,
                "target": approval.command_or_path,
                "risk_level": approval.risk_level,
                "reason": approval.reason,
            },
        )

    def record_tool_result(self, result) -> None:
        self.repl.session.recent_tool_results.append(result)
        self.repl.session.references.last_tool_name = result.tool_name
        if result.tool_name == "shell.run":
            command = result.input.get("command")
            if isinstance(command, str) and command:
                self.repl.session.references.last_shell_command = command
                if "pytest" in command or "test" in command.lower():
                    self.repl.session.references.last_test_command = command
        self.repl.logger.write(
            "tool_result",
            {
                "session_id": self.repl.session.id,
                "tool_name": result.tool_name,
                "status": result.status,
                "risk_level": result.risk_level,
                "requires_approval": result.requires_approval,
                "artifacts": result.artifacts,
            },
        )

    def render_tool_result(self, result) -> None:
        for line in self.repl.renderer.render_tool_activity(result):
            self.repl.write(line)

    def handle_tool_result(self, result) -> None:
        path = result.input.get("path") or result.artifacts.get("path")
        if isinstance(path, str) and path:
            compact_path = Path(path).name if Path(path).is_absolute() else path
            self.repl.session.references.last_active_path = compact_path
            self.repl.session.references.last_diff_path = compact_path
        self.record_tool_result(result)
        self.render_tool_result(result)

    def handle_loaded_memories(self, records) -> None:
        if not records:
            return
        self.repl.logger.write(
            "memories_loaded",
            {
                "session_id": self.repl.session.id,
                "task_id": self.repl.session.current_task_id,
                "memory_ids": [record.id for record in records],
            },
        )
        self.repl.write(
            paint("memory", Style.magenta, enabled=self.repl.color)
            + f" loaded {len(records)} relevant item(s)."
        )

    def handle_learned_memories(self, records) -> None:
        if not records:
            return
        self.repl.logger.write(
            "memories_learned",
            {
                "session_id": self.repl.session.id,
                "task_id": self.repl.session.current_task_id,
                "memory_ids": [record.id for record in records],
            },
        )
        self.repl.write(
            paint("learned", Style.magenta, enabled=self.repl.color)
            + f" stored {len(records)} safe memory item(s)."
        )
