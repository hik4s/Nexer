from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from resolver import VariableResolver


@dataclass
class ExecutionContext:
    page: object
    variables: dict
    downloads_dir: Path
    dry_run: bool = False
    emit: Callable[[dict], None] | None = None
    resolver: object | None = None
    secret_provider: object | None = None
    artifacts: list[dict] = field(default_factory=list)
    current_step_id: str | None = None
    cancellation_requested: Callable[[], bool] | None = None

    def __post_init__(self):
        self.downloads_dir = Path(self.downloads_dir)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        if self.resolver is None:
            declarations = {
                name: {
                    "type": _infer_type(value),
                    "required": True,
                }
                for name, value in self.variables.items()
            }
            self.resolver = VariableResolver(
                declarations=declarations,
                values=self.variables,
                secret_provider=self.secret_provider,
            )

    def event(self, event_type: str, **payload) -> None:
        if self.emit is not None:
            self.emit({"type": event_type, **payload})

    def resolve(self, value):
        return self.resolver.resolve(value)

    def is_cancellation_requested(self) -> bool:
        return bool(self.cancellation_requested and self.cancellation_requested())

    def checkpoint(self, *, step_id: str, step_index: int, status: str) -> None:
        self.event(
            "checkpoint",
            step_id=step_id,
            step_index=step_index,
            status=status,
        )


def _infer_type(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"
