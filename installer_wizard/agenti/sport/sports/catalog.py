from dataclasses import dataclass


@dataclass(frozen=True)
class League:
    code: str
    name: str
    flag: str
    cup: bool = False
    sport: str = "soccer"
    sport_label: str = "calcio"
    aliases: tuple[str, ...] = ()

    @property
    def path(self) -> str:
        return f"{self.sport}/{self.code}"

    @property
    def labels(self) -> tuple[str, ...]:
        return (self.name, *self.aliases)


LEAGUES: tuple[League, ...] = (
    League("ita.1", "Serie A", "🇮🇹", aliases=("campionato italiano",)),
    League("ita.2", "Serie B", "🇮🇹"),
    League("ita.coppa_italia", "Coppa Italia", "🇮🇹", True),
    League("uefa.champions", "Champions League", "🇪🇺", True, aliases=("champions",)),
    League("uefa.europa", "Europa League", "🇪🇺", True),
    League("uefa.europa.conf", "Conference League", "🇪🇺", True),
    League("eng.1", "Premier League", "🏴", aliases=("premier",)),
    League("esp.1", "LaLiga", "🇪🇸", aliases=("liga",)),
    League("ger.1", "Bundesliga", "🇩🇪"),
    League("fra.1", "Ligue 1", "🇫🇷"),
    League("por.1", "Liga Portugal", "🇵🇹"),
    League("ned.1", "Eredivisie", "🇳🇱"),
    League("fifa.world", "Mondiali", "🌍", True),
    League("uefa.euro", "Europei", "🇪🇺", True),
    League("uefa.nations", "Nations League", "🇪🇺", True),
    League("nhl", "NHL", "🏒", sport="hockey", sport_label="hockey su ghiaccio", aliases=("hockey", "hockey su ghiaccio")),
    League("nba", "NBA", "🏀", sport="basketball", sport_label="basket", aliases=("basket", "pallacanestro")),
    League("wnba", "WNBA", "🏀", sport="basketball", sport_label="basket femminile"),
    League("nfl", "NFL", "🏈", sport="football", sport_label="football americano", aliases=("football americano",)),
    League("mlb", "MLB", "⚾", sport="baseball", sport_label="baseball", aliases=("baseball",)),
)
BY_CODE = {lg.code: lg for lg in LEAGUES}
TABLE_LEAGUES = tuple(lg.code for lg in LEAGUES if not lg.cup)
INDEXED = tuple(lg.code for lg in LEAGUES if not lg.cup)
F1_LABELS = ("formula 1", "formula uno", "f1", "gran premio", "mondiale piloti", "mondiale costruttori")
TEAM_ALIASES = {"juve": "juventus", "inter": "internazionale", "milan": "ac milan", "roma": "as roma", "barca": "barcelona",
                "real": "real madrid", "psg": "paris saint-germain", "bayern": "bayern munich", "atletico": "atletico madrid"}
LIVE, PRE, POST = "in", "pre", "post"


def sports_summary() -> str:
    labels = dict.fromkeys(["Formula 1", *(lg.sport_label for lg in LEAGUES)])
    return ", ".join(labels)
