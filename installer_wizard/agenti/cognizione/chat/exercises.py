from agenti._study import Exercise
from agenti.chat.skills import weather

TOPICS = ("weather_requests",)
LADDER = (
    (("che tempo fa a Roma", "Roma", None), ("che tempo fa domani a Milano", "Milano", 1), ("meteo di Napoli dopodomani", "Napoli", 2)),
    (("previsioni per Torino stasera", "Torino", None), ("piove a Bologna domani", "Bologna", 1), ("tempo a Parigi dopodomani", "Parigi", 2)),
    (("che tempo fa fuori", None, None), ("com'è il tempo oggi", None, None), ("che tempo fa", None, None)),
    (("dimmi il meteo a San Giovanni Rotondo", "San Giovanni Rotondo", None), ("meteo a Reggio Emilia domani", "Reggio Emilia", 1),
     ("che tempo fa a La Spezia dopodomani", "La Spezia", 2)),
    (("che tempo ci sarà a Firenze domani sera", "Firenze", 1), ("tempo a Parigi dopodomani mattina", "Parigi", 2),
     ("fa freddo a Torino domani", "Torino", 1)),
    (("meteo Venezia", "Venezia", None), ("previsioni Genova domani", "Genova", 1), ("meteo Bari dopodomani", "Bari", 2)),
    (("meteo venezia", "venezia", None), ("previsioni genova domani", "genova", 1), ("tempo a pisa dopodomani", "pisa", 2)),
    (("serve l'ombrello a Trieste domani", "Trieste", 1), ("farà caldo a Palermo dopodomani", "Palermo", 2),
     ("c'è il sole a Cagliari oggi", "Cagliari", None)),
    (("ho tempo domani", None, 1), ("com'è il tempo domani", None, 1), ("che tempo fa dopodomani", None, 2)),
    (("che tempo farà nel weekend a Verona", "Verona", None), ("come sarà il meteo a Padova domani pomeriggio", "Padova", 1),
     ("dimmi se piove a Lecce dopodomani sera", "Lecce", 2)),
)


def make(topic: str, tier: int) -> Exercise:
    return Exercise(topic, tier, f"tier {tier}", {"cases": LADDER[min(max(tier, 0), len(LADDER) - 1)]})


async def attempt(exercise: Exercise):
    return [(text, weather._weather_place(text), weather._day_index(text)) for text, _, _ in exercise.data["cases"]]


def grade(exercise: Exercise, result) -> tuple[float, str]:
    cases = exercise.data["cases"]
    if not isinstance(result, list) or len(result) != len(cases):
        return 0.0, ""
    right, missed = 0, []
    for (text, place, day), (_, got_place, got_day) in zip(cases, result):
        if got_place == place and got_day == day:
            right += 1
        else:
            missed.append(f"«{text}» atteso {place}/{day}, ottenuto {got_place}/{got_day}")
    return round(right / len(cases), 4), "; ".join(missed)[:280]
