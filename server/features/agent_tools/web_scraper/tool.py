import json
import logging
import urllib.request
import urllib.parse
from html.parser import HTMLParser
from typing import Any
from server.core.scanner.base import DiscoveryManifest
from server.features.agent_tools.base import BaseAgentTool

logger = logging.getLogger("nuxiva.tool.web_scraper")

class SimpleHTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.in_body = False

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.in_body = True

    def handle_endtag(self, tag):
        if tag == "body":
            self.in_body = False

    def handle_data(self, data):
        if self.in_body:
            text = data.strip()
            if text:
                self.result.append(text)

    def get_text(self):
        return " ".join(self.result)

async def search_catalog(query: str, max_results: int = 3) -> str:
    try:
        safe_query = urllib.parse.quote(query)
        url = f"https://it.wikipedia.org/w/api.php?action=query&list=search&srsearch={safe_query}&utf8=&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": "Nuxiva-Agent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
        results = []
        for i, item in enumerate(data.get("query", {}).get("search", [])[:max_results]):
            title = item.get("title")
            snippet = item.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
            results.append(f"Prodotto/Risultato {i+1}: {title} - Descrizione: {snippet}")
        if not results:
            return "Nessun catalogo o informazione trovata per questa ricerca."
        return "Risultati estratti con successo:\n" + "\n".join(results)
    except Exception as e:
        logger.error(f"Errore nello scraping del catalogo: {e}")
        return f"Errore durante l'accesso al web: {e}"

class WebScraperTool(BaseAgentTool):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id="search_catalog",
            name="Web Scraper & Catalog Extractor",
            category="tool",
            description="Estrae informazioni e contenuti puliti da pagine web e cataloghi online.",
            icon="🕸️",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer", "default": 3},
                },
                "required": ["query"],
            },
            metadata={"alias": "web_scraper"},
        )

    async def execute(self, query: str, max_results: int = 3, **kwargs: Any) -> str:
        return await search_catalog(query=query, max_results=max_results)
