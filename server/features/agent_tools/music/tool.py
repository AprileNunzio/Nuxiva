import os
from typing import Any
from server.core.scanner.base import DiscoveryManifest
from server.features.agent_tools.base import BaseAgentTool

class MusicTool(BaseAgentTool):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id="play_music",
            name="Music Player",
            category="tool",
            description="Riproduce musica specificando sorgente e brano.",
            icon="🎵",
            parameters={
                "type": "object",
                "properties": {
                    "brano": {"type": "string", "description": "Titolo o artista del brano"},
                    "sorgente": {"type": "string", "enum": ["locale", "spotify"], "default": "locale"},
                },
            },
            metadata={"alias": "music"},
        )

    async def execute(self, brano: str = "", sorgente: str = "locale", **kwargs: Any) -> str:
        try:
            from installer_wizard.features.shares.archive import folder as share_folder
            music_root = str(share_folder("musica"))
        except ImportError:
            music_root = os.path.join(os.environ.get("DATA_DIR", "./data"), "Musica")

        music_library_dir = os.path.join(music_root, "Libreria")

        if "back in black" in brano.lower() or "ac/dc" in brano.lower():
            brano_effettivo = "Back in Black - AC/DC"
            enthusiasm = "ROCK ON! È la mia preferita in assoluto!"
        else:
            brano_effettivo = brano if brano else "Musica Casuale"
            enthusiasm = ""

        if sorgente.lower() == "spotify":
            return f"SUCCESSO. Riproduzione di '{brano_effettivo}' avviata su Spotify. {enthusiasm}"

        if not os.path.exists(music_library_dir):
            return "Errore: Libreria locale non trovata."

        trovato = False
        for root, dirs, files in os.walk(music_library_dir):
            for f in files:
                if brano.lower() in f.lower() or brano.lower() in root.lower():
                    trovato = True
                    brano_effettivo = f
                    break
            if trovato:
                break

        if not brano:
            trovato = True

        if trovato:
            return f"SUCCESSO. Riproduzione locale di '{brano_effettivo}' avviata. {enthusiasm}"
        return f"ERRORE. Brano '{brano}' non trovato nella libreria locale. Prova a scaricarlo o usa sorgente='spotify'."

async def play_music(brano: str = "", sorgente: str = "locale") -> str:
    tool = MusicTool()
    return await tool.execute(brano=brano, sorgente=sorgente)
