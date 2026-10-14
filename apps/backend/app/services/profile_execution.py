from copy import deepcopy
from urllib.parse import urlsplit
from app.models import LoginProfile
from app.repositories.login_profile import find_version
from app.errors import ApiError
from login_profiles import profile_key

def _resolve_profile_configuration(db, reference):
    profile = db.get(LoginProfile, reference["id"])
    version = find_version(db, reference["id"], reference["version"])
    if not profile or profile.status == "DISABLED" or not version or version.published_at is None:
        raise ApiError(409, "LOGIN_PROFILE_UNAVAILABLE", "Publique uma configuração de login válida antes de executar.")
    return profile, version, deepcopy(version.configuration)

def validate_profile_reference(db, reference):
    """Confirm a published profile can be linked without starting corporate auth."""
    _resolve_profile_configuration(db, reference)

def profile_configuration(db, reference):
    profile, version, configuration = _resolve_profile_configuration(db, reference)
    if any(urlsplit(url).hostname.lower().rstrip(".") == "indicadoresenergisaess.scl.corp" for url in configuration["allowed_origins"]):
        raise ApiError(409, "CORPORATE_AUTH_NOT_VALIDATED", "Integração corporativa aguarda validação autorizada.")
    return profile_key(profile.id, version.version), configuration
