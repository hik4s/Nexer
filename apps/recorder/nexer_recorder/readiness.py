"""Strict normalization of locally observed readiness; never page data."""
from copy import deepcopy

_ACTIONS = {'click', 'download', 'fill', 'select', 'check', 'choose', 'choose_radio', 'set_value'}


def normalize_readiness(event: dict, previous_step: dict) -> tuple[dict | None, dict]:
    if not isinstance(event, dict):
        raise ValueError('RECORDER_EVENT_INVALID')
    clean = deepcopy(event)
    if 'readiness' not in clean:
        return None, clean
    signal = clean.pop('readiness')
    selector, frames = clean.get('selector'), clean.get('frames', [])
    if (not isinstance(clean.get('action'), str) or clean['action'] not in _ACTIONS or not isinstance(signal, dict)
            or set(signal) != {'state'} or not isinstance(signal['state'], str) or signal['state'] not in {'visible', 'enabled'}
            or not isinstance(selector, str) or not selector.strip() or len(selector) > 2048
            or not isinstance(frames, list) or len(frames) > 16
            or any(not isinstance(frame, str) or not frame.strip() or len(frame) > 2048 for frame in frames)):
        raise ValueError('RECORDER_EVENT_INVALID')
    same_wait = (
        (previous_step.get('action') == 'wait_for' and previous_step.get('selector') == selector
         and previous_step.get('frames', []) == frames)
        or (previous_step.get('action') == 'wait_for_outcome' and previous_step.get('ready_selector') == selector
            and previous_step.get('ready_state') == signal['state'] and not frames)
    )
    if same_wait or (clean['action'] == 'download' and 'collection' in clean):
        return None, clean
    return {'action': 'wait_for', 'selector': selector, 'frames': list(frames),
            'state': signal['state'], 'timeout_ms': 30000,
            'learning': {'source': 'automatic', 'confidence': 'high'}}, clean
