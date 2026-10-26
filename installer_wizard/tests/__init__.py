import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SANDBOX = tempfile.mkdtemp(prefix="nuxiva-tests-")
tempfile.tempdir = SANDBOX
os.environ["TMPDIR"] = SANDBOX
os.environ.pop("NUXIVA_DEMO", None)
os.environ["NUXIVA_TEST_AUTH"] = "1"
os.environ["NUXIVA_STATE_ROOT"] = str(Path(SANDBOX) / "state")
os.environ["NUXIVA_PUBLIC_PORT"] = "8000"
os.environ["NUXIVA_ADMIN_PORT"] = "8001"
os.environ.setdefault("NUXIVA_ALLOWED_HOSTS", "testserver")
os.environ.setdefault("NUXIVA_DIR", str(ROOT.parent))
for p in (str(ROOT.parent), str(ROOT / "backend"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(ROOT / "backend")
