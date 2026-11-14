from config import STATE_DIR

ROOT = STATE_DIR / "collaudo"
LOG_DIR = ROOT / "log"
PY_LOG_DIR = ROOT / "log_py"
KEY_FILE = ROOT / "key"
TOKEN_FILE = ROOT / "token"
MODE_FILE = ROOT / "mode"
SOCKET = ROOT / "intake.sock"
BASELINE = ROOT / "baseline.json"
SEGMENT_BYTES = 8 * 1024 * 1024
KEEP_SEGMENTS = 24
