import unittest

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


class BackendSafetyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_local_configuration_defaults_are_safe(self):
        settings = Settings()

        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.port, 8000)
        self.assertEqual(settings.environment, "local")
        self.assertIn("http://127.0.0.1:5173", settings.cors_origins)
        self.assertIn("http://localhost:5173", settings.cors_origins)

    def test_not_found_uses_standard_error_schema(self):
        response = self.client.get("/this-route-does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json(),
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Route not found",
                    "details": None,
                }
            },
        )

    def test_cors_allows_only_development_origins(self):
        allowed = self.client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        denied = self.client.get(
            "/health",
            headers={"Origin": "https://example.com"},
        )

        self.assertEqual(
            allowed.headers.get("access-control-allow-origin"),
            "http://localhost:5173",
        )
        self.assertNotIn("access-control-allow-origin", denied.headers)


if __name__ == "__main__":
    unittest.main()
