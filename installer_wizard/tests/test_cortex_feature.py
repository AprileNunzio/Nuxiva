import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.cortex import api


class CortexFeatureTests(unittest.TestCase):
    def test_status_route_requires_an_admin_session(self):
        app = FastAPI()
        app.include_router(api.admin_routes)
        response = TestClient(app).get("/api/v1/cognition/hippocampus/status")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
