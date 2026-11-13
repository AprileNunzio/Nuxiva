import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from agenti.weather import alerts, extras, provider, radar, settings
from tests.test_weather import forecast

NOW = datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)


def meteoalarm_feed():
    def warning(area, level, expires="2026-11-14T00:00:00+01:00", lang="it-IT"):
        return {"alert": {"info": [
            {"language": "en-GB", "event": "Wind", "severity": "Moderate", "headline": "Wind EN", "area": [{"areaDesc": area}],
             "onset": "2026-11-13T06:00:00+01:00", "expires": expires, "parameter": [{"valueName": "awareness_level", "value": level}]},
            {"language": lang, "event": "Vento\x07 forte", "severity": "Severe", "headline": "<b>Allerta</b> vento", "area": [{"areaDesc": area}],
             "onset": "2026-11-13T06:00:00+01:00", "expires": expires, "parameter": [{"valueName": "awareness_level", "value": level}]}]}}
    return {"warnings": [warning("Lazio", "3; orange; Severe"), warning("Puglia", "2; yellow; Moderate"),
                         warning("Lazio", "1; green; Minor"), warning("Lazio", "2; yellow; Moderate", "2026-11-12T00:00:00+01:00")]}


class AlertsTest(unittest.TestCase):
    def test_meteoalarm_matches_region_language_and_drops_green_or_expired(self):
        found = alerts.meteoalarm(meteoalarm_feed(), ["Roma", "Lazio"], "it", NOW)
        self.assertEqual(len(found), 1)
        alert = found[0]
        self.assertEqual((alert["level"], alert["severity"], alert["area"]), ("orange", "severe", "Lazio"))
        self.assertEqual(alert["event"], "Vento forte")
        self.assertEqual(alert["headline"], "<b>Allerta</b> vento")

    def test_nws_and_ranking(self):
        raw = {"features": [{"properties": {"event": "Flood Watch", "severity": "Moderate", "onset": "2026-11-13T10:00:00Z",
                                            "ends": "2026-11-14T10:00:00Z", "areaDesc": "Kings"}},
                            {"properties": {"event": "Tornado Warning", "severity": "Extreme", "onset": "2026-11-13T11:00:00Z",
                                            "expires": "2026-11-13T12:00:00Z", "areaDesc": "Kings"}},
                            {"properties": {"event": "Old", "severity": "Severe", "expires": "2026-11-12T12:00:00Z"}}]}
        ranked = alerts.ranked(alerts.nws(raw, NOW))
        self.assertEqual([a["event"] for a in ranked], ["Tornado Warning", "Flood Watch"])

    def test_official_uses_cached_area_and_country_feed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        calls = []

        class Response:
            def __init__(self, body):
                self.body = body

            def raise_for_status(self):
                return None

            def json(self):
                return self.body

        class Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, url, params=None, headers=None):
                calls.append(url)
                if "reverse" in url:
                    return Response({"address": {"country_code": "IT", "state": "Lazio", "city": "Roma"}})
                return Response(meteoalarm_feed())

        with mock.patch.object(alerts, "AREA_FILE", Path(tmp.name) / "areas.json"), mock.patch.object(alerts.httpx, "AsyncClient", Client), \
                mock.patch.object(alerts, "cache", {}), mock.patch.object(alerts, "datetime", mock.Mock(now=lambda tz=None: NOW, fromisoformat=datetime.fromisoformat)):
            first = asyncio.run(alerts.official({"lat": 41.9, "lon": 12.5, "name": "Roma"}))
            alerts.cache.clear()
            asyncio.run(alerts.official({"lat": 41.9, "lon": 12.5, "name": "Roma"}))
        self.assertEqual(first[0]["area"], "Lazio")
        self.assertTrue(calls[1].endswith("feeds-italy"))
        self.assertEqual(sum("reverse" in c for c in calls), 1)


class RadarAndExtrasTest(unittest.TestCase):
    def test_radar_accepts_only_known_host_and_safe_paths(self):
        raw = {"host": radar.HOST, "radar": {"past": [{"time": i, "path": f"/v2/radar/abc{i}"} for i in range(9)] +
                                             [{"time": 99, "path": "/../evil"}]}}
        out = radar.frames(raw)
        self.assertEqual(len(out["frames"]), radar.FRAMES)
        self.assertTrue(all(f["path"].startswith("/v2/radar/abc") for f in out["frames"]))
        self.assertIsNone(radar.frames({**raw, "host": "https://evil.example"}))

    def test_nowcast_yesterday_and_air_days(self):
        slots = {"time": [f"2026-11-13T09:{m:02d}" for m in (0, 15, 30, 45)] + [f"2026-11-13T10:{m:02d}" for m in (0, 15, 30, 45)],
                 "precipitation": [0, 0, 0.3, 0.5, float("nan"), 0, 0, 0]}
        cast = extras.nowcast(slots, "2026-11-13T09:20")
        self.assertEqual(cast[0]["time"], "2026-11-13T09:15")
        self.assertIsNone(cast[3]["rain"])
        daily = {"time": ["2026-11-12", "2026-11-13"], "temperature_2m_max": [16.4, 18], "temperature_2m_min": [8.6, 9], "precipitation_sum": [2.0, 0]}
        hourly = {"temperature_2m": [10.0 + i for i in range(30)]}
        self.assertEqual(extras.yesterday(daily, hourly, 25), {"iso": "2026-11-12", "tmax": 16, "tmin": 9, "rain_sum": 2.0, "same_hour": 11.0})
        today = datetime.now().date().isoformat()
        air = {"hourly": {"time": [f"{today}T0{h}:00" for h in range(3)], "european_aqi": [20, 45, 30], "pm2_5": [5, 9, 7], "grass_pollen": [1, 30, 2]}}
        self.assertEqual(extras.air_days(air), [{"iso": today, "aqi": 45.0, "pm25": 9.0, "pollen": {"grass": 30.0}}])

    def test_report_adds_insights_alerts_radar_without_network(self):
        payload = provider.build({"name": "Roma", "lat": 41.9, "lon": 12.5}, forecast(), None, 24)
        with mock.patch.object(provider, "fetch", mock.AsyncMock(return_value=payload)) as fetched, \
                mock.patch.object(provider.alerts, "official", mock.AsyncMock(side_effect=alerts.AlertsUnavailable("x"))), \
                mock.patch.object(provider.radar, "latest", mock.AsyncMock(return_value=None)), \
                mock.patch.object(provider.skill, "preferred_model", return_value="icon_seamless") as chosen, \
                mock.patch.object(settings, "env_get", side_effect=lambda k, d="": d):
            out = asyncio.run(provider.report({"name": "Roma", "lat": 41.9, "lon": 12.5}))
        chosen.assert_called_once()
        self.assertEqual(fetched.await_args.args[-1], "icon_seamless")
        self.assertIsNone(out["alerts"])
        self.assertIsInstance(out["insights"], list)


if __name__ == "__main__":
    unittest.main()
