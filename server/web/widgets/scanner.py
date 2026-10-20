import os
from typing import Dict, List, Optional, Any
from server.core.scanner.universal_scanner import UniversalScanner
from server.core.scanner.watcher import registry_watcher
from server.web.widgets.base import BaseWidget

class WidgetScanner:
    def __init__(self, widgets_dir: Optional[str] = None) -> None:
        if widgets_dir is None:
            widgets_dir = os.path.dirname(os.path.abspath(__file__))
        self._scanner = UniversalScanner(
            root_dir=widgets_dir,
            target_filename="widget.py",
            expected_type=BaseWidget,
            category="widget",
            enable_security_check=True,
        )
        registry_watcher.register_scanner("widgets", self._scanner)

    def scan_all(self, force: bool = False) -> Dict[str, BaseWidget]:
        return self._scanner.scan_all(force=force)

    def get_widget(self, widget_id: str) -> Optional[BaseWidget]:
        widget = self._scanner.get(widget_id)
        if widget:
            return widget
        for w in self._scanner.list_all():
            if w.manifest.id == widget_id or w.manifest.metadata.get("alias") == widget_id:
                return w
        return None

    def list_all(self) -> List[BaseWidget]:
        return self._scanner.list_all()

    def get_manifests(self) -> List[Any]:
        return self._scanner.get_manifests()

    def invalidate(self, widget_id: str) -> None:
        self._scanner.invalidate(widget_id)

widget_scanner = WidgetScanner()
