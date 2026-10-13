import glob
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from config import FEATURES_DIR, STATE_DIR, WIDGETS_DIR

log = logging.getLogger("nuxiva.team.scanner")

USER_FEATURES_DIR = STATE_DIR / "features"
USER_WIDGETS_DIR = STATE_DIR / "widgets"
WORD_RE = re.compile(r"[a-zà-ÿ0-9_-]{3,}", re.IGNORECASE)


@dataclass
class DiscoveredAgent:
    id: str
    name: str
    description: str
    capabilities: list[str] = field(default_factory=list)
    category: str = "altro"
    source: str = "system"  # system, user, ai
    dir_path: str = ""
    tools: list[dict] = field(default_factory=list)
    widgets: list[dict] = field(default_factory=list)
    keywords: set[str] = field(default_factory=set)
    mtime: float = 0.0

    def brief(self) -> str:
        tools_count = len(self.tools)
        widgets_count = len(self.widgets)
        details = []
        if tools_count:
            details.append(f"{tools_count} strumenti")
        if widgets_count:
            details.append(f"{widgets_count} widget")
        detail_str = f" ({', '.join(details)})" if details else ""
        return f"«{self.name}» [{self.id}]{detail_str}: {self.description[:110]}"


class AgentScanner:
    """
    Scanner dinamico che analizza in tempo reale le directory degli agenti,
    i loro strumenti (tools), widget e capacità dichiarate, senza nulla di cablato nel codice.
    Rileva automaticamente nuovi agenti aggiunti a mano o creati dinamicamente dall'AI/utente.
    """

    def __init__(self) -> None:
        self.agents: dict[str, DiscoveredAgent] = {}
        self.signature = ""
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        try:
            USER_FEATURES_DIR.mkdir(parents=True, exist_ok=True)
            USER_WIDGETS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _compute_signature(self, feature_paths: list[str], widget_paths: list[str]) -> str:
        items = []
        for p in feature_paths + widget_paths:
            try:
                items.append(f"{p}:{os.path.getmtime(p)}")
            except OSError:
                continue
        return "|".join(items)

    def scan(self, force: bool = False) -> dict[str, DiscoveredAgent]:
        self._ensure_dirs()
        feat_paths = sorted(
            glob.glob(str(FEATURES_DIR / "*" / "feature.json")) +
            glob.glob(str(USER_FEATURES_DIR / "*" / "feature.json"))
        )
        widget_paths = sorted(
            glob.glob(str(WIDGETS_DIR / "*" / "widget.json")) +
            glob.glob(str(USER_WIDGETS_DIR / "*" / "widget.json"))
        )

        sig = self._compute_signature(feat_paths, widget_paths)
        if not force and sig == self.signature and self.agents:
            # Sincronizza solo gli strumenti registrati a runtime se la firma dei file non è cambiata
            self._sync_registered_tools()
            return self.agents

        self.signature = sig
        discovered_widgets = self._scan_widgets(widget_paths)
        discovered_agents: dict[str, DiscoveredAgent] = {}

        # 1. Scansione degli agenti dalle directory
        for p in feat_paths:
            path_obj = Path(p)
            folder = path_obj.parent
            agent_id = folder.name
            try:
                data = json.loads(path_obj.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError) as exc:
                log.warning("Impossibile leggere manifest agente %s: %s", p, exc)
                continue

            agent_id = str(data.get("id") or agent_id).strip()
            name = str(data.get("name") or agent_id).strip()
            desc = str(data.get("description") or "").strip()
            caps = [str(c).strip() for c in data.get("capabilities", []) if c]
            cat = str(data.get("category") or "altro").strip()
            source = "system" if path_obj.is_relative_to(FEATURES_DIR) else str(data.get("source") or "user")

            mtime = 0.0
            try:
                mtime = os.path.getmtime(p)
            except OSError:
                pass

            agent = DiscoveredAgent(
                id=agent_id,
                name=name,
                description=desc,
                capabilities=caps,
                category=cat,
                source=source,
                dir_path=str(folder),
                mtime=mtime
            )
            discovered_agents[agent_id] = agent

        # 2. Assegna i widget scansionati agli agenti di competenza
        for wid, w_info in discovered_widgets.items():
            assigned = False
            # Se il widget specifica espressamente l'agente proprietario
            target_agent = w_info.get("agent")
            if target_agent and target_agent in discovered_agents:
                discovered_agents[target_agent].widgets.append(w_info)
                assigned = True
            else:
                # Correlazione automatica: se l'ID del widget corrisponde o inizia con l'ID dell'agente
                for aid, agent in discovered_agents.items():
                    if wid == aid or wid.startswith(f"{aid}_") or wid.startswith(f"{aid}-"):
                        agent.widgets.append(w_info)
                        assigned = True
                        break
            # Se non assegnato, cerca corrispondenze per categoria o intent
            if not assigned:
                w_desc = (w_info.get("description") or "").lower()
                for aid, agent in discovered_agents.items():
                    if aid in w_desc or agent.name.lower() in w_desc:
                        agent.widgets.append(w_info)
                        break

        # 3. Assegna gli strumenti registrati (tools)
        self.agents = discovered_agents
        self._sync_registered_tools()

        # 4. Estrazione semantica dinamica dei vocaboli e keyword per ciascun agente
        for agent in self.agents.values():
            self._build_semantic_index(agent)

        return self.agents

    def _scan_widgets(self, paths: list[str]) -> dict[str, dict]:
        widgets = {}
        for p in paths:
            path_obj = Path(p)
            folder = path_obj.parent
            wid = folder.name
            try:
                data = json.loads(path_obj.read_text(encoding="utf-8"))
                wid = str(data.get("id") or wid).strip()
                widgets[wid] = {
                    "id": wid,
                    "name": str(data.get("name") or wid).strip(),
                    "description": str(data.get("description") or "").strip(),
                    "agent": data.get("agent"),
                    "intents": list(data.get("intents") or []),
                    "size": data.get("size", "m"),
                    "dir": str(folder)
                }
            except Exception:
                continue
        return widgets

    def _sync_registered_tools(self) -> None:
        try:
            import importlib
            import importlib.util
            from features.agent import registry as tool_reg
            from features.team import priority
        except ImportError:
            return

        # 1. Carica dinamicamente i file tools.py e tools_*.py da tutte le cartelle degli agenti scansionati
        for aid, agent in self.agents.items():
            folder = Path(agent.dir_path) if agent.dir_path else None
            if not folder or not folder.exists():
                continue
            # tools.py
            tools_file = folder / "tools.py"
            if tools_file.exists():
                mod_name = f"features.{folder.name}.tools"
                try:
                    importlib.import_module(mod_name)
                except Exception:
                    try:
                        spec = importlib.util.spec_from_file_location(f"user_feature_{aid}_tools", str(tools_file))
                        if spec and spec.loader:
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                    except Exception:
                        pass
            # tools_*.py
            for tf in folder.glob("tools_*.py"):
                mod_name = f"features.{folder.name}.{tf.stem}"
                try:
                    importlib.import_module(mod_name)
                except Exception:
                    pass

        # 2. Svuota gli strumenti precedentemente associati per evitare duplicati
        for agent in self.agents.values():
            agent.tools.clear()

        tools_dict = getattr(tool_reg, "TOOLS", {})
        for tname, tmeta in tools_dict.items():
            # Determina a quale agente appartiene lo strumento
            owner_id = tmeta.get("agent")
            if not owner_id:
                # Ispezione del modulo di appartenenza della funzione
                fn = tmeta.get("fn")
                mod = getattr(fn, "__module__", "") if fn else ""
                owner_id = priority.MODULE_OWNER.get(mod, "")
                if not owner_id and mod.startswith("features."):
                    parts = mod.split(".")
                    if len(parts) > 1 and parts[1] in self.agents:
                        owner_id = parts[1]

            if not owner_id or owner_id not in self.agents:
                owner_id = "agent" if "agent" in self.agents else ""

            tool_entry = {
                "name": tname,
                "description": tmeta.get("description", ""),
                "args": dict(tmeta.get("args") or {}),
                "confirm": bool(tmeta.get("confirm"))
            }

            if owner_id and owner_id in self.agents:
                self.agents[owner_id].tools.append(tool_entry)

    def _build_semantic_index(self, agent: DiscoveredAgent) -> None:
        tokens: set[str] = set()

        def add_text(t: str) -> None:
            if t:
                for w in WORD_RE.findall(t.lower()):
                    if len(w) >= 3:
                        tokens.add(w)

        add_text(agent.id)
        add_text(agent.name)
        add_text(agent.description)
        add_text(agent.category)

        for cap in agent.capabilities:
            add_text(cap)

        for t in agent.tools:
            add_text(t["name"])
            add_text(t.get("description", ""))
            for arg_k, arg_v in t.get("args", {}).items():
                add_text(arg_k)
                add_text(str(arg_v))

        for w in agent.widgets:
            add_text(w["name"])
            add_text(w.get("description", ""))
            for intent in w.get("intents", []):
                add_text(intent)

        agent.keywords = tokens

    def find_agent(self, identifier: str) -> DiscoveredAgent | None:
        clean = (identifier or "").strip().lower()
        if not clean:
            return None
        # Ricerca esatta per ID
        if clean in self.agents:
            return self.agents[clean]
        # Ricerca per nome esatto
        for a in self.agents.values():
            if a.name.lower() == clean:
                return a
        # Ricerca per inclusione parziale
        for a in self.agents.values():
            if clean in a.id.lower() or clean in a.name.lower():
                return a
        return None


scanner = AgentScanner()
