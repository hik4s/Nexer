import unittest


from resolver import VariableResolver, VariableResolutionError


class VariableResolverTests(unittest.TestCase):
    def test_resolves_full_and_embedded_variables(self):
        resolver = VariableResolver(
            declarations={
                "period_start": {"type": "string", "required": True},
                "period_end": {"type": "string", "required": True},
            },
            values={
                "period_start": "2026-10-01",
                "period_end": "2026-10-31",
            },
        )

        self.assertEqual(
            resolver.resolve("{{period_start}}"),
            "2026-10-01",
        )
        self.assertEqual(
            resolver.resolve("period={{period_start}}..{{period_end}}"),
            "period=2026-10-01..2026-10-31",
        )

    def test_missing_required_variable_is_rejected(self):
        resolver = VariableResolver(
            declarations={
                "period_start": {"type": "string", "required": True},
            },
            values={},
        )

        with self.assertRaises(VariableResolutionError) as raised:
            resolver.resolve("{{period_start}}")

        self.assertIn("MISSING_VARIABLE", str(raised.exception))

    def test_secret_value_is_never_in_error_text(self):
        resolver = VariableResolver(
            declarations={
                "password": {"type": "string", "required": True, "secret": True},
            },
            values={"password": ""},
        )

        with self.assertRaises(VariableResolutionError) as raised:
            resolver.resolve("{{password}}")

        self.assertNotIn("password", str(raised.exception).lower())
        self.assertNotIn("{{password}}", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
