"""Execution guard for an already authenticated corporate page."""
from corporate_auth import get_login_definition, validate_corporate_url


class CorporateExecutionGuard:
    def __init__(self, system, policy):
        self.system = system
        self.policy = policy
        self.definition = get_login_definition(system)

    def ensure_authenticated(self, page):
        try:
            self.policy.check()
            validate_corporate_url(self.system, page.url)
            if page.locator(self.definition.form_selector).count() != 0:
                raise RuntimeError()
            return page
        except Exception:
            try:
                page.close()
            except Exception:
                pass
            raise RuntimeError("CORPORATE_CONTEXT_REVOKED") from None


def validate_corporate_recipe(recipe):
    # Recipe code must never supply login selectors, credential providers,
    # script execution or another tab in an authenticated corporate context.
    from recipe import validate_recipe
    normalized = validate_recipe(recipe)
    if normalized.get("authentication") is not None:
        raise RuntimeError("CORPORATE_RECIPE_FORBIDDEN")
    if any(declaration.get("secret") or declaration.get("type") == "secret"
           for declaration in normalized.get("variables", {}).values()):
        raise RuntimeError("CORPORATE_RECIPE_FORBIDDEN")
    if any(step["action"] == "switch_tab" for step in normalized["steps"]):
        raise RuntimeError("CORPORATE_RECIPE_FORBIDDEN")
    return normalized
