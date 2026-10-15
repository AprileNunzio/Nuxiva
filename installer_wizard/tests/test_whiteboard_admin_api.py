import unittest

from fastapi.testclient import TestClient

import nuxiva_supervisor

HEADERS = {"X-Nuxiva-Request": "1"}


class WhiteboardAdminApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(nuxiva_supervisor.admin)
        self.client.post("/api/auth/login", json={"username": "admin", "password": "nuxiva"}, headers=HEADERS)

    def test_requires_session_and_csrf(self):
        anonymous = TestClient(nuxiva_supervisor.admin)
        self.assertEqual(anonymous.get("/api/board").status_code, 401)
        self.assertEqual(self.client.post("/api/board/undo", json={}).status_code, 403)

    def test_board_view_is_served(self):
        data = self.client.get("/api/board").json()
        self.assertIn("rev", data)
        self.assertIn("items", data)

    def test_invalid_page_is_rejected(self):
        for page in ("2", 1.5, True, None):
            r = self.client.post("/api/board/page/switch", json={"page": page}, headers=HEADERS)
            self.assertEqual(r.status_code, 400, page)

    def test_save_names_are_validated(self):
        self.assertEqual(self.client.post("/api/board/save", json={"name": "../../"}, headers=HEADERS).status_code, 400)
        self.assertEqual(self.client.post("/api/board/load", json={"name": "missing board zz"}, headers=HEADERS).status_code, 404)
        self.assertEqual(self.client.post("/api/board/delete_save", json={"name": "missing board zz"}, headers=HEADERS).status_code, 404)


if __name__ == "__main__":
    unittest.main()
