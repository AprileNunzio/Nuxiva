import sqlite3
import json
import time
import logging

log = logging.getLogger("nuxiva.event_sourcing")

try:
    from nuxiva_native import RustCrdtMesh
except ImportError:
    RustCrdtMesh = None


class TimeTravelLedger:
    """
    Motore Event Sourcing e CRDT State Ledger di Nuxiva v5.0.
    Tutte le azioni sono immutabili e memorizzate come stream di eventi.
    Integra la sincronizzazione CRDT Rust per il Control Plane del Nucleo Virtuale Condiviso.
    """
    def __init__(self, db_path="nuxiva_ledger.db", node_id: str = "node-local"):
        self.db_path = db_path
        self.node_id = node_id
        self._init_db()
        self._crdt = RustCrdtMesh() if RustCrdtMesh is not None else None
        self._fallback_crdt: dict[str, dict] = {}

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    aggregate_id TEXT,
                    event_type TEXT,
                    payload JSON
                )
            ''')
            conn.commit()

    def append_event(self, aggregate_id: str, event_type: str, payload: dict):
        """Aggiunge un evento immutabile al ledger e aggiorna lo stato CRDT."""
        ts = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events (timestamp, aggregate_id, event_type, payload) VALUES (?, ?, ?, ?)",
                (ts, aggregate_id, event_type, json.dumps(payload))
            )
            conn.commit()

        ts_ms = int(ts * 1000)
        for key, val in payload.items():
            full_key = f"{aggregate_id}.{key}"
            val_str = json.dumps(val) if not isinstance(val, str) else val
            if self._crdt is not None:
                self._crdt.set(full_key, val_str, ts_ms, self.node_id)
            else:
                self._fallback_crdt[full_key] = {
                    "value": val_str,
                    "timestamp_ms": ts_ms,
                    "node_id": self.node_id
                }

        log.debug(f"Event Appended: {event_type} on {aggregate_id}")

    def get_crdt_value(self, key: str) -> str | None:
        if self._crdt is not None:
            return self._crdt.get(key)
        entry = self._fallback_crdt.get(key)
        return entry["value"] if entry else None

    def export_crdt_state(self) -> str:
        if self._crdt is not None:
            return self._crdt.to_json()
        return json.dumps(self._fallback_crdt)

    def merge_crdt_state(self, remote_json: str) -> int:
        if self._crdt is not None:
            return self._crdt.merge_json(remote_json)
        try:
            remote = json.loads(remote_json)
            updated = 0
            for k, v in remote.items():
                local = self._fallback_crdt.get(k)
                if local is None or v.get("timestamp_ms", 0) > local.get("timestamp_ms", 0):
                    self._fallback_crdt[k] = v
                    updated += 1
            return updated
        except Exception:
            return 0

    def replay_to_timestamp(self, target_timestamp: float):
        """
        Riavvolge il sistema ricostruendo lo stato ESATTAMENTE com'era a un dato istante.
        Ritorna lo stato aggregato calcolato.
        """
        log.warning(f"INIZIO TIME-TRAVEL. Ricostruzione stato al timestamp {target_timestamp}...")
        state = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT aggregate_id, event_type, payload FROM events WHERE timestamp <= ? ORDER BY timestamp ASC",
                (target_timestamp,)
            )
            for row in cursor.fetchall():
                agg_id, e_type, payload_str = row
                payload = json.loads(payload_str)
                if agg_id not in state:
                    state[agg_id] = {}
                state[agg_id].update(payload)
        return state


ledger = TimeTravelLedger()
