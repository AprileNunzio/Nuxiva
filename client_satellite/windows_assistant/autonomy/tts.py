import logging
import os
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("nuxiva.localtts")
NO_WINDOW = 0x08000000
MAX_CHARS = 1200
CULTURES = {"it": "it-IT", "en": "en-US", "fr": "fr-FR", "es": "es-ES"}
SCRIPT = (
    "Add-Type -AssemblyName System.Speech;"
    "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "$c=[Globalization.CultureInfo]::GetCultureInfo($env:NUXIVA_CULTURE);"
    "try{$s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::NotSet,[System.Speech.Synthesis.VoiceAge]::NotSet,0,$c)}catch{};"
    "$s.Rate=[int]$env:NUXIVA_RATE;$s.SetOutputToWaveFile($env:NUXIVA_OUT);$s.Speak($env:NUXIVA_TEXT);$s.Dispose()"
)


class LocalSpeechError(OSError):
    pass


def culture_for(lang: str | None) -> str:
    return CULTURES.get((lang or "it")[:2].lower(), "en-US")


def clamp(text: str) -> str:
    return " ".join(text.split())[:MAX_CHARS]


class SapiSpeech:
    def __init__(self, rate: int = 1) -> None:
        self.rate = max(-5, min(5, int(rate)))

    def synthesize(self, text: str, lang: str | None = None) -> bytes:
        clean = clamp(text)
        if not clean:
            raise LocalSpeechError("testo vuoto")
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "speech.wav"
            env = {**os.environ, "NUXIVA_TEXT": clean, "NUXIVA_CULTURE": culture_for(lang), "NUXIVA_RATE": str(self.rate),
                   "NUXIVA_OUT": str(out)}
            try:
                result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", SCRIPT], env=env,
                                        capture_output=True, timeout=60, creationflags=NO_WINDOW, check=False)
            except (OSError, subprocess.SubprocessError) as exc:
                raise LocalSpeechError(f"sintesi locale non disponibile: {exc}") from exc
            if result.returncode != 0 or not out.is_file():
                raise LocalSpeechError(result.stderr.decode(errors="replace").strip()[:200] or "sintesi locale fallita")
            return out.read_bytes()
