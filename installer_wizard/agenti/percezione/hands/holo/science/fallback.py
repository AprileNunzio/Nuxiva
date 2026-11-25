import math

from agenti.hands.holo.dna import _ball, _rod

MAX_TEXT = 8 * 1024 * 1024
MAX_ATOMS = 160
MAX_BONDS = 240
MAX_RESIDUES = 190
MIN_ATOMS = 2
BOND_COLOR = "#b8c4d6"
CHAIN_COLORS = ("#5ef2ff", "#ff6b9d", "#ffd166", "#06d6a0", "#a78bfa", "#ff9f1c", "#4cc9f0", "#f15bb5")
CA_GAP = 4.4
STYLE = {"H": ("#f1f5f9", 0.24), "C": ("#8d99ae", 0.38), "N": ("#3a6bff", 0.36), "O": ("#ff3b3b", 0.35), "S": ("#ffe14d", 0.48),
         "P": ("#ff8c1a", 0.48), "F": ("#3ddc84", 0.42), "Cl": ("#3ddc84", 0.42), "Br": ("#b5452f", 0.46), "I": ("#9b30c7", 0.5),
         "Fe": ("#e06633", 0.5), "Na": ("#a35cf2", 0.55), "K": ("#a35cf2", 0.55), "Ca": ("#7bdc3a", 0.52), "Mg": ("#7bdc3a", 0.52)}
BOND_RADIUS = {2: 0.17, 3: 0.22}


def _number(line: str, start: int, end: int) -> float:
    value = float(line[start:end].strip())
    if not math.isfinite(value) or abs(value) >= 10_000:
        raise ValueError("holo_bad_model")
    return value


def _count(line: str, start: int, end: int) -> int:
    return int(line[start:end].strip())


def _element(raw: str) -> str:
    letters = [c for c in raw if c.isascii() and c.isalpha()][:2]
    return (letters[0].upper() + "".join(letters[1:]).lower()) if letters else ""


def sdf_parts(text: str) -> list[dict]:
    if len(text) > MAX_TEXT:
        raise ValueError("holo_too_large")
    lines = text.splitlines()
    if len(lines) < 4 or "V2000" not in lines[3]:
        raise ValueError("holo_bad_model")
    atoms, bonds = _count(lines[3], 0, 3), _count(lines[3], 3, 6)
    if not MIN_ATOMS <= atoms <= MAX_ATOMS or bonds > MAX_BONDS or len(lines) < 4 + atoms + bonds:
        raise ValueError("holo_bad_model")
    placed = []
    for line in lines[4:4 + atoms]:
        symbol = _element(line[31:34])
        if not symbol:
            raise ValueError("holo_bad_model")
        placed.append(([_number(line, 0, 10), _number(line, 10, 20), _number(line, 20, 30)], symbol))
    out = []
    for line in lines[4 + atoms:4 + atoms + bonds]:
        a, b = _count(line, 0, 3) - 1, _count(line, 3, 6) - 1
        if not (0 <= a < atoms and 0 <= b < atoms):
            raise ValueError("holo_bad_model")
        order = int(line[6:9].strip() or 1)
        out.append(_rod("bond", placed[a][0], placed[b][0], BOND_RADIUS.get(order, 0.12), BOND_COLOR, 0))
    for at, symbol in placed:
        color, radius = STYLE.get(symbol, ("#ff4fb3", 0.45))
        out.append(_ball(f"atom_{symbol}", at, radius, color, 0))
    return out


def _carbons(text: str) -> list[tuple[list[float], str]]:
    found = []
    for line in text.splitlines():
        if line.startswith("ENDMDL"):
            break
        if not line.startswith("ATOM") or line[12:16].strip() != "CA" or line[16:17] not in (" ", "A", ""):
            continue
        chain = line[21:22]
        chain = chain if chain.isascii() and chain.isalnum() else "A"
        found.append(([_number(line, 30, 38), _number(line, 38, 46), _number(line, 46, 54)], chain))
    if len(found) < MIN_ATOMS:
        raise ValueError("holo_bad_model")
    return found


def pdb_parts(text: str) -> list[dict]:
    if len(text) > MAX_TEXT:
        raise ValueError("holo_too_large")
    found = _carbons(text)
    stride = max(1, -(-len(found) // MAX_RESIDUES))
    gap = CA_GAP * stride * 1.25
    chains, out, previous = [], [], None
    for at, chain in found[::stride]:
        if chain not in chains:
            chains.append(chain)
        color = CHAIN_COLORS[chains.index(chain) % len(CHAIN_COLORS)]
        name = f"protein_chain_{chain}"
        if previous and previous[1] == chain and math.dist(previous[0], at) <= gap:
            out.append(_rod(name, previous[0], at, 0.75, color, 0))
        out.append(_ball(name, at, 1.25, color, 0))
        previous = (at, chain)
    return out
