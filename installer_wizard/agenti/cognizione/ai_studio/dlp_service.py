"""Servizio di protezione dati sensibili e DLP (Data Loss Prevention) per AI Studio."""

import re
from typing import Dict, List, Tuple

# Pattern comuni per segreti, token e dati personali sensibili
PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # Chiavi API comuni (OpenAI, AWS, GitHub, JWT, token generici)
    ("API_KEY_OPENAI", re.compile(r"sk-[a-zA-Z0-9]{32,}", re.IGNORECASE), "[CHIAVE_API_OPENAI_MASCHERATA]"),
    ("API_KEY_GITHUB", re.compile(r"gh[pousr]-[a-zA-Z0-9]{36,}", re.IGNORECASE), "[TOKEN_GITHUB_MASCHERATO]"),
    ("AWS_KEY", re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}", re.ASCII), "[CHIAVE_AWS_MASCHERATA]"),
    ("JWT_TOKEN", re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", re.ASCII), "[TOKEN_JWT_MASCHERATO]"),
    # Carte di credito (Luhn like 13-19 cifre con trattini o spazi)
    ("CREDIT_CARD", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[CARTA_CREDITO_MASCHERATA]"),
    # Indirizzi IP privati o sensibili con porte interne
    ("INTERNAL_TOKEN", re.compile(r"(?:password|passwd|secret|token)\s*[:=]\s*['\"]?([a-zA-Z0-9!@#$%^&*()_+=-]{6,})['\"]?", re.IGNORECASE), "[CREDENZIALE_MASCHERATA]"),
]


class DlpService:
    @staticmethod
    def inspect_and_mask(text: str) -> Tuple[str, List[Dict[str, str]]]:
        """Analizza il testo e sostituisce eventuali token/segreti con placeholder protetti."""
        masked_text = text
        detected: List[Dict[str, str]] = []

        for rule_id, pattern, placeholder in PATTERNS:
            matches = list(pattern.finditer(masked_text))
            if matches:
                detected.append({
                    "rule": rule_id,
                    "count": str(len(matches)),
                })
                masked_text = pattern.sub(placeholder, masked_text)

        return masked_text, detected
