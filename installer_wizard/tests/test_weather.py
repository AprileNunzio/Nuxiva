import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from features.chat.skills import weather as skill
from features.weather import api, astro, codes, places, provider, settings


def hours(count=72):
    return [f"2026-10-23T{h % 24:02d}:00" if h < 24 else f"2026-10-{23 + h // 24}T{h % 24:02d}:00" for h in range(count)]


def forecast():
    times = hours()
    series = lambda value: [value] * len(times)
    return {
        "timezone": "Europe/Rome", "elevation": 12,
        "current": {"time": "2026-10-23T10:00", "temperature_2m": 18.4, "apparent_temperature": 17.2, "relative_humidity_2m": 61,
                    "wind_speed_10m": 14.2, "wind_gusts_10m": 30.1, "wind_direction_10m": 200, "weather_code": 2, "is_day": 1,
                    "pressure_msl": 1014.2, "cloud_cover": 40, "precipitation": 0},
        "hourly": {"time": times, **{k: series(v) for k, v in {
            "temperature_2m": 18, "apparent_temperature": 17, "relative_humidity_2m": 60, "dew_point_2m": 10,
            "precipitation_probability": 10, "precipitation": 0, "weather_code": 2, "pressure_msl": 1013, "visibility": 20000,
            "wind_speed_10m": 12, "wind_gusts_10m": 25, "wind_direction_10m": 180, "uv_index": 3, "cloud_cover": 30, "is_day": 1}.items()}},
        "daily": {"time": [f"2026-10-{23 + i}" for i in range(7)], **{k: [v] * 7 for k, v in {
            "weather_code": 3, "temperature_2m_max": 20, "temperature_2m_min": 11, "precipitation_sum": 0.4,
            "precipitation_probability_max": 30, "wind_speed_10m_max": 22, "wind_gusts_10m_max": 40, "uv_index_max": 4,
            "sunrise": "2026-10-23T07:10", "sunset": "2026-10-23T17:50", "sunshine_duration": 28000,
            "apparent_temperature_max": 19, "apparent_temperature_min": 10, "wind_direction_10m_dominant": 190}.items()}},
    }


class Sandbox(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patch = mock.patch.object(places, "FILE", Path(tmp.name) / "weather.json")
        patch.start()
        self.addCleanup(patch.stop)


class PlacesTest(Sandbox):
    def test_first_place_becomes_default_and_twins_merge(self):
        first = places.add("Roma", 41.9028, 12.4964)
        again = places.add("Roma centro", 41.9029, 12.4965)
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(places.load()["default"], first["id"])
        self.assertEqual(len(places.load()["places"]), 1)

    def test_default_rename_remove(self):
        a, b = places.add("Roma", 41.9, 12.5), places.add("Milano", 45.46, 9.19)
        self.assertTrue(places.set_default(b["id"]))
        self.assertEqual(places.default()["name"], "Milano")
        self.assertTrue(places.rename(a["id"], "<b>Capitale</b>\x00"))
        self.assertEqual(places.find(a["id"])["name"], "bCapitale/b")
        self.assertTrue(places.remove(b["id"]))
        self.assertEqual(places.load()["default"], a["id"])
        self.assertFalse(places.remove("deadbeef"))

    def test_rejects_invalid_and_caps(self):
        with self.assertRaises(ValueError):
            places.add("X", 99, 0)
        with self.assertRaises(ValueError):
            places.add("", 10, 10)
        for i in range(places.MAX_PLACES):
            places.add(f"P{i}", i * 3, i * 5)
        with self.assertRaises(ValueError):
            places.add("Extra", 80, 170)

    def test_corrupt_file_is_ignored(self):
        places.FILE.write_text("{nope", encoding="utf-8")
        self.assertEqual(places.load(), {"places": [], "default": ""})
        self.assertEqual(oct(places.add("Roma", 41.9, 12.5) and places.FILE.stat().st_mode & 0o777), oct(0o600))


class SettingsTest(unittest.TestCase):
    def test_defaults_and_imperial(self):
        with mock.patch.object(settings, "env_get", side_effect=lambda k, d="": d):
            data = settings.current()
        self.assertEqual(data["units"], {"temp": "c", "wind": "kmh", "precip": "mm", "pressure": "hpa", "distance": "km"})
        self.assertEqual((data["days"], data["hours"], data["view"]), (7, 24, "day"))
        env = {"NUXIVA_WEATHER_UNITS": "imperial", "NUXIVA_WEATHER_DAYS": "10", "NUXIVA_WEATHER_REFRESH": "9999", "NUXIVA_WEATHER_VIEW": "bogus"}
        with mock.patch.object(settings, "env_get", side_effect=lambda k, d="": env.get(k, d)):
            data = settings.current()
        self.assertEqual(data["units"]["wind"], "mph")
        self.assertEqual((data["days"], data["refresh"], data["view"]), (10, 120, "day"))

    def test_days_outside_choices_fall_back(self):
        with mock.patch.object(settings, "env_get", side_effect=lambda k, d="": "6" if k.endswith("DAYS") else d):
            self.assertEqual(settings.current()["days"], 7)


class CodesAndAstroTest(unittest.TestCase):
    def test_describe_and_compass(self):
        self.assertEqual(codes.describe(0)[1], "clear")
        self.assertEqual(codes.describe(0, True)[1], "night")
        self.assertEqual(codes.describe(2, True)[1], "night_partly")
        self.assertEqual(codes.compass(0), "N")
        self.assertEqual(codes.compass(185), "S")

    def test_moon_phase_known_dates(self):
        full = astro.moon(datetime(2026, 10, 26, 12, tzinfo=timezone.utc))
        new = astro.moon(datetime(2026, 11, 9, 12, tzinfo=timezone.utc))
        self.assertGreater(full["illumination"], 0.9)
        self.assertLess(new["illumination"], 0.1)


class ProviderTest(Sandbox):
    def test_build_normalises_and_keeps_consumer_contract(self):
        data = provider.build({"name": "Roma", "lat": 41.9, "lon": 12.5}, forecast(), None, 24)
        self.assertEqual(data["location"], "Roma")
        self.assertEqual(len(data["hourly"]), 24)
        self.assertEqual(len(data["days"]), 7)
        for key in ("temp", "feels", "humidity", "wind", "desc", "icon"):
            self.assertIn(key, data["current"])
        for key in ("label", "date", "desc", "icon", "tmax", "tmin", "rain", "wind", "sunrise", "sunset"):
            self.assertIn(key, data["days"][0])
        self.assertEqual(data["current"]["dir_name"], "SSW")

    def test_air_block_levels(self):
        raw = {"current": {"european_aqi": 85, "us_aqi": 120, "pm2_5": 30.4, "pm10": 40, "alder_pollen": 5}}
        block = provider.air_block(raw)
        self.assertEqual(block["aqi"], 85)
        self.assertEqual(block["pm25"], 30.4)
        self.assertIn("alder", block["pollen"])
        self.assertIsNone(provider.air_block(None))

    def test_fetch_caches_and_falls_back_to_stale(self):
        import httpx
        provider.cache.clear()
        place = {"name": "Roma", "lat": 41.9, "lon": 12.5}
        calls = []

        class Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, url, params=None):
                calls.append(url)
                if len(calls) > 1 and not hasattr(Client, "ok"):
                    raise httpx.ConnectError("down")
                return mock.Mock(json=lambda: forecast(), raise_for_status=lambda: None)

        with mock.patch.object(provider.httpx, "AsyncClient", Client):
            first = asyncio.run(provider.fetch(place, 7, 24, False, 10))
            second = asyncio.run(provider.fetch(place, 7, 24, False, 10))
            self.assertEqual(len(calls), 1)
            self.assertEqual(first["current"], second["current"])
            provider.cache[next(iter(provider.cache))] = (0.0, first)
            provider.cache[next(iter(provider.cache))] = (provider.time.time() - 11 * 60, first)
            stale = asyncio.run(provider.fetch(place, 7, 24, False, 10))
            self.assertTrue(stale["stale"])
            provider.cache.clear()
            with self.assertRaises(provider.WeatherUnavailable):
                asyncio.run(provider.fetch(place, 7, 24, False, 10))


class ApiTest(Sandbox):
    def setUp(self):
        super().setUp()
        app = FastAPI()
        app.dependency_overrides[api.require_admin] = lambda: "admin"
        app.include_router(api.admin_routes)
        self.client = TestClient(app)

    def test_place_lifecycle(self):
        created = self.client.post("/api/weather/places", json={"name": "Roma", "lat": 41.9, "lon": 12.5})
        self.assertEqual(created.status_code, 201)
        pid = created.json()["id"]
        self.assertEqual(self.client.patch(f"/api/weather/places/{pid}", json={"name": "Capitale"}).status_code, 200)
        self.assertEqual(self.client.post(f"/api/weather/places/{pid}/default").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/weather/places/{pid}").status_code, 200)
        self.assertEqual(self.client.delete(f"/api/weather/places/{pid}").status_code, 404)
        self.assertEqual(self.client.delete("/api/weather/places/..%2Fx").status_code, 404)

    def test_validation(self):
        self.assertEqual(self.client.post("/api/weather/places", json={"name": "X", "lat": 200, "lon": 0}).status_code, 422)
        self.assertEqual(self.client.post("/api/weather/places", json={"name": "X", "lat": 1, "lon": 1, "extra": 1}).status_code, 422)
        self.assertEqual(self.client.get("/api/weather/search?q=a").status_code, 422)

    def test_overview_reports_errors_and_data(self):
        with mock.patch.object(api, "_current_place", mock.AsyncMock(return_value=None)):
            self.assertEqual(self.client.get("/api/weather/overview").json()["error"], "no_location")
        place = places.add("Roma", 41.9, 12.5)
        with mock.patch.object(api.provider, "report", mock.AsyncMock(side_effect=provider.WeatherUnavailable("x"))):
            self.assertEqual(self.client.get("/api/weather/overview").json()["error"], "unavailable")
        with mock.patch.object(api.provider, "report", mock.AsyncMock(return_value={"location": "Roma"})):
            body = self.client.get(f"/api/weather/overview?place={place['id']}").json()
        self.assertEqual(body["report"]["location"], "Roma")
        self.assertEqual(body["default"], place["id"])


class SkillTest(Sandbox):
    def run_skill(self, text):
        report = provider.build({"name": "Roma", "lat": 41.9, "lon": 12.5}, forecast(), None, 24)
        report.update(units=settings.units(), view="day", astro=None)
        places.add("Roma", 41.9, 12.5)
        with mock.patch.object(skill.provider, "report", mock.AsyncMock(return_value=report)):
            return asyncio.run(skill.weather_skill(text))

    def test_day_is_default(self):
        _, ui = self.run_skill("che tempo fa oggi")
        self.assertEqual(ui["panels"][0]["data"]["view"], "day")
        self.assertEqual(ui["panels"][0]["type"], "forecast")

    def test_week_words_open_week(self):
        for phrase in ("meteo della settimana", "che tempo farà nei prossimi giorni", "previsioni per il weekend"):
            _, ui = self.run_skill(phrase)
            self.assertEqual(ui["panels"][0]["data"]["view"], "week", phrase)

    def test_named_day_focuses_it(self):
        _, ui = self.run_skill("che tempo fa domani")
        data = ui["panels"][0]["data"]
        self.assertEqual((data["view"], data["focus"]), ("day", 1))


if __name__ == "__main__":
    unittest.main()
