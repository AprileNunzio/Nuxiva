from dataclasses import dataclass

K4 = "X...X...X...X..."
BACK = "....X.......X..."
H8 = "x.x.x.x.x.x.x.x."
H16 = "xxxxxxxxxxxxxxxx"
ROLES_ALL = ("drums", "bass", "chords", "pad", "lead", "arp")


@dataclass(frozen=True)
class Genre:
    id: str
    name: str
    family: str
    tempo: tuple[int, int]
    mode: str
    drums: dict
    bass: str
    comp: str
    kit: str
    bass_i: str
    chords_i: str
    lead_i: str
    prog: str = ""
    swing: float = 0.0
    beats: int = 4
    seventh: bool = False
    roles: tuple[str, ...] = ROLES_ALL
    pad_i: str = "pad_warm"
    arp_i: str = "arp_pluck"
    tags: tuple[str, ...] = ()
    feel: str = ""


def g(id: str, name: str, family: str, tempo: tuple[int, int], mode: str, drums: dict, bass: str, comp: str, kit: str, bass_i: str, chords_i: str, lead_i: str, **extra) -> Genre:
    return Genre(id, name, family, tempo, mode, drums, bass, comp, kit, bass_i, chords_i, lead_i, **extra)
