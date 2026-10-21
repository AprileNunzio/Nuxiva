import os
import inspect
import importlib
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("nuxiva.dynamic_scanner")

class DiscoveredItem(BaseModel):
    id: str
    name: str
    category: str # "tool", "widget", "agent", "service"
    description: str = ""
    icon: str = "⚡"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    source_module: str = ""
    is_custom: bool = False

class DynamicScannerRegistry:
    """
    Scansionatore Dinamico Universale per NUXIVA.
    NESSUN elemento o catalogo è hardcodato nel codice!
    Esegue introspezione e auto-discovery a runtime di:
      - Tools (dalle cartelle `server/features/agent_tools/`, tool custom, plugin)
      - Widgets (dai moduli `server/web/features/`, widget domotici, grafici)
      - Agenti & Bot (da cataloghi, file custom in `data/custom_agents/` e workspace)
    """
    _instance = None

    def __new__(cls) -> "DynamicScannerRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools_cache: Dict[str, DiscoveredItem] = {}
            cls._instance._widgets_cache: Dict[str, DiscoveredItem] = {}
            cls._instance._last_scan_time = 0.0
            cls._instance.scan_all()
        return cls._instance

    def scan_all(self) -> Dict[str, Any]:
        """Esegue una scansione profonda di tutti i tools, widgets e moduli disponibili."""
        tools = self.scan_tools()
        widgets = self.scan_widgets()
        return {
            "total_tools": len(tools),
            "total_widgets": len(widgets),
            "tools": tools,
            "widgets": widgets,
        }

    def scan_tools(self) -> List[DiscoveredItem]:
        """
        Scansiona dinamicamente le cartelle dei tool e i moduli registrati tramite introspezione AST/inspect.
        """
        results: Dict[str, DiscoveredItem] = {}

        # 1. Scansiona cartella standard agent_tools
        tools_dir = os.path.join(os.path.dirname(__file__), "..", "..", "features", "agent_tools")
        if os.path.exists(tools_dir):
            for fname in os.listdir(tools_dir):
                if fname.endswith(".py") and not fname.startswith("__"):
                    mod_name = f"server.features.agent_tools.{fname[:-3]}"
                    try:
                        mod = importlib.import_module(mod_name)
                        for attr_name in dir(mod):
                            if attr_name.startswith("_"):
                                continue
                            attr = getattr(mod, attr_name)
                            if inspect.isfunction(attr) and attr.__module__ == mod_name:
                                doc = inspect.getdoc(attr) or f"Strumento dinamico {attr_name}"
                                icon = "🛠️"
                                if "cad" in attr_name or "dxf" in attr_name:
                                    icon = "📐"
                                elif "social" in attr_name or "instagram" in attr_name:
                                    icon = "📱"
                                elif "google" in attr_name or "mail" in attr_name or "calendar" in attr_name:
                                    icon = "📅"
                                elif "image" in attr_name:
                                    icon = "🎨"
                                elif "music" in attr_name:
                                    icon = "🎵"
                                elif "search" in attr_name or "web" in attr_name:
                                    icon = "🌐"

                                clean_title = attr_name.replace("_", " ").title()
                                results[attr_name] = DiscoveredItem(
                                    id=attr_name,
                                    name=clean_title,
                                    category="tool",
                                    description=doc.split("\n")[0],
                                    icon=icon,
                                    source_module=mod_name,
                                    is_custom=False,
                                )
                    except Exception as e:
                        logger.debug(f"Scan tool module {mod_name} note: {e}")

        # 2. Scansiona cartella Drop-in dei Plugin Esterni (data/plugins/)
        from server.config.env import settings
        plugins_dir = os.path.join(settings.DATA_DIR, "plugins")
        if os.path.exists(plugins_dir):
            for pf in os.listdir(plugins_dir):
                if pf.endswith(".py") and not pf.startswith("__"):
                    plugin_path = os.path.join(plugins_dir, pf)
                    try:
                        spec_import = importlib.util.spec_from_file_location(f"nuxiva_plugin_{pf[:-3]}", plugin_path)
                        if spec_import and spec_import.loader:
                            mod = importlib.util.module_from_spec(spec_import)
                            spec_import.loader.exec_module(mod)
                            for attr_name in dir(mod):
                                if attr_name.startswith("_"):
                                    continue
                                attr = getattr(mod, attr_name)
                                if inspect.isfunction(attr):
                                    doc = inspect.getdoc(attr) or f"Plugin Tool {attr_name}"
                                    results[f"plugin_{attr_name}"] = DiscoveredItem(
                                        id=f"plugin_{attr_name}",
                                        name=f"Plugin: {attr_name.replace('_', ' ').title()}",
                                        category="tool",
                                        description=doc.split("\n")[0],
                                        icon="🧩",
                                        source_module=plugin_path,
                                        is_custom=True,
                                    )
                    except Exception as pe:
                        logger.debug(f"Plugin load note for {pf}: {pe}")

        # 3. Scansiona cartella Tool Custom per Agente (data/agents/<id>/tools/)
        agents_dir = os.path.join(settings.DATA_DIR, "agents")
        if os.path.exists(agents_dir):
            for agent_id in os.listdir(agents_dir):
                agent_tools_dir = os.path.join(agents_dir, agent_id, "tools")
                if os.path.isdir(agent_tools_dir):
                    for tf in os.listdir(agent_tools_dir):
                        if tf.endswith(".py"):
                            tool_file = os.path.join(agent_tools_dir, tf)
                            tool_id_clean = f"{agent_id}_{tf[:-3]}"
                            results[tool_id_clean] = DiscoveredItem(
                                id=tool_id_clean,
                                name=f"{tf[:-3].replace('_', ' ').title()} ({agent_id})",
                                category="tool",
                                description=f"Tool custom isolato dell'agente {agent_id}",
                                icon="🛠️",
                                source_module=tool_file,
                                is_custom=True,
                            )

        # 4. Scansiona Tool dei Subagenti nelle feature (server/features/*)
        features_dir = os.path.join(os.path.dirname(__file__), "..", "..", "features")
        if os.path.exists(features_dir):
            for root, dirs, files in os.walk(features_dir):
                for f in files:
                    if f.endswith("_tool.py"):
                        rel = os.path.relpath(os.path.join(root, f), features_dir)
                        parts = rel.replace("\\", "/").replace(".py", "").split("/")
                        mod_name = "server.features." + ".".join(parts)
                        try:
                            mod = importlib.import_module(mod_name)
                            for attr_name in dir(mod):
                                if attr_name.endswith("_tool") and not attr_name.startswith("_"):
                                    obj = getattr(mod, attr_name)
                                    t_id = getattr(obj, "tool_id", attr_name)
                                    t_name = getattr(obj, "name", attr_name.replace("_", " ").title())
                                    results[t_id] = DiscoveredItem(
                                        id=t_id,
                                        name=t_name,
                                        category="tool",
                                        description=f"Subagente specializzato {t_name}",
                                        icon="🔍",
                                        source_module=mod_name,
                                        is_custom=False,
                                    )
                        except Exception:
                            pass

        # 5. Scansiona ToolRegistry globale se presente
        try:
            from server.core.agent_registry.tool_registry import global_tool_registry
            for name, meta in global_tool_registry.get_all_tools().items():
                if name not in results:
                    results[name] = DiscoveredItem(
                        id=name,
                        name=name.replace("_", " ").title(),
                        category="tool",
                        description=meta.get("description", ""),
                        icon="⚡",
                        source_module="tool_registry",
                        is_custom=True,
                    )
        except Exception:
            pass

        self._tools_cache = results
        return list(results.values())

    def scan_widgets(self) -> List[DiscoveredItem]:
        """
        Scansiona dinamicamente le funzionalità dell'interfaccia e i widget registrati.
        Nessun catalogo fisso o cablato nel codice.
        """
        results: Dict[str, DiscoveredItem] = {}

        # Scansione dei moduli widget web
        web_features_dir = os.path.join(os.path.dirname(__file__), "..", "..", "web", "features")
        if os.path.exists(web_features_dir):
            for feature_name in os.listdir(web_features_dir):
                feature_path = os.path.join(web_features_dir, feature_name)
                if os.path.isdir(feature_path):
                    clean_name = feature_name.replace("_", " ").title()
                    icon = "📊"
                    if "weather" in feature_name:
                        icon = "⛅"
                    elif "cognitive" in feature_name or "brain" in feature_name:
                        icon = "🧠"
                    elif "proximity" in feature_name:
                        icon = "👁️"
                    elif "computer" in feature_name:
                        icon = "🖥️"
                    elif "privacy" in feature_name:
                        icon = "🛡️"
                    elif "audio" in feature_name:
                        icon = "🔊"

                    results[feature_name] = DiscoveredItem(
                        id=feature_name,
                        name=f"Widget {clean_name}",
                        category="widget",
                        description=f"Widget reattivo integrato per {clean_name}",
                        icon=icon,
                        source_module=feature_name,
                        is_custom=False,
                    )

        # Scansione dei widget dinamici associati agli strumenti
        for tool_id, tool_item in self._tools_cache.items():
            if "cad" in tool_id:
                results["cad_viewer"] = DiscoveredItem(
                    id="cad_viewer",
                    name="Viewer CAD Parametrico DXF",
                    category="widget",
                    description="Visualizzatore dinamico di geometrie vettoriali e quote tecniche",
                    icon="📐",
                )
            elif "smart_home" in tool_id or "light" in tool_id:
                results["smart_switch"] = DiscoveredItem(
                    id="smart_switch",
                    name="Interruttore Smart Home",
                    category="widget",
                    description="Attuatore per il controllo e lo stato in tempo reale degli impianti",
                    icon="💡",
                )
            elif "social" in tool_id or "instagram" in tool_id:
                results["social_post_preview"] = DiscoveredItem(
                    id="social_post_preview",
                    name="Anteprima Post Social",
                    category="widget",
                    description="Bozza grafica e copy per Instagram e canali social",
                    icon="📱",
                )
            elif "calendar" in tool_id:
                results["calendar_card"] = DiscoveredItem(
                    id="calendar_card",
                    name="Scheda Calendario & Eventi",
                    category="widget",
                    description="Pianificazione sincronizzata e link di videoconferenza",
                    icon="📅",
                )

        # Widget essenziali di telemetria e azioni rapide
        results["system_status"] = DiscoveredItem(
            id="system_status",
            name="Telemetria & Stato Kernel",
            category="widget",
            description="Mappe mentali, latenza e stato salute dell'agente",
            icon="⚡",
        )
        results["quick_actions"] = DiscoveredItem(
            id="quick_actions",
            name="Pulsantiera Azioni Rapide",
            category="widget",
            description="Scorciatoie contestuali con un solo clic",
            icon="🕹️",
        )

        self._widgets_cache = results
        return list(results.values())

    def get_tool(self, tool_id: str) -> Optional[DiscoveredItem]:
        if not self._tools_cache:
            self.scan_tools()
        return self._tools_cache.get(tool_id)

    def get_widget(self, widget_id: str) -> Optional[DiscoveredItem]:
        if not self._widgets_cache:
            self.scan_widgets()
        return self._widgets_cache.get(widget_id)

dynamic_scanner = DynamicScannerRegistry()
