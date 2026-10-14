import unittest
from target_picker_contract import validate_configuration, validate_target


class TargetContractTests(unittest.TestCase):
    def test_only_configured_url_and_supported_kind_are_accepted(self):
        self.assertEqual(validate_configuration({'url': 'https://example.test/form', 'kind': 'text'}),
                         {'url': 'https://example.test/form', 'kind': 'text'})
        for config in [{'url': 'http://other.test/', 'kind': 'text'},
                       {'url': 'https://example.test/?token=private', 'kind': 'text'},
                       {'url': 'https://example.test/', 'kind': 'password'},
                       {'url': 'https://example.test/', 'kind': 'text', 'value': 'private'}]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                validate_configuration(config)

    def test_generated_structural_selectors_only(self):
        for selector in ['#company', 'input[type="text"]', 'form[name="search"] input',
                         'html:nth-of-type(1) > body:nth-of-type(1) > button:nth-of-type(2)',
                         'x-host input[role="textbox"]', 'div[contenteditable=""]']:
            self.assertEqual(validate_target({'selector': selector}), {'selector': selector})
        for selector in ['#private-canary', 'input[value="private-canary"]', 'text=private',
                         'button:has-text("private")', '#search, #run', ':scope', 'a[href="/private"]',
                         'input[name="secret"]', 'x' * 2049]:
            with self.subTest(selector=selector), self.assertRaises(ValueError):
                validate_target({'selector': selector})
        with self.assertRaises(ValueError):
            validate_target({'selector': '#search', 'value': 'private-canary'})
