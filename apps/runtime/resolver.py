import re


_VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")


from credentials import CredentialResolutionError


class VariableResolutionError(ValueError):
    """Raised when recipe variables cannot be resolved safely."""


class VariableResolver:
    def __init__(self, *, declarations: dict, values: dict, secret_provider=None):
        self.declarations = declarations
        self.values = values
        self.secret_provider = secret_provider

    def resolve(self, value):
        if isinstance(value, str):
            match = _VARIABLE_PATTERN.fullmatch(value.strip())
            if match:
                return self._value_for(match.group(1))

            return _VARIABLE_PATTERN.sub(
                lambda match: str(self._value_for(match.group(1))),
                value,
            )

        if isinstance(value, dict):
            return {key: self.resolve(child) for key, child in value.items()}

        if isinstance(value, list):
            return [self.resolve(child) for child in value]

        return value

    def validate_required(self) -> None:
        for name, declaration in self.declarations.items():
            if declaration.get("required", True):
                if name not in self.values or self._is_empty(self.values[name]):
                    raise VariableResolutionError("MISSING_VARIABLE")

    def _value_for(self, name: str):
        declaration = self.declarations.get(name)
        if declaration is None:
            raise VariableResolutionError("UNDECLARED_VARIABLE")

        if name not in self.values or self._is_empty(self.values[name]):
            raise VariableResolutionError("MISSING_VARIABLE")

        value = self.values[name]
        if declaration.get("secret"):
            if not isinstance(value, dict) or set(value) != {"credential_ref"}:
                raise VariableResolutionError("SECRET_VALUE_INLINE_FORBIDDEN")
            if self.secret_provider is None:
                raise VariableResolutionError("CREDENTIAL_PROVIDER_UNAVAILABLE")
            reference = value.get("credential_ref")
            try:
                value = self.secret_provider.get(reference)
            except CredentialResolutionError as exc:
                raise VariableResolutionError(str(exc)) from exc

        expected = declaration.get("type", "string")
        if not _type_matches(value, expected):
            raise VariableResolutionError("INVALID_VARIABLE_TYPE")

        return value

    @staticmethod
    def _is_empty(value) -> bool:
        return value is None or (isinstance(value, str) and value == "")


def _type_matches(value, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True
