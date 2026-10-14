"""Strict declarative query contract. No browser or persisted query identities."""

QUERY_IDENTITY_ATTRIBUTES = frozenset({'data-query-id', 'data-request-id'})
SAFE_QUERY_ERRORS = frozenset({
    'QUERY_BASELINE_UNAVAILABLE', 'QUERY_IDENTITY_INVALID', 'QUERY_CONFIRMATION_TIMEOUT',
    'QUERY_RESULT_TIMEOUT', 'QUERY_CONTEXT_MISMATCH', 'QUERY_SUPERSEDED',
    'QUERY_OUTCOME_AMBIGUOUS', 'QUERY_NO_DATA', 'QUERY_SITE_ERROR',
    'QUERY_AUTHORIZATION_REVOKED', 'QUERY_EXECUTION_FAILED',
})


def _selector(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2048


def validate_query_step(step: dict) -> None:
    allowed = {'id', 'action', 'selector', 'frames', 'timeout_ms', 'retry', 'label', 'confirmation', 'result'}
    valid = (isinstance(step, dict) and not set(step) - allowed
             and _selector(step.get('selector')))
    if not valid:
        raise ValueError('QUERY_CONFIG_INVALID')
    frames = step.get('frames', [])
    timeout = step.get('timeout_ms', 180000)
    confirmation, result = step.get('confirmation'), step.get('result')
    if (not isinstance(frames, list) or len(frames) > 16 or not all(map(_selector, frames))
            or type(timeout) is not int or not 1000 <= timeout <= 900000
            or not isinstance(confirmation, dict) or set(confirmation) != {'selector', 'attribute'}
            or not _selector(confirmation['selector'])
            or not isinstance(confirmation['attribute'], str) or confirmation['attribute'] not in QUERY_IDENTITY_ATTRIBUTES
            or not isinstance(result, dict) or set(result) != {'container', 'attribute', 'outcomes'}
            or not _selector(result['container'])
            or not isinstance(result['attribute'], str) or result['attribute'] not in QUERY_IDENTITY_ATTRIBUTES):
        raise ValueError('QUERY_CONFIG_INVALID')
    outcomes = result['outcomes']
    if (not isinstance(outcomes, dict) or set(outcomes) != {'data', 'empty', 'error'}
            or not all(map(_selector, outcomes.values()))
            or len({value.strip() for value in outcomes.values()}) != 3):
        raise ValueError('QUERY_CONFIG_INVALID')
    retry = step.get('retry')
    if retry is not None and (not isinstance(retry, dict) or type(retry.get('max_attempts', 1)) is not int
                              or retry.get('max_attempts', 1) != 1):
        raise ValueError('QUERY_RETRY_FORBIDDEN')
