import re
from datetime import date

from features.weather import places, provider
from features.weather.codes import DAYS_IT

WEEK_WORDS = re.compile(r"\b(settimana|settimanale|sette giorni|7 giorni|prossimi giorni|prossimi \d+ giorni|weekend|fine settimana|"
                        r"prossima settimana|tutta la settimana|per i prossimi)\b", re.I)


async def _locate() -> dict:
    chosen = places.default()
    if chosen:
        return chosen
    from features.location.locator import locator
    loc = await locator.current()
    if loc.get("lat") is None:
        raise ValueError("posizione sconosciuta")
    return {"name": loc["name"], "lat": float(loc["lat"]), "lon": float(loc["lon"]), "detail": ""}


_PREPS = {"a", "ad", "di", "del", "per", "su", "sul", "in", "da", "nel", "verso"}
_PLACE_END = {"oggi", "domani", "dopodomani", "stasera", "stanotte", "stamattina", "adesso", "ora", "questa", "questo",
              "nei", "nel", "nella", "per", "a", "ad", "in", "e", "ma", "che", "come", "com'è", "fine", "weekend",
              "settimana", "prossimi", "prossima", "prossimo", "giorni", "tempo", "meteo", "sarà", "farà", "fa",
              *(d.lower() for d in DAYS_IT)}
_NOT_PLACE = {"tempo", "meteo", "previsioni", "casa", "qui", "qua", "fuori", "noi", "me", "te", "solito", *_PLACE_END}


def _weather_place(text: str) -> str | None:
    words = re.findall(r"[A-Za-zÀ-ÿ']+|[?.!,;]", text)
    for i, w in enumerate(words):
        bare = w.lower() in ("meteo", "previsioni") and i + 1 < len(words) and words[i + 1][:1].isupper()
        if w.lower() not in _PREPS and not bare:
            continue
        name = []
        for x in words[i + 1:i + 5]:
            if not x[0].isalpha() or x.lower() in _PLACE_END:
                break
            name.append(x)
        while name and name[-1].lower() in ("di", "del", "la", "il"):
            name.pop()
        if name and name[0].lower() not in _NOT_PLACE:
            return " ".join(name)
    return None


def _day_index(text: str) -> int | None:
    t = text.lower()
    if "dopodomani" in t:
        return 2
    if "domani" in t:
        return 1
    for i, name in enumerate(DAYS_IT):
        if re.search(rf"\b{name.lower()}\b", t):
            return (i - date.today().weekday()) % 7
    return None


AIR_WORDS = {"good": "buona", "fair": "discreta", "moderate": "moderata", "poor": "scadente", "very_poor": "molto scadente",
             "extreme": "pessima"}


def _day_speech(place: str, current: dict, day: dict, index: int, air: dict | None) -> str:
    when = "Oggi" if index == 0 else ("Domani" if index == 1 else f"{day['label']} {day['date']}")
    parts = [f"{when} a {place}: {day['desc'].lower()}, massima {day['tmax']} e minima {day['tmin']} gradi"]
    if (day["rain"] or 0) >= 30:
        parts.append(f"pioggia al {day['rain']} per cento" + (f", circa {day['rain_sum']} millimetri" if (day["rain_sum"] or 0) >= 1 else ""))
    wind = day["gust"] or day["wind"] or 0
    if wind >= 40:
        parts.append(f"vento forte da {day['dir_name']} con raffiche fino a {day['gust']} chilometri orari")
    elif wind >= 20:
        parts.append(f"vento da {day['dir_name']} fino a {day['wind']} chilometri orari")
    if (day["uv"] or 0) >= 6:
        parts.append(f"indice UV alto, {day['uv']}")
    text = ", ".join(parts) + "."
    if index == 0:
        text += (f" Ora ci sono {current['temp']} gradi, percepiti {current['feels']}, umidità {current['humidity']} per cento"
                 f", pressione {current['pressure']} ettopascal.")
        if air and air.get("level"):
            text += f" Qualità dell'aria {AIR_WORDS.get(air['level'], air['level'])}."
    return text


def _week_speech(place: str, current: dict, days: list[dict]) -> str:
    hottest = max(days, key=lambda d: d["tmax"])
    rainy = [d["label"] for d in days[1:] if (d["rain"] or 0) >= 60]
    text = (f"A {place} ora ci sono {current['temp']} gradi, {current['desc'].lower()}. Nei prossimi {len(days)} giorni le massime vanno da "
            f"{min(d['tmax'] for d in days)} a {hottest['tmax']} gradi, con il picco {hottest['label'].lower()}. ")
    return text + (f"Pioggia probabile {', '.join(x.lower() for x in rainy[:3])}." if rainy else "Non sono previste piogge significative.")


async def weather_skill(text: str = "") -> tuple[str, dict]:
    asked = _weather_place(text)
    if asked:
        from features.location.locator import search
        found = await search(asked, 1)
        if not found:
            return (f"Non ho trovato nessun luogo chiamato {asked}. Puoi ripetere il nome della città?", {"mode": "face"})
        place = {"name": found[0]["name"], "lat": found[0]["lat"], "lon": found[0]["lon"], "detail": found[0].get("detail", "")}
    else:
        place = await _locate()
    try:
        report = await provider.report(place)
    except provider.WeatherUnavailable:
        return "Non riesco a raggiungere il servizio meteo in questo momento. Riprovo tra poco?", {"mode": "face"}
    days, current = report["days"], report["current"]
    index = _day_index(text)
    week = bool(WEEK_WORDS.search(text)) or (index is None and report["view"] == "week" and "oggi" not in text.lower())
    if index is not None and index >= len(days):
        index, week = None, True
    focus = 0 if index is None else index
    speech = _week_speech(report["location"], current, days) if week else _day_speech(report["location"], current, days[focus], focus, report["air"])
    view = "week" if week else "day"
    title = f"Meteo — {report['location']}"
    ui = {"mode": "focus", "title": title,
          "subtitle": f"Previsioni per i prossimi {len(days)} giorni" if week else f"Previsioni di {days[focus]['label'].lower()}",
          "panels": [{"type": "forecast", "title": "Settimana" if week else days[focus]["label"],
                      "data": {**report, "view": view, "focus": focus}}]}
    return speech, ui
