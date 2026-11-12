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
    env_key: str
    steps: tuple[str, ...]
    detect: str = ""
    removable: bool = True


STORE_CATALOG = (
    StoreItem(
        "music",
        "audio",
        "Riconoscimento Musicale",
        "Riconosce brano, artista e album della musica in riproduzione o ascolto",
        0.3,
        "NUXIVA_MUSIC_ID",
        ("music",),
    ),
    StoreItem(
        "ear",
        "audio",
        "Ascolto Continuo",
        "Abilita il microfono sempre attivo con rilevamento della wake-word",
        1.5,
        "NUXIVA_EAR",
        ("ear",),
    ),
    StoreItem(
        "vision",
        "vision",
        "Visione e Biometria",
        "Riconoscimento facciale e tracciamento visivo con elaborazione locale",
        1.0,
        "NUXIVA_VISION",
        ("vision",),
        detect="camera",
    ),
    StoreItem(
        "documents",
        "productivity",
        "Suite Documenti Office",
        "Elabora, genera e legge file Word, Excel, PowerPoint e PDF",
        1.5,
        "NUXIVA_DOCUMENTS",
        ("office",),
    ),
    StoreItem(
        "convert3d",
        "productivity",
        "Conversione & CAD 3D",
        "Visualizzazione e conversione per modelli BLEND, OBJ, STL e DWG",
        1.0,
        "NUXIVA_3D_CONVERT",
        ("convert3d",),
    ),
    StoreItem(
        "shares",
        "system",
        "Cartelle Condivise",
        "Condivisione file di rete compatibile con Windows, macOS e Linux",
        0.05,
        "NUXIVA_SHARES",
        ("shares",),
    ),
    StoreItem(
        "brain_local",
        "intelligence",
        "Cervello Neurale Locale",
        "Esegue modelli linguistici avanzati sul computer tramite Ollama",
        8.0,
        "NUXIVA_BRAIN",
        ("ollama", "brain", "soup"),
        removable=False,
    ),
    StoreItem(
        "voicestudio",
        "audio",
        "Studio Voci Neurali",
        "Personalizzazione e sintesi vocale ad alta definizione con VoiceStudio",
        6.0,
        "NUXIVA_VOICESTUDIO",
        ("voicestudio",),
    ),
    StoreItem(
        "bluetooth",
        "system",
        "Dispositivi Bluetooth",
        "Connessione con altoparlanti, cuffie e sensori wireless",
        0.05,
        "NUXIVA_BLUETOOTH",
        ("bluetooth",),
        detect="bluetooth",
    ),
    StoreItem(
        "display",
        "system",
        "Display Kiosk HDMI",
        "Interfaccia grafica a tutto schermo su monitor fisico via Chromium",
        0.5,
        "NUXIVA_KIOSK",
        ("kiosk",),
        detect="monitor",
        removable=True,
    ),
)

ITEM_BY_ID = {item.id: item for item in STORE_CATALOG}


def get_catalog_with_status() -> List[dict]:
    env = read_env()
    out = []
    for item in STORE_CATALOG:
        val = env.get(item.env_key, "0").lower()
        is_installed = val in packages.ON
        out.append({
            "id": item.id,
            "category": item.category,
            "title": item.title,
            "description": item.description,
            "size_gb": item.size_gb,
            "installed": is_installed,
            "removable": item.removable,
            "detect": item.detect,
            "source": "official",
            "repository_id": "official",
            "repository_name": "Repository Ufficiale Nuxiva",
        })
    return out


def find_item(item_id: str) -> Optional[StoreItem]:
    return ITEM_BY_ID.get(item_id)
