import asyncio
import unittest
from unittest import mock

from agenti.weather import blend, provider, sources
from tests.test_weather import forecast


def chosen_model():
    data = forecast()
    times = data["hourly"]["time"]
    return {"current": {"time": data["current"]["time"], "temperature_2m": 21.0, "wind_speed_10m": None},
            "hourly": {"time": times, "temperature_2m": [21.0] * len(times), "uv_index": [None] * len(times)},
            "daily": {"time": data["daily"]["time"], "temperature_2m_max": [25] * 7}}


class BlendTest(unittest.TestCase):
    def test_model_overrides_core_but_keeps_rich_fields(self):
        merged, used = blend.merge(forecast(), chosen_model())
        self.assertTrue(used)
        self.assertEqual(merged["current"]["temperature_2m"], 21.0)
        self.assertEqual(merged["current"]["wind_speed_10m"], 14.2)
        self.assertEqual(merged["hourly"]["temperature_2m"][0], 21.0)
        self.assertEqual(merged["hourly"]["uv_index"][0], 3)
        self.assertEqual(merged["hourly"]["precipitation_probability"][0], 10)
        self.assertEqual(merged["daily"]["temperature_2m_max"][0], 25)
        self.assertEqual(merged["daily"]["uv_index_max"][0], 4)

    def test_original_is_untouched_and_missing_model_falls_back(self):
        base = forecast()
        blend.merge(base, chosen_model())
        self.assertEqual(base["hourly"]["temperature_2m"][0], 18)
        merged, used = blend.merge(base, None)
        self.assertFalse(used)
        self.assertIs(merged, base)

    def test_params_ask_only_core_fields(self):
        query = blend.params({"latitude": 1, "hourly": "x", "current": "y", "minutely_15": "precipitation", "forecast_minutely_15": 12}, "gfs_seamless")
        self.assertEqual(query["models"], "gfs_seamless")
        self.assertNotIn("minutely_15", query)
        self.assertNotIn("uv_index", query["hourly"])


class SourcesTest(unittest.TestCase):
    def test_states(self):
        self.assertEqual(sources.air_state(None, False), sources.DISABLED)
        self.assertEqual(sources.air_state({"error": True}, True), sources.UNAVAILABLE)
        self.assertEqual(sources.air_state({"current": {"european_aqi": 30}}, True), sources.OK)
        self.assertEqual(sources.pollen_state({"current": {"grass_pollen": None}, "hourly": {}}, sources.OK), sources.OUT_OF_SEASON)
        self.assertEqual(sources.pollen_state({"current": {"grass_pollen": 4}}, sources.OK), sources.OK)
        self.assertEqual(sources.pollen_state(None, sources.UNAVAILABLE), sources.UNAVAILABLE)
        self.assertEqual(sources.model_state("icon_seamless", False), sources.FALLBACK)
        self.assertEqual(sources.model_state(None, False), sources.DISABLED)

    def test_preferences_mark_disabled(self):
        result = sources.apply_preferences({"air": {"aqi": 10, "pollen": {"grass": {}}}, "air_days": [{"pollen": {"grass": 1}}],
                                            "sources": {"air": "ok", "pollen": "ok"}}, {"air": True, "pollen": False})
        self.assertEqual(result["air"]["pollen"], {})
        self.assertEqual(result["sources"]["pollen"], sources.DISABLED)


class FetchTest(unittest.TestCase):
    def test_air_error_and_model_failure_are_reported(self):
        import httpx
        provider.cache.clear()
        place = {"name": "Roma", "lat": 41.9, "lon": 12.5}

        class Client:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def get(self, url, params=None):
                if url == provider.AIR_URL:
                    return mock.Mock(json=lambda: {"error": True, "reason": "x"}, raise_for_status=lambda: None)
                if params.get("models"):
                    raise httpx.ConnectError("down")
                return mock.Mock(json=lambda: forecast(), raise_for_status=lambda: None)

        with mock.patch.object(provider.httpx, "AsyncClient", Client):
            data = asyncio.run(provider.fetch(place, 7, 24, True, 10, "icon_seamless"))
        provider.cache.clear()
        self.assertEqual(data["sources"]["air"], sources.UNAVAILABLE)
        self.assertEqual(data["sources"]["pollen"], sources.UNAVAILABLE)
        self.assertEqual(data["sources"]["model"], sources.FALLBACK)
        self.assertEqual(data["model"], "best_match")
        self.assertIsNone(data["air"])
        self.assertEqual(data["current"]["uv"], 3)


if __name__ == "__main__":
    unittest.main()
