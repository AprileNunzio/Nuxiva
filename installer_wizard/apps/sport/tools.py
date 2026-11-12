from features.agent.registry import tool

OWNER = "sport"

SPORTS_DATA = {
    "football": {
        "name": "Calcio",
        "events": [
            {"title": "Inter vs Juventus", "score": "2 - 1", "status": "LIVE (74’)", "tv": "DAZN 1 HD"},
            {"title": "Napoli vs Milan", "score": "1 - 1", "status": "LIVE (62’)", "tv": "Sky Sport Calcio"},
            {"title": "Roma vs Lazio", "score": "0 - 0", "status": "Oggi 20:45", "tv": "DAZN 1 HD"},
        ],
        "standings": [
            {"rank": 1, "team": "Napoli", "pts": 19},
            {"rank": 2, "team": "Inter", "pts": 17},
            {"rank": 3, "team": "Juventus", "pts": 16},
            {"rank": 4, "team": "Milan", "pts": 14},
        ],
        "channels": ["Sky Sport Calcio HD", "DAZN 1 HD", "Rai Sport HD"],
    },
    "formula1": {
        "name": "Formula 1",
        "events": [
            {"title": "GP USA Austin", "score": "Giro 38/56", "status": "GARA LIVE", "leader": "C. Leclerc", "tv": "Sky Sport F1 HD"},
        ],
        "standings": [
            {"rank": 1, "driver": "Max Verstappen", "pts": 354},
            {"rank": 2, "driver": "Lando Norris", "pts": 297},
            {"rank": 3, "driver": "Charles Leclerc", "pts": 275},
        ],
        "channels": ["Sky Sport F1 HD", "F1 Live Timing Feed"],
    },
    "motogp": {
        "name": "MotoGP",
        "events": [
            {"title": "GP Malesia Sepang", "score": "Giro 14/20", "status": "GARA LIVE", "leader": "F. Bagnaia", "tv": "Sky Sport MotoGP HD"},
        ],
        "standings": [
            {"rank": 1, "rider": "Jorge Martín", "pts": 453},
            {"rank": 2, "rider": "Francesco Bagnaia", "pts": 436},
            {"rank": 3, "rider": "Marc Márquez", "pts": 356},
        ],
        "channels": ["Sky Sport MotoGP HD"],
    },
    "basketball": {
        "name": "Pallacanestro",
        "events": [
            {"title": "Boston Celtics vs Los Angeles Lakers", "score": "88 - 82", "status": "LIVE Q3", "tv": "Sky Sport NBA HD"},
        ],
        "standings": [
            {"rank": 1, "team": "Boston Celtics", "record": "7-1"},
            {"rank": 2, "team": "Cleveland Cavaliers", "record": "8-0"},
        ],
        "channels": ["Sky Sport NBA HD", "DAZN 2 HD"],
    },
    "tennis": {
        "name": "Tennis",
        "events": [
            {"title": "Jannik Sinner vs Carlos Alcaraz", "score": "6-4, 4-6, 3-2", "status": "LIVE (3° Set)", "tv": "Sky Sport Tennis HD"},
        ],
        "standings": [
            {"rank": 1, "player": "Jannik Sinner", "pts": "11,830"},
            {"rank": 2, "player": "Carlos Alcaraz", "pts": "7,120"},
        ],
        "channels": ["Sky Sport Tennis HD"],
    },
}


@tool("sport_list_events", "elenca gli eventi, match e gare sportive in programma o live su Nuxiva",
      {"sport_id": "identificatore dello sport (football, formula1, motogp, basketball, tennis o vuoto per tutti)"},
      agent=OWNER)
def sport_list_events(sport_id: str = "") -> list[dict]:
    sid = sport_id.strip().lower()
    if sid and sid in SPORTS_DATA:
        return SPORTS_DATA[sid]["events"]
    res = []
    for s_key, s_val in SPORTS_DATA.items():
        for ev in s_val["events"]:
            res.append({"sport": s_val["name"], **ev})
    return res


@tool("sport_get_live_scores", "restituisce i punteggi in tempo reale e lo stato di avanzamento per lo sport selezionato",
      {"sport_id": "identificatore dello sport (football, formula1, motogp, basketball, tennis)"},
      agent=OWNER)
def sport_get_live_scores(sport_id: str) -> dict:
    sid = sport_id.strip().lower()
    if sid not in SPORTS_DATA:
        return {"error": f"Sport «{sport_id}» non riconosciuto. Scegli tra football, formula1, motogp, basketball, tennis."}
    return {
        "sport": SPORTS_DATA[sid]["name"],
        "live_events": [ev for ev in SPORTS_DATA[sid]["events"] if "LIVE" in ev.get("status", "")],
    }


@tool("sport_get_standings", "mostra la classifica aggiornata per la disciplina o campionato specificato",
      {"sport_id": "identificatore dello sport (football, formula1, motogp, basketball, tennis)"},
      agent=OWNER)
def sport_get_standings(sport_id: str) -> dict:
    sid = sport_id.strip().lower()
    if sid not in SPORTS_DATA:
        return {"error": f"Sport «{sport_id}» non riconosciuto."}
    return {
        "sport": SPORTS_DATA[sid]["name"],
        "standings": SPORTS_DATA[sid]["standings"],
    }


@tool("sport_get_tv_channels", "restituisce i canali TV ed IPTV collegati per vedere in diretta le gare o i match dello sport selezionato",
      {"sport_id": "identificatore dello sport (football, formula1, motogp, basketball, tennis)"},
      agent=OWNER)
def sport_get_tv_channels(sport_id: str) -> dict:
    sid = sport_id.strip().lower()
    if sid not in SPORTS_DATA:
        return {"error": f"Sport «{sport_id}» non riconosciuto."}
    return {
        "sport": SPORTS_DATA[sid]["name"],
        "channels": SPORTS_DATA[sid]["channels"],
    }
