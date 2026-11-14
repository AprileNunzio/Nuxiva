import os
import subprocess
import tempfile
import wave
from pathlib import Path

NO_WINDOW = 0x08000000
RATE = 16000
CULTURES = {"it": "it-IT", "en": "en-US", "fr": "fr-FR", "es": "es-ES"}
SCRIPT = (
    "Add-Type -AssemblyName System.Speech;"
    "$c=[Globalization.CultureInfo]::GetCultureInfo($env:NUXIVA_CULTURE);"
    "$e=New-Object System.Speech.Recognition.SpeechRecognitionEngine($c);"
    "$e.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar));"
    "$e.SetInputToWaveFile($env:NUXIVA_IN);$t=@();"
    "while($true){$r=$e.Recognize();if($r -eq $null){break};if($r.Text){$t+=$r.Text}};"
    "$e.Dispose();[Console]::OutputEncoding=[Text.Encoding]::UTF8;Write-Output ($t -join ' ')"
)


def write_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(RATE)
        target.writeframes(pcm)


class SapiRecognizer:
    def __init__(self, lang: str = "it") -> None:
        self.lang = (lang or "it")[:2].lower()

    def ready(self) -> bool:
        return os.name == "nt"

    def transcribe(self, pcm: bytes, lang: str | None = None) -> tuple[str, str]:
        code = (lang or self.lang)[:2].lower()
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "speech.wav"
            write_wav(source, pcm)
            env = {**os.environ, "NUXIVA_CULTURE": CULTURES.get(code, "en-US"), "NUXIVA_IN": str(source)}
            try:
                result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", SCRIPT], env=env,
                                        capture_output=True, timeout=60, creationflags=NO_WINDOW, check=False)
            except (OSError, subprocess.SubprocessError) as exc:
                raise OSError(f"riconoscimento di Windows non disponibile: {exc}") from exc
        if result.returncode != 0:
            raise OSError(result.stderr.decode(errors="replace").strip()[:200] or "riconoscimento di Windows fallito")
        return result.stdout.decode("utf-8", errors="replace").strip(), code
