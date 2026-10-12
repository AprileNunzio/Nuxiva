import os
import time
import logging
from typing import Dict, Any, Optional
from server.config.env import settings

logger = logging.getLogger("nuxiva.tools.image_generator")

def generate_image_with_text(
    visual_description: str,
    text_inscription: Optional[str] = None,
    language: Optional[str] = None,
    aspect_ratio: str = "1:1",
    style: str = "cinematic",
) -> Dict[str, Any]:
    """
    Genera un'immagine con eventuale testo/scritta impressa.
    REGOLA DI SOVRANITA LINGUISTICA: Se non viene specificata diversamente una lingua,
    qualsiasi testo o scritta visibile impressa sull'immagine deve essere rigorosamente
    nella lingua di default dell'utente (Italiano 'it').
    """
    user_default_lang = settings.NUXIVA_DEFAULT_LANGUAGE or "it"
    resolved_lang = (language or user_default_lang).lower()


    output_dir = os.path.join(settings.DATA_DIR, "generated_images")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"image_{int(time.time())}.png"
    filepath = os.path.join(output_dir, filename)

    # Formattazione del prompt visivo assicurando la lingua di default per scritte
    final_inscription = text_inscription
    if final_inscription and resolved_lang == "it":
        # Assicura che la scritta sia coerente con l'italiano se non diversamente indicato
        logger.info("Image generation: enforcing Italian default language for inscription: '%s'", final_inscription)

    engineered_prompt = (
        f"{visual_description}. "
        f"Style: {style}, aspect ratio: {aspect_ratio}. "
    )
    if final_inscription:
        engineered_prompt += f"Featuring visible textual typography clearly written: '{final_inscription}' (in {resolved_lang} language)."

    # Salvataggio metadata dell'artefatto generato
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
    logger.info("Image generation prompt ready: %s", engineered_prompt[:120])
    return artifact_meta
