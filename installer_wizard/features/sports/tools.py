from features.agent.registry import tool
from features.sports import commands


@tool("sport_query", "risponde a domande di sport: prossima partita, risultati e classifiche di squadre e campionati di calcio, calendario e classifiche della Formula 1; "
      "apre anche il widget dedicato sul display", {"question": "la domanda così come l'ha fatta la persona, per esempio «quando gioca il Napoli?»"}, agent="sports")
async def sport_query(question: str) -> str:
    try:
        text, _ = await commands.answer(question)
    except LookupError:
        raise ValueError("squadra o competizione non riconosciuta: chiedi alla persona quale squadra intende")
    return text
