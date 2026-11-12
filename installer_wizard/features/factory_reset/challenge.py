import hashlib
import hmac
import secrets
import threading
import time

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TTL = 180.0
MIN_WAIT = 8.0
MAX_ACTIVE = 4
MAX_ATTEMPTS = 3


class ChallengeError(Exception):
    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Challenges:

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.rows: dict[str, dict] = {}

    def _sweep(self, now: float) -> None:
        for key in [key for key, row in self.rows.items() if row["expires"] < now]:
            del self.rows[key]

    def issue(self, user: str, options: dict, now: float | None = None) -> dict:
        moment = time.time() if now is None else now
        token = secrets.token_urlsafe(32)
        phrase = "RESET-" + "".join(secrets.choice(ALPHABET) for _ in range(6))
        with self.lock:
            self._sweep(moment)
            for key in [key for key, row in self.rows.items() if row["user"] == user]:
                del self.rows[key]
            while len(self.rows) >= MAX_ACTIVE:
                del self.rows[min(self.rows, key=lambda key: self.rows[key]["issued"])]
            self.rows[digest(token)] = {"user": user, "phrase": phrase, "options": dict(options), "issued": moment,
                                        "expires": moment + TTL, "attempts": 0}
        return {"token": token, "phrase": phrase, "wait_seconds": int(MIN_WAIT), "expires_in": int(TTL)}

    def redeem(self, token: str, user: str, phrase: str, options: dict, now: float | None = None) -> None:
        moment = time.time() if now is None else now
        key = digest(token)
        with self.lock:
            self._sweep(moment)
            row = self.rows.get(key)
            if row is None:
                raise ChallengeError("challenge_invalid", 403)
            if not hmac.compare_digest(row["user"], user):
                del self.rows[key]
                raise ChallengeError("challenge_invalid", 403)
            if moment - row["issued"] < MIN_WAIT:
                raise ChallengeError("challenge_too_early", 425)
            if row["options"] != options:
                del self.rows[key]
                raise ChallengeError("challenge_options_changed", 409)
            if not hmac.compare_digest(row["phrase"], phrase.strip()):
                row["attempts"] += 1
                if row["attempts"] >= MAX_ATTEMPTS:
                    del self.rows[key]
                raise ChallengeError("phrase_mismatch", 403)
            del self.rows[key]


challenges = Challenges()
