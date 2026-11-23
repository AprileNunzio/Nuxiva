import hashlib
import io
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from updates import fetch
from updates.errors import UpdateCancelled, UpdateFailure

API = "https://api.github.com/repos/AprileNunzio/NUXIVA/releases"
ASSET = "https://github.com/AprileNunzio/NUXIVA/releases/download/v1.0.0/Nuxiva_Setup.exe"


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def http_error(code):
    return urllib.error.HTTPError(API, code, "x", {}, None)


class FetchTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(fetch.random, "uniform", return_value=0.0)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stop = threading.Event()

    def test_json_accept_header_is_sent_to_the_api(self):
        with mock.patch.object(fetch._OPENER, "open", return_value=Response(b"[]")) as opener:
            fetch.get(API, 100, self.stop, accept=fetch.JSON)
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Accept"), "application/vnd.github+json")

    def test_client_errors_are_not_retried_and_carry_the_status(self):
        with mock.patch.object(fetch._OPENER, "open", side_effect=http_error(415)) as opener:
            with self.assertRaises(UpdateFailure) as caught:
                fetch.get(API, 100, self.stop)
        self.assertEqual(opener.call_count, 1)
        self.assertEqual((caught.exception.code, caught.exception.detail), ("server_rejected", "HTTP 415"))

    def test_transient_errors_are_retried_with_backoff(self):
        outcomes = [http_error(503), urllib.error.URLError(TimeoutError()), Response(b"ok")]
        with mock.patch.object(fetch._OPENER, "open", side_effect=outcomes) as opener:
            self.assertEqual(fetch.get(API, 100, self.stop), b"ok")
        self.assertEqual(opener.call_count, 3)

    def test_retries_stop_after_the_limit(self):
        with mock.patch.object(fetch._OPENER, "open", side_effect=http_error(502)) as opener:
            with self.assertRaises(UpdateFailure):
                fetch.get(API, 100, self.stop)
        self.assertEqual(opener.call_count, fetch.ATTEMPTS)

    def test_stop_cancels_the_wait(self):
        self.stop.set()
        with mock.patch.object(fetch._OPENER, "open", side_effect=http_error(503)):
            with self.assertRaises(UpdateCancelled):
                fetch.get(API, 100, self.stop)

    def test_oversized_answers_are_rejected(self):
        with mock.patch.object(fetch._OPENER, "open", return_value=Response(b"x" * 101)):
            with self.assertRaises(UpdateFailure):
                fetch.get(API, 100, self.stop)

    def test_only_trusted_https_hosts(self):
        self.assertTrue(fetch.trusted(ASSET))
        for url in ("http://github.com/x", "https://evil.example/x", "https://github.com:8443/x", "https://github.com.evil.example/x"):
            with self.subTest(url=url):
                self.assertFalse(fetch.trusted(url))
                with self.assertRaises(UpdateFailure):
                    fetch.get(url, 10, self.stop)

    def test_redirects_to_untrusted_hosts_are_refused(self):
        handler = fetch._TrustedRedirects()
        with self.assertRaises(UpdateFailure):
            handler.redirect_request(mock.Mock(), None, 302, "Found", {}, "https://evil.example/file")


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / "setup.exe"
        patcher = mock.patch.object(fetch.random, "uniform", return_value=0.0)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_streams_to_disk_and_returns_the_digest(self):
        data = b"MZ" + b"\x01" * 200_000
        with mock.patch.object(fetch._OPENER, "open", return_value=Response(data)):
            digest = fetch.download(ASSET, self.target, len(data), threading.Event())
        self.assertEqual(digest, hashlib.sha256(data).hexdigest())
        self.assertEqual(self.target.read_bytes(), data)

    def test_larger_than_signed_size_is_rejected(self):
        with mock.patch.object(fetch._OPENER, "open", return_value=Response(b"x" * 20)):
            with self.assertRaises(UpdateFailure) as caught:
                fetch.download(ASSET, self.target, 10, threading.Event())
        self.assertEqual(caught.exception.code, "hash_mismatch")

    def test_truncated_download_is_retried(self):
        outcomes = [Response(b"x" * 5), Response(b"x" * 10)]
        with mock.patch.object(fetch._OPENER, "open", side_effect=outcomes) as opener:
            fetch.download(ASSET, self.target, 10, threading.Event())
        self.assertEqual(opener.call_count, 2)


if __name__ == "__main__":
    unittest.main()
