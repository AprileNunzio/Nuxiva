import json
import os
import re
import tempfile
from contextvars import ContextVar
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
APP_DIR = BACKEND_DIR.parent
WEB_DIR = APP_DIR / "web"
FEATURES_DIR = APP_DIR / "features"
WIDGETS_DIR = APP_DIR / "widgets"
SKILLS_DIR = APP_DIR / "skills"

DEMO = os.environ.get("NUXIVA_DEMO") == "1"

NUXIVA_DIR = Path(os.environ.get("NUXIVA_DIR", BACKEND_DIR.parents[1] if DEMO else "/opt/Nuxiva"))
_ROOT = Path(tempfile.gettempdir()) / "nuxiva-demo" if DEMO else Path("/")
ETC_DIR = _ROOT / "etc/nuxiva"
STATE_DIR = _ROOT / "var/lib/nuxiva"
LOG_DIR = _ROOT / "var/log/nuxiva"
ENV_FILE = ETC_DIR / "nuxiva.env"
STEPS_DIR = NUXIVA_DIR / "scripts/os/steps"
HEAL_SCRIPT = NUXIVA_DIR / "scripts/os/heal.sh"

PUBLIC_PORT = int(os.environ.get("NUXIVA_PUBLIC_PORT", 8000 if DEMO else 80))
ADMIN_PORT = int(os.environ.get("NUXIVA_ADMIN_PORT", 8001 if DEMO else 8080))
CORE_URL = os.environ.get("NUXIVA_CORE_URL", "http://127.0.0.1:8443")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

VERSION = "4.1.53"
UI_LANGUAGES = {"it": "Italiano", "en": "English", "fr": "Français", "es": "Español", "de": "Deutsch", "pt": "Português",
                "nl": "Nederlands", "pl": "Polski", "ro": "Română", "ru": "Русский", "uk": "Українська", "el": "Ελληνικά",
                "tr": "Türkçe", "ar": "العربية", "he": "עברית", "fa": "فارسی", "zh": "中文", "ja": "日本語", "ko": "한국어",
                "hi": "हिन्दी", "sv": "Svenska", "da": "Dansk", "nb": "Norsk", "fi": "Suomi", "cs": "Čeština", "hu": "Magyar",
                "sq": "Shqip", "hr": "Hrvatski", "bg": "Български", "vi": "Tiếng Việt", "th": "ไทย", "id": "Bahasa Indonesia",
                "ms": "Bahasa Melayu"}

for _d in (ETC_DIR, STATE_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

EDITABLE_KEYS = {
    "NUXIVA_LLM_MODEL": "Cervello potente: modello per il ragionamento (Ollama; vuoto = automatico)",
    "NUXIVA_LLM_FAST_MODEL": "Cervello veloce: modello per la conversazione (Ollama; vuoto = automatico)",
    "NUXIVA_LLM_ROUTING": "Instradamento tra cervello veloce e potente (auto, 1 = sempre, 0 = un solo cervello)",
    "NUXIVA_LLM_CHAT_ORDER": "Priorità dei modelli per la conversazione (separati da virgola; vuoto = automatico)",
    "NUXIVA_LLM_DEEP_ORDER": "Priorità dei modelli per il ragionamento (separati da virgola; vuoto = automatico)",
    "NUXIVA_EMBED_MODEL": "Modello di embedding (Ollama)",
    "NUXIVA_NETGUARD": "Analisi del traffico per il firewall (1 = attiva, 0 = spenta)",
    "NUXIVA_NETGUARD_INTERFACES": "Interfacce analizzate dal firewall (es. eth0, wlan0; vuoto = tutte quelle ethernet e wifi)",
    "NUXIVA_GATEWAY_IP": "IP del router di casa, che il firewall non bloccherà mai",
    "NUXIVA_VPN": "Strumenti VPN WireGuard, OpenVPN e IPsec (1 = installati, 0 = no)",
    "NUXIVA_OLLAMA_URL": "Server Ollama (vuoto = locale; es. http://192.168.1.50:11434 per usare un altro server)",
    "NUXIVA_ASSISTANT_NAME": "Nome dell'assistente (predefinito NUXIVA)",
    "NUXIVA_USER_NAME": "Nome dell'utente principale (come Nuxiva ti chiama)",
    "NUXIVA_UI_LANG": "Lingua dell'interfaccia del display e del pannello (it, en, fr)",
    "NUXIVA_LOCATION": "Posizione predefinita (nome; si imposta meglio da Audio e posizione)",
    "NUXIVA_LOCATION_MODE": "Posizione: auto (display/Wi-Fi più precisi) o fixed (sempre la predefinita)",
    "NUXIVA_LOCATION_LAT": "Latitudine della posizione predefinita",
    "NUXIVA_LOCATION_LON": "Longitudine della posizione predefinita",
    "NUXIVA_MUSIC_ID": "Riconoscimento della musica in ascolto (1/0; invia 10 s di audio a Shazam, servizio non ufficiale: serve anche NUXIVA_UNOFFICIAL_SERVICES=1)",
    "NUXIVA_STUDY_FINETUNE": "Consolidamento dello studio nei pesi con Soup (auto = deciso dall'hardware, 1 = sempre, 0 = mai)",
    "NUXIVA_STUDY_BASE_MODEL": "Modello base per Soup (Hugging Face, es. Qwen/Qwen2.5-1.5B-Instruct)",
    "NUXIVA_VOICE": "Voce principale (es. if_sara, im_nicola, it_IT-serena-high; si gestisce da Voci)",
    "NUXIVA_VOICE_ORDER": "Priorità delle voci (separate da virgola; si gestisce meglio da Voci)",
    "NUXIVA_VOICE_SPEED": "Velocità della voce (0.6 - 1.6)",
    "NUXIVA_CAMERAS": "Telecamere e registrazione ad anello (1/0, spento di default)",
    "NUXIVA_ADDRESSEE_THRESHOLD": "Soglia per decidere se gli stai parlando (0.2 - 0.95)",
    "NUXIVA_ADDRESSEE_ALONE": "Fiducia aggiuntiva quando sei solo nella stanza (0 - 1)",
    "NUXIVA_VOICE_PITCH": "Tono della voce in semitoni (-6 grave, +6 acuto)",
    "NUXIVA_VOICE_VOLUME": "Volume della voce (0.4 - 2.0)",
    "NUXIVA_VOICE_LANG": "Voce preferita per ogni lingua (es. en:am_michael,de:de_DE-thorsten-medium; si gestisce da Voci)",
    "NUXIVA_VOICE_ONLINE": "Voci neurali online di Edge (1 = sì, 0 = mai; servizio non ufficiale: serve anche NUXIVA_UNOFFICIAL_SERVICES=1)",
    "NUXIVA_VOICE_AUTO_DOWNLOAD": "Scarica da solo la voce di una lingua nuova quando serve (1/0)",
    "NUXIVA_EAR_MULTILANG": "Riconosce la lingua in cui parli (1/0; 0 = ascolta solo l'italiano)",
    "NUXIVA_EAR_MODE": "Modalità di ascolto: offline (locale privato, default), online (cloud alta precisione) o hybrid",
    "NUXIVA_ONLINE_STT_PROVIDER": "Fornitore STT online (deepgram, groq, openai, gemini)",
    "NUXIVA_ONLINE_STT_KEY": "Chiave API per il servizio STT online",
    "NUXIVA_EAR_AUTO_FOLLOWUP": "Finestra di ascolto continuo dopo una risposta (secondi, default 8)",
    "NUXIVA_VOICEPRINT_ENFORCE": "Filtro anti-TV ed estranei: rispondi solo alle voci registrate (1/0)",
    "NUXIVA_EAR_ENHANCE_ENGINE": "Motore di pulizia audio e dereverberazione (auto, deepfilternet, spectral)",
    "NUXIVA_VISION": "Webcam e riconoscimento facciale (1/0)",
    "NUXIVA_EAR": "Ascolto vocale con parola \"Nuxiva\" (1/0)",
    "NUXIVA_STT_MODEL": "Modello di ascolto offline (vuoto = automatico; base, small, medium, large-v3-turbo)",
    "NUXIVA_EAR_MAX_GAIN": "Amplificazione massima del microfono per il campo lontano (2 - 80)",
    "NUXIVA_EAR_TARGET_RMS": "Livello vocale obiettivo dell'autolivellamento (0.03 - 0.2)",
    "NUXIVA_AVATAR": "Aspetto dell'assistente (auto = in base al dispositivo, full = ologramma 3D con volto, light = nucleo leggero)",
    "NUXIVA_FACE_COLOR": "Colore dell'ologramma (colore, es. #29e0ff)",
    "NUXIVA_AUTO_UPDATE": "Aggiornamenti automatici (1/0)",
    "NUXIVA_UPDATE_INTERVAL_MIN": "Controllo aggiornamenti ogni N minuti (default 5)",
    "NUXIVA_UPDATE_BRANCH": "Ramo GitHub",
    "NUXIVA_KIOSK": "Display kiosk (1/0)",
    "GEMINI_API_KEY": "API key Google Gemini (fallback)",
    "ANTHROPIC_API_KEY": "API key Anthropic Claude (fallback)",
    "NUXIVA_TELEGRAM_TOKEN": "Token del bot Telegram (da @BotFather)",
    "NUXIVA_TELEGRAM": "Bot Telegram attivo (1/0)",
    "NUXIVA_NETWORK": "Esploratore della rete locale (1/0)",
    "NUXIVA_SPOTIFY": "Spotify attivo (1/0)",
    "NUXIVA_SPOTIFY_CLIENT_ID": "Spotify: Client ID dell'app (developer.spotify.com)",
    "NUXIVA_SPOTIFY_CLIENT_SECRET": "Spotify: Client Secret dell'app",
    "NUXIVA_SPOTIFY_WHEN": "Spotify: quando mostrare il brano (present = se ti vede, always = sempre)",
    "NUXIVA_GOOGLE": "Google: connettori Calendar, Gmail, Tasks, Contatti, Drive, Keep attivi (1/0)",
    "NUXIVA_GOOGLE_CLIENT_ID": "Google: Client ID OAuth (App desktop, console.cloud.google.com)",
    "NUXIVA_GOOGLE_CLIENT_SECRET": "Google: Client Secret OAuth",
    "NUXIVA_GOOGLE_SERVICES": "Google: servizi da collegare (calendar,gmail,tasks,contacts,drive,keep)",
    "NUXIVA_GOOGLE_REMIND_MIN": "Google: avviso sul display N minuti prima di ogni appuntamento (0 = mai)",
    "NUXIVA_MAPS": "Maps: indicazioni, tempi e avvisi di viaggio (1/0)",
    "NUXIVA_MAPS_API_KEY": "Maps: chiave Google Maps Platform (Routes API) per traffico e mezzi; vuota = OpenStreetMap",
    "NUXIVA_MAPS_MODE": "Maps: mezzo predefinito (drive, walk, bike, transit, moto)",
    "NUXIVA_MAPS_EVENT_HOURS": "Maps: ore in anticipo in cui guardare gli appuntamenti con un luogo (default 4)",
    "NUXIVA_SKILLS": "Algoritmi riutilizzabili per calcoli e conversioni (1/0)",
    "NUXIVA_SKILLS_GENERATE": "Nuxiva scrive da sola nuovi algoritmi quando servono (1/0)",
    "HOME_ASSISTANT_URL": "URL Home Assistant",
    "HOME_ASSISTANT_TOKEN": "Token Home Assistant",
    "HOME_ASSISTANT_VERIFY_SSL": "Home Assistant: verifica il certificato HTTPS (1/0; 0 per certificati autofirmati)",
    "NUXIVA_HOME_ASSISTANT": "Casa: collegamento a Home Assistant attivo (1/0)",
    "NUXIVA_HOME_ROOM": "Casa: stanza in cui si trova Nuxiva (nome dell'area di Home Assistant)",
    "NUXIVA_HOME_MOTION_MIN": "Casa: minuti dopo l'ultimo movimento in cui una stanza resta occupata (default 5)",
    "NUXIVA_HOME_CONFIRM": "Casa: chiedi conferma per serrature, allarme, cancelli e garage (1/0)",
    "NUXIVA_HANDS": "Comandi con le mani davanti alla webcam (auto = solo se la GPU del display li regge, 1 = sempre, 0 = mai)",
    "NUXIVA_HANDS_FPS": "Comandi con le mani: analisi al secondo con una mano in vista (10/20/30)",
    "NUXIVA_HANDS_COUNT": "Comandi con le mani: mani riconosciute (1/2)",
    "NUXIVA_HANDS_MAX_MS": "Comandi con le mani: in automatico si spengono se un'analisi supera questi millisecondi (30/50/90)",
    "NUXIVA_AUTOMATIONS": "Automazioni a più stadi: inneschi, condizioni, azioni, rami, attese, webhook (1/0)",
    "NUXIVA_SOUNDS": "Suoni ed effetti (1/0)",
    "NUXIVA_SOUNDS_VOLUME": "Suoni: volume degli effetti 0-100",
    "NUXIVA_SOUNDS_THEME": "Suoni: tema (nuxiva, soft, classic)",
    "NUXIVA_SOUNDS_FEEDBACK": "Suoni di attivazione e richiesta (1/0)",
    "NUXIVA_SOUNDS_THINKING": "Suono mentre pensa ed elabora (1/0)",
    "NUXIVA_SOUNDS_NOTIFY": "Suoni di notifica (1/0)",
    "NUXIVA_SOUNDS_AMBIENT": "Sottofondo (none, reactor, space, rain, ocean, lab)",
    "NUXIVA_SOUNDS_AMBIENT_VOLUME": "Volume del sottofondo 0-100",
    "NUXIVA_QUIET_MODE": "Orari di silenzio: soft (attenua), mute (solo allarmi), off",
    "NUXIVA_QUIET_START": "Silenzio dalle HH:MM",
    "NUXIVA_QUIET_END": "Silenzio fino alle HH:MM",
    "NUXIVA_QUIET_DAYS": "Notti di silenzio: all, weekdays, weekend",
    "NUXIVA_QUIET_VOICE": "Volume della voce in silenzio 0-100",
    "NUXIVA_QUIET_EFFECTS": "Volume degli effetti in silenzio attenuato 0-100",
    "NUXIVA_SELFTEST": "Collaudo notturno e dopo ogni aggiornamento (1/0)",
    "NUXIVA_SELFTEST_AT": "Ora del collaudo notturno HH:MM",
    "NUXIVA_SELFTEST_ROLLBACK": "Torna alla versione precedente se un aggiornamento rompe una funzione essenziale (1/0)",
    "NUXIVA_UPDATE_REQUIRE_CI": "Installa solo versioni con i test superati su GitHub (1/0)",
    "NUXIVA_HABITS": "Abitudini: osserva la casa e propone automazioni (1/0)",
    "NUXIVA_HABITS_CONFIDENCE": "Abitudini: regolarità minima per proporre (0.6, 0.7, 0.8)",
    "NUXIVA_HABITS_ASK": "Abitudini: proposte a voce (1/0)",
    "NUXIVA_HABITS_ANOMALIES": "Avvisi di situazioni insolite con casa vuota (1/0)",
    "NUXIVA_VAULT": "Memoria in file leggibili e diario giornaliero (1/0)",
    "NUXIVA_VAULT_DIR": "Cartella della memoria in chiaro (vuoto = /var/lib/nuxiva/memoria, solo sul server)",
    "NUXIVA_GPU_DRIVER": "Driver video del display: auto (NVIDIA ufficiale se adatto), nouveau (libero)",
    "NUXIVA_GPU_DRIVER_REBOOT": "Riavvio per attivare il driver video: night (alle 04:15) o now",
    "NUXIVA_SHARES": "Cartella condivisa Samba «condivisa» con le creazioni di Nuxiva, protetta da password (1/0)",
    "NUXIVA_SMB_PASSWORD": "Password dell'utente nuxiva-share per la cartella condivisa",
    "NUXIVA_AUTONOMY": "Autonomia: compiti programmati, autopilota (diagnosi, studio, riepilogo serale) e approvazioni (1/0)",
    "NUXIVA_WELCOME": "Quando ti riconosce mostra meteo, promemoria e riepilogo Google nei widget (1/0)",
    "NUXIVA_AGENT": "Agente con strumenti: file, widget, ologramma, 3D, email, SMB, terminale (1/0)",
    "NUXIVA_AGENT_ACCESS": "Accesso dell'agente (completo = tutto il server con conferma per le azioni delicate, standard = solo /srv/nuxiva e modelli 3D)",
    "NUXIVA_SMTP_HOST": "Email in uscita: server SMTP (es. smtp.gmail.com; vuoto = usa Gmail collegato)",
    "NUXIVA_SMTP_PORT": "Email in uscita: porta SMTP (587 STARTTLS, 465 SSL)",
    "NUXIVA_SMTP_USER": "Email in uscita: utente SMTP",
    "NUXIVA_SMTP_PASSWORD": "Email in uscita: password SMTP (per Gmail una password per le app)",
    "NUXIVA_SMTP_FROM": "Email in uscita: mittente (vuoto = utente SMTP)",
    "NUXIVA_DOCUMENTS": "Documenti Office e LibreOffice: Word, Excel, PowerPoint, ODT, ODS, ODP, PDF e progetti (1/0)",
    "NUXIVA_COMMERCIAL": "Uso commerciale (1 = Nuxiva è usata in un'attività: non installa da sola componenti con licenza non commerciale e li segnala con un avviso; 0 = uso personale)",
    "NUXIVA_UNOFFICIAL_SERVICES": "Servizi non ufficiali (riconoscimento Shazam, voci online di Edge): 1 = li attivo accettandone i termini sotto la mia responsabilità, 0 = mai",
    "NUXIVA_3D_CONVERT": "Conversione 3D sul server: Blender per BLEND/USD/USDZ e LibreDWG per DWG (auto = se c'è spazio, 1 = sì, 0 = no)",
}
SECRET_KEYS = {"NUXIVA_SECRET_KEY", "NUXIVA_SMB_PASSWORD", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "HOME_ASSISTANT_TOKEN", "NUXIVA_TELEGRAM_TOKEN", "NUXIVA_SMTP_PASSWORD",
               "NUXIVA_SPOTIFY_CLIENT_SECRET", "NUXIVA_SPOTIFY_REFRESH_TOKEN",
               "NUXIVA_GOOGLE_CLIENT_SECRET", "NUXIVA_GOOGLE_REFRESH_TOKEN", "NUXIVA_MAPS_API_KEY",
               "NUXIVA_ONLINE_STT_KEY", "NUXIVA_MUSIC_APP_PASSWORD", "NUXIVA_CLOUD_KEY"}
SECRET_RE = re.compile(r"(KEY|TOKEN|PASSWORD|PASSWD|SECRET|PASSPHRASE|CREDENTIALS?|COOKIE)(_|$)")


def is_secret(key: str) -> bool:
    return key in SECRET_KEYS or bool(SECRET_RE.search(key))
_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


NODE = ContextVar("nuxiva_node", default="")
NODE_FIXED = {"NUXIVA_AUTO_UPDATE", "NUXIVA_UPDATE_INTERVAL_MIN", "NUXIVA_UPDATE_BRANCH", "NUXIVA_GOOGLE_CLIENT_ID",
              "NUXIVA_SPOTIFY_CLIENT_ID", "HOME_ASSISTANT_URL", "NUXIVA_TELEGRAM", "NUXIVA_AGENT_ACCESS"}
_nodes_cache = {"mtime": -1.0, "data": {}}


def node_keys() -> list[str]:
    return [k for k in EDITABLE_KEYS if not is_secret(k) and k not in NODE_FIXED]


def node_overrides(node_id: str) -> dict:
    path = STATE_DIR / "nodes.json"
    try:
        mtime = path.stat().st_mtime
        if mtime != _nodes_cache["mtime"]:
            _nodes_cache.update(mtime=mtime, data=json.loads(path.read_text(encoding="utf-8")).get("nodes", {}))
    except (OSError, ValueError):
        return {}
    allowed = set(node_keys())
    return {k: v for k, v in (_nodes_cache["data"].get(node_id, {}).get("settings") or {}).items() if k in allowed}


def read_env() -> dict:
    env = read_global_env()
    node = NODE.get()
    if node:
        env.update(node_overrides(node))
    return env


def read_global_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


_ollama_cache: dict = {}


def ollama_url() -> str:
    import time
    node = NODE.get()
    at, url = _ollama_cache.get(node, (0.0, OLLAMA_URL))
    if time.time() - at > 5:
        custom = read_env().get("NUXIVA_OLLAMA_URL", "").strip().rstrip("/")
        if custom and not custom.startswith(("http://", "https://")):
            custom = f"http://{custom}"
        if custom and not re.search(r":\d+$", custom.split("//", 1)[1]):
            custom += ":11434"
        url = custom or OLLAMA_URL
        _ollama_cache[node] = (time.time(), url)
    return url


def ollama_remote() -> bool:
    host = ollama_url().split("//", 1)[-1].split(":", 1)[0]
    return host not in ("127.0.0.1", "localhost", "::1", "")


def write_env(updates: dict) -> None:
    for key, value in updates.items():
        if not _KEY_RE.match(key) or "\n" in str(value):
            raise ValueError(f"Chiave o valore non valido: {key}")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    pending = dict(updates)
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in pending:
            value = pending.pop(key)
            if value != "":
                out.append(f"{key}={value}")
        else:
            out.append(line)
    out.extend(f"{k}={v}" for k, v in pending.items() if v != "")
    tmp = ENV_FILE.with_suffix(".tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, ENV_FILE)


def env_get(key: str, default: str = "") -> str:
    return read_env().get(key, default)


def kiosk_log() -> Path:
    user = env_get("NUXIVA_KIOSK_USER", "nuxiva-kiosk")
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
        user = "nuxiva-kiosk"
    return Path("/home") / user / ".cache" / "nuxiva-kiosk.log"
