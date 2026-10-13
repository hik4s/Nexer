"""Deterministic, privacy-preserving smart recording pass.

Adds executable readiness conditions without inspecting page text, network
payloads, field values, or download filenames. Manual waits always win.
"""
from copy import deepcopy

from recipe import validate_recipe

_ACTION_STATES = {
    "click": "visible",
    "fill": "visible",
    "select": "visible",
    "check": "visible",
    "choose": "visible",
    "choose_radio": "visible",
    "set_value": "visible",
    "press": "visible",
    "download": "enabled",
}


def optimize_recipe(recipe: dict) -> dict:
    """Insert conservative conditions before UI actions; idempotent.

    The browser executor already auto-waits for many actions. Explicit steps
    make the dependency visible, reviewable, and configurable in the Studio.
    """
    source = validate_recipe(recipe)
    optimized = deepcopy(source)
    steps = []
    ids = {step["id"] for step in source["steps"]}
    for step in source["steps"]:
        # Collection downloads already poll for matching rows in the executor.
        # Waiting on the originally clicked row would break async exports.
        state = None if step["action"] == "download" and "collection" in step else _ACTION_STATES.get(step["action"])
        previous = steps[-1] if steps else None
        same_wait = (previous is not None and previous["action"] == "wait_for"
                     and previous.get("selector") == step.get("selector")
                     and previous.get("frames", []) == step.get("frames", []))
        if state and not same_wait:
            candidate = f"smart_{step['id']}"
            suffix = 2
            while candidate in ids:
                candidate = f"smart_{step['id']}_{suffix}"
                suffix += 1
            ids.add(candidate)
            wait = {
                "id": candidate,
                "action": "wait_for",
                "selector": step["selector"],
                "state": state,
                "timeout_ms": 30000,
                "learning": {"source": "automatic", "confidence": "medium"},
            }
            if step.get("frames"):
                wait["frames"] = list(step["frames"])
            steps.append(wait)
        steps.append(step)
    optimized["steps"] = steps
    return validate_recipe(optimized)
