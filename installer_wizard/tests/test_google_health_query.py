import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from features.people.sync_board import board
from features.people.vitals import cloud

END = datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc)


class QueryTest(unittest.TestCase):
    def test_sample_interval_sleep_and_daily(self):
        self.assertEqual(cloud.query("heart-rate", END - timedelta(minutes=10), END),
                         'heart_rate.sample_time.physical_time >= "2026-11-02T09:20:00Z" AND heart_rate.sample_time.physical_time < "2026-11-02T09:30:00Z"')
        self.assertTrue(cloud.query("steps", END - timedelta(hours=26), END).startswith('steps.interval.start_time >= "2026-11-01T07:30:00Z"'))
        self.assertIn("sleep.interval.end_time <", cloud.query("sleep", END - timedelta(hours=36), END))
        self.assertEqual(cloud.query("daily-resting-heart-rate", END - timedelta(days=3), END),
                         'daily_resting_heart_rate.date >= "2026-10-30" AND daily_resting_heart_rate.date < "2026-11-03"')

    def test_rejects_bad_type(self):
        for bad in ("heart_rate", "x\" OR 1", "", "Heart-Rate"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                cloud.query(bad, END, END)

    def test_poll_sends_filter_and_no_legacy_params(self):
        calls = []

        async def fake_get(url, **params):
            calls.append((url, params))
            return {"dataPoints": []}

        session = mock.Mock()
        session.ready.return_value = True
        session._get = fake_get
        cloud._state.pop("ana", None)
        self.addCleanup(board.forget, "ana")
        with mock.patch("features.google.gservices.google.session", return_value=session):
            asyncio.run(cloud.poll("ana", END.timestamp()))
        self.assertEqual(len(calls), len(cloud.SOURCES) + len(cloud.DAILY))
        for url, params in calls:
            self.assertEqual(set(params), {"filter"})
            self.assertIn(url.rsplit("/", 2)[1].replace("-", "_"), params["filter"])


if __name__ == "__main__":
    unittest.main()
