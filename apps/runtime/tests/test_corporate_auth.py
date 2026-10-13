import unittest

class CorporateAuthPolicyTests(unittest.TestCase):
    def test_sgind_origin_is_exact_and_https_only(self):
        from corporate_auth import validate_corporate_url
        validate_corporate_url("SGIND", "https://indicadoresenergisaess.scl.corp/sgind/#/home")
        for url in [
            "http://indicadoresenergisaess.scl.corp/sgind/",
            "https://indicadoresenergisaess.scl.corp.evil.example/",
            "https://user:pass@indicadoresenergisaess.scl.corp/",
            "https://indicadoresenergisaess.scl.corp:444/",
            "https://evil.example/",
        ]:
            with self.assertRaisesRegex(RuntimeError, "^CORPORATE_DESTINATION_FORBIDDEN$"):
                validate_corporate_url("SGIND", url)

    def test_unknown_iqos_and_unvalidated_sgind_remain_blocked(self):
        from corporate_auth import require_validated_adapter
        for system in ("IQOS", "SGIND", "OTHER"):
            with self.assertRaisesRegex(RuntimeError, "^CORPORATE_AUTH_NOT_VALIDATED$"):
                require_validated_adapter(system)
