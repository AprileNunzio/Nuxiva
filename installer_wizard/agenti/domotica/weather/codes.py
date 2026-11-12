WMO = {
    0: ("Sereno", "clear"), 1: ("Prevalentemente sereno", "clear"), 2: ("Parzialmente nuvoloso", "partly"),
    3: ("Coperto", "cloudy"), 45: ("Nebbia", "fog"), 48: ("Nebbia con brina", "fog"),
    51: ("Pioviggine leggera", "drizzle"), 53: ("Pioviggine", "drizzle"), 55: ("Pioviggine intensa", "drizzle"),
    56: ("Pioviggine gelata", "drizzle"), 57: ("Pioviggine gelata", "drizzle"),
    61: ("Pioggia debole", "rain"), 63: ("Pioggia", "rain"), 65: ("Pioggia forte", "rain"),
    66: ("Pioggia gelata", "rain"), 67: ("Pioggia gelata forte", "rain"),
    71: ("Neve debole", "snow"), 73: ("Neve", "snow"), 75: ("Neve forte", "snow"), 77: ("Granelli di neve", "snow"),
    80: ("Rovesci", "rain"), 81: ("Rovesci", "rain"), 82: ("Rovesci violenti", "storm"),
    85: ("Rovesci di neve", "snow"), 86: ("Rovesci di neve forti", "snow"),
    95: ("Temporale", "storm"), 96: ("Temporale con grandine", "storm"), 99: ("Temporale con grandine", "storm"),
}
DAYS_IT = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
MONTHS_IT = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
             "ottobre", "novembre", "dicembre"]
COMPASS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")


def describe(code, night: bool = False) -> tuple[str, str]:
    desc, icon = WMO.get(int(code) if code is not None else -1, ("—", "cloudy"))
    if night and icon in ("clear", "partly"):
        icon = "night" if icon == "clear" else "night_partly"
    return desc, icon


def compass(degrees) -> str:
    if degrees is None:
        return ""
    return COMPASS[int((float(degrees) % 360) / 22.5 + 0.5) % 16]
