from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class ExecutionContext:
    page: object
    variables: dict
    downloads_dir: Path
    dry_run: bool = False
    emit: Callable[[dict], None] | None = None
    resolver: object | None = None
    artifacts: list[dict] = field(default_factory=list)
    current_step_id: str | None = None

    def __post_init__(self):
        self.downloads_dir = Path(self.downloads_dir)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)

    def event(self, event_type: str, **payload) -> None:
        if self.emit is not None:
            self.emit({"type": event_type, **payload})

    def resolve(self, value):
        if self.resolver is None:
            return value
        return self.resolver.resolve(value)

    def checkpoint(self, *, step_id: str, step_index: int, status: str) -> None:
        self.event(
            "checkpoint",
            step_id=step_id,
            step_index=step_index,
            status=status,
        )
