from features.agent.registry import tool
from features.camsense import service
from features.camsense.model import SenseError
from features.camsense.store import sensors

STATE_TEXT = "{name}: {state} (affidabilità {confidence:.0%})"


def _describe(row: dict) -> str:
    if row["state"]:
        return STATE_TEXT.format(name=row["name"], state=row["state"], confidence=row["confidence"])
    reasons = {"needs_two_states": "mancano esempi di almeno due stati", "unlike_any_state": "la scena non somiglia a nessuno stato imparato",
               "ambiguous": "la scena è ambigua tra due stati", "camera_offline": "la telecamera non risponde"}
    return f"{row['name']}: stato sconosciuto ({reasons.get(row['reason'], 'nessuna lettura ancora')})"


@tool("camsense_list", "elenca i sensori virtuali basati sulle telecamere (per esempio porta del garage, luce del salotto) con lo stato attuale di ciascuno",
      {}, agent="camsense")
async def camsense_list() -> str:
    rows = list(sensors.all().values())
    return "\n".join(_describe(r) for r in rows) or "nessun sensore: creane uno con camsense_create"


@tool("camsense_state", "dice in che stato è un sensore a telecamera (per esempio se la porta è aperta o chiusa), leggendo subito l'immagine",
      {"sensor": "nome del sensore"}, agent="camsense")
async def camsense_state(sensor: str) -> str:
    try:
        return _describe(await service.check(service.slug(sensor)))
    except SenseError as exc:
        raise ValueError(f"lettura non riuscita: {exc.code}")


@tool("camsense_create", "crea un sensore a telecamera su una zona dell'immagine; poi insegna gli stati con camsense_learn",
      {"name": "nome del sensore", "camera": "identificativo della telecamera",
       "x": "bordo sinistro della zona da 0 a 1", "y": "bordo alto da 0 a 1", "w": "larghezza da 0 a 1", "h": "altezza da 0 a 1"}, agent="camsense")
async def camsense_create(name: str, camera: str, x: float = 0, y: float = 0, w: float = 1, h: float = 1) -> str:
    try:
        row = service.create(name, camera, [x, y, w, h])
    except SenseError as exc:
        raise ValueError(f"sensore non creato: {exc.code}")
    return f"sensore {row['name']} creato: insegnagli almeno due stati con camsense_learn"


@tool("camsense_learn", "insegna a un sensore come appare uno stato: guarda l'immagine adesso e la associa all'etichetta (per esempio aperta o chiusa)",
      {"sensor": "nome del sensore", "label": "etichetta dello stato visibile in questo momento"}, agent="camsense")
async def camsense_learn(sensor: str, label: str) -> str:
    try:
        row = await service.learn(service.slug(sensor), label)
    except SenseError as exc:
        raise ValueError(f"esempio non salvato: {exc.code}")
    quality = row["quality"]
    return f"{row['name']}: esempi {row['samples']}; qualità {quality['reason']}" + (f", precisione {quality['accuracy']:.0%}" if quality["accuracy"] is not None else "")
