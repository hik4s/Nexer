"""Metadata-only contract shared by the target picker and backend, without browser imports."""
import re
from site_urls import validate_site_url

KINDS = frozenset({'element', 'text', 'select', 'checkbox', 'range', 'color'})
SAFE_PICKER_ERRORS = frozenset({'TARGET_PICKER_CANCELLED', 'TARGET_PICKER_TIMEOUT',
    'TARGET_PICKER_FAILED', 'TARGET_PICKER_CONTEXT_UNSUPPORTED'})
_WORDS = frozenset(('period start end company regional query search filter filters result results export submit apply run download report form table list menu panel tab tabs content main toolbar date input field button select check checkbox radio frame host').split())
_ATTRIBUTES = {
    'type': frozenset('text search email url tel password hidden file number date datetime-local time month week range color checkbox radio button submit reset'.split()),
    'role': frozenset('button textbox searchbox combobox listbox option checkbox radio radiogroup slider spinbutton menu menuitem tab tablist table row cell list listitem dialog region navigation main form'.split()),
    'aria-haspopup': frozenset({'true', 'false', 'menu', 'listbox', 'tree', 'grid', 'dialog'}),
    'contenteditable': frozenset({'', 'true', 'false', 'plaintext-only'}),
}
_TAG = re.compile(r'[a-z][a-z0-9-]*')
_TAIL = re.compile(r':nth-of-type\([1-9][0-9]{0,6}\)|\[([a-z-]+)="([a-z_-]*)"\]')


def _identifier(value):
    return (len(value) <= 64 and re.fullmatch(r'[a-z]+(?:[-_][a-z]+)*', value)
            and all(word in _WORDS for word in re.split('[-_]', value)))


def _token(token):
    if token.startswith('#'):
        return bool(_identifier(token[1:]))
    tag = _TAG.match(token)
    if not tag:
        return False
    position = tag.end()
    while position < len(token):
        match = _TAIL.match(token, position)
        if not match:
            return False
        attribute, value = match.groups()
        if attribute:
            if attribute in {'id', 'data-testid', 'name'}:
                if not _identifier(value):
                    return False
            elif attribute not in _ATTRIBUTES or value not in _ATTRIBUTES[attribute]:
                return False
            if attribute == 'type' and tag.group() != 'input':
                return False
        position = match.end()
    return True


def validate_target(target: dict) -> dict:
    if not isinstance(target, dict) or set(target) != {'selector'}:
        raise ValueError('TARGET_PICKER_FAILED')
    selector = target['selector']
    if not isinstance(selector, str) or not 0 < len(selector) <= 2048:
        raise ValueError('TARGET_PICKER_FAILED')
    parts = selector.split(' ')
    previous = None
    for part in parts:
        if part == '>':
            if previous is None or previous == '>':
                raise ValueError('TARGET_PICKER_FAILED')
        elif not _token(part):
            raise ValueError('TARGET_PICKER_FAILED')
        previous = part
    if previous == '>':
        raise ValueError('TARGET_PICKER_FAILED')
    return {'selector': selector}


def validate_configuration(configuration: dict) -> dict:
    if (not isinstance(configuration, dict) or set(configuration) != {'url', 'kind'}
            or not isinstance(configuration['kind'], str) or configuration['kind'] not in KINDS):
        raise ValueError('TARGET_PICKER_FAILED')
    return {'url': validate_site_url(configuration['url']), 'kind': configuration['kind']}
