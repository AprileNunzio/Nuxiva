import itertools
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

for p in (str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[1] / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

import auth
import env_format
import https_guard
import identity
import native_core
from origin_guard import OriginGuard

NATIVE = native_core.load()
GUARD_SYMBOLS = ("RustSessionCodec", "RustLoginLimiter", "RustOriginGuard", "guard_safe_host",
                 "guard_redirect_target", "env_decode_value", "env_format_line", "env_entries",
                 "env_normalize", "identity_normalize_name")
READY = NATIVE is not None and all(hasattr(NATIVE, name) for name in GUARD_SYMBOLS)

HOSTS = ["", "nuxiva.local", "NUXIVA.LOCAL:8080", "evil.com", "box", "box:80", "[::1]:8080", "[fe80::1]",
         "192.168.1.5", "192.168.1.5:443", "user@box", "a b", "evil.com/@x", "nas.local", "x.localhost",
         "[0:0:0:0:0:0:0:1]", "[1:0:0:2:0:0:0:3]:80", "-bad", ".bad", "a..b", "host:", "host:99999",
         "host:123456", "  box.local  ", "01.2.3.4", "256.1.1.1", "[::]"]
ORIGINS = ["", "null", "http://box", "https://evil.com", "http://BOX:80", "http://[::1]:8080", "box",
           "http://user@box/path?x", "file:///etc", "http://nas.local"]
METHODS = ["GET", "POST", "put", "DELETE", "PATCH", "HEAD", "OPTIONS"]
SITES = ["", "same-origin", "cross-site", "CROSS-SITE", "none"]
ENV_VALUES = ["", "plain", "  spaced  ", "\"quoted\"", "'single'", "\"a\\\"b\\$c\"", "'\"x\"'", "\"a\" \"b\"",
              "\"\\u00e9\"", "\"\\ud83d\\ude00\"", "\"bad\\q\"", "\"\"", "''", "\"'\"", "x=y", "é ù 😀",
              "\"tab\\tnl\"", "'  inner  '"]
NAMES = ["", "  hey   nuxiva  ", "OKAY Friday", "ok", "okay", "MAX", "<script>", "!!!", "ｎｕｘｉｖａ",
         "a" * 50, "Anna   Maria", "Ehi Luna", "hé Zoé", "R2-D2", "O'Neil", "Jean.Luc", "日本", "ÉLODIE",
         "hi\tthere", "x"]


def scope(path="/", host="192.168.1.5:8080", client="192.168.1.20", scheme="http", method="GET",
          mode="navigate", accept="", query=b""):
    headers = [(b"host", host.encode("latin-1"))]
    if mode:
        headers.append((b"sec-fetch-mode", mode.encode()))
    if accept:
        headers.append((b"accept", accept.encode()))
    return {"type": "http", "scheme": scheme, "method": method, "path": path, "query_string": query,
            "client": (client, 5000), "headers": headers}


@unittest.skipUnless(READY, "modulo nativo guard-core non installato")
class GuardParityTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.object(auth, "_SECRET_FILE", Path(self.tmp.name) / "session.key")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_sessions_cross_verify_between_engines(self):
        for user in ("admin", "display", "a|b", "utente.ü"):
            with self.subTest(user=user):
                rust_token = auth.issue(user)
                python_token = auth._py_issue(user)
                self.assertEqual(auth._py_verify(rust_token), user)
                self.assertEqual(auth.verify(python_token), user)
                self.assertEqual(auth.verify(rust_token), user)

    def test_sessions_reject_the_same_forgeries(self):
        token = auth.issue("admin")
        for forged in ("", "!!!", token[:-4] + "AAAA", "A" * 64, token.swapcase()):
            with self.subTest(token=forged):
                self.assertEqual(auth.verify(forged), auth._py_verify(forged))

    def test_expired_session_is_rejected(self):
        token = auth.issue("admin")
        with mock.patch("auth.time.time", return_value=10 ** 12):
            self.assertIsNone(auth.verify(token))
            self.assertIsNone(auth._py_verify(token))

    def test_limiter_matches_python_window(self):
        auth._engines.update(limiter=None, limiter_key=None)
        auth._failures.clear()
        for _ in range(5):
            self.assertFalse(auth.rate_limited("10.0.0.9"))
            auth._record_failure("10.0.0.9")
        self.assertTrue(auth.rate_limited("10.0.0.9"))
        with mock.patch("auth.time.time", return_value=auth.time.time() + 301):
            self.assertFalse(auth.rate_limited("10.0.0.9"))

    def test_origin_verdicts_match(self):
        guard = OriginGuard(None, extra_hosts=("box",))
        for host, origin, method, site in itertools.product(HOSTS, ORIGINS, METHODS, SITES):
            headers = [(b"host", host.encode())]
            if origin:
                headers.append((b"origin", origin.encode()))
            if site:
                headers.append((b"sec-fetch-site", site.encode()))
            request = {"type": "http", "method": method, "headers": headers}
            with self.subTest(host=host, origin=origin, method=method, site=site):
                self.assertEqual(guard.verdict(request), guard._py_verdict(request))

    def test_safe_hosts_match(self):
        for host in HOSTS:
            with self.subTest(host=host):
                self.assertEqual(https_guard._safe_host(host), https_guard._py_safe_host(host))

    def test_redirect_targets_match(self):
        paths = ["/", "/apps/people", "/a b/é", "/healthz", "/api/health/x", "/nuxiva-ca.crt", "/%2e%2e"]
        queries = [b"", b"a=1&b=2", b"x=\xe9", b"q=a+b%20c", b"k=<script>"]
        variants = [dict(), dict(client="127.0.0.1"), dict(scheme="https"), dict(method="POST"),
                    dict(mode="cors"), dict(mode="", accept="text/html"), dict(mode="", accept="")]
        for path, query, extra, host, admin, port in itertools.product(
                paths, queries, variants, HOSTS[:12], (False, True), (0, 443, 8444)):
            s = scope(path=path, query=query, host=host, **extra)
            with self.subTest(path=path, query=query, extra=extra, host=host, admin=admin, port=port):
                self.assertEqual(https_guard.redirect_target(s, admin, port),
                                 https_guard._py_redirect_target(s, admin, port))

    def test_env_values_match(self):
        for value in ENV_VALUES:
            with self.subTest(value=value):
                self.assertEqual(env_format.decode_value(value), env_format._py_decode_value(value))
                if not any(c in value for c in "\n\r\0"):
                    self.assertEqual(env_format.format_line("KEY", value), env_format._py_format_line("KEY", value))
        for key, value in (("1BAD", "x"), ("OK", "a\nb"), ("A-B", "x"), ("OK", "a\0b")):
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    env_format._py_format_line(key, value)
                with self.assertRaises(ValueError):
                    env_format.format_line(key, value)

    def test_env_files_match(self):
        text = ("# commento\nA=1\r\nA=2\n'B'=\"x y\"\nbad line\n9X=1\n  C = 'z'  \nD=\"\\u00e9\\$HOME\"\n"
                "E=\x0bF=2\u2028G=3\n")
        self.assertEqual(list(env_format.entries(text)), list(env_format._py_entries(text)))
        self.assertEqual(env_format.normalize(text), env_format._py_normalize(text))

    def test_assistant_names_match(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual(identity.normalize_name(name), identity._py_normalize_name(name))


class GuardFallbackTest(unittest.TestCase):

    def test_python_engine_still_answers_without_native_module(self):
        with mock.patch.object(native_core, "load", return_value=None), \
                mock.patch("native_module.feature", return_value=None):
            self.assertEqual(identity.normalize_name("hey Luna"), "Luna")
            self.assertEqual(env_format.decode_value("'x'"), "x")
            self.assertEqual(https_guard._safe_host("Box.Local:80"), "box.local")
            with tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(auth, "_SECRET_FILE", Path(tmp) / "session.key"):
                self.assertEqual(auth.verify(auth.issue("admin")), "admin")
                self.assertEqual((Path(tmp) / "session.key").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
