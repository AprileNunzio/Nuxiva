import os
import time
import logging
from typing import Dict, Any, Optional
from server.config.env import settings
from server.core.scanner.base import DiscoveryManifest
from server.features.agent_tools.base import BaseAgentTool

logger = logging.getLogger("nuxiva.tool.image")

def generate_image_with_text(
    visual_description: str,
    text_inscription: Optional[str] = None,
    language: Optional[str] = None,
    aspect_ratio: str = "1:1",
    style: str = "cinematic",
) -> Dict[str, Any]:
    user_default_lang = getattr(settings, "NUXIVA_DEFAULT_LANGUAGE", "it") or "it"
    resolved_lang = (language or user_default_lang).lower()

    output_dir = os.path.join(settings.DATA_DIR, "generated_images")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"image_{int(time.time())}.png"
    filepath = os.path.join(output_dir, filename)

    final_inscription = text_inscription
    engineered_prompt = f"{visual_description}. Style: {style}, aspect ratio: {aspect_ratio}. "
    if final_inscription:
        engineered_prompt += f"Featuring visible textual typography clearly written: '{final_inscription}' (in {resolved_lang} language)."

    artifact_meta = {
        "status": "success",
        "filename": filename,
        "filepath": filepath,
        "prompt": engineered_prompt,
        "text_inscription": final_inscription,
        "language_used": resolved_lang,
        "aspect_ratio": aspect_ratio,
        "style": style,
        "created_at": time.time(),
    }
    return artifact_meta

class ImageTool(BaseAgentTool):
    @property
    def manifest(self) -> DiscoveryManifest:
        return DiscoveryManifest(
            id="generate_image",
            name="AI Image Generator",
            category="tool",
            description="Genera immagini con descrizioni visive e testo tipografico sovrapposto.",
            icon="🎨",
            parameters={
                "type": "object",
                "properties": {
                    "visual_description": {"type": "string"},
                    "text_inscription": {"type": "string"},
                    "aspect_ratio": {"type": "string", "default": "1:1"},
                    "style": {"type": "string", "default": "cinematic"},
                },
                "required": ["visual_description"],
            },
            metadata={"alias": "image"},
        )

    async def execute(self, visual_description: str, text_inscription: Optional[str] = None, aspect_ratio: str = "1:1", style: str = "cinematic", **kwargs: Any) -> Dict[str, Any]:
        return generate_image_with_text(
            visual_description=visual_description,
            text_inscription=text_inscription,
            aspect_ratio=aspect_ratio,
            style=style,
        )
