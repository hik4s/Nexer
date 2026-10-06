import hashlib
from pathlib import Path, PurePath


class ActionExecutionError(RuntimeError):
    """Raised when a runtime action cannot be completed safely."""


class ActionRegistry:
    def __init__(self):
        self._actions = {}

    def register(self, name: str, action) -> None:
        if not name or not name.strip():
            raise ValueError("Action name is required")
        self._actions[name] = action

    def execute(self, name: str, step: dict, context) -> object:
        action = self._actions.get(name)
        if action is None:
            raise ActionExecutionError(f"UNKNOWN_ACTION:{name}")
        return action(step, context)


def create_default_registry() -> ActionRegistry:
    registry = ActionRegistry()
    registry.register("navigate", _navigate)
    registry.register("click", _click)
    registry.register("fill", _fill)
    registry.register("select", _select)
    registry.register("press", _press)
    registry.register("wait_for", _wait_for)
    registry.register("wait_for_any", _wait_for_any)
    registry.register("switch_tab", _switch_tab)
    registry.register("download", _download)
    registry.register("validate_file", _validate_file)
    return registry


def _navigate(step, context):
    url = context.resolve(step["url"])
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ActionExecutionError("UNSAFE_URL")

    context.event("action.started", action="navigate", step_id=step["id"])
    if not context.dry_run:
        context.page.goto(
            url,
            wait_until=step.get("wait_until", "domcontentloaded"),
            timeout=step.get("timeout_ms", 30000),
        )
    context.event("action.finished", action="navigate", step_id=step["id"])
    return url


def _click(step, context):
    selector = context.resolve(step["selector"])
    context.event("action.started", action="click", step_id=step["id"])
    if not context.dry_run:
        context.page.locator(selector).click(
            timeout=step.get("timeout_ms", 30000)
        )
    context.event("action.finished", action="click", step_id=step["id"])


def _fill(step, context):
    selector = context.resolve(step["selector"])
    value = context.resolve(step["value"])
    context.event("action.started", action="fill", step_id=step["id"])
    if not context.dry_run:
        context.page.locator(selector).fill(
            str(value),
            timeout=step.get("timeout_ms", 30000),
        )
    context.event("action.finished", action="fill", step_id=step["id"])


def _select(step, context):
    selector = context.resolve(step["selector"])
    value = context.resolve(step["value"])
    context.event("action.started", action="select", step_id=step["id"])
    if not context.dry_run:
        context.page.locator(selector).select_option(str(value))
    context.event("action.finished", action="select", step_id=step["id"])


def _press(step, context):
    selector = context.resolve(step["selector"])
    value = context.resolve(step.get("key", "Enter"))
    context.event("action.started", action="press", step_id=step["id"])
    if not context.dry_run:
        context.page.locator(selector).press(
            str(value),
            timeout=step.get("timeout_ms", 30000),
        )
    context.event("action.finished", action="press", step_id=step["id"])


def _wait_for(step, context):
    selector = context.resolve(step["selector"])
    state = step.get("state", "visible")
    timeout = step.get("timeout_ms", 30000)
    context.event("action.started", action="wait_for", step_id=step["id"])
    if not context.dry_run:
        context.page.locator(selector).wait_for(state=state, timeout=timeout)
    context.event("action.finished", action="wait_for", step_id=step["id"])


def _wait_for_any(step, context):
    selectors = [context.resolve(item) for item in step["selectors"]]
    timeout = step.get("timeout_ms", 30000)
    state = step.get("state", "visible")
    context.event("action.started", action="wait_for_any", step_id=step["id"])

    if not context.dry_run:
        deadline = context.page.timeouts if False else None
        del deadline
        started = __import__("time").monotonic()
        while (__import__("time").monotonic() - started) * 1000 < timeout:
            for selector in selectors:
                if context.page.locator(selector).is_visible():
                    context.event(
                        "action.finished",
                        action="wait_for_any",
                        step_id=step["id"],
                        matched_selector=selector,
                    )
                    return selector
            if hasattr(context.page, "wait_for_timeout"):
                context.page.wait_for_timeout(200)
            else:
                break

        raise ActionExecutionError(
            f"WAIT_FOR_ANY_TIMEOUT:{state}"
        )

    context.event("action.finished", action="wait_for_any", step_id=step["id"])
    return selectors[0]


def _switch_tab(step, context):
    index = step["index"]
    browser_context = getattr(context.page, "context", None)
    pages = getattr(browser_context, "pages", None)
    if context.dry_run:
        context.event("action.finished", action="switch_tab", step_id=step["id"])
        return None
    if pages is None or index >= len(pages):
        raise ActionExecutionError("TAB_NOT_FOUND")
    context.page = pages[index]
    context.event("action.finished", action="switch_tab", step_id=step["id"])
    return context.page


def _download(step, context):
    selector = context.resolve(step["selector"])
    filename = context.resolve(step["filename"])
    safe_name = _safe_filename(filename)

    context.event("action.started", action="download", step_id=step["id"])
    if context.dry_run:
        context.event("action.finished", action="download", step_id=step["id"])
        return str(context.downloads_dir / safe_name)

    if not hasattr(context.page, "expect_download"):
        raise ActionExecutionError("DOWNLOAD_API_UNAVAILABLE")

    target = context.downloads_dir / safe_name
    with context.page.expect_download(timeout=step.get("timeout_ms", 30000)) as download_info:
        context.page.locator(selector).click(timeout=step.get("click_timeout_ms", 30000))
    download = download_info.value
    download.save_as(str(target))

    context.artifacts.append({"path": str(target), "type": "download"})
    context.event("action.finished", action="download", step_id=step["id"], path=str(target))
    return str(target)


def _validate_file(step, context):
    if context.dry_run:
        context.event("action.finished", action="validate_file", step_id=step["id"])
        return True

    raw_path = context.resolve(step["path"])
    path = _resolve_download_path(raw_path, context.downloads_dir)

    if not path.is_file():
        raise ActionExecutionError("FILE_NOT_FOUND")
    size = path.stat().st_size
    if size < int(step.get("min_size", 1)):
        raise ActionExecutionError("FILE_TOO_SMALL")

    extensions = {str(item).lower() for item in step.get("extensions", [])}
    if extensions and path.suffix.lower() not in extensions:
        raise ActionExecutionError("FILE_EXTENSION_NOT_ALLOWED")

    checksum = None
    if step.get("checksum") or step.get("calculate_checksum"):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        checksum = digest.hexdigest()

    if step.get("checksum") and checksum != step["checksum"]:
        raise ActionExecutionError("FILE_CHECKSUM_MISMATCH")

    artifact = {
        "path": str(path),
        "type": "validated_file",
        "size": size,
    }
    if checksum:
        artifact["checksum"] = checksum
    context.artifacts.append(artifact)
    context.event(
        "action.finished",
        action="validate_file",
        step_id=step["id"],
        path=str(path),
        size=size,
        checksum=checksum,
    )
    return artifact


def _safe_filename(filename) -> str:
    if not isinstance(filename, str) or not filename.strip():
        raise ActionExecutionError("INVALID_FILENAME")

    raw = PurePath(filename)
    if raw.is_absolute() or ".." in raw.parts or len(raw.parts) != 1:
        raise ActionExecutionError("UNSAFE_FILENAME")

    return raw.name


def _resolve_download_path(raw_path, downloads_dir: Path) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = downloads_dir / path
    resolved = path.resolve()
    root = downloads_dir.resolve()
    if resolved != root and root not in resolved.parents:
        raise ActionExecutionError("UNSAFE_PATH")
    return resolved
