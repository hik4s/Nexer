from copy import deepcopy
import unittest

from nexer_recorder.readiness import normalize_readiness


class ReadinessTests(unittest.TestCase):
    def test_valid_transition_keeps_target_frames_and_arguments(self):
        event = {'action': 'fill', 'selector': '#search', 'frames': ['#frame'], 'readiness': {'state': 'visible'}}
        before = deepcopy(event)
        wait, clean = normalize_readiness(event, {'action': 'click', 'selector': '#run'})
        self.assertEqual(wait, {'action': 'wait_for', 'selector': '#search', 'frames': ['#frame'],
                                'state': 'visible', 'timeout_ms': 30000,
                                'learning': {'source': 'automatic', 'confidence': 'high'}})
        self.assertNotIn('readiness', clean)
        self.assertEqual(event, before)

    def test_invalid_readiness_is_rejected_instead_of_silently_removed(self):
        for signal in ('enabled', None, {}, {'state': 'hidden'}, {'state': []}, {'state': {}}, {'state': 'enabled', 'value': 'canary'}):
            with self.subTest(signal=signal), self.assertRaisesRegex(ValueError, 'RECORDER_EVENT_INVALID'):
                normalize_readiness({'action': 'click', 'selector': '#run', 'readiness': signal}, {})
        for event in ({'action': 'scroll', 'selector': '#run'}, {'action': [], 'selector': '#run'}, {'action': 'click', 'selector': ''},
                      {'action': 'click', 'selector': '#run', 'frames': [None]}):
            with self.subTest(event=event), self.assertRaisesRegex(ValueError, 'RECORDER_EVENT_INVALID'):
                normalize_readiness({**event, 'readiness': {'state': 'enabled'}}, {})

    def test_manual_wait_and_collection_do_not_generate_duplicate_waits(self):
        previous = {'action': 'wait_for', 'selector': '#download', 'state': 'hidden',
                    'learning': {'source': 'manual', 'confidence': 'high'}}
        before = deepcopy(previous)
        wait, clean = normalize_readiness({'action': 'download', 'selector': '#download', 'readiness': {'state': 'enabled'}}, previous)
        self.assertIsNone(wait)
        self.assertEqual(previous, before)
        wait, clean = normalize_readiness({'action': 'download', 'selector': '#download',
                                           'collection': {'rows': 'tr', 'name': 'td', 'button': 'button'},
                                           'readiness': {'state': 'enabled'}}, {})
        self.assertIsNone(wait)
        self.assertNotIn('readiness', clean)

    def test_each_supported_action_can_consume_enabled_or_visible_readiness(self):
        for action in ('click', 'download', 'fill', 'select', 'check', 'choose', 'choose_radio', 'set_value'):
            for state in ('visible', 'enabled'):
                with self.subTest(action=action, state=state):
                    wait, clean = normalize_readiness({'action': action, 'selector': '#field', 'readiness': {'state': state}}, {})
                    self.assertEqual(wait['state'], state)
                    self.assertEqual(clean, {'action': action, 'selector': '#field'})


if __name__ == '__main__':
    unittest.main()
