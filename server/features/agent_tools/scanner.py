import os
from typing import Dict, List, Optional, Any
from server.core.scanner.universal_scanner import UniversalScanner
from server.core.scanner.watcher import registry_watcher
from server.features.agent_tools.base import BaseAgentTool

class ToolScanner:
    def __init__(self, tools_dir: Optional[str] = None) -> None:
        if tools_dir is None:
            tools_dir = os.path.dirname(os.path.abspath(__file__))
        self._scanner = UniversalScanner(
            root_dir=tools_dir,
            target_filename="tool.py",
            expected_type=BaseAgentTool,
            category="tool",
            enable_security_check=True,
        )
        registry_watcher.register_scanner("agent_tools", self._scanner)

    def scan_all(self, force: bool = False) -> Dict[str, BaseAgentTool]:
        return self._scanner.scan_all(force=force)

    def get_tool(self, tool_id: str) -> Optional[BaseAgentTool]:
        tool = self._scanner.get(tool_id)
        if tool:
            return tool
        for t in self._scanner.list_all():
            if t.manifest.id == tool_id or t.manifest.metadata.get("alias") == tool_id:
                return t
        return None

    def list_all(self) -> List[BaseAgentTool]:
        return self._scanner.list_all()

    async def execute(self, tool_id: str, **kwargs) -> Any:
        tool = self.get_tool(tool_id)
        if not tool:
            raise KeyError(f"Tool '{tool_id}' not found in dynamic registry")
        return await tool.execute(**kwargs)

    def invalidate(self, tool_id: str) -> None:
        self._scanner.invalidate(tool_id)

tool_scanner = ToolScanner()
