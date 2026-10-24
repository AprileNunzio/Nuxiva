from features.agent.registry import tool
from features.sports import commands


@tool("sport_query", "risponde a domande di sport: prossima partita, risultati e classifiche di squadre e campionati di calcio, calendario e classifiche della Formula 1, risultati, prossime partite e classifica dell'hockey su ghiaccio NHL; "
      "apre anche il widget dedicato sul display", {"question": "la domanda così come l'ha fatta la persona, per esempio «quando gioca il Napoli?»"}, agent="sports")
async def sport_query(question: str) -> str:
    try:
        text, _ = await commands.answer(question)
    except LookupError:
        raise ValueError("domanda non coperta dai dati sportivi in tempo reale (calcio, Formula 1, hockey NHL: risultati, calendari, classifiche): "
                         "per storia, regole, giocatori, record o altri sport usa la ricerca online; se la squadra non è chiara chiedi quale intende")
    return text
