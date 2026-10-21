import re
import logging
from typing import Any
from server.core.scanner.base import DiscoveryManifest
from server.features.agent_tools.base import BaseAgentTool

logger = logging.getLogger("nuxiva.tool.maps")

class MapsTool(BaseAgentTool):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id="show_maps_route",
            name="Google Maps Route",
            category="tool",
            description="Mostra mappa e indicazioni stradali per una destinazione.",
            icon="🗺️",
            parameters={
                "type": "object",
                "properties": {
                    "destinazione": {"type": "string", "description": "Nome del luogo o citta"},
                    "partenza": {"type": "string", "description": "Punto di partenza opzionale"},
                },
                "required": ["destinazione"],
            },
            metadata={"alias": "maps"},
        )

    async def execute(self, destinazione: str, partenza: str = "", **kwargs: Any) -> str:
        try:
            from installer_wizard.features.maps.maps import answer
            dest = re.sub(r"[\?\.\!].*$", "", destinazione).strip()
            part = re.sub(r"[\?\.\!].*$", "", partenza).strip() if partenza else ""
            testo_domanda = f"da {part} a {dest}" if part else f"per {dest}"
            speech, payload = await answer(testo_domanda)
            return f"SUCCESSO. Widget inviato. Dì ESATTAMENTE questo all'utente: '{speech}'"
        except Exception as e:
            logger.error(f"Errore nel calcolo del percorso Maps: {e}")
            return f"Errore nel caricamento delle mappe: {str(e)}"

async def show_maps_route(destinazione: str, partenza: str = "") -> str:
    tool = MapsTool()
    return await tool.execute(destinazione=destinazione, partenza=partenza)
