import re
from copy import deepcopy
from field_schema import validate_field
from download_contract import validate_generation_steps, validate_collection
from query_contract import validate_query_step


KNOWN_ACTIONS = {
    "navigate",
    "click",
    "fill",
    "select",
    "press",
    "wait_for",
    "wait_for_any",
    "wait_for_outcome",
    "switch_tab",
    "download",
    "validate_file",
    "check", "set_value", "choose", "choose_radio", "scroll", "hover", "drag", "close_tab",
    "snapshot_downloads", "request_download", "query",
}

_VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")


class RecipeValidationError(ValueError):
    """Raised when a declarative recipe is not safe or structurally valid."""


def validate_recipe(recipe: dict) -> dict:
    if not isinstance(recipe, dict):
        raise RecipeValidationError("RECIPE_OBJECT_REQUIRED")

    normalized = deepcopy(recipe)
    profile = normalized.get("login_profile")
    if profile is not None and (not isinstance(profile, dict) or set(profile) != {"id", "version"}
        or any(type(value) is not int or value < 1 for value in profile.values())):
        raise RecipeValidationError("LOGIN_PROFILE_REFERENCE_INVALID")

    if normalized.get("schema_version") != 1:
        raise RecipeValidationError("UNSUPPORTED_SCHEMA_VERSION")

    name = normalized.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RecipeValidationError("RECIPE_NAME_REQUIRED")

    if "site_url" in normalized:
        from site_urls import validate_site_url
        try:
            normalized["site_url"] = validate_site_url(normalized["site_url"])
        except ValueError:
            raise RecipeValidationError("SITE_URL_INVALID") from None

    variables = normalized.get("variables", {})
    if not isinstance(variables, dict):
        raise RecipeValidationError("VARIABLES_OBJECT_REQUIRED")
    if any(not isinstance(declaration, dict) for declaration in variables.values()):
        raise RecipeValidationError("VARIABLE_DECLARATION_INVALID")
    if profile is not None and ("authentication" in normalized or any(declaration.get("secret") for declaration in variables.values())):
        raise RecipeValidationError("LOGIN_PROFILE_CONTRACT_CONFLICT")
    for declaration in variables.values():
        if "label" in declaration and (not isinstance(declaration["label"], str) or len(declaration["label"]) > 100):
            raise RecipeValidationError("VARIABLE_LABEL_INVALID")
        if "field" in declaration:
            try:
                validate_field(declaration["field"])
            except ValueError:
                raise RecipeValidationError("FIELD_SCHEMA_INVALID") from None

    steps = normalized.get("steps")
    if not isinstance(steps, list) or not steps:
        raise RecipeValidationError("STEPS_REQUIRED")

    output = normalized.get("output")
    if not isinstance(output, dict) or output.get("type") not in {"file", "none"}:
        raise RecipeValidationError("FILE_OUTPUT_REQUIRED")

    seen_ids: set[str] = set()
    previous_actions: dict[str, str] = {}
    declared = set(variables)

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise RecipeValidationError(f"STEP_OBJECT_REQUIRED:{index}")

        step_id = step.get("id")
        if not isinstance(step_id, str) or not step_id.strip():
            raise RecipeValidationError(f"STEP_ID_REQUIRED:{index}")
        if step_id in seen_ids:
            raise RecipeValidationError(f"DUPLICATE_STEP_ID:{step_id}")
        seen_ids.add(step_id)

        action = step.get("action")
        if action not in KNOWN_ACTIONS:
            raise RecipeValidationError(f"UNKNOWN_ACTION:{action}")

        _validate_step_requirements(action, step)
        if action == "wait_for_outcome":
            previous = steps[index - 1] if index else None
            if not isinstance(previous, dict) or previous.get("action") != "click" or step["after_step_id"] != previous.get("id"):
                raise RecipeValidationError("OUTCOME_PREDECESSOR_INVALID")
            if (previous.get("retry") or {}).get("max_attempts", 1) > 1:
                raise RecipeValidationError("OUTCOME_RETRY_FORBIDDEN")
        if action == "validate_file" and "source_download" in step:
            if previous_actions.get(step["source_download"]) != "download":
                raise RecipeValidationError("FILE_VALIDATION_SOURCE_INVALID")
        previous_actions[step_id] = action
        _validate_retry(step)

        for value in step.values():
            for variable in _find_variables(value):
                if variable not in declared:
                    raise RecipeValidationError(
                        f"UNDECLARED_VARIABLE:{variable}"
                    )

    try:
        validate_generation_steps(steps)
    except ValueError as exc:
        raise RecipeValidationError(str(exc)) from None

    authentication = normalized.get("authentication")
    if authentication is not None:
        _validate_authentication(authentication)

    expected_extension = output.get("expected_extension")
    if expected_extension is not None:
        if (
            not isinstance(expected_extension, str)
            or not expected_extension.startswith(".")
        ):
            raise RecipeValidationError("INVALID_EXPECTED_EXTENSION")

    return normalized


def _validate_authentication(authentication: dict) -> None:
    if not isinstance(authentication, dict):
        raise RecipeValidationError("AUTHENTICATION_CONFIG_INVALID")

    session_ref = authentication.get("session_ref")
    if session_ref is not None:
        if not isinstance(session_ref, str) or not re.fullmatch(
            r"[A-Za-z0-9_.:-]{1,200}",
            session_ref,
        ):
            raise RecipeValidationError("INVALID_SESSION_REFERENCE")

    login_selectors = authentication.get("login_selectors")
    if (
        not isinstance(login_selectors, list)
        or not login_selectors
        or not all(isinstance(item, str) and item.strip() for item in login_selectors)
    ):
        raise RecipeValidationError("AUTH_LOGIN_SELECTORS_REQUIRED")

    renewal = authentication.get("renewal")
    if renewal is None:
        return
    if not isinstance(renewal, dict):
        raise RecipeValidationError("AUTH_RENEWAL_CONFIG_INVALID")

    required = (
        "login_url",
        "username_selector",
        "password_selector",
        "submit_selector",
        "success_selector",
        "username_ref",
        "password_ref",
    )
    for key in required:
        value = renewal.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RecipeValidationError("AUTH_RENEWAL_CONFIG_INVALID")

    if not renewal["login_url"].startswith(("http://", "https://")):
        raise RecipeValidationError("AUTH_RENEWAL_CONFIG_INVALID")


def _validate_retry(step: dict) -> None:
    retry = step.get("retry")
    if retry is None:
        return
    if not isinstance(retry, dict):
        raise RecipeValidationError("RETRY_CONFIG_INVALID")

    max_attempts = retry.get("max_attempts", 1)
    backoff_ms = retry.get("backoff_ms", 0)

    if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
        raise RecipeValidationError("RETRY_MAX_ATTEMPTS_INVALID")
    if type(backoff_ms) is not int or not 0 <= backoff_ms <= 60000:
        raise RecipeValidationError("RETRY_BACKOFF_INVALID")


def _validate_step_requirements(action: str, step: dict) -> None:
    if action == "wait_for_outcome":
        required = {"id", "action", "after_step_id", "ready_selector", "ready_state", "timeout_ms", "learning"}
        optional = {"busy_selector", "error_selector", "retry"}
        if not required.issubset(step) or set(step) - (required | optional):
            raise RecipeValidationError("OUTCOME_CONTRACT_INVALID")
        for key in ("after_step_id", "ready_selector", "busy_selector", "error_selector"):
            if key in step and (not isinstance(step[key], str) or not step[key].strip() or len(step[key]) > 2048):
                raise RecipeValidationError("OUTCOME_CONTRACT_INVALID")
        if step["ready_state"] not in {"visible", "enabled"}:
            raise RecipeValidationError("OUTCOME_CONTRACT_INVALID")
        retry = step.get("retry") or {}
        if not isinstance(retry, dict):
            raise RecipeValidationError("RETRY_CONFIG_INVALID")
        if retry.get("max_attempts", 1) > 1:
            raise RecipeValidationError("OUTCOME_RETRY_FORBIDDEN")
        if "frames" in step or any("{{" in step[key] for key in ("ready_selector", "busy_selector", "error_selector") if key in step):
            raise RecipeValidationError("OUTCOME_CONTRACT_INVALID")
    if action == "validate_file":
        has_path = "path" in step
        has_source = "source_download" in step
        if has_path == has_source:
            raise RecipeValidationError("FILE_VALIDATION_SOURCE_INVALID")
        reference = step["path" if has_path else "source_download"]
        if not isinstance(reference, str) or not reference.strip():
            raise RecipeValidationError("FILE_VALIDATION_SOURCE_INVALID")
        return
    if action == 'query':
        try:
            validate_query_step(step)
        except ValueError as exc:
            raise RecipeValidationError(str(exc)) from None
        return
    frames = step.get("frames", [])
    if not isinstance(frames, list) or len(frames) > 16 or any(not isinstance(item, str) or not item.strip() for item in frames):
        raise RecipeValidationError("FRAME_SELECTORS_INVALID")
    if action == "click":
        if step.get("button", "left") not in {"left", "right", "middle"} or type(step.get("click_count", 1)) is not int or not 1 <= step.get("click_count", 1) <= 3:
            raise RecipeValidationError("CLICK_OPTIONS_INVALID")
    if action == "wait_for":
        if step.get("state", "visible") not in {"visible", "hidden", "attached", "detached", "enabled", "disabled"}:
            raise RecipeValidationError("WAIT_STATE_INVALID")
    if action == "scroll":
        if any(type(step.get(key)) is not int or not 0 <= step[key] <= 10000000 for key in ("x", "y")):
            raise RecipeValidationError("SCROLL_POSITION_INVALID")
    if action == "drag" and (not isinstance(step.get("target_selector"), str) or not step["target_selector"].strip()):
        raise RecipeValidationError("DRAG_TARGET_REQUIRED")
    if action == "set_value" and step.get("input_type") not in {"range", "color"}:
        raise RecipeValidationError("INPUT_TYPE_INVALID")
    if action == "choose_radio" and (type(step.get("group_index", 0)) is not int or not 0 <= step.get("group_index", 0) <= 1000):
        raise RecipeValidationError("RADIO_GROUP_INVALID")
    correlated = action == "request_download" or (action == "download" and "generation" in step)
    lower, upper = (60000, 900000) if correlated else (100, 180000)
    if "timeout_ms" in step and (type(step["timeout_ms"]) is not int or not lower <= step["timeout_ms"] <= upper):
        raise RecipeValidationError("STEP_TIMEOUT_INVALID")
    if "learning" in step:
        learning = step["learning"]
        if action not in {"wait_for", "wait_for_outcome"} or not isinstance(learning, dict) or set(learning) != {"source", "confidence"} or learning["source"] not in {"automatic", "manual"} or learning["confidence"] not in {"high", "medium"}:
            raise RecipeValidationError("WAIT_LEARNING_INVALID")
    if action == "navigate":
        url = step.get("url")
        if not isinstance(url, str) or not url.strip():
            raise RecipeValidationError("URL_REQUIRED")
        if not url.startswith(("http://", "https://")):
            if not _VARIABLE_PATTERN.fullmatch(url.strip()):
                raise RecipeValidationError("UNSAFE_URL")

    if action in {"click", "fill", "select", "press", "wait_for", "download", "check", "set_value", "choose", "choose_radio", "scroll", "hover", "drag", "request_download"}:
        selector = step.get("selector")
        if not isinstance(selector, str) or not selector.strip():
            raise RecipeValidationError("SELECTOR_REQUIRED")

    if action in {"fill", "select", "check", "set_value", "choose", "choose_radio"} and "value" not in step:
        raise RecipeValidationError("VALUE_REQUIRED")

    if action == "wait_for_any":
        selectors = step.get("selectors")
        if (
            not isinstance(selectors, list)
            or not selectors
            or not all(isinstance(item, str) and item.strip() for item in selectors)
        ):
            raise RecipeValidationError("SELECTORS_REQUIRED")

    if action == "switch_tab":
        index = step.get("index")
        if not isinstance(index, int) or index < 0:
            raise RecipeValidationError("TAB_INDEX_REQUIRED")

    if action == "download":
        if "preserve_filename" in step and type(step["preserve_filename"]) is not bool:
            raise RecipeValidationError("DOWNLOAD_FILENAME_INVALID")
        if "collection" in step:
            try:
                validate_collection(step["collection"], extended="generation" in step or (isinstance(step["collection"], dict) and "shared" in step["collection"]))
            except (ValueError, TypeError):
                raise RecipeValidationError("DOWNLOAD_COLLECTION_INVALID") from None
        filename = step.get("filename")
        if not isinstance(filename, str) or not filename.strip():
            raise RecipeValidationError("DOWNLOAD_FILENAME_REQUIRED")


def _find_variables(value) -> set[str]:
    found: set[str] = set()

    if isinstance(value, str):
        found.update(_VARIABLE_PATTERN.findall(value))
    elif isinstance(value, dict):
        for child in value.values():
            found.update(_find_variables(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_variables(child))

    return found
