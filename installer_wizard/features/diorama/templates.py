import random
import re

from features.diorama import spec as S

JAPAN = re.compile(r"giappon|japan|stazione|station|treno|train|ciliegi|sakura|ferrovi|railway|binari", re.I)
CASTLE = re.compile(r"castell|castle|fortezz|fortress|rocca|manier|medieval", re.I)
STAGES = ("terrain", "structures", "vegetation", "props", "life", "details")


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
            "base": {"w": 22, "d": 15, "depth": 1.2}, "look": {"light": "golden_hour", "lens": "tilt_shift", "blur": 0.45, "mist": 0.08},
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


def castle(rng: random.Random) -> dict:
    stone, roof = "#b5a58d", "#8c3a2c"
    pines = [(-11.0, -6.5), (-11.2, 3.0), (10.8, -5.0), (11.4, 2.5), (11.4, 6.0), (-11.0, 8.5), (5.5, -9.4), (-5.8, -9.0)]
    staged = {
        "terrain": [
            item("grass_patch", 0, 0, w=25, d=21, density=0.8, color="#5f8a3a"),
            item("hill", 0, -9.6, radius=3.2, height=1.5),
            item("moat", 0, 0, w=15.6, d=13.6, ring=1.6),
            item("path", 0, 10.2, rot=90, w=3.4, d=1.6, material="stone", color="#a39a88"),
            item("path", 0, 12.0, rot=90, w=2.0, d=1.4, material="soil", color="#8a7355"),
            item("pond", 11.0, 9.4, w=3.2, d=2.0),
        ],
        "structures": [
            item("castle_wall", 0, -5, length=12, height=2.4, color=stone),
            item("castle_wall", -4.15, 5, length=4, height=2.4, color=stone),
            item("castle_wall", 4.15, 5, length=4, height=2.4, color=stone),
            item("castle_wall", -6, 0, rot=90, length=10, height=2.4, color=stone),
            item("castle_wall", 6, 0, rot=90, length=10, height=2.4, color=stone),
            item("tower_round", -6, -5, radius=1.25, height=4.6, color=stone, roof=roof),
            item("tower_round", 6, -5, radius=1.25, height=4.6, color=stone, roof=roof),
            item("tower_round", -6, 5, radius=1.25, height=4.2, color=stone, roof=roof),
            item("tower_round", 6, 5, radius=1.25, height=4.2, color=stone, roof=roof),
            item("keep", 0, -1.4, w=6, d=4.6, h=4.4, color="#b3a38b", roof="#6d3a30"),
            item("gatehouse", 0, 5, width=3.4, height=3.2, color=stone),
            item("drawbridge", 0, 5.9, length=2.9, width=1.5),
        ],
        "vegetation": [item("tree_pine", x, z, rot=rng.uniform(0, 360), height=rng.uniform(2.8, 4.2), color=rng.choice(["#2f5d3a", "#3a6b44", "#2b5336"])) for x, z in pines]
        + [item("tree_maple", -11.0, -1.4, height=2.6), item("bush", 7.6, 10.2, radius=0.6), item("bush", -7.2, 10.2, radius=0.7)],
        "props": [
            item("lamp", -2.2, 10.2, height=1.7), item("lamp", 2.2, 10.2, height=1.7),
            item("rock", -9.8, 6.6, radius=0.7), item("rock", 10.6, -8.6, radius=0.9), item("rock", 11.4, 7.0, radius=0.5),
            item("block", 3.2, 1.6, w=0.7, d=0.7, h=0.6, material="wood", color="#6b4a2e"), item("block", 3.9, 1.9, w=0.6, d=0.6, h=0.5, material="wood", color="#7a5535"),
            item("cylinder", -3.1, 2.0, radius=0.35, top=0.35, h=0.7, material="wood", color="#6b4a2e"),
            item("fence", -4.2, 10.6, length=3, height=0.7, material="wood", color="#6b4a2e"),
        ],
        "life": [
            item("person", 0, 9.4, rot=0, color="#8c3a2c"), item("person", 1.2, 4.0, rot=180, color="#3b6ea5"), item("person", -1.6, 1.0, rot=90, color="#6a4c93"),
            item("person", -2.4, 10.6, rot=40, color="#2f855a", height=0.7),
        ],
        "details": [
            item("flag", 8.4, -8.0, height=2.0), item("flag", -2.0, 7.2, height=1.4, color="#1b5fa6"),
            *[item("bush", rng.uniform(-9.5, 9.5), rng.choice([-9.6, 9.8]), radius=rng.uniform(0.3, 0.55), color="#4f7d3a") for _ in range(6)],
            *[item("rock", rng.uniform(-11, 11), rng.uniform(-9.5, 9.5), radius=rng.uniform(0.2, 0.4)) for _ in range(5)],
        ],
    }
    return {"title": "Il castello sul fossato", "story": "Una rocca di pietra con torri, mura merlate e ponte levatoio, circondata da pini.",
            "base": {"w": 26, "d": 22, "depth": 1.6}, "look": {"light": "golden_hour", "lens": "tilt_shift", "blur": 0.4, "mist": 0.06},
            "palette": {"grass": "#5f8a3a", "wall": "#b5a58d", "roof": roof, "stone": stone, "water": "#3f7f93"}, "stages": staged}


def compose(prompt: str, seed: int | None = None) -> dict:
    rng = random.Random(seed if seed is not None else S.new_id())
    plan = castle(rng) if CASTLE.search(prompt) else japanese_station(rng) if JAPAN.search(prompt) else garden(rng)
    plan["stages"] = {name: S.clean_items(plan["stages"].get(name, [])) for name in STAGES}
    return plan
