import asyncio
import unittest
from unittest import mock

import https_guard


def scope(path="/", host="192.168.1.5:8080", client="192.168.1.20", scheme="http", method="GET", mode="navigate", query=b""):
    headers = [(b"host", host.encode())]
    if mode:
        headers.append((b"sec-fetch-mode", mode.encode()))
    return {"type": "http", "scheme": scheme, "method": method, "path": path, "query_string": query,
            "client": (client, 5000), "headers": headers}


class RedirectTest(unittest.TestCase):
    def test_remote_browser_on_admin_port_goes_to_https_admin(self):
        self.assertEqual(https_guard.redirect_target(scope("/apps/people"), True, 443), "https://192.168.1.5/admin/apps/people")

    def test_public_port_keeps_path_and_query_and_non_default_port(self):
        target = https_guard.redirect_target(scope("/display", host="casa.local", query=b"a=1&b=2"), False, 8444)
        self.assertEqual(target, "https://casa.local:8444/display?a=1&b=2")

    def test_loopback_kiosk_stays_on_http(self):
        self.assertEqual(https_guard.redirect_target(scope(client="127.0.0.1"), False, 443), "")

    def test_api_calls_and_unsafe_methods_are_not_redirected(self):
        self.assertEqual(https_guard.redirect_target(scope(mode="cors"), False, 443), "")
        self.assertEqual(https_guard.redirect_target(scope(method="POST"), False, 443), "")

    def test_certificate_download_stays_reachable_over_http(self):
        self.assertEqual(https_guard.redirect_target(scope("/nuxiva-ca.crt"), False, 443), "")

    def test_no_redirect_without_a_running_tls_server(self):
        self.assertEqual(https_guard.redirect_target(scope(), False, 0), "")

    def test_hostile_host_header_is_refused(self):
        self.assertEqual(https_guard.redirect_target(scope(host="evil.com/@x"), False, 443), "")
        self.assertEqual(https_guard.redirect_target(scope(host="a b"), False, 443), "")

    def test_ipv6_host_is_bracketed(self):
        self.assertEqual(https_guard.redirect_target(scope(host="[fe80::1]:80"), False, 443), "https://[fe80::1]/")

    def test_accept_header_used_when_fetch_metadata_is_missing(self):
        s = scope(mode="")
        s["headers"].append((b"accept", b"text/html,application/xhtml+xml"))
        self.assertEqual(https_guard.redirect_target(s, False, 443), "https://192.168.1.5/")


class MiddlewareTest(unittest.TestCase):
    def run_app(self, s):
        sent = []

        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": [(b"permissions-policy", b"camera=()")]})
            await send({"type": "http.response.body", "body": b"ok"})

        async def send(message):
            sent.append(message)

        async def receive():
            return {"type": "http.request"}

        with mock.patch.object(https_guard, "tls_port", return_value=443), mock.patch.object(https_guard, "enforced", return_value=True):
            asyncio.run(https_guard.HttpsGuard(app)(s, receive, send))
        return sent

    def test_redirect_response_is_permanent_and_uncached(self):
        start = self.run_app(scope())[0]
        headers = dict(start["headers"])
        self.assertEqual(start["status"], 308)
        self.assertEqual(headers[b"location"], b"https://192.168.1.5/")
        self.assertEqual(headers[b"cache-control"], b"no-store")

    def test_https_responses_carry_hsts_and_keep_existing_policies(self):
        headers = dict(self.run_app(scope(scheme="https"))[0]["headers"])
        self.assertEqual(headers[b"strict-transport-security"], https_guard.HSTS)
        self.assertEqual(headers[b"permissions-policy"], b"camera=()")
        self.assertEqual(headers[b"x-content-type-options"], b"nosniff")

    def test_plain_http_loopback_has_no_hsts(self):
        headers = dict(self.run_app(scope(client="127.0.0.1"))[0]["headers"])
        self.assertNotIn(b"strict-transport-security", headers)
        self.assertEqual(headers[b"referrer-policy"], b"same-origin")


if __name__ == "__main__":
    unittest.main()
