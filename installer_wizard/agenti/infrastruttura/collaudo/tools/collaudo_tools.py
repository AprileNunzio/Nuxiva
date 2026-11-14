from agenti.agent.registry import tool
from agenti.collaudo.agent import agent


@tool("collaudo_describe", "Flusso unico e strutturato di eventi di Sentinella, ascolto, visione, supervisore, MCP ed errori per il collaudo su macchina reale, con rapporto di diagnosi e test di fumo.", {}, agent="collaudo")
async def collaudo_describe() -> dict:
    return agent.describe()
