from dataclasses import dataclass
import time

from actions import ActionExecutionError, create_default_registry
from recipe import validate_recipe
from resolver import VariableResolver


@dataclass(frozen=True)
class RunResult:
    completed_steps: int
    failed_step_id: str | None
    error: str | None = None
    cancelled: bool = False


class RecipeRunner:
    def __init__(self, registry=None):
        self.registry = registry or create_default_registry()

    def run(self, recipe: dict, context) -> RunResult:
        validated = validate_recipe(recipe)
        resolver = VariableResolver(
            declarations=validated.get("variables", {}),
            values=context.variables,
            secret_provider=context.secret_provider,
        )
        resolver.validate_required()
        context.resolver = resolver

        completed = 0

        for index, step in enumerate(validated["steps"]):
            if context.is_cancellation_requested():
                context.checkpoint(
                    step_id=step["id"],
                    step_index=index,
                    status="CANCELLED",
                )
                return RunResult(
                    completed_steps=completed,
                    failed_step_id=None,
                    cancelled=True,
                )

            context.current_step_id = step["id"]
            context.event(
                "step.started",
                step_id=step["id"],
                step_index=index,
                action=step["action"],
            )

            retry = step.get("retry") or {}
            max_attempts = retry.get("max_attempts", 1)
            backoff_ms = retry.get("backoff_ms", 0)
            step_succeeded = False
            last_error: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                if context.auth_guard is not None:
                    context.page = context.auth_guard.ensure_authenticated(context.page)
                try:
                    self.registry.execute(step["action"], step, context)
                    step_succeeded = True
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt >= max_attempts:
                        break

                    context.event(
                        "step.retrying",
                        step_id=step["id"],
                        step_index=index,
                        attempt=attempt,
                        next_attempt=attempt + 1,
                        error_type=type(exc).__name__,
                    )

                    if context.is_cancellation_requested():
                        context.checkpoint(
                            step_id=step["id"],
                            step_index=index,
                            status="CANCELLED",
                        )
                        return RunResult(
                            completed_steps=completed,
                            failed_step_id=None,
                            cancelled=True,
                        )

                    if backoff_ms:
                        time.sleep(backoff_ms / 1000)

            if not step_succeeded:
                context.checkpoint(
                    step_id=step["id"],
                    step_index=index,
                    status="FAILED",
                )
                context.event(
                    "step.failed",
                    step_id=step["id"],
                    step_index=index,
                    error_type=type(last_error).__name__ if last_error else "RUNTIME_ERROR",
                )
                return RunResult(
                    completed_steps=completed,
                    failed_step_id=step["id"],
                    error=str(last_error) if last_error else "RUNTIME_ERROR",
                )

            completed += 1
            context.checkpoint(
                step_id=step["id"],
                step_index=index,
                status="SUCCEEDED",
            )
            context.event(
                "step.finished",
                step_id=step["id"],
                step_index=index,
                action=step["action"],
            )

        return RunResult(completed_steps=completed, failed_step_id=None)
