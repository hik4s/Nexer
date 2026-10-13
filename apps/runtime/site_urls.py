"""Configured site URLs and origins, without query or credential persistence."""
from ipaddress import ip_address
import re
from urllib.parse import urlsplit, urlunsplit

_HOST = re.compile(r"(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*")
_ROUTE = re.compile(r"/[A-Za-z0-9_/-]*")

def _parts(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("SITE_URL_INVALID")
    value = value.strip()
    if not value or any(char.isspace() for char in value):
        raise ValueError("SITE_URL_INVALID")
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("SITE_URL_INVALID")
    hostname = parsed.hostname.encode("idna").decode("ascii").lower().rstrip(".")
    if "%" in hostname:
        raise ValueError("SITE_URL_INVALID")
    try:
        ip_address(hostname)
    except ValueError:
        if not _HOST.fullmatch(hostname):
            raise ValueError("SITE_URL_INVALID")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and hostname in {"127.0.0.1", "localhost", "::1"}):
        raise ValueError("SITE_URL_INVALID")
    port = parsed.port
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("SITE_URL_INVALID")
    return parsed, hostname, port or (443 if parsed.scheme == "https" else 80)

def validate_site_url(value):
    try:
        parsed, hostname, port = _parts(value)
        if parsed.query or "?" in value or (parsed.fragment and not _ROUTE.fullmatch(parsed.fragment)):
            raise ValueError()
        host = f"[{hostname}]" if ":" in hostname else hostname
        if port != (443 if parsed.scheme == "https" else 80):
            host += f":{port}"
        return urlunsplit((parsed.scheme, host, parsed.path or "/", "", parsed.fragment))
    except (TypeError, ValueError, UnicodeError):
        raise ValueError("SITE_URL_INVALID") from None

def site_origin(value):
    try:
        parsed, hostname, port = _parts(value)
        return parsed.scheme, hostname, port
    except (TypeError, ValueError, UnicodeError):
        raise ValueError("SITE_ORIGIN_INVALID") from None
