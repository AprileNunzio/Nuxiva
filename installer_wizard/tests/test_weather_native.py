import asyncio
import json
import random
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from agenti.weather import exercises, skill
from agenti.weather.algorithms import engine
from agenti.weather.algorithms import insights as py_insights
from agenti.weather.algorithms import verify as py_verify

try:
    import nuxiva_native
    NATIVE = hasattr(nuxiva_native, "weather_insights")
except ImportError:
    NATIVE = False


def _random_situation(rng: random.Random) -> dict:
    pick = lambda lo, hi: None if rng.random() < 0.1 else round(rng.uniform(lo, hi), 2)
    hourly = [{"time": f"2026-11-13T{h % 24:02d}:00", "temp": pick(-10, 40), "feels": pick(-15, 42), "rain_prob": pick(0, 100),
               "rain": pick(0, 5), "gust": pick(0, 100), "uv": pick(0, 11), "code": rng.choice([0, 2, 3, 45, 61, 73, 95, 99, None])}
              for h in range(rng.randint(0, 30))]
    days = [{"tmax": pick(-5, 40), "tmin": pick(-12, 25), "uv": pick(0, 11)} for _ in range(rng.randint(0, 3))]
    nowcast = [{"time": f"n{i}", "rain": pick(0, 1)} for i in range(rng.randint(0, 8))]
    return {"hourly": hourly, "days": days, "yesterday": {"tmax": pick(-5, 40)} if rng.random() < 0.7 else None, "nowcast": nowcast}


def _random_verify(rng: random.Random) -> dict:
    times = [f"t{i}" for i in range(rng.randint(1, 40))]
    observed = [{"time": t, "temp": round(rng.uniform(0, 30), 2), "rain": round(rng.uniform(0, 2), 2), "wind": round(rng.uniform(0, 40), 2)}
                for t in times if rng.random() < 0.9]
    forecasts = [{"model": rng.choice(skill.MODELS), "lead": rng.randint(1, 4), "time": rng.choice(times),
                  "temp": round(rng.uniform(0, 30), 2), "rain": None if rng.random() < 0.2 else round(rng.uniform(0, 2), 2),
                  "wind": round(rng.uniform(0, 40), 2)} for _ in range(rng.randint(0, 120))]
    return {"forecasts": forecasts, "observed": observed, "lead": rng.choice([None, 1, 2]), "min_pairs": rng.randint(0, 6)}


class PythonEngineTest(unittest.TestCase):
    def test_exercise_ladder_is_fully_solved(self):
        for tier in range(len(exercises.LADDER)):
            item = exercises.make("weather_insights", tier)
            score, lesson = exercises.grade(item, asyncio.run(exercises.attempt(item)))
            self.assertEqual(score, 1.0, f"tier {tier}: {lesson}")

    def test_verify_prefers_closest_model(self):
        observed = [{"time": f"t{i}", "temp": 10.0, "rain": 0.0, "wind": 10.0} for i in range(20)]
        forecasts = [{"model": "icon_seamless", "lead": 1, "time": f"t{i}", "temp": 10.5, "rain": 0.0, "wind": 11.0} for i in range(20)]
        forecasts += [{"model": "gfs_seamless", "lead": 1, "time": f"t{i}", "temp": 14.0, "rain": 1.0, "wind": 20.0} for i in range(20)]
        verdict = py_verify.verify(forecasts, observed, 1, 16)
        self.assertEqual(verdict["best"], "icon_seamless")
        self.assertEqual(verdict["models"][0]["temp_mae"], 0.5)

    def test_skill_without_data_is_honest(self):
        item = exercises.make("forecast_skill", 0)
        score, lesson = exercises.grade(item, {"best": None, "models": []})
        self.assertEqual(score, 0.0)
        self.assertIn("confronti", lesson)


class SkillArchiveTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        patch = mock.patch.object(skill, "ROOT", Path(tmp.name))
        patch.start()
        self.addCleanup(patch.stop)

    def test_record_judge_and_preferred_model(self):
        place = {"lat": 41.9, "lon": 12.5}
        today = date(2026, 11, 10)
        times = [f"2026-11-{d:02d}T{h:02d}:00" for d in range(11, 14) for h in range(24)]
        models_hourly = {"time": times}
        for model, offset in zip(skill.MODELS, (0.2, 1.5, 3.0, 4.0)):
            models_hourly[f"temperature_2m_{model}"] = [12.0 + offset] * len(times)
            models_hourly[f"precipitation_{model}"] = [0.0] * len(times)
            models_hourly[f"wind_speed_10m_{model}"] = [10.0 + offset] * len(times)
        data = skill.record(skill.load(place), models_hourly, {}, today, "2026-11-10T00:00")
        self.assertEqual(len(data["forecasts"]), 4 * 8 * 3)
        again = skill.record(data, models_hourly, {}, today, "2026-11-10T00:00")
        self.assertEqual(len(again["forecasts"]), 4 * 8 * 3)
        observed = {"time": times, "temperature_2m": [12.0] * len(times), "precipitation": [0.0] * len(times), "wind_speed_10m": [10.0] * len(times)}
        data = skill.record(again, {}, observed, date(2026, 11, 14), "2026-11-14T00:00")
        data["choice"] = skill.judge(data)
        skill._save(place, data)
        self.assertEqual(data["choice"]["model"], "ecmwf_ifs025")
        self.assertEqual(skill.preferred_model(place), "ecmwf_ifs025")
        self.assertEqual(oct(skill._file(place).stat().st_mode & 0o777), "0o600")

    def test_bad_coordinates_rejected(self):
        with self.assertRaises(ValueError):
            skill.key({"lat": float("nan"), "lon": 1})


@unittest.skipUnless(NATIVE, "modulo nativo non installato")
class NativeParityTest(unittest.TestCase):
    def test_insights_parity(self):
        rng = random.Random(7)
        cases = [case for tier in exercises.LADDER for case, _ in tier] + [_random_situation(rng) for _ in range(400)]
        for case in cases:
            try:
                raw = json.dumps(case, allow_nan=False)
            except ValueError:
                self.assertEqual(engine.insights(case), py_insights.insights(case))
                continue
            self.assertEqual(json.loads(nuxiva_native.weather_insights(raw)), py_insights.insights(case))

    def test_verify_parity(self):
        rng = random.Random(11)
        for _ in range(300):
            body = _random_verify(rng)
            native = json.loads(nuxiva_native.weather_verify(json.dumps(body)))
            self.assertEqual(native, py_verify.verify(body["forecasts"], body["observed"], body["lead"], body["min_pairs"]))

    def test_engine_uses_native_and_rejects_oversize(self):
        self.assertEqual(engine.insights({"hourly": [], "days": [], "nowcast": []}), [])
        with self.assertRaises(ValueError):
            nuxiva_native.weather_insights("x" * (5 * 1024 * 1024))


if __name__ == "__main__":
    unittest.main()
