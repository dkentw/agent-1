"""Reflection service for safe Phase 7 memory writes."""

from __future__ import annotations

from dataclasses import dataclass

from agent.memory import MemoryRecord, MemoryService
from agent.planner import Plan
from agent.sensitive_data import contains_sensitive_data
from agent.workspace import WorkspaceContext


@dataclass(frozen=True)
class MemoryProposal:
    type: str
    scope: str
    content: str
    summary: str
    confidence: float
    reliability_score: float
    tags: tuple[str, ...] = ()
    review_required: bool = False


class ReflectionService:
    def propose(
        self,
        *,
        task_input: str,
        plan: Plan,
        workspace_context: WorkspaceContext | None,
    ) -> list[MemoryProposal]:
        if plan.status != "completed":
            return []

        proposals: list[MemoryProposal] = []
        if workspace_context and workspace_context.package_manager:
            proposals.append(
                MemoryProposal(
                    type="project_fact",
                    scope="workspace",
                    content=f"Workspace package manager: {workspace_context.package_manager}",
                    summary=f"Workspace uses {workspace_context.package_manager}",
                    confidence=0.8,
                    reliability_score=0.8,
                    tags=("workspace", workspace_context.package_manager),
                )
            )
        if workspace_context:
            for command in workspace_context.test_commands[:2]:
                proposals.append(
                    MemoryProposal(
                        type="project_fact",
                        scope="workspace",
                        content=f"Likely test command: {command}",
                        summary=f"Use test command {command}",
                        confidence=0.85,
                        reliability_score=0.85,
                        tags=("tests", "workspace"),
                    )
                )

        for step in plan.steps:
            path = str(step.args.get("path", "")).strip()
            if step.status != "completed" or not path:
                continue
            if step.tool_name == "filesystem.read":
                proposals.append(
                    MemoryProposal(
                        type="project_fact",
                        scope="workspace",
                        content=f"Useful file for repo inspection: {path}",
                        summary=f"Inspect {path} for repository context",
                        confidence=0.65,
                        reliability_score=0.7,
                        tags=("file", path.lower()),
                    )
                )
            if step.tool_name == "filesystem.write":
                proposals.append(
                    MemoryProposal(
                        type="workflow_fact",
                        scope="workspace",
                        content=f"Previous task successfully updated {path}",
                        summary=f"Edits have been applied to {path}",
                        confidence=0.6,
                        reliability_score=0.65,
                        tags=("edit", path.lower()),
                    )
                )

        deduped: list[MemoryProposal] = []
        seen = set()
        for proposal in proposals:
            key = (proposal.type, proposal.scope, proposal.summary)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(proposal)
        return deduped

    def store_safe_proposals(
        self,
        *,
        memory_service: MemoryService,
        task_id: str,
        task_input: str,
        plan: Plan,
        workspace_context: WorkspaceContext | None,
    ) -> tuple[list[MemoryRecord], list[MemoryProposal]]:
        stored: list[MemoryRecord] = []
        rejected: list[MemoryProposal] = []
        for proposal in self.propose(
            task_input=task_input,
            plan=plan,
            workspace_context=workspace_context,
        ):
            if proposal.review_required or contains_sensitive_data(
                task_input,
                proposal.summary,
                proposal.content,
            ):
                rejected.append(proposal)
                continue
            stored.append(
                memory_service.create_or_update(
                    type=proposal.type,
                    scope=proposal.scope,
                    content=proposal.content,
                    summary=proposal.summary,
                    source_task_id=task_id,
                    confidence=proposal.confidence,
                    reliability_score=proposal.reliability_score,
                    tags=proposal.tags,
                )
            )
        return stored, rejected
