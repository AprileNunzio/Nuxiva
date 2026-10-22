from features.agent.registry import tool
from features.research import service
from features.research.report import render


@tool("web_research", "cerca su internet informazioni vere e recenti da fonti affidabili (notizie, eventi, orari, prezzi, risultati, persone, fatti che possono essere cambiati) e restituisce "
      "estratti con fonte, data e affidabilità; usalo ogni volta che non sei sicuro o la risposta dipende dall'attualità e non inventare mai ciò che non trovi",
      {"question": "la domanda da cercare, con nomi e contesto (senza dati personali)", "days": "solo fonti degli ultimi N giorni (0 = qualsiasi, facoltativo)",
       "limit": "numero massimo di fonti da 1 a 8 (facoltativo, 5 se vuoto)"}, agent="research")
async def web_research(question: str, days: int = 0, limit: int = 5) -> str:
    try:
        days, limit = int(days or 0), int(limit or 5)
    except (TypeError, ValueError):
        raise ValueError("days e limit devono essere numeri")
    return render(await service.research(str(question), days, limit))
