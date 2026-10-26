from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    id: str
    env_key: str
    icon: str
    label: str
    hint: str
    max_tokens: int = 1200

    @property
    def scope_key(self) -> str:
        return self.env_key.removesuffix("_ORDER") + "_SCOPE"

    @property
    def profile_key(self) -> str:
        return self.env_key.removesuffix("_ORDER") + "_PROFILE"

    @property
    def strategy_key(self) -> str:
        return self.env_key.removesuffix("_ORDER") + "_STRATEGY"


ROLES: tuple[Role, ...] = (
    Role("chat", "NUXIVA_LLM_CHAT_ORDER", "⚡", "Conversazione veloce",
         "Saluti e domande brevi: risponde il primo cervello disponibile.", 320),
    Role("deep", "NUXIVA_LLM_DEEP_ORDER", "🧠", "Ragionamento",
         "Spiegazioni, analisi, codice, testi lunghi, azioni."),
    Role("ricercatore", "NUXIVA_LLM_RICERCATORE_ORDER", "🔎", "Ricercatore",
         "Ricerche sul web e sintesi di fonti."),
    Role("domotico", "NUXIVA_LLM_DOMOTICO_ORDER", "🏠", "Domotico",
         "Comandi e scene per la casa."),
    Role("studio", "NUXIVA_LLM_STUDIO_ORDER", "🎓", "Studio autonomo",
         "Studio, esercizi ed esami a riposo."),
    Role("coder", "NUXIVA_LLM_CODER_ORDER", "🌐", "Architetto web",
         "Progettazione e scrittura di siti e app."),
    Role("modello3d", "NUXIVA_LLM_3D_ORDER", "🧊", "Modellazione 3D",
         "Generazione di modelli tridimensionali."),
)

BY_ID: dict[str, Role] = {r.id: r for r in ROLES}
FALLBACK_ROLE = "deep"


def split_order(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(",") if x.strip()]
