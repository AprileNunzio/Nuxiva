import random
import secrets

from agenti._study import Exercise
from agenti.ear.vote import vote

TOPICS = ("consensus",)
SENTENCES = (
    "accendi la luce del salotto per favore",
    "che tempo farà domani mattina a roma",
    "ricordami di chiamare il dottore alle cinque del pomeriggio",
    "metti la sveglia domani alle sei e mezza e spegni tutte le luci",
    "dimmi quanti gradi ci sono fuori e se serve l'ombrello per uscire",
    "apri la porta del garage quando arriva mia moglie con la macchina",
    "sposta la riunione di giovedì alle quindici e avvisa tutti i partecipanti",
)
FILLERS = ("ehm", "boh", "xx", "allora", "ecco")


def _corrupt(words: list[str], count: int, rng: random.Random) -> list[str]:
    out = list(words)
    for _ in range(count):
        if not out:
            break
        index = rng.randrange(len(out))
        action = rng.choice(("swap", "drop", "add"))
        if action == "swap":
            out[index] = rng.choice(FILLERS)
        elif action == "drop" and len(out) > 2:
            del out[index]
        else:
            out.insert(index, rng.choice(FILLERS))
    return out


def make(topic: str, tier: int) -> Exercise:
    seed = secrets.randbits(32)
    rng = random.Random(seed)
    sentence = SENTENCES[rng.randrange(len(SENTENCES))]
    mics = 5 if tier < 3 else 3
    errors = 1 + tier
    return Exercise(topic, tier, sentence, {"seed": seed, "mics": mics, "errors": errors})


async def attempt(exercise: Exercise):
    rng = random.Random(exercise.data["seed"] ^ 0x5EED)
    words = exercise.prompt.split()
    heard = [(" ".join(_corrupt(words, exercise.data["errors"], rng)), 1.0) for _ in range(exercise.data["mics"])]
    text, agreement, changed = vote(heard)
    return {"text": text, "agreement": agreement, "changed": changed, "heard": [t for t, _ in heard]}


def _distance(a: list[str], b: list[str]) -> int:
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (x != y))
    return row[-1]


def _accuracy(reference: str, text: str) -> float:
    ref = reference.split()
    return max(0.0, 1.0 - _distance(ref, str(text).split()) / max(1, len(ref)))


def grade(exercise: Exercise, result) -> tuple[float, str]:
    if not isinstance(result, dict):
        return 0.0, ""
    voted = _accuracy(exercise.prompt, result.get("text", ""))
    score = round(voted, 4)
    lesson = ""
    if voted < 0.7:
        lesson = f"con {exercise.data['mics']} microfoni e {exercise.data['errors']} errori ciascuno il voto recupera {voted:.0%}"
    return score, lesson
