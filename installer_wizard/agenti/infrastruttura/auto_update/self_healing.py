from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from config import NUXIVA_DIR, STATE_DIR

log = logging.getLogger("nuxiva.self_healing")


class SelfHealingEngine:
    def __init__(self, state_dir: Path = STATE_DIR, root_dir: Path = NUXIVA_DIR) -> None:
        self.state_dir = state_dir
        self.root_dir = root_dir

    def run_all(self) -> dict[str, bool]:
        return {
            "directories": self.heal_directories(),
            "git_locks": self.heal_git_locks(),
            "activation_state": self.heal_activation_state(),
            "bad_revs": self.heal_bad_revs(),
        }

    def heal_directories(self) -> bool:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        return True

    def heal_git_locks(self) -> bool:
        lock_file = self.root_dir / ".git" / "index.lock"
        if not lock_file.exists():
            return True
        try:
            mtime = lock_file.stat().st_mtime
            if time.time() - mtime > 180.0:
                lock_file.unlink(missing_ok=True)
                log.warning("Rimossa stale git lock in self-healing")
                return True
        except OSError:
            pass
        return False

    def heal_activation_state(self) -> bool:
        setup_file = self.state_dir / "setup.json"
        if not setup_file.exists():
            return True
        try:
            setup_data = json.loads(setup_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not setup_data.get("done"):
            return True

        act_file = self.state_dir / "activation.json"
        need_write = False
        if not act_file.exists():
            need_write = True
        else:
            try:
                act_data = json.loads(act_file.read_text(encoding="utf-8"))
                if act_data.get("stage") != "done":
                    need_write = True
            except (OSError, ValueError):
                need_write = True

        if need_write:
            from agenti.activation.domain.journey import Journey, Stage
            from agenti.activation.infrastructure.journey_store import JourneyStore
            now = time.time()
            j = Journey(stage=Stage.DONE, created_at=now, updated_at=now)
            JourneyStore(act_file).save(j)
            log.info("Self-healing: sincronizzato activation.json con setup completato")
        return True

    def heal_bad_revs(self) -> bool:
        bad_file = self.state_dir / "bad_revs"
        if not bad_file.exists():
            return True
        try:
            lines = bad_file.read_text(encoding="utf-8").splitlines()
            valid = []
            now = time.time()
            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue
                ts = float(parts[1]) if len(parts) > 1 and parts[1].replace(".", "", 1).isdigit() else 0.0
                if ts == 0.0 or (now - ts) < 86400.0:
                    valid.append(line)
            bad_file.write_text("\n".join(valid) + ("\n" if valid else ""), encoding="utf-8")
        except OSError:
            return False
        return True


self_healer = SelfHealingEngine()
