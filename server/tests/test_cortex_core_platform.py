import json
import re
import unittest
from pathlib import Path

from fastapi import FastAPI

from server.core.core_platform.errors import CortexFailure, fail, translate_code
from server.core.core_platform.input_sanitizer import sanitize_identifier, sanitize_utterance
from server.core.core_platform.native_bridge import call_native
from server.core.core_platform.result import Err, Ok
from server.core.core_platform.zero_trust_crypto import SignedBlob, ZeroTrustVault
from server.shared.errors.global_handler import register_global_error_handlers
from server.tests.cortex_support import SECRET, asgi_get, requires_native

ROOT = Path(__file__).resolve().parents[2]
RUST_ERRORS = ROOT / "native" / "crates" / "cortex-core" / "src" / "platform" / "error.rs"
LANGUAGE_DIR = ROOT / "server" / "core" / "core_platform" / "language"
LANGUAGES = ("it", "en", "es", "fr")
PLATFORM_CODES = (
    "platform.native.unavailable",
    "platform.native.outdated",
    "platform.vault.weak_secret",
    "platform.storage.io_failed",
    "hippocampus.embedding.unavailable",
    "hippocampus.embedding.failed",
    "hippocampus.storage.undecryptable",
    "hippocampus.storage.corrupted",
    "hippocampus.skills.unavailable",
    "hippocampus.service.degraded",
    "gliner.unavailable",
    "gliner.inference_failed",
)


def flatten(tree: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for name, value in tree.items():
        path = f"{prefix}.{name}" if prefix else name
        keys |= flatten(value, path) if isinstance(value, dict) else {path}
    return keys


def rust_codes() -> list[str]:
    return re.findall(r'"(cortex\.[a-z_.]+)"', RUST_ERRORS.read_text(encoding="utf-8"))


class ResultTests(unittest.TestCase):
    def test_ok_transforms_and_chains(self):
        value = Ok(2).map(lambda x: x + 1).and_then(lambda x: Ok(x * 2))
        self.assertTrue(value.is_ok)
        self.assertEqual(value.unwrap(), 6)
        self.assertEqual(value.unwrap_or(0), 6)

    def test_err_short_circuits_and_unwrap_raises(self):
        failure = fail("cortex.input.empty")
        chained = failure.map(lambda x: x + 1).and_then(lambda x: Ok(x))
        self.assertFalse(chained.is_ok)
        self.assertIs(chained, failure)
        self.assertEqual(failure.unwrap_or(7), 7)
        with self.assertRaises(CortexFailure):
            failure.unwrap()


class ErrorCatalogTests(unittest.TestCase):
    def test_every_native_and_platform_code_is_translated_in_every_language(self):
        codes = rust_codes() + list(PLATFORM_CODES)
        self.assertGreaterEqual(len(codes), 30)
        for lang in LANGUAGES:
            for code in codes:
                with self.subTest(lang=lang, code=code):
                    self.assertTrue(translate_code(code, lang).strip())

    def test_languages_share_the_same_keys(self):
        trees = {lang: json.loads((LANGUAGE_DIR / f"{lang}.json").read_text(encoding="utf-8")) for lang in LANGUAGES}
        reference = flatten(trees["it"])
        for lang in LANGUAGES:
            with self.subTest(lang=lang):
                self.assertEqual(flatten(trees[lang]), reference)
                self.assertEqual(trees[lang]["meta"]["locale"], lang)

    def test_status_codes_follow_the_failure_class(self):
        self.assertEqual(CortexFailure("cortex.input.empty").status_code, 422)
        self.assertEqual(CortexFailure("cortex.slots.required_missing").status_code, 422)
        self.assertEqual(CortexFailure("cortex.neuron.unknown").status_code, 404)
        self.assertEqual(CortexFailure("platform.native.unavailable").status_code, 503)
        self.assertEqual(CortexFailure("hippocampus.embedding.unavailable").status_code, 503)
        self.assertEqual(CortexFailure("cortex.crypto.decryption_failed").status_code, 500)

    def test_global_handler_maps_failures_to_http_statuses(self):
        app = FastAPI()
        register_global_error_handlers(app)

        @app.get("/empty")
        async def empty():
            raise CortexFailure("cortex.input.empty", "en")

        @app.get("/missing")
        async def missing():
            raise CortexFailure("cortex.neuron.unknown", "en")

        status, body = asgi_get(app, "/empty")
        self.assertEqual(status, 422)
        self.assertEqual(body["code"], "cortex.input.empty")
        self.assertEqual(asgi_get(app, "/missing")[0], 404)

    def test_failure_message_is_localised(self):
        self.assertIn("vuoto", CortexFailure("cortex.input.empty", "it").message)
        self.assertIn("empty", CortexFailure("cortex.input.empty", "en").message)


@requires_native
class SanitizerTests(unittest.TestCase):
    def test_hostile_text_is_normalised_or_rejected(self):
        self.assertEqual(sanitize_utterance("  ｓｐｅｇｎｉ​  la luce ").unwrap(), "spegni la luce")
        self.assertEqual(sanitize_utterance("a\x00b").error.code, "cortex.input.forbidden_characters")
        self.assertEqual(sanitize_utterance("   ").error.code, "cortex.input.empty")
        self.assertEqual(sanitize_utterance("x" * 5000).error.code, "cortex.input.too_long")

    def test_identifiers_reject_path_traversal(self):
        self.assertEqual(sanitize_identifier("light.on-1").unwrap(), "light.on-1")
        self.assertEqual(sanitize_identifier("../secret").error.code, "cortex.input.invalid_identifier")

    def test_native_errors_are_returned_as_values(self):
        outcome = call_native(lambda native: native.cortex_sanitize_utterance("", 10))
        self.assertIsInstance(outcome, Err)
        self.assertEqual(outcome.error.code, "cortex.input.empty")


@requires_native
class VaultTests(unittest.TestCase):
    def setUp(self):
        self.vault = ZeroTrustVault(lambda: SECRET)

    def test_json_round_trip_with_bound_context(self):
        sealed = self.vault.seal_json("memory", {"neuron": "light.on", "weight": 0.8}, b"aad").unwrap()
        self.assertNotIn(b"light.on", sealed)
        self.assertEqual(self.vault.open_json("memory", sealed, b"aad").unwrap(), {"neuron": "light.on", "weight": 0.8})
        self.assertEqual(self.vault.open_json("memory", sealed, b"other").error.code, "cortex.crypto.decryption_failed")
        self.assertEqual(self.vault.open_json("skills", sealed, b"aad").error.code, "cortex.crypto.decryption_failed")

    def test_other_master_secret_cannot_open(self):
        sealed = self.vault.seal_bytes("memory", b"payload").unwrap()
        stranger = ZeroTrustVault(lambda: "another-master-secret-0123456789abcdef")
        self.assertEqual(stranger.open_bytes("memory", sealed).error.code, "cortex.crypto.decryption_failed")

    def test_weak_master_secret_is_refused(self):
        weak = ZeroTrustVault(lambda: "short")
        self.assertEqual(weak.seal_bytes("memory", b"x").error.code, "platform.vault.weak_secret")
        self.assertEqual(weak.sign("skills", b"x").error.code, "platform.vault.weak_secret")

    def test_signatures_are_bound_to_purpose_and_payload(self):
        blob = self.vault.sign("skills", b"def run(): return 1").unwrap()
        self.assertTrue(self.vault.verify("skills", blob).unwrap())
        self.assertFalse(self.vault.verify("other", blob).unwrap())
        forged = SignedBlob(b"def run(): return 2", blob.signature, blob.public_key)
        self.assertFalse(self.vault.verify("skills", forged).unwrap())
        truncated = SignedBlob(blob.payload, blob.signature[:10], blob.public_key)
        self.assertEqual(self.vault.verify("skills", truncated).error.code, "cortex.crypto.malformed_signature")


if __name__ == "__main__":
    unittest.main()
