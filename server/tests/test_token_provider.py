import base64
import hashlib
import hmac
import importlib.util
import json
import time
import unittest
from unittest import mock

from server.core.security_guard import token_provider as module
from server.shared.errors.domain_errors import UnauthorizedException

NATIVE = importlib.util.find_spec("nuxiva_native") is not None
SECRET = "f3a9c1d7e5b2084f6a1c3e5d7b9f0a2c4e6b8d0f1a3c5e7"


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def signed(payload, secret: str = SECRET) -> str:
    body = b64(json.dumps(payload).encode())
    return f"v1.local.{body}.{b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())}"


def legacy(subject: str, claims: dict, secret: str = SECRET) -> str:
    now = int(time.time())
    return signed({"sub": subject, "iat": now, "exp": now + 3600, "claims": claims}, secret)


class ProviderContract:
    def provider(self) -> module.TokenProvider:
        raise NotImplementedError

    def test_round_trip(self):
        provider = self.provider()
        payload = provider.verify_token(provider.issue_token("tablet-1", {"role": "OPERATOR"}))
        self.assertEqual(payload["sub"], "tablet-1")
        self.assertEqual(payload["claims"], {"role": "OPERATOR"})
        self.assertEqual(payload["exp"] - payload["iat"], module.security_config.TOKEN_EXPIRATION_MINUTES * 60)

    def test_tokens_from_the_previous_implementation_stay_valid(self):
        payload = self.provider().verify_token(legacy("supervisor", {"device_type": "pc", "role": "OPERATOR"}))
        self.assertEqual(payload["claims"]["device_type"], "pc")

    def test_rejections_are_unauthorized_never_crashes(self):
        provider, now = self.provider(), int(time.time())
        bad = [
            "", "garbage", "v1.local.", "v2.local.a.b", "v1.local.%%%.%%%", "v1.local." + "a" * 9000,
            legacy("x", {}, secret="another-secret-another-secret-0123456789"),
            legacy("x", {})[:-1] + ("A" if legacy("x", {})[-1] != "A" else "B"),
            signed({"sub": "x", "iat": now - 100, "exp": now - 10, "claims": {}}),
            signed({"sub": "x", "iat": now + 600, "exp": now + 900, "claims": {}}),
            signed({"sub": "x", "iat": now, "exp": now + 10}),
            signed({"sub": "x", "iat": now, "exp": now + 10, "claims": {}, "admin": True}),
            signed({"sub": "", "iat": now, "exp": now + 10, "claims": {}}),
            signed({"sub": "x", "iat": now, "exp": True, "claims": {}}),
            signed({"sub": "x", "iat": now, "exp": now + 10, "claims": []}),
            signed(["x"]),
        ]
        for token in bad:
            with self.subTest(token=token[:60]), self.assertRaises(UnauthorizedException):
                provider.verify_token(token)
        with self.assertRaises(UnauthorizedException):
            provider.verify_token(None)

    def test_reason_codes_are_exposed(self):
        now = int(time.time())
        with self.assertRaises(UnauthorizedException) as ctx:
            self.provider().verify_token(signed({"sub": "x", "iat": now - 100, "exp": now - 10, "claims": {}}))
        self.assertEqual(ctx.exception.details["reason"], "token.expired")

    def test_invalid_issue_requests_are_refused(self):
        provider = self.provider()
        for subject, claims in (("", {}), ("a\nb", {}), ("x" * 300, {}), ("ok", {"blob": "x" * 5000})):
            with self.subTest(subject=subject[:10]), self.assertRaises(UnauthorizedException):
                provider.issue_token(subject, claims)

    def test_weak_secret_disables_the_service(self):
        with mock.patch.object(module, "log"):
            for secret in ("short", "0" * 64):
                provider = self.make(secret)
                self.assertEqual(provider.engine, "disabled")
                with self.assertRaises(UnauthorizedException):
                    provider.issue_token("x", {})
                with self.assertRaises(UnauthorizedException):
                    provider.verify_token(legacy("x", {}, secret=secret))


class SoftwareTokenTest(ProviderContract, unittest.TestCase):
    def make(self, secret: str) -> module.TokenProvider:
        with mock.patch.object(module, "nuxiva_native", None):
            return module.TokenProvider(secret)

    def provider(self) -> module.TokenProvider:
        provider = self.make(SECRET)
        self.assertEqual(provider.engine, "software")
        return provider


@unittest.skipUnless(NATIVE, "nuxiva_native non disponibile")
class NativeTokenTest(ProviderContract, unittest.TestCase):
    def make(self, secret: str) -> module.TokenProvider:
        return module.TokenProvider(secret)

    def provider(self) -> module.TokenProvider:
        provider = self.make(SECRET)
        self.assertEqual(provider.engine, "native")
        return provider

    def test_native_and_software_tokens_interoperate(self):
        native = self.provider()
        software = SoftwareTokenTest.make(self, SECRET)
        self.assertEqual(software.verify_token(native.issue_token("a", {"r": 1}))["claims"], {"r": 1})
        self.assertEqual(native.verify_token(software.issue_token("b", {"r": 2}))["claims"], {"r": 2})


if __name__ == "__main__":
    unittest.main()
