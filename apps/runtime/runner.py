from dataclasses import dataclass

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

            if context.auth_guard is not None:
                context.page = context.auth_guard.ensure_authenticated(context.page)

            context.current_step_id = step["id"]
            context.event(
                "step.started",
                step_id=step["id"],
                step_index=index,
                action=step["action"],
            )

            try:
                self.registry.execute(step["action"], step, context)
            except Exception as exc:
                context.checkpoint(
                    step_id=step["id"],
                    step_index=index,
                    status="FAILED",
                )
                context.event(
                    "step.failed",
                    step_id=step["id"],
                    step_index=index,
                    error_type=type(exc).__name__,
                )
                return RunResult(
                    completed_steps=completed,
                    failed_step_id=step["id"],
                    error=str(exc),
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
