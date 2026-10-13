"""Presentation rules only: recorded field values and option catalogs are forbidden."""
import math
import re

CONTROLS = {"text", "textarea", "date", "datetime-local", "time", "month", "week", "number", "email", "url", "tel", "search", "range", "color", "select", "multiselect", "checkbox", "radio"}
KEYS = {"control", "min", "max", "step", "min_length", "max_length", "pattern", "input_mode", "rows", "required"}


def validate_field(field):
    if not isinstance(field, dict) or set(field) - KEYS or field.get("control") not in CONTROLS:
        raise ValueError("FIELD_SCHEMA_INVALID")
    if "required" in field and type(field["required"]) is not bool:
        raise ValueError("FIELD_SCHEMA_INVALID")
    temporal = {"date": r"\d{4,}-\d{2}-\d{2}", "time": r"\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?", "datetime-local": r"\d{4,}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?", "month": r"\d{4,}-\d{2}", "week": r"\d{4,}-W\d{2}"}
    for key in ("min", "max", "step"):
        if key in {"min", "max"} and field.get("control") in temporal and key in field:
            if not isinstance(field[key], str) or not re.fullmatch(temporal[field["control"]], field[key]):
                raise ValueError("FIELD_SCHEMA_INVALID")
            continue
        if key in field and not (key == "step" and field[key] == "any"):
            if type(field[key]) not in (int, float) or not math.isfinite(field[key]):
                raise ValueError("FIELD_SCHEMA_INVALID")
    if isinstance(field.get("step"), (int, float)) and field["step"] <= 0:
        raise ValueError("FIELD_SCHEMA_INVALID")
    for key in ("min_length", "max_length", "rows"):
        if key in field and (type(field[key]) is not int or not 0 <= field[key] <= 100000):
            raise ValueError("FIELD_SCHEMA_INVALID")
    if "pattern" in field and (not isinstance(field["pattern"], str) or len(field["pattern"]) > 512):
        raise ValueError("FIELD_SCHEMA_INVALID")
    if "input_mode" in field and field["input_mode"] not in {"none", "text", "decimal", "numeric", "tel", "search", "email", "url"}:
        raise ValueError("FIELD_SCHEMA_INVALID")
    return dict(field)
