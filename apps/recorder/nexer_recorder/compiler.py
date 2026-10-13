from copy import deepcopy
import re

from recipe import validate_recipe
from field_schema import validate_field


class Recording:
    def __init__(self, name):
        self.name = name
        self.steps = [{"id": "open", "action": "navigate", "url": "{{base_url}}"}]
        self.variables = {"base_url": {"type": "string", "required": True}}
        self.parameters = {}
        self.current_tab = 0

    def accept(self, event):
        allowed = {
            "click": {"button", "click_count"}, "fill": {"parameter", "field"},
            "select": {"parameter", "multiple", "field"}, "check": {"parameter", "field"},
            "set_value": {"parameter", "input_type", "field"}, "choose": {"parameter", "field"}, "choose_radio": {"parameter", "group_index", "field"}, "download": set(),
            "wait_for": {"state", "timeout_ms", "learning"},
            "press": {"key"}, "scroll": {"x", "y"}, "hover": set(),
            "drag": {"target_selector"}, "switch_tab": {"index"}, "close_tab": set(),
        }
        if not isinstance(event, dict) or len(self.steps) >= 1000:
            raise ValueError("RECORDER_EVENT_INVALID")
        action = event.get("action")
        for control in ("fill", "select", "check", "set_value", "choose", "choose_radio"):
            allowed[control].add("label")
        allowed["download"].add("collection")
        if action not in allowed or set(event) - ({"action", "selector", "frames"} | allowed[action]):
            raise ValueError("RECORDER_EVENT_INVALID")
        if action == "close_tab":
            if set(event) != {"action"}:
                raise ValueError("RECORDER_EVENT_INVALID")
            self.steps.append({"id": f"step_{len(self.steps):03d}", "action": action})
            return
        if action == "switch_tab":
            if set(event) != {"action", "index"} or type(event["index"]) is not int or not 0 <= event["index"] <= 100:
                raise ValueError("RECORDER_EVENT_INVALID")
            self.current_tab = event["index"]
            self.steps.append({"id": f"step_{len(self.steps):03d}", **event})
            return
        selector = event.get("selector")
        frames = event.get("frames", [])
        if (not isinstance(selector, str) or not 0 < len(selector) <= 2048 or not isinstance(frames, list)
                or len(frames) > 16 or any(not isinstance(item, str) or not 0 < len(item) <= 2048 for item in frames)):
            raise ValueError("RECORDER_EVENT_INVALID")
        if action == "wait_for":
            state = event.get("state", "visible")
            learning = event.get("learning", {"source": "manual", "confidence": "high"})
            if state not in {"visible", "hidden", "enabled", "disabled"} or not isinstance(learning, dict) or set(learning) != {"source", "confidence"} or learning["source"] not in {"automatic", "manual"} or learning["confidence"] not in {"high", "medium"}:
                raise ValueError("RECORDER_EVENT_INVALID")
            timeout = event.get("timeout_ms", 30000)
            if type(timeout) is not int or not 100 <= timeout <= 180000:
                raise ValueError("RECORDER_EVENT_INVALID")
        if action == "press" and event.get("key") not in {"Enter", "Tab", "Escape", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown", "Space"}:
            raise ValueError("RECORDER_EVENT_INVALID")
        if action == "set_value" and event.get("input_type") not in {"range", "color"}:
            raise ValueError("RECORDER_EVENT_INVALID")
        if "multiple" in event and type(event["multiple"]) is not bool:
            raise ValueError("RECORDER_EVENT_INVALID")
        parameter = event.get("parameter")
        field = validate_field(event["field"]) if "field" in event else None
        label = event.get("label")
        if label is not None and (not isinstance(label, str) or not 0 < len(label.strip()) <= 100):
            raise ValueError("RECORDER_EVENT_INVALID")
        if parameter is not None and (not isinstance(parameter, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", parameter) or parameter == "base_url"):
            raise ValueError("RECORDER_EVENT_INVALID")
        step = {"id": f"step_{len(self.steps):03d}", "action": action, "selector": selector}
        if frames:
            step["frames"] = list(frames)
        if action == "wait_for":
            step["state"] = event.get("state", "visible")
            step["timeout_ms"] = event.get("timeout_ms", 30000)
            step["learning"] = event.get("learning", {"source": "manual", "confidence": "high"})
        if action == "choose_radio":
            if type(event.get("group_index", 0)) is not int or not 0 <= event.get("group_index", 0) <= 1000:
                raise ValueError("RECORDER_EVENT_INVALID")
            step["group_index"] = event.get("group_index", 0)
        adjacent = self.steps[-1].get("action") == action and self.steps[-1].get("selector") == selector and self.steps[-1].get("frames", []) == frames and self.steps[-1].get("group_index", 0) == step.get("group_index", 0)
        if action in {"fill", "select", "check", "set_value", "choose", "choose_radio"}:
            identity = (self.current_tab, tuple(frames), selector, action, step.get("group_index", 0))
            existing = self.parameters.get(identity)
            if action == "check" and not adjacent:
                existing = None
            if existing and parameter and (parameter == existing or existing.startswith(parameter + "_")):
                parameter = existing
            if parameter and not existing and parameter in self.variables:
                base = parameter
                suffix = 2
                while f"{base}_{suffix:03d}" in self.variables:
                    suffix += 1
                parameter = f"{base}_{suffix:03d}"
            if not parameter and not existing:
                index = 1
                while f"input_{index:03d}" in self.variables:
                    index += 1
                parameter = f"input_{index:03d}"
            parameter = parameter or existing
            if (existing and existing != parameter) or any(key != identity and value == parameter for key, value in self.parameters.items()):
                raise ValueError("RECORDER_EVENT_INVALID")
            self.parameters[identity] = parameter
            kind = "boolean" if action == "check" else "array" if event.get("multiple") else "string"
            self.variables[parameter] = {"type": kind, "required": True}
            if label:
                self.variables[parameter]["label"] = label.strip()
            control = {"fill": "text", "select": "multiselect" if event.get("multiple") else "select",
                       "check": "checkbox", "choose": "select", "choose_radio": "radio", "set_value": event.get("input_type")}[action]
            self.variables[parameter]["field"] = field or {"control": "date" if event.get("parameter") in {"period_start", "period_end"} else control}
            if event.get("parameter") in {"period_start", "period_end"}:
                self.variables[parameter]["format"] = "date"
            elif action == "fill" and not (field or {}).get("required"):
                self.variables[parameter]["allow_empty"] = True
            if (field or {}).get("required"):
                self.variables[parameter].pop("allow_empty", None)
            if action == "select" and self.variables[parameter]["type"] == "array" and not (field or {}).get("required"):
                self.variables[parameter]["allow_empty"] = True
            step["value"] = "{{" + parameter + "}}"
            if action == "set_value":
                step["input_type"] = event["input_type"]
            if adjacent:
                return
        if action == "download":
            index = 1
            while f"download_file_{index:03d}" in self.variables or f"download_pattern_{index:03d}" in self.variables:
                index += 1
            parameter = f"download_file_{index:03d}"
            self.variables[parameter] = {"type": "string", "required": True}
            step["filename"] = "{{" + parameter + "}}"
            self.variables[parameter]["label"] = "Nome do arquivo salvo"
            if "collection" in event:
                collection = event["collection"]
                if (not isinstance(collection, dict) or set(collection) != {"rows", "name", "button"}
                        or any(not isinstance(value, str) or not 0 < len(value) <= 2048 for value in collection.values())):
                    raise ValueError("RECORDER_EVENT_INVALID")
                pattern = f"download_pattern_{index:03d}"
                self.variables[pattern] = {"type": "string", "required": True, "label": "Padrão do relatório na central (* e ?)"}
                step["collection"] = {**collection, "pattern": "{{" + pattern + "}}"}
                del self.variables[parameter]
                step["filename"] = "download"
                step["preserve_filename"] = True
        if action == "press":
            step["key"] = event["key"]
        if action in {"click", "scroll", "drag"}:
            step.update({key: event[key] for key in allowed[action] if key in event})
        previous = self.steps[-1]
        validate_recipe({"schema_version": 1, "name": self.name, "variables": self.variables,
                         "steps": [step], "output": {"type": "file"}})
        if action == "click" and step.get("click_count", 1) > 1 and previous.get("action") == "click" and previous.get("selector") == selector and previous.get("frames", []) == frames and previous.get("button", "left") == step.get("button", "left"):
            previous["click_count"] = step["click_count"]
            return
        self.steps.append(step)

    def recipe(self):
        return validate_recipe(deepcopy({"schema_version": 1, "name": self.name,
            "variables": self.variables, "steps": self.steps,
            "output": {"type": "file" if any(step["action"] == "download" for step in self.steps) else "none"}}))

    def mark_download(self):
        step = self.steps[-1]
        if step["action"] != "download":
            raise ValueError("RECORDER_DOWNLOAD_UNSUPPORTED")

    def promote_recent_click_to_download(self, *, step_index: int):
        """Promote only the exact last click; never guess across intervening steps.

        The caller must first correlate the browser download with the same page
        and a short, uninterrupted time window. No filename or URL is recorded.
        """
        if step_index != len(self.steps) - 1:
            raise ValueError("RECORDER_DOWNLOAD_UNSUPPORTED")
        click = self.steps[step_index]
        if click["action"] != "click" or click.get("button", "left") != "left" or click.get("click_count", 1) != 1:
            raise ValueError("RECORDER_DOWNLOAD_UNSUPPORTED")
        self.steps.pop()
        try:
            self.accept({"action": "download", "selector": click["selector"],
                         **({"frames": click["frames"]} if "frames" in click else {})})
        except Exception:
            self.steps.append(click)
            raise
