import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from connection import enroll


def main(installer: str) -> int:
    work = Path(tempfile.mkdtemp(prefix="nuxiva-trailer-"))
    target = work / "Nuxiva_Setup.exe"
    shutil.copyfile(installer, target)
    payload = json.dumps({"server": "https://127.0.0.1:8443", "token": "T" * 43, "pin": "ab" * 32, "expires": int(time.time()) - 60}).encode()
    with target.open("ab") as handle:
        handle.write(payload + len(payload).to_bytes(enroll.LENGTH_SIZE, "big") + enroll.TRAILER_MAGIC)
    try:
        enroll.load_trailer(target)
    except enroll.EnrollError as exc:
        if exc.key != "enroll.file_expired":
            print(f"Lettura del blocco non riuscita: {exc.key}")
            return 1
    app = work / "app"
    result = subprocess.run([str(target), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", f"/DIR={app}", f"/LOG={work / 'setup.log'}"],
                            timeout=600, check=False)
    if result.returncode != 0 or not (app / "Nuxiva.exe").is_file():
        print(f"L'installer con blocco aggiunto non si installa (codice {result.returncode})")
        log = work / "setup.log"
        print(log.read_text(errors="replace")[-4000:] if log.is_file() else "nessun log")
        return 1
    subprocess.run(["taskkill", "/F", "/IM", "Nuxiva.exe"], check=False)
    uninstaller = next(app.glob("unins*.exe"), None)
    if uninstaller:
        subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=300, check=False)
    print("Installer con blocco di iscrizione aggiunto: installazione riuscita")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
