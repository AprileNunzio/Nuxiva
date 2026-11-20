import re
from typing import List
from .models import Artifact

CODE_BLOCK_RE = re.compile(r"```([a-zA-Z0-9_-]+)?(?::([^\n]+))?\n([\s\S]*?)```")


class ArtifactExtractor:
    @staticmethod
    def extract(text: str) -> List[Artifact]:
        artifacts: List[Artifact] = []
        matches = CODE_BLOCK_RE.findall(text)
        for idx, (lang, title, content) in enumerate(matches):
            lang = (lang or "").strip().lower()
            title = (title or "").strip()
            content = content.strip()
            if not content:
                continue

            if not title:
                ext_map = {
                    "rs": "source.rs",
                    "rust": "source.rs",
                    "ts": "component.ts",
                    "tsx": "Component.tsx",
                    "py": "script.py",
                    "python": "script.py",
                    "html": "page.html",
                    "css": "styles.css",
                    "json": "data.json",
                    "sql": "query.sql",
                    "sh": "script.sh",
                    "bash": "script.sh",
                    "mermaid": "diagram.mermaid",
                }
                title = ext_map.get(lang, f"artifact_{idx + 1}.txt")

            kind = "code"
            if lang in ("html", "svg"):
                kind = "html" if lang == "html" else "svg"
            elif lang == "mermaid":
                kind = "diagram"
            elif lang in ("md", "markdown"):
                kind = "markdown"

            artifacts.append(
                Artifact(
                    id=f"art_{idx + 1}",
                    identifier=title.lower().replace(" ", "_"),
                    title=title,
                    kind=kind,
                    language=lang or "text",
                    content=content,
                )
            )
        return artifacts
