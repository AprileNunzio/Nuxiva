from features.agent.registry import tool
from features.sports import commands
from features.sports.catalog import sports_summary


@tool("sport_query", f"risponde con dati sportivi in tempo reale e apre il widget sul display: partite in corso, risultati, prossime partite, classifiche e calendari "
      f"per gli sport del catalogo ({sports_summary()}); per ciò che il catalogo non copre (giocatori, statistiche, storia, altri sport) non è lo strumento adatto",
      {"question": "la domanda così come l'ha fatta la persona, per esempio «quando gioca il Napoli?»"}, agent="sports")
async def sport_query(question: str) -> str:
    try:
        text, _ = await commands.answer(question)
    except LookupError:
        raise ValueError("nessuna squadra o competizione del catalogo sportivo riconosciuta: usa la ricerca online (web_research) per questa domanda")
    return text
