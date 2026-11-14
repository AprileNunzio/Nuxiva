import unittest
from unittest import mock

import native_core
from fastapi import Request

from agenti.desktop import host_origin
from agenti.desktop.display_scope import is_host_display, remote_display_scope

LOCALS = ["192.168.1.197", "10.0.0.5", "fe80::1%eth0", "2001:db8::10", "172.17.0.2", "0.0.0.0", "garbage"]
CASES = [
    ("127.0.0.1", "localhost:8080"),
    ("::1", "[::1]:8080"),
    ("127.0.0.5", "127.0.0.1"),
    ("localhost", "LOCALHOST."),
    ("192.168.1.197", "192.168.1.197"),
    ("192.168.1.197", "192.168.1.197:80"),
    ("10.0.0.5", "localhost"),
    ("172.17.0.2", "172.17.0.2"),
    ("2001:db8::10", "[2001:db8::10]:80"),
    ("fe80::1%eth0", "[fe80::1]"),
    ("::ffff:192.168.1.197", "192.168.1.197"),
    ("192.168.1.20", "192.168.1.197"),
    ("192.168.1.20", "localhost"),
    ("2001:db8::99", "[2001:db8::10]"),
    ("8.8.8.8", "127.0.0.1"),
    ("127.0.0.1", "nuxiva.local"),
    ("127.0.0.1", "evil.example:80"),
    ("192.168.1.197", "nuxiva.lan"),
    ("127.0.0.1", "localhost.evil.example"),
    ("192.168.1.197", "192.168.1.20"),
    ("127.0.0.1", ""),
    ("127.0.0.1", "[::1"),
    ("127.0.0.1", "local\nhost"),
    ("", "localhost"),
    ("not-an-ip", "localhost"),
    ("0.0.0.0", "0.0.0.0"),
    ("224.0.0.1", "224.0.0.1"),
    ("::", "[::]"),
]
EXPECTED = {
    CASES[i]: value
    for i, value in enumerate([True, True, True, True, True, True, True, True, True, True, True,
                               False, False, False, False, False, False, False, False, False,
                               False, False, False, False, False, False, False, False])
}


def request(peer, host, forwarded=None):
    headers = [(b"host", host.encode())]
    if forwarded:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request({"type": "http", "scheme": "http", "path": "/", "headers": headers,
                    "client": (peer, 50000), "server": ("127.0.0.1", 8080)})


class HostOriginTest(unittest.TestCase):
    def test_python_engine_decisions(self):
        for case, expected in EXPECTED.items():
            with self.subTest(case=case):
                self.assertIs(host_origin.python_is_host_origin(case[0], case[1], LOCALS), expected)

    @unittest.skipIf(native_core.symbol("access_is_host_origin") is None, "native module missing")
    def test_native_engine_matches_python(self):
        native = native_core.symbol("access_is_host_origin")
        for case, expected in EXPECTED.items():
            with self.subTest(case=case):
                self.assertIs(native(case[0], case[1], LOCALS), expected)
                self.assertIs(native(case[0], case[1], LOCALS), host_origin.python_is_host_origin(case[0], case[1], LOCALS))

    def test_empty_local_set_trusts_only_loopback(self):
        self.assertTrue(host_origin.python_is_host_origin("127.0.0.1", "localhost", []))
        self.assertFalse(host_origin.python_is_host_origin("192.168.1.197", "192.168.1.197", []))

    def test_local_set_is_bounded(self):
        many = [f"10.1.{a}.{b}" for a in range(10) for b in range(250)]
        self.assertTrue(host_origin.python_is_host_origin("10.1.0.0", "127.0.0.1", many))
        self.assertFalse(host_origin.python_is_host_origin("10.1.9.100", "127.0.0.1", many))

    def test_enumeration_is_cached_and_refreshed(self):
        host_origin.reset_cache()
        with mock.patch.object(host_origin, "_interface_addresses", side_effect=[["10.0.0.5"], ["10.0.0.6"]]) as scan:
            self.assertEqual(host_origin.local_addresses(100.0), ("10.0.0.5",))
            self.assertEqual(host_origin.local_addresses(105.0), ("10.0.0.5",))
            self.assertEqual(host_origin.local_addresses(200.0), ("10.0.0.6",))
            self.assertEqual(scan.call_count, 2)
        host_origin.reset_cache()

    def test_forced_python_fallback_decides_the_same(self):
        with mock.patch.dict("os.environ", {"NUXIVA_NATIVE": "0"}):
            self.assertTrue(host_origin.is_host_origin("192.168.1.197", "192.168.1.197", LOCALS))
            self.assertFalse(host_origin.is_host_origin("192.168.1.20", "192.168.1.197", LOCALS))


class HostDisplayScopeTest(unittest.TestCase):
    def setUp(self):
        host_origin.reset_cache()
        patcher = mock.patch.object(host_origin, "_interface_addresses", return_value=list(LOCALS))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(host_origin.reset_cache)

    def test_browsing_through_the_machine_own_lan_address_is_the_host_display(self):
        self.assertTrue(is_host_display(request("192.168.1.197", "192.168.1.197")))
        self.assertFalse(remote_display_scope(request("192.168.1.197", "192.168.1.197")))

    def test_real_lan_clients_stay_remote(self):
        self.assertFalse(is_host_display(request("192.168.1.20", "192.168.1.197")))
        self.assertTrue(remote_display_scope(request("192.168.1.20", "192.168.1.197")))

    def test_proxy_headers_never_grant_host_scope(self):
        self.assertFalse(is_host_display(request("127.0.0.1", "localhost", "192.168.1.20")))
        self.assertFalse(is_host_display(request("192.168.1.197", "192.168.1.197", "203.0.113.9")))

    def test_rebinding_names_stay_remote(self):
        self.assertFalse(is_host_display(request("127.0.0.1", "nuxiva.local")))
        self.assertFalse(is_host_display(request("192.168.1.197", "attacker.example")))

    def test_missing_client_is_remote(self):
        scope = {"type": "http", "scheme": "http", "path": "/", "headers": [(b"host", b"localhost")], "server": ("127.0.0.1", 8080)}
        self.assertFalse(is_host_display(Request(scope)))


if __name__ == "__main__":
    unittest.main()
