import random
import re

from features.diorama import spec as S

JAPAN = re.compile(r"giappon|japan|stazione|station|treno|train|ciliegi|sakura|ferrovi|railway|binari", re.I)
STAGES = ("terrain", "structures", "vegetation", "props", "life")


def item(kind: str, x: float, z: float, rot: float = 0.0, y: float = 0.0, scale: float = 1.0, motion: dict | None = None, **params) -> dict:
    return {"kind": kind, "x": x, "y": y, "z": z, "rot": rot, "scale": scale, "params": params, "motion": motion or {}}


def japanese_station(rng: random.Random) -> dict:
    cherries = [(-9.0, -5.6, 4.0), (-6.2, -6.2, 3.4), (-1.5, -6.4, 3.8), (3.2, -6.0, 3.2), (9.0, -5.2, 4.2),
                (-9.4, 5.8, 3.6), (-4.0, 6.2, 3.0), (6.4, 6.0, 3.6), (9.6, 4.2, 3.2)]
    staged = {
        "terrain": [
            item("grass_patch", 0, -5.6, w=22, d=3.6, density=0.8),
            item("grass_patch", 0, 5.6, w=22, d=3.8, density=0.75),
            item("rails", 0, 0, length=22, tracks=1),
            item("platform", -1.5, -2.5, length=15, width=3.2),
            item("road", 8.2, 0, rot=90, length=14, width=2.2),
            item("petals", -2, -3.2, w=14, d=3, count=260),
            item("petals", 2, 5.4, w=14, d=3, count=200),
        ],
        "structures": [
            item("station_building", -2.5, -5.0, w=8, d=3.6, h=3.0, sign="SAKURA"),
            item("canopy", -1.5, -2.5, length=11, width=3.0),
            item("footbridge", 3.6, -1.2, rot=90, length=9, height=3.2),
            item("crossing", 8.2, 0, rot=90, width=2.8),
            item("house", -8.5, 5.0, rot=10),
            item("house", -5.2, 5.6, rot=-6, w=3.6, h=2.2),
            item("house", 5.2, 5.4, rot=180, w=3.0),
        ],
        "vegetation": [item("tree_cherry", x, z, rot=rng.uniform(0, 360), height=h, bloom=rng.uniform(0.78, 1.0)) for x, z, h in cherries]
        + [item("bush", -10.2, -3.0, radius=0.7), item("bush", 10.0, -2.4, radius=0.6), item("tree_pine", 10.2, 1.8, height=3.2)],
        "props": [
            item("lamp", -6.0, -3.6, height=2.2), item("lamp", -0.5, -3.6, height=2.2), item("lamp", 3.5, -3.6, height=2.2),
            item("bench", -4.0, -3.5, rot=180), item("bench", 1.2, -3.5, rot=180),
            item("vending", -7.2, -4.0, rot=180, color="#c0392b"), item("vending", -7.9, -4.0, rot=180, color="#1b5fa6"),
            item("sign", 0.6, -2.0, text="1  SAKURA", height=1.5, rot=180),
            item("fence", -3, 2.0, length=12, height=0.7),
            item("rock", 10.4, -4.4, radius=0.6),
        ],
        "life": [
            item("train", 0, 0, cars=3, color="#e8e6e1", stripe="#2b7a4b", motion={"axis": "x", "speed": 1.6, "span": 34}),
            item("person", -5.0, -2.9, rot=200, color="#3b6ea5"), item("person", -4.4, -2.8, rot=170, color="#c0392b", height=0.7),
            item("person", 0.5, -2.6, rot=20, color="#6a4c93"), item("person", 2.2, -3.0, rot=120, color="#2f855a"),
            item("car", 8.2, 0, rot=90, color="#d9d9d9", motion={"axis": "z", "speed": 0.9, "span": 18}),
        ],
    }
    return {"title": "Stazione tra i ciliegi", "story": "Una piccola stazione di campagna in piena fioritura, all'ora d'oro.",
            "base": {"w": 22, "d": 15, "depth": 1.2}, "look": {"light": "golden_hour", "lens": "tilt_shift", "blur": 0.65, "mist": 0.2},
            "stages": staged}


def garden(rng: random.Random) -> dict:
    staged = {
        "terrain": [item("grass_patch", 0, 0, w=22, d=15), item("pond", -4, 2, w=5, d=3.5), item("path", 3, 0, rot=20, w=10, d=1.2)],
        "structures": [item("house", 5.0, -3.5, w=4, d=3.4, h=2.3)],
        "vegetation": [item("tree_maple", rng.uniform(-9, -6), rng.uniform(-5, -2), height=4.2), item("tree_cherry", -8, 4, height=3.6),
                       item("bush", 1.5, -3.8), item("bush", 8, 1.5, radius=0.7)],
        "props": [item("bench", 1.0, 2.2, rot=180), item("lamp", 3.2, 1.2), item("rock", -6.6, 2.4), item("rock", -2.2, 3.8, radius=0.4)],
        "life": [item("person", 2.0, 1.0, rot=90)],
    }
    return {"title": "Giardino", "story": "Un angolo di giardino con laghetto, casa e alberi.",
            "base": {"w": 22, "d": 15, "depth": 1.2}, "look": {"light": "golden_hour", "lens": "tilt_shift"}, "stages": staged}


def compose(prompt: str, seed: int | None = None) -> dict:
    rng = random.Random(seed if seed is not None else S.new_id())
    plan = japanese_station(rng) if JAPAN.search(prompt) else garden(rng)
    plan["stages"] = {name: S.clean_items(rows) for name, rows in plan["stages"].items()}
    return plan
