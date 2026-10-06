import unittest

from fastapi.testclient import TestClient

from app.main import app


class BackendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_exposes_api_identity(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"name": "RelatPy API", "version": "0.1.0"},
        )

    def test_version_exposes_version(self):
        response = self.client.get("/version")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"api": "RelatPy API", "version": "0.1.0"},
        )

    def test_metrics_exposes_safe_runtime_metrics(self):
        response = self.client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["service"], "relatpy-api")
        self.assertEqual(body["version"], "0.1.0")
        self.assertIsInstance(body["requests_total"], int)
        self.assertGreaterEqual(body["requests_total"], 1)


if __name__ == "__main__":
    unittest.main()
