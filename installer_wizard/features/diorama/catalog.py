from dataclasses import dataclass, field

MATERIALS = ("concrete", "wood", "metal", "plastic", "brick", "tile", "glass", "grass", "soil", "asphalt", "paint", "stone")
LIGHTS = ("golden_hour", "overcast", "blue_hour", "noon", "night")
LENSES = ("macro", "tilt_shift", "standard_50mm")
LIGHT_DEFAULT = "golden_hour"
LENS_DEFAULT = "tilt_shift"


@dataclass(frozen=True)
class Param:
    kind: str
    low: float = 0.0
    high: float = 0.0
    default: object = None
    choices: tuple[str, ...] = ()


def num(low: float, high: float, default: float) -> Param:
    return Param("number", low, high, default)


def color(default: str) -> Param:
    return Param("color", default=default)


def choice(options: tuple[str, ...], default: str) -> Param:
    return Param("choice", default=default, choices=options)


def text(default: str, limit: int = 24) -> Param:
    return Param("text", high=limit, default=default)


def flag(default: bool) -> Param:
    return Param("flag", default=default)


@dataclass(frozen=True)
class Kind:
    id: str
    label: str
    group: str
    hint: str
    params: dict[str, Param] = field(default_factory=dict)


KINDS: tuple[Kind, ...] = (
    Kind("grass_patch", "Prato", "Terreno", "Erba fitta con fili singoli e fiori di campo.",
         {"w": num(1, 40, 8), "d": num(1, 40, 6), "density": num(0.1, 1, 0.7), "color": color("#6f9a3c"), "flowers": color("#f4d35e")}),
    Kind("path", "Percorso", "Terreno", "Lastra di ghiaia, cemento o asfalto.",
         {"w": num(0.5, 40, 6), "d": num(0.5, 40, 1.4), "material": choice(("concrete", "asphalt", "stone", "soil"), "concrete"), "color": color("#a9a79f")}),
    Kind("pond", "Laghetto", "Terreno", "Specchio d'acqua con bordo di sassi.",
         {"w": num(1, 20, 4), "d": num(1, 20, 3), "color": color("#4a8fa8")}),
    Kind("rock", "Roccia", "Terreno", "Masso irregolare.", {"radius": num(0.1, 3, 0.6), "color": color("#8b8a84")}),
    Kind("petals", "Petali caduti", "Terreno", "Petali sparsi sul suolo.",
         {"w": num(0.5, 30, 6), "d": num(0.5, 30, 4), "count": num(10, 600, 220), "color": color("#f7c5d3")}),
    Kind("platform", "Banchina", "Ferrovia", "Marciapiede di stazione con linea gialla e guida tattile.",
         {"length": num(2, 40, 14), "width": num(1, 8, 3), "height": num(0.1, 1.2, 0.45), "color": color("#b9b7ae")}),
    Kind("rails", "Binari", "Ferrovia", "Binari con traversine e massicciata.",
         {"length": num(2, 60, 24), "tracks": num(1, 3, 1), "ballast": flag(True)}),
    Kind("train", "Treno", "Ferrovia", "Convoglio elettrico a più carrozze.",
         {"cars": num(1, 8, 3), "color": color("#e8e6e1"), "stripe": color("#2b7a4b"), "car_length": num(2, 6, 3.6)}),
    Kind("station_building", "Edificio di stazione", "Architettura", "Stazione con tetto, finestre, insegna e porta.",
         {"w": num(2, 20, 7), "d": num(2, 14, 4), "h": num(1.5, 8, 3), "style": choice(("japanese", "modern", "wood"), "japanese"),
          "wall": color("#d9d2c3"), "roof": color("#3c4a57"), "sign": text("SAKURA")}),
    Kind("canopy", "Pensilina", "Architettura", "Tettoia della banchina su pilastri.",
         {"length": num(2, 40, 10), "width": num(1, 8, 3.4), "height": num(1, 5, 2.4), "color": color("#cfd3d6")}),
    Kind("footbridge", "Passerella", "Architettura", "Cavalcavia pedonale coperto con scale.",
         {"length": num(3, 30, 9), "height": num(1.5, 6, 3.2), "color": color("#d8d4cb")}),
    Kind("house", "Casa", "Architettura", "Casa tradizionale con tetto a falde.",
         {"w": num(1, 12, 3.2), "d": num(1, 12, 2.8), "h": num(1, 6, 1.9), "wall": color("#e4dccb"), "roof": color("#4f5b66")}),
    Kind("crossing", "Passaggio a livello", "Ferrovia", "Barriere a strisce, semaforo e luci.",
         {"width": num(1, 8, 3), "open": flag(False)}),
    Kind("tree_cherry", "Ciliegio in fiore", "Vegetazione", "Tronco nodoso con chioma di migliaia di fiori.",
         {"height": num(0.8, 8, 3.4), "bloom": num(0.3, 1, 0.9), "color": color("#f5b6c8")}),
    Kind("tree_pine", "Pino", "Vegetazione", "Conifera a strati.", {"height": num(0.8, 8, 3), "color": color("#2f5d3a")}),
    Kind("tree_maple", "Acero", "Vegetazione", "Chioma tondeggiante dai toni caldi.", {"height": num(0.8, 8, 3), "color": color("#c8542b")}),
    Kind("bush", "Cespuglio", "Vegetazione", "Siepe o arbusto con fiori.", {"radius": num(0.1, 2, 0.5), "color": color("#4f7d3a"), "flowers": color("#e35d8f")}),
    Kind("lamp", "Lampione", "Arredo", "Palo con lampada.", {"height": num(0.5, 5, 2), "lit": flag(True), "color": color("#454a50")}),
    Kind("bench", "Panchina", "Arredo", "Panchina in legno con struttura in metallo.", {"length": num(0.4, 4, 1.2), "color": color("#8a5a35")}),
    Kind("fence", "Recinzione", "Arredo", "Ringhiera o steccato.", {"length": num(0.5, 30, 6), "height": num(0.2, 2, 0.8), "material": choice(("metal", "wood"), "metal"), "color": color("#5b6168")}),
    Kind("road", "Strada", "Terreno", "Strada asfaltata con linee.", {"length": num(1, 40, 14), "width": num(0.8, 8, 2.4)}),
    Kind("vending", "Distributore automatico", "Arredo", "Distributore con vetrina luminosa.", {"color": color("#c0392b")}),
    Kind("sign", "Cartello", "Arredo", "Cartello con scritta.", {"text": text("PLATFORM 1"), "color": color("#1b5fa6"), "height": num(0.5, 4, 1.4)}),
    Kind("person", "Persona", "Arredo", "Figura in scala, in piedi.", {"color": color("#3b6ea5"), "height": num(0.3, 1.2, 0.75)}),
    Kind("car", "Auto", "Arredo", "Utilitaria compatta.", {"color": color("#d9d9d9")}),
    Kind("block", "Volume libero", "Libero", "Parallelepipedo con materiale a scelta per forme su misura.",
         {"w": num(0.05, 30, 1), "h": num(0.05, 20, 1), "d": num(0.05, 30, 1), "material": choice(MATERIALS, "concrete"), "color": color("#b0b0b0")}),
    Kind("cylinder", "Cilindro libero", "Libero", "Cilindro o cono tronco con materiale a scelta.",
         {"radius": num(0.05, 10, 0.5), "top": num(0, 10, 0.5), "h": num(0.05, 20, 1), "material": choice(MATERIALS, "concrete"), "color": color("#b0b0b0")}),
)

BY_ID = {k.id: k for k in KINDS}


def public() -> dict:
    kinds = [{"id": k.id, "label": k.label, "group": k.group, "hint": k.hint,
              "params": {n: {"type": p.kind, "min": p.low, "max": p.high, "default": p.default, "choices": list(p.choices)}
                         for n, p in k.params.items()}} for k in KINDS]
    return {"kinds": kinds, "lights": list(LIGHTS), "lenses": list(LENSES), "materials": list(MATERIALS)}


MOTION_NOTE = "Items train, person and car accept an optional \"motion\":{\"axis\":\"x\"|\"z\",\"speed\":-4..4 (m/s),\"span\":4..60 (loop length in m)} so they travel and wrap around."


def prompt_catalog() -> str:
    rows = []
    for k in KINDS:
        spec = []
        for name, p in k.params.items():
            if p.kind == "number":
                spec.append(f"{name}:{p.low:g}-{p.high:g}")
            elif p.kind == "choice":
                spec.append(f"{name}:{'|'.join(p.choices)}")
            elif p.kind == "color":
                spec.append(f"{name}:#hex")
            elif p.kind == "flag":
                spec.append(f"{name}:bool")
            else:
                spec.append(f"{name}:text")
        rows.append(f"- {k.id} ({k.hint}) params {{{', '.join(spec)}}}")
    return "\n".join(rows) + "\n" + MOTION_NOTE
