import hashlib
from fnmatch import fnmatchcase
import re
import time
from download_generation import snapshot_downloads, request_download, correlated_download
from query_execution import execute_query
from outcome_wait import wait_for_outcome
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
    registry.register("wait_for_outcome", wait_for_outcome)
    registry.register("switch_tab", _switch_tab)
    registry.register("snapshot_downloads", snapshot_downloads)
    registry.register("request_download", request_download)
    registry.register("query", execute_query)
    registry.register("download", _download)
    registry.register("validate_file", _validate_file)
    registry.register("check", _check)
    registry.register("set_value", _set_value)
    registry.register("choose", _choose)
    registry.register("choose_radio", _choose_radio)
    registry.register("scroll", _scroll)
    registry.register("hover", _hover)
    registry.register("drag", _drag)
    registry.register("close_tab", _close_tab)
    return registry


def _scope(step, context):
    scope = context.page
    for selector in step.get("frames", []):
        scope = scope.frame_locator(context.resolve(selector))
    return scope


def _locator(step, context):
    return _scope(step, context).locator(context.resolve(step["selector"]))


def _control(step, context, operation):
    context.event("action.started", action=step["action"], step_id=step["id"])
    if not context.dry_run:
        operation(_locator(step, context))
    context.event("action.finished", action=step["action"], step_id=step["id"])


def _check(step, context):
    value = context.resolve(step["value"])
    if type(value) is not bool:
        raise ActionExecutionError("CHECK_VALUE_INVALID")
    _control({"action": "check", **step}, context, lambda locator: locator.set_checked(value, timeout=step.get("timeout_ms", 30000)))


def _set_value(step, context):
    value = context.resolve(step["value"])
    kind = step["input_type"]
    if not isinstance(value, str):
        raise ActionExecutionError("INPUT_VALUE_INVALID")
    if kind == "color" and not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ActionExecutionError("INPUT_VALUE_INVALID")
    if kind == "range" and not re.fullmatch(r"-?(?:\d+(?:\.\d+)?|\.\d+)", value):
        raise ActionExecutionError("INPUT_VALUE_INVALID")
    def apply(locator):
        locator.evaluate("""(element, data) => {
            if (!(element instanceof HTMLInputElement) || element.type !== data.kind || !['range', 'color'].includes(data.kind)) throw new Error('INPUT_TYPE_INVALID');
            const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
            setter.call(element, data.value);
            if (data.kind === 'range' && Number(element.value) !== Number(data.value)) throw new Error('INPUT_VALUE_OUT_OF_RANGE');
            element.dispatchEvent(new Event('input', {bubbles: true}));
            element.dispatchEvent(new Event('change', {bubbles: true}));
        }""", {"kind": kind, "value": value})
    _control({"action": "set_value", **step}, context, apply)


def _choose(step, context):
    value = context.resolve(step["value"])
    if not isinstance(value, str):
        raise ActionExecutionError("CHOICE_VALUE_INVALID")
    _control({"action": "choose", **step}, context,
             lambda locator: locator.get_by_role("option", name=value, exact=True).click(timeout=step.get("timeout_ms", 30000)))


def _choose_radio(step, context):
    value = context.resolve(step["value"])
    if not isinstance(value, str):
        raise ActionExecutionError("CHOICE_VALUE_INVALID")
    def apply(locator):
        options = locator.locator('input[type="radio"]')
        indexes = options.evaluate_all("""(elements, data) => {
            const groups = [];
            return elements.flatMap((element, index) => {
                const identity = element.name || element;
                if (!groups.includes(identity)) groups.push(identity);
                return groups.indexOf(identity) === data.group && element.value === data.value ? [index] : [];
            });
        }""", {"value": value, "group": step.get("group_index", 0)})
        if len(indexes) != 1:
            raise ActionExecutionError("RADIO_OPTION_NOT_UNIQUE")
        options.nth(indexes[0]).check(timeout=step.get("timeout_ms", 30000))
    _control({"action": "choose_radio", **step}, context, apply)


def _scroll(step, context):
    def apply(locator):
        locator.evaluate("""(element, position) => {
            const target = element === document.documentElement || element === document.body ? document.scrollingElement : element;
            target.scrollTo({left: position.x, top: position.y, behavior: 'instant'});
        }""", {"x": step["x"], "y": step["y"]})
    _control({"action": "scroll", **step}, context, apply)


def _hover(step, context):
    _control({"action": "hover", **step}, context, lambda locator: locator.hover(timeout=step.get("timeout_ms", 30000)))


def _drag(step, context):
    _control({"action": "drag", **step}, context,
             lambda locator: locator.drag_to(_scope(step, context).locator(context.resolve(step["target_selector"])), timeout=step.get("timeout_ms", 30000)))


def _close_tab(step, context):
    context.event("action.started", action="close_tab", step_id=step["id"])
    if not context.dry_run:
        browser_context = context.page.context
        if not context.page.is_closed():
            if len(browser_context.pages) < 2:
                raise ActionExecutionError("LAST_TAB_CLOSE_FORBIDDEN")
            context.page.close()
        pages = [page for page in browser_context.pages if not page.is_closed()]
        if not pages:
            raise ActionExecutionError("TAB_NOT_FOUND")
        context.page = pages[0]
    context.event("action.finished", action="close_tab", step_id=step["id"])


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
        options = {"timeout": step.get("timeout_ms", 30000)}
        for key in ("button", "click_count"):
            if key in step:
                options[key] = step[key]
        _locator(step, context).click(**options)
    context.event("action.finished", action="click", step_id=step["id"])


def _fill(step, context):
    selector = context.resolve(step["selector"])
    value = context.resolve(step["value"])
    context.event("action.started", action="fill", step_id=step["id"])
    if not context.dry_run:
        _locator(step, context).fill(
            str(value),
            timeout=step.get("timeout_ms", 30000),
        )
    context.event("action.finished", action="fill", step_id=step["id"])


def _select(step, context):
    selector = context.resolve(step["selector"])
    value = context.resolve(step["value"])
    context.event("action.started", action="select", step_id=step["id"])
    if not context.dry_run:
        _locator(step, context).select_option(value if isinstance(value, list) else str(value))
    context.event("action.finished", action="select", step_id=step["id"])


def _press(step, context):
    selector = context.resolve(step["selector"])
    value = context.resolve(step.get("key", "Enter"))
    context.event("action.started", action="press", step_id=step["id"])
    if not context.dry_run:
        _locator(step, context).press(
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
        locator = _locator(step, context)
        if state in {"enabled", "disabled"}:
            # locator.wait_for does not support enabled/disabled; use auto-polling assertions.
            from playwright.sync_api import expect
            if state == "enabled":
                expect(locator).to_be_enabled(timeout=timeout)
            else:
                expect(locator).to_be_disabled(timeout=timeout)
        else:
            locator.wait_for(state=state, timeout=timeout)
    context.event("action.finished", action="wait_for", step_id=step["id"])


def _wait_for_any(step, context):
    selectors = [context.resolve(item) for item in step["selectors"]]
    timeout = step.get("timeout_ms", 30000)
    state = step.get("state", "visible")
    context.event("action.started", action="wait_for_any", step_id=step["id"])

    if not context.dry_run:
        started = time.monotonic()
        while (time.monotonic() - started) * 1000 < timeout:
            for selector in selectors:
                if _scope(step, context).locator(selector).is_visible():
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
    deadline = time.monotonic() + step.get("timeout_ms", 30000) / 1000
    while pages is not None and index >= len(pages) and time.monotonic() < deadline:
        if context.is_cancellation_requested():
            raise ActionExecutionError("EXECUTION_CANCELLED")
        context.page.wait_for_timeout(100)
        pages = browser_context.pages
    if pages is None or index >= len(pages):
        raise ActionExecutionError("TAB_NOT_FOUND")
    context.page = pages[index]
    context.event("action.finished", action="switch_tab", step_id=step["id"])
    return context.page


def _matching_download(scope, collection, pattern):
    rows = scope.locator(collection["rows"])
    for index in range(rows.count()):
        row = rows.nth(index)
        if not row.is_visible():
            continue
        if collection["name"] == ":scope":
            name = row.evaluate("""element => {
                const copy = element.cloneNode(true);
                copy.querySelectorAll('button,a,[role="button"],input,select,textarea,script,style').forEach(node => node.remove());
                return (copy.textContent || '').replace(/\\s+/g, ' ').trim();
            }""")
        else:
            name = row.locator(collection["name"]).inner_text(timeout=1000).strip()
        if fnmatchcase(name, pattern):
            return row.locator(collection["button"])
    return None


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
    if "generation" in step:
        download = correlated_download(step, context)
    else:
        locator = _locator(step, context)
        if "collection" in step:
            collection = {key: context.resolve(value) for key, value in step["collection"].items()}
            pattern = collection["pattern"]
            if not isinstance(pattern, str) or not pattern.strip() or len(pattern) > 2048:
                raise ActionExecutionError("DOWNLOAD_PATTERN_INVALID")
            deadline = time.monotonic() + step.get("timeout_ms", 30000) / 1000
            while True:
                if context.is_cancellation_requested():
                    raise ActionExecutionError("EXECUTION_CANCELLED")
                locator = _matching_download(_scope(step, context), collection, pattern)
                if locator is not None:
                    break
                if time.monotonic() >= deadline:
                    raise ActionExecutionError("DOWNLOAD_MATCH_NOT_FOUND")
                context.page.wait_for_timeout(250)
        with context.page.expect_download(timeout=step.get("timeout_ms", 30000)) as download_info:
            locator.click(timeout=step.get("click_timeout_ms", 30000))
        download = download_info.value
    if step.get("preserve_filename"):
        target = context.downloads_dir / _safe_filename(download.suggested_filename)
        if target.exists():
            raise ActionExecutionError("DOWNLOAD_FILENAME_ALREADY_EXISTS")
    download.save_as(str(target))
    context.download_outputs[step["id"]] = target

    context.artifacts.append({"path": str(target), "type": "download"})
    context.event("action.finished", action="download", step_id=step["id"], path=str(target))
    return str(target)


def _validate_file(step, context):
    if context.dry_run:
        context.event("action.finished", action="validate_file", step_id=step["id"])
        return True

    if "source_download" in step:
        completed = context.download_outputs.get(step["source_download"])
        if completed is None:
            raise ActionExecutionError("DOWNLOAD_SOURCE_UNAVAILABLE")
        raw_path = completed
    else:
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

    # Bind validation to these bytes even when the recipe does not supply a digest.
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            if context.is_cancellation_requested():
                raise ActionExecutionError("EXECUTION_CANCELLED")
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
