"""Declarative contracts for request-correlated downloads; no browser imports."""
IDENTITY_ATTRIBUTES = frozenset({'data-job-id', 'data-report-id', 'data-download-id'})
SAFE_DOWNLOAD_ERRORS = frozenset({
    'DOWNLOAD_BASELINE_UNAVAILABLE', 'DOWNLOAD_BASELINE_INCOMPLETE', 'DOWNLOAD_IDENTITY_INVALID',
    'DOWNLOAD_CONTEXT_MISMATCH', 'DOWNLOAD_CONFIRMATION_AMBIGUOUS', 'DOWNLOAD_CONFIRMATION_TIMEOUT',
    'DOWNLOAD_MATCH_AMBIGUOUS', 'DOWNLOAD_GENERATION_TIMEOUT', 'DOWNLOAD_BUTTON_AMBIGUOUS',
    'DOWNLOAD_GENERATION_UNAVAILABLE', 'DOWNLOAD_AUTHORIZATION_REVOKED', 'DOWNLOAD_GENERATION_FAILED',
})


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2048


def validate_collection(collection, *, extended=False):
    required = {'rows', 'name', 'button', 'pattern'}
    optional = {'identity_attribute', 'shared', 'container'} if extended else set()
    if (not isinstance(collection, dict) or not required <= set(collection)
            or set(collection) - required - optional or any(not _text(collection[key]) for key in required)):
        raise ValueError('DOWNLOAD_COLLECTION_INVALID')
    if 'shared' in collection and type(collection['shared']) is not bool:
        raise ValueError('DOWNLOAD_COLLECTION_INVALID')
    if 'container' in collection and not _text(collection['container']):
        raise ValueError('DOWNLOAD_COLLECTION_INVALID')
    if 'identity_attribute' in collection and (not isinstance(collection['identity_attribute'], str)
                                              or collection['identity_attribute'] not in IDENTITY_ATTRIBUTES):
        raise ValueError('DOWNLOAD_COLLECTION_INVALID')


def validate_generation_steps(steps: list[dict]) -> None:
    previous = {}
    tab = 0
    snapshots = 0
    for index, step in enumerate(steps):
        action = step['action']
        frames = step.get('frames', [])
        if action == 'switch_tab':
            tab = step['index']
        if action == 'snapshot_downloads':
            snapshots += 1
            if snapshots > 50 or set(step) - {'id', 'action', 'frames', 'collection', 'timeout_ms', 'retry'}:
                raise ValueError('DOWNLOAD_GENERATION_CONFIG_INVALID')
            validate_collection(step.get('collection'), extended=True)
            if not _text(step['collection'].get('container')):
                raise ValueError('DOWNLOAD_COLLECTION_INVALID')
            if index + 1 >= len(steps) or steps[index + 1].get('baseline') != step['id'] or steps[index + 1]['action'] != 'request_download':
                raise ValueError('DOWNLOAD_GENERATION_REFERENCE_INVALID')
        elif action == 'request_download':
            if set(step) - {'id', 'action', 'selector', 'frames', 'baseline', 'confirmation', 'timeout_ms', 'retry', 'button', 'click_count'}:
                raise ValueError('DOWNLOAD_GENERATION_CONFIG_INVALID')
            baseline = previous.get(step.get('baseline')) if isinstance(step.get('baseline'), str) else None
            if (baseline is None or baseline[0]['action'] != 'snapshot_downloads' or baseline[1] != tab
                    or baseline[0].get('frames', []) != frames or index == 0 or steps[index - 1]['id'] != step.get('baseline')):
                raise ValueError('DOWNLOAD_GENERATION_REFERENCE_INVALID')
            confirmation = step.get('confirmation')
            if (not isinstance(confirmation, dict) or set(confirmation) - {'selector', 'attribute'}
                    or not _text(confirmation.get('selector'))
                    or ('attribute' in confirmation and (not isinstance(confirmation['attribute'], str)
                        or confirmation['attribute'] not in IDENTITY_ATTRIBUTES))):
                raise ValueError('DOWNLOAD_GENERATION_CONFIG_INVALID')
            if step.get('button', 'left') != 'left' or type(step.get('click_count', 1)) is not int or step.get('click_count', 1) != 1:
                raise ValueError('DOWNLOAD_GENERATION_CONFIG_INVALID')
        elif action == 'download' and 'generation' in step:
            generation = previous.get(step['generation']) if isinstance(step['generation'], str) else None
            if generation is None or generation[0]['action'] != 'request_download' or generation[1] != tab or generation[0].get('frames', []) != frames:
                raise ValueError('DOWNLOAD_GENERATION_REFERENCE_INVALID')
            baseline = previous[generation[0]['baseline']][0]
            validate_collection(step.get('collection'), extended=True)
            if step['collection'] != baseline['collection']:
                raise ValueError('DOWNLOAD_GENERATION_REFERENCE_INVALID')
        elif 'generation' in step or 'baseline' in step or ('confirmation' in step and action != 'query'):
            raise ValueError('DOWNLOAD_GENERATION_CONFIG_INVALID')
        if action == 'download' and 'collection' in step and 'generation' not in step:
            validate_collection(step['collection'], extended='shared' in step['collection'])
            if step['collection'].get('shared'):
                raise ValueError('DOWNLOAD_SHARED_CORRELATION_REQUIRED')
        if action == 'request_download' or (action == 'download' and 'generation' in step):
            if (step.get('retry') or {}).get('max_attempts', 1) != 1:
                raise ValueError('DOWNLOAD_GENERATION_RETRY_FORBIDDEN')
        previous[step['id']] = (step, tab)
