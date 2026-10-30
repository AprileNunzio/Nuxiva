import base64
import binascii
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict

from server.config.env import settings
from server.config.security import security_config
from server.shared.errors.domain_errors import UnauthorizedException

try:
    import nuxiva_native
except ImportError:
    nuxiva_native = None

log = logging.getLogger("nuxiva.security.token")

PREFIX = "v1.local."
MAX_TOKEN = 8192
MAX_CLAIMS = 4096
MAX_SUBJECT = 256
MIN_SECRET = 32
MAX_TTL = 30 * 24 * 3600
SKEW = 60
SIGNATURE_CHARS = 43
PAYLOAD_KEYS = {"sub", "iat", "exp", "claims"}


class TokenRejected(ValueError):
    pass


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    if "=" in text or len(text) % 4 == 1:
        raise TokenRejected("token.format")
    try:
        raw = base64.b64decode((text + "=" * (-len(text) % 4)).encode("ascii"), altchars=b"-_", validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise TokenRejected("token.format") from exc
    if _b64encode(raw) != text:
        raise TokenRejected("token.format")
    return raw


def _valid_subject(subject: Any) -> bool:
    return isinstance(subject, str) and 0 < len(subject) <= MAX_SUBJECT and subject.isprintable()


def _strict_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def native_ready() -> bool:
    return nuxiva_native is not None and hasattr(nuxiva_native, "RustTokenCodec")


class SoftwareTokenCodec:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < MIN_SECRET or len(set(secret)) < 2:
            raise TokenRejected("token.secret.weak")
        self._secret = secret

    def _sign(self, body: str) -> bytes:
        return hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).digest()

    def issue(self, subject: str, claims_json: str, now: int, ttl: int) -> str:
        if not _valid_subject(subject):
            raise TokenRejected("token.subject.invalid")
        if not 0 < ttl <= MAX_TTL:
            raise TokenRejected("token.lifetime.invalid")
        if len(claims_json) > MAX_CLAIMS or not isinstance(json.loads(claims_json), dict):
            raise TokenRejected("token.claims.invalid")
        payload = {"sub": subject, "iat": now, "exp": now + ttl, "claims": json.loads(claims_json)}
        body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        token = f"{PREFIX}{body}.{_b64encode(self._sign(body))}"
        if len(token) > MAX_TOKEN:
            raise TokenRejected("token.too_large")
        return token

    def verify(self, token: str, now: int) -> str:
        if len(token) > MAX_TOKEN:
            raise TokenRejected("token.too_large")
        if not token.startswith(PREFIX):
            raise TokenRejected("token.format")
        body, dot, signature = token[len(PREFIX):].partition(".")
        if not dot or not body or len(signature) != SIGNATURE_CHARS or not body.isascii():
            raise TokenRejected("token.format")
        expected = _b64decode(signature)
        if not hmac.compare_digest(expected, self._sign(body)):
            raise TokenRejected("token.signature")
        try:
            payload = json.loads(_b64decode(body).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TokenRejected("token.payload") from exc
        if not isinstance(payload, dict) or set(payload) != PAYLOAD_KEYS or not isinstance(payload["claims"], dict):
            raise TokenRejected("token.payload")
        if not _valid_subject(payload["sub"]) or not _strict_int(payload["iat"]) or not _strict_int(payload["exp"]):
            raise TokenRejected("token.payload")
        if payload["exp"] < payload["iat"]:
            raise TokenRejected("token.payload")
        if payload["exp"] < now:
            raise TokenRejected("token.expired")
        if payload["iat"] > now + SKEW:
            raise TokenRejected("token.not_yet_valid")
        return json.dumps(payload, separators=(",", ":"))


def _codec(secret: bytes):
    if native_ready():
        try:
            return nuxiva_native.RustTokenCodec(secret)
        except nuxiva_native.TokenRejected as exc:
            raise TokenRejected(str(exc)) from exc
    return SoftwareTokenCodec(secret)


def _rejections() -> tuple:
    return (TokenRejected, nuxiva_native.TokenRejected) if native_ready() else (TokenRejected,)


class TokenProvider:
    def __init__(self, secret_key: str = settings.NUXIVA_SECRET_KEY):
        try:
            self._codec = _codec(secret_key.encode("utf-8"))
        except TokenRejected:
            log.error("NUXIVA_SECRET_KEY troppo debole: token disabilitati finche non viene sostituita")
            self._codec = None

    @property
    def engine(self) -> str:
        if self._codec is None:
            return "disabled"
        return "software" if isinstance(self._codec, SoftwareTokenCodec) else "native"

    def _require(self):
        if self._codec is None:
            raise UnauthorizedException("Token service disabled", details={"reason": "token.secret.weak"})
        return self._codec

    def issue_token(self, subject: str, claims: Dict[str, Any]) -> str:
        codec = self._require()
        ttl = security_config.TOKEN_EXPIRATION_MINUTES * 60
        try:
            return codec.issue(subject, json.dumps(claims, separators=(",", ":")), int(time.time()), ttl)
        except _rejections() as exc:
            raise UnauthorizedException("Token request rejected", details={"reason": str(exc)}) from exc

    def verify_token(self, token: str) -> Dict[str, Any]:
        codec = self._require()
        if not isinstance(token, str):
            raise UnauthorizedException("Invalid token format", details={"reason": "token.format"})
        try:
            return json.loads(codec.verify(token, int(time.time())))
        except _rejections() as exc:
            raise UnauthorizedException("Invalid authentication token", details={"reason": str(exc)}) from exc


token_provider = TokenProvider()
