"""
AgentOrchestrator — sequential multi-step pipeline runner.
Each step function receives (context: AgentContext) and returns
an updated AgentContext. Steps run one at a time, in order.
No human input required between steps.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

StepFn = Callable[["AgentContext"], Awaitable[Optional["AgentContext"]]]


def _now_ist() -> str:
    return datetime.now(IST).isoformat()


@dataclass
class AgentStep:
    """Represents one step in an agent pipeline."""

    name: str
    description: str
    fn: StepFn


@dataclass
class StepResult:
    """Output of a single completed step."""

    step_name: str
    description: str
    status: str
    duration_ms: int
    output_summary: str
    error: Optional[str] = None


@dataclass
class AgentContext:
    """
    Shared state passed between all steps in a pipeline.
    Each step reads from it and adds to it.
    """

    pipeline_name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    portfolio: dict = field(default_factory=dict)
    raw_data: dict = field(default_factory=dict)
    signals: list = field(default_factory=list)
    enriched: list = field(default_factory=list)
    personalised: list = field(default_factory=list)
    alerts: list = field(default_factory=list)
    video_path: Optional[str] = None
    narration: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    step_results: list[StepResult] = field(default_factory=list)
    started_at: str = field(default_factory=_now_ist)


@dataclass
class AgentRun:
    """The complete result of an agent pipeline run."""

    run_id: str
    pipeline_name: str
    status: str
    steps: list[StepResult]
    context: AgentContext
    total_ms: int
    completed_at: str


class AgentMemory:
    """Stores context snapshots after each step for fallback and traceability."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.snapshots: list[dict[str, Any]] = []

    def remember(self, step_name: str, ctx: AgentContext) -> None:
        snapshot = {
            field_name: copy.deepcopy(getattr(ctx, field_name))
            for field_name in AgentContext.__dataclass_fields__
        }
        self.snapshots.append(
            {
                "step_name": step_name,
                "captured_at": _now_ist(),
                "context": snapshot,
            }
        )


class AgentOrchestrator:
    """
    Runs a sequence of async step functions, tracking results
    and emitting structured log events for the frontend trace panel.
    """

    def __init__(self, pipeline_name: str, steps: list[AgentStep]):
        self.pipeline_name = pipeline_name
        self.steps = steps
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to real-time step events. Returns an async queue."""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Remove a previously subscribed queue."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    async def _emit(self, event: dict[str, Any]) -> None:
        """Broadcast an event to all subscribers."""
        for queue in list(self._subscribers):
            await queue.put(event)

    @staticmethod
    def _snapshot_context(ctx: AgentContext) -> dict[str, Any]:
        return {
            field_name: copy.deepcopy(getattr(ctx, field_name))
            for field_name in AgentContext.__dataclass_fields__
        }

    @staticmethod
    def _hydrate_context(target: AgentContext, snapshot: dict[str, Any]) -> AgentContext:
        for field_name in AgentContext.__dataclass_fields__:
            if field_name in snapshot:
                setattr(target, field_name, copy.deepcopy(snapshot[field_name]))
        return target

    async def run(
        self,
        portfolio: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> AgentRun:
        """
        Execute all steps sequentially. Zero human input required.
        If a step fails, the pipeline keeps moving using the previous step's
        context snapshot as fallback.
        """

        ctx = AgentContext(
            pipeline_name=self.pipeline_name,
            portfolio=copy.deepcopy(portfolio or {}),
        )
        if metadata:
            ctx.metadata.update(copy.deepcopy(metadata))

        memory = AgentMemory(ctx.run_id)
        pipeline_start = time.perf_counter()

        await self._emit(
            {
                "type": "pipeline_start",
                "pipeline": self.pipeline_name,
                "run_id": ctx.run_id,
                "total_steps": len(self.steps),
                "timestamp": ctx.started_at,
            }
        )

        for step_index, step in enumerate(self.steps):
            step_start = time.perf_counter()
            previous_snapshot = self._snapshot_context(ctx)

            await self._emit(
                {
                    "type": "step_start",
                    "run_id": ctx.run_id,
                    "step_index": step_index,
                    "step_number": step_index + 1,
                    "step_name": step.name,
                    "description": step.description,
                }
            )

            try:
                returned_ctx = await step.fn(ctx)
                if returned_ctx is not None:
                    if not isinstance(returned_ctx, AgentContext):
                        raise TypeError(
                            f"Step '{step.name}' returned {type(returned_ctx).__name__}, "
                            "expected AgentContext or None."
                        )
                    if returned_ctx is not ctx:
                        self._hydrate_context(ctx, self._snapshot_context(returned_ctx))

                duration_ms = int((time.perf_counter() - step_start) * 1000)
                summary = str(
                    ctx.metadata.get(f"step_{step_index}_summary")
                    or ctx.metadata.get(f"step_{step.name}_summary")
                    or "Step completed successfully."
                )
                result = StepResult(
                    step_name=step.name,
                    description=step.description,
                    status="success",
                    duration_ms=duration_ms,
                    output_summary=summary,
                )
                ctx.step_results.append(result)
                memory.remember(step.name, ctx)

                event = {
                    "type": "step_complete",
                    "run_id": ctx.run_id,
                    "step_index": step_index,
                    "step_number": step_index + 1,
                    "step_name": step.name,
                    "status": "success",
                    "duration_ms": duration_ms,
                    "output_summary": summary,
                }
                await self._emit(event)
                logger.info(
                    "agent.step_complete",
                    extra={
                        "pipeline": self.pipeline_name,
                        "run_id": ctx.run_id,
                        "step_name": step.name,
                        "status": "success",
                        "duration_ms": duration_ms,
                    },
                )
            except Exception as exc:
                self._hydrate_context(ctx, previous_snapshot)
                duration_ms = int((time.perf_counter() - step_start) * 1000)
                error_msg = str(exc)

                result = StepResult(
                    step_name=step.name,
                    description=step.description,
                    status="failed",
                    duration_ms=duration_ms,
                    output_summary="Step failed; continuing with previous output.",
                    error=error_msg,
                )
                ctx.step_results.append(result)
                memory.remember(f"{step.name}:fallback", ctx)

                event = {
                    "type": "step_complete",
                    "run_id": ctx.run_id,
                    "step_index": step_index,
                    "step_number": step_index + 1,
                    "step_name": step.name,
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "error": error_msg,
                    "output_summary": result.output_summary,
                }
                await self._emit(event)
                logger.exception(
                    "agent.step_failed",
                    extra={
                        "pipeline": self.pipeline_name,
                        "run_id": ctx.run_id,
                        "step_name": step.name,
                        "status": "failed",
                        "duration_ms": duration_ms,
                    },
                )

        total_ms = int((time.perf_counter() - pipeline_start) * 1000)
        all_ok = all(step.status == "success" for step in ctx.step_results)
        any_ok = any(step.status == "success" for step in ctx.step_results)
        run_status = "complete" if all_ok else "partial" if any_ok else "failed"

        run = AgentRun(
            run_id=ctx.run_id,
            pipeline_name=self.pipeline_name,
            status=run_status,
            steps=list(ctx.step_results),
            context=ctx,
            total_ms=total_ms,
            completed_at=_now_ist(),
        )

        await self._emit(
            {
                "type": "pipeline_complete",
                "run_id": ctx.run_id,
                "pipeline": self.pipeline_name,
                "status": run_status,
                "total_ms": total_ms,
                "alert_count": len(ctx.alerts),
                "timestamp": run.completed_at,
            }
        )
        logger.info(
            "agent.pipeline_complete",
            extra={
                "pipeline": self.pipeline_name,
                "run_id": ctx.run_id,
                "status": run_status,
                "total_ms": total_ms,
                "steps": len(self.steps),
            },
        )
        return run
