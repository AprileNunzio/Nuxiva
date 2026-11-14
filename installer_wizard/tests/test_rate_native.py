import random
import unittest

import native_core

from agenti.brain.free_router import rate_limiter as module
from agenti.brain.free_router.rate_limiter import ModelRate, RateLimiter

NAMES = ["Retry-After", "x-ratelimit-remaining", "X-RateLimit-Remaining-Requests", "x-ratelimit-remaining-tokens",
         "x-ratelimit-limit", "X-Ratelimit-Limit-Requests", "x-ratelimit-reset", "x-ratelimit-reset-requests", "x-other"]
VALUES = ["0", "1", "2", "30", "30s", "5m", "2h", "1d", "1.5", "2.5s", "  7 ", "", "abc", "-4", "1e3", "inf", "nan", "1e999",
          "99999999999999999999", "Wed, 21 Oct 2026 07:28:00 GMT", "1_000", "٣", "0.0", "00012", "9", "+5", ".5", "5.", "10 m"]
STATUSES = [200, 429, 401, 403, 500, 503, 404, 302]


def blank():
    return ModelRate()


@unittest.skipIf(native_core.symbol("RustRateRules") is None, "modulo nativo assente")
class RateParityTest(unittest.TestCase):
    def test_differential_fuzz(self):
        rng = random.Random(20261114)
        for _ in range(3000):
            now = rng.choice([1000.0, 1.7e9, 5.5, 0.0])
            headers = {rng.choice(NAMES): rng.choice(VALUES) for _ in range(rng.randint(0, 5))}
            status = rng.choice(STATUSES)
            seed = [(None, None, None, 0.0, 0.0, False), (3, 10, 5000, now + 20, now + 5, False), (0, 5, 0, now - 1, 0.0, True)]
            for start in seed:
                a, b = blank(), blank()
                for rate in (a, b):
                    (rate.remaining_requests, rate.request_limit, rate.remaining_tokens, rate.reset_at,
                     rate.cooldown_until, rate.disabled) = start
                la, lb = RateLimiter(), RateLimiter()
                la._rates[("p", "m")], lb._rates[("p", "m")] = a, b
                got = la.observe("p", "m", headers, status, now)
                want = lb._py_observe("p", "m", headers, status, now)
                with self.subTest(headers=headers, status=status, now=now, start=start):
                    self.assertEqual(repr(got), repr(want))
                    for tokens in (0, 100, 10000):
                        self.assertEqual(la.available("p", "m", tokens, now + 1), RateLimiter._py_available(want, tokens, now + 1))

    def test_dates_defer_to_python(self):
        engine = native_core.symbol("RustRateRules")()
        kind, _ = engine.observe((None, None, None, 0.0, 0.0, False), [("retry-after", "Wed, 21 Oct 2026 07:28:00 GMT")], 429, 1.0)
        self.assertEqual(kind, "defer")

    def test_fallback_engine_alone(self):
        limiter = RateLimiter()
        rate = limiter._py_observe("p", "m", {"retry-after": "10"}, 429, 100.0)
        self.assertEqual(rate.cooldown_until, 110.0)


if __name__ == "__main__":
    unittest.main()
