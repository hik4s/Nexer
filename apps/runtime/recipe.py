import re
from copy import deepcopy


KNOWN_ACTIONS = {
    "navigate",
    "click",
    "fill",
    "select",
    "press",
    "wait_for",
    "wait_for_any",
    "switch_tab",
    "download",
    "validate_file",
}

_VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")


class RecipeValidationError(ValueError):
    """Raised when a declarative recipe is not safe or structurally valid."""


def validate_recipe(recipe: dict) -> dict:
    if not isinstance(recipe, dict):
        raise RecipeValidationError("RECIPE_OBJECT_REQUIRED")

    normalized = deepcopy(recipe)

    if normalized.get("schema_version") != 1:
        raise RecipeValidationError("UNSUPPORTED_SCHEMA_VERSION")

    name = normalized.get("name")
    if not isinstance(name, str) or not name.strip():
        raise RecipeValidationError("RECIPE_NAME_REQUIRED")

    variables = normalized.get("variables", {})
    if not isinstance(variables, dict):
        raise RecipeValidationError("VARIABLES_OBJECT_REQUIRED")

    steps = normalized.get("steps")
    if not isinstance(steps, list) or not steps:
        raise RecipeValidationError("STEPS_REQUIRED")

    output = normalized.get("output")
    if not isinstance(output, dict) or output.get("type") != "file":
        raise RecipeValidationError("FILE_OUTPUT_REQUIRED")

    seen_ids: set[str] = set()
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

        for value in step.values():
            for variable in _find_variables(value):
                if variable not in declared:
                    raise RecipeValidationError(
                        f"UNDECLARED_VARIABLE:{variable}"
                    )

    expected_extension = output.get("expected_extension")
    if expected_extension is not None:
        if (
            not isinstance(expected_extension, str)
            or not expected_extension.startswith(".")
        ):
            raise RecipeValidationError("INVALID_EXPECTED_EXTENSION")

    return normalized


def _validate_step_requirements(action: str, step: dict) -> None:
    if action == "navigate":
        url = step.get("url")
        if not isinstance(url, str) or not url.strip():
            raise RecipeValidationError("URL_REQUIRED")
        if not url.startswith(("http://", "https://")):
            if not _VARIABLE_PATTERN.fullmatch(url.strip()):
                raise RecipeValidationError("UNSAFE_URL")

    if action in {"click", "fill", "select", "press", "wait_for", "download"}:
        selector = step.get("selector")
        if not isinstance(selector, str) or not selector.strip():
            raise RecipeValidationError("SELECTOR_REQUIRED")

    if action in {"fill", "select"} and "value" not in step:
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
