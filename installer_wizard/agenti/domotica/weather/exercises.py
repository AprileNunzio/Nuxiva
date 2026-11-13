from agenti._study import Exercise
from agenti.weather import places, skill
from agenti.weather.algorithms import engine

TOPICS = ("forecast_skill", "weather_insights")


def _hour(n: int, prob=0.0, gust=10.0, feels=18.0, code=1, rain=0.0) -> dict:
    return {"time": f"h{n:02d}", "temp": feels, "feels": feels, "rain_prob": prob, "rain": rain, "gust": gust, "uv": None, "code": code}


def _case(hourly=None, days=None, yesterday=None, nowcast=None) -> dict:
    return {"hourly": hourly or [_hour(0)], "days": [{"tmax": 18.0, "tmin": 9.0, "uv": 2.0}] if days is None else days,
            "yesterday": yesterday, "nowcast": nowcast or []}


def _slots(*values) -> list[dict]:
    return [{"time": f"n{i}", "rain": v} for i, v in enumerate(values)]


LADDER = (
    ((_case(), set()), (_case(hourly=[_hour(0, prob=70)]), {"umbrella"}), (_case(hourly=[_hour(0, gust=60)]), {"wind"})),
    ((_case(hourly=[_hour(0, code=95)]), {"storm"}), (_case(hourly=[_hour(0, code=73)]), {"snow"}), (_case(hourly=[_hour(0, code=45)]), {"fog"})),
    ((_case(days=[{"tmax": 5, "tmin": -1, "uv": 1}]), {"frost"}), (_case(days=[{"tmax": 30, "tmin": 20, "uv": 9}]), {"uv"}),
     (_case(hourly=[_hour(0, feels=35)]), {"heat"})),
    ((_case(yesterday={"tmax": 14.0}), {"warmer"}), (_case(yesterday={"tmax": 22.0}), {"colder"}), (_case(yesterday={"tmax": 18.4}), {"same"})),
    ((_case(nowcast=_slots(0, 0, 0.3, 0.8)), {"rain_soon"}), (_case(nowcast=_slots(0.5, 0.4, 0, 0)), {"rain_stops"}),
     (_case(nowcast=_slots(0.5, 0.6, 0.7)), {"raining"})),
    ((_case(hourly=[_hour(0, prob=49.9, gust=49.9, feels=31.9)]), set()), (_case(hourly=[_hour(0, prob=50, gust=50, feels=32)]), {"umbrella", "wind", "heat"}),
     (_case(days=[{"tmax": 8, "tmin": 1.0, "uv": 6.0}]), {"frost", "uv"})),
    ((_case(hourly=[_hour(0, code=96, gust=80)], days=[{"tmax": 25, "tmin": 15, "uv": 8}]), {"storm", "wind", "uv"}),
     (_case(hourly=[_hour(0, prob=90, code=63)], yesterday={"tmax": 25}, nowcast=_slots(0, 1.2)), {"umbrella", "colder", "rain_soon"}),
     (_case(hourly=[_hour(0, code=75)], days=[{"tmax": -2, "tmin": -8, "uv": 1}, {"tmax": 0, "tmin": -3, "uv": 1}]), {"snow", "frost"})),
    ((_case(hourly=[_hour(i) for i in range(12)] + [_hour(12, code=45)]), set()),
     (_case(hourly=[_hour(i) for i in range(12)] + [_hour(12, prob=95)]), set()),
     (_case(hourly=[_hour(i) for i in range(24)] + [_hour(24, code=99, gust=90)]), set())),
    ((_case(hourly=[_hour(i) for i in range(20)] + [_hour(20, code=99)]), {"storm"}),
     (_case(hourly=[_hour(0, feels=39), _hour(1, gust=76)]), {"heat", "wind"}),
     (_case(days=[{"tmax": 9, "tmin": 3, "uv": 1}, {"tmax": 6, "tmin": 0.5, "uv": 1}]), {"frost"})),
    ((_case(hourly=[_hour(0, prob=85, gust=77, feels=38, code=95), _hour(1, code=45)], days=[{"tmax": 30, "tmin": -6, "uv": 8.5}],
            yesterday={"tmax": 20}, nowcast=_slots(0.2, 0.0)),
      {"storm", "umbrella", "wind", "heat", "frost", "uv", "fog", "warmer", "rain_stops"}),
     (_case(hourly=[{"time": "h0", "temp": None, "feels": float("nan"), "rain_prob": None, "rain": None, "gust": None, "uv": None, "code": None}]), set()),
     (_case(days=[], yesterday={"tmax": 10}), set())),
)


def make(topic: str, tier: int) -> Exercise:
    tier = min(max(tier, 0), len(LADDER) - 1)
    if topic == "forecast_skill":
        return Exercise(topic, tier, f"lead {tier + 1}", {"lead": tier + 1})
    return Exercise(topic, tier, f"tier {tier}", {"cases": LADDER[tier]})


async def _place() -> dict:
    chosen = places.default()
    if chosen:
        return chosen
    from agenti.location.locator import locator
    here = await locator.current()
    if here.get("lat") is None:
        raise ValueError("posizione sconosciuta")
    return {"name": here.get("name") or "", "lat": float(here["lat"]), "lon": float(here["lon"])}


async def attempt(exercise: Exercise):
    if exercise.topic == "forecast_skill":
        try:
            choice = await skill.learn(await _place())
        except skill.SkillUnavailable as exc:
            raise RuntimeError("servizio meteo non raggiungibile") from exc
        return choice["leads"].get(str(exercise.data["lead"]), {})
    return [{item["kind"] for item in engine.insights(case)} for case, _ in exercise.data["cases"]]


def _jaccard(got: set, want: set) -> float:
    return 1.0 if not got and not want else len(got & want) / len(got | want)


def grade(exercise: Exercise, result) -> tuple[float, str]:
    if exercise.topic == "forecast_skill":
        lead = exercise.data["lead"]
        if not isinstance(result, dict) or not result.get("best"):
            return 0.0, f"a {lead} giorni non ci sono ancora abbastanza confronti tra previsioni e dati rilevati"
        top = result["models"][0]
        return float(top["score"]), (f"a {lead} giorni il modello più preciso è {top['model']}: errore medio "
                                     f"{top['temp_mae']}°C su {top['pairs']} confronti")[:280]
    cases = exercise.data["cases"]
    if not isinstance(result, list) or len(result) != len(cases):
        return 0.0, ""
    scores, missed = [], []
    for (_, want), got in zip(cases, result):
        scores.append(_jaccard(set(got), want))
        if set(got) != want:
            missed.append(f"atteso {sorted(want)}, ottenuto {sorted(got)}")
    return round(sum(scores) / len(scores), 4), "; ".join(missed)[:280]
