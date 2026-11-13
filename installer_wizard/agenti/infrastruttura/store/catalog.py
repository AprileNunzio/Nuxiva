from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import packages
from config import read_env


@dataclass(frozen=True)
class StoreItem:
    id: str
    category: str
    title: str
    description: str
    size_gb: float

    @property
    def package(self) -> packages.Package:
        return packages.PACKAGE_BY_ID[self.id]

    @property
    def env_key(self) -> str:
        return self.package.env

    @property
    def steps(self) -> tuple[str, ...]:
        return self.package.steps

    @property
    def detect(self) -> str:
        return self.package.detect

    @property
    def removable(self) -> bool:
        return self.package.removable


STORE_CATALOG = (
    StoreItem(
        "music",
        "audio",
        "Riconoscimento Musicale",
        "Riconosce brano, artista e album della musica in riproduzione o ascolto",
        0.3,
    ),
    StoreItem(
        "ear",
        "audio",
        "Ascolto Continuo",
        "Abilita il microfono sempre attivo con rilevamento della wake-word",
        1.5,
    ),
    StoreItem(
        "vision",
        "vision",
        "Visione e Biometria",
        "Riconoscimento facciale e tracciamento visivo con elaborazione locale",
        1.0,
    ),
    StoreItem(
        "documents",
        "productivity",
        "Suite Documenti Office",
        "Elabora, genera e legge file Word, Excel, PowerPoint e PDF",
        1.5,
    ),
    StoreItem(
        "convert3d",
        "productivity",
        "Conversione & CAD 3D",
        "Visualizzazione e conversione per modelli BLEND, OBJ, STL e DWG",
        1.0,
    ),
    StoreItem(
        "shares",
        "system",
        "Cartelle Condivise",
        "Condivisione file di rete compatibile con Windows, macOS e Linux",
        0.05,
    ),
    StoreItem(
        "brain_local",
        "intelligence",
        "Cervello Neurale Locale",
        "Esegue modelli linguistici avanzati sul computer tramite Ollama",
        8.0,
    ),
    StoreItem(
        "voicestudio",
        "audio",
        "Studio Voci Neurali",
        "Personalizzazione e sintesi vocale ad alta definizione con VoiceStudio",
        6.0,
    ),
    StoreItem(
        "bluetooth",
        "system",
        "Dispositivi Bluetooth",
        "Connessione con altoparlanti, cuffie e sensori wireless",
        0.05,
    ),
    StoreItem(
        "display",
        "system",
        "Display Kiosk HDMI",
        "Interfaccia grafica a tutto schermo su monitor fisico via Chromium",
        0.5,
    ),
)

ITEM_BY_ID = {item.id: item for item in STORE_CATALOG}


def get_catalog_with_status() -> List[dict]:
    env = read_env()
    out = []
    for item in STORE_CATALOG:
        state = packages.state(item.package, env)
        out.append({
            "id": item.id,
            "category": item.category,
            "title": item.title,
            "description": item.description,
            "size_gb": item.size_gb,
            "installed": state == "installed",
            "state": state,
            "removable": item.removable,
            "detect": item.detect,
            "source": "official",
            "repository_id": "official",
            "repository_name": "Repository Ufficiale Nuxiva",
        })
    return out


def find_item(item_id: str) -> Optional[StoreItem]:
    return ITEM_BY_ID.get(item_id)
