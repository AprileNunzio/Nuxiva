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


LCID_MAP = {
    "it": "410",
    "en": "409",
    "fr": "40c",
    "es": "40a",
}


def _synthesize_com(text: str, culture: str, rate: int, out_path: Path) -> bool:
    try:
        import comtypes  # type: ignore
        import comtypes.client  # type: ignore
        comtypes.CoInitialize()
        voice = comtypes.client.CreateObject("SAPI.SpVoice")
        stream = comtypes.client.CreateObject("SAPI.SpFileStream")
    except Exception:
        try:
            import win32com.client  # type: ignore
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            stream = win32com.client.Dispatch("SAPI.SpFileStream")
        except Exception:
            return False

    try:
        target_lcid = LCID_MAP.get(culture[:2].lower(), "409")
        try:
            voices = voice.GetVoices()
            for i in range(voices.Count):
                v = voices.Item(i)
                lang_attr = str(v.GetAttribute("Language") or "")
                desc = str(v.GetDescription() or "").lower()
                if lang_attr.lower().endswith(target_lcid) or culture[:2].lower() in desc:
                    voice.Voice = v
                    break
        except Exception:
            pass

        voice.Rate = max(-10, min(10, rate))
        # SSFMCreateForWrite = 3, DoEvents = False
        stream.Open(str(out_path), 3, False)
        voice.AudioOutputStream = stream
        # SVSFDefault = 0 (synchronous speak)
        voice.Speak(text, 0)
        stream.Close()
        return out_path.is_file() and out_path.stat().st_size > 44
    except Exception as exc:
        log.debug("SAPI COM non disponibile: %s", exc)
        return False


def _synthesize_powershell(text: str, culture: str, rate: int, out_path: Path) -> None:
    env = {
        **os.environ,
        "NUXIVA_TEXT": text,
        "NUXIVA_CULTURE": culture,
        "NUXIVA_RATE": str(rate),
        "NUXIVA_OUT": str(out_path),
    }
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-NoLogo",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        SCRIPT,
    ]
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            timeout=60,
            creationflags=NO_WINDOW,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise LocalSpeechError(f"sintesi locale non disponibile: {exc}") from exc
    if result.returncode != 0 or not out_path.is_file():
        raise LocalSpeechError(result.stderr.decode(errors="replace").strip()[:200] or "sintesi locale fallita")


class SapiSpeech:
    def __init__(self, rate: int = 2) -> None:
        self.rate = max(-5, min(5, int(rate)))

    def synthesize(self, text: str, lang: str | None = None) -> bytes:
        clean = clamp(text)
        if not clean:
            raise LocalSpeechError("testo vuoto")
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "speech.wav"
            culture = culture_for(lang)
            if not _synthesize_com(clean, culture, self.rate, out):
                _synthesize_powershell(clean, culture, self.rate, out)
            return out.read_bytes()
