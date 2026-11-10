from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sqlite3

from config import STATE_DIR


@dataclass(frozen=True)
class PersonaProfile:
    user_name: str
    style: str
    interests: list[str]
    facts: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


class ReflexMemoryStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.path = db_path or (STATE_DIR / "reflex_memory.sqlite3")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS persona_profile (
                    user_name TEXT PRIMARY KEY,
                    style TEXT NOT NULL,
                    interests_json TEXT NOT NULL,
                    facts_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_cache (
                    hash_key TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    phrase TEXT NOT NULL,
                    used_count INTEGER NOT NULL DEFAULT 0,
                    last_used REAL NOT NULL DEFAULT 0.0
                )
            """)
            conn.commit()
        if not self.get_profile("Nunzio"):
            self.save_profile(PersonaProfile(
                user_name="Nunzio",
                style="conversational",
                interests=["napoli_calcio", "clean_architecture", "ai_automation", "devops"],
                facts={
                    "favorite_team": "SSC Napoli",
                    "napoli_status": "Napoli - Inter 2-1",
                    "focus_today": "Nuxiva v5.6.0",
                },
            ))

    def get_profile(self, user_name: str = "Nunzio") -> PersonaProfile | None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT user_name, style, interests_json, facts_json FROM persona_profile WHERE user_name = ?", (user_name,))
            row = cur.fetchone()
            if not row:
                return None
            try:
                interests = json.loads(row[2])
                facts = json.loads(row[3])
            except (ValueError, TypeError):
                interests, facts = [], {}
            return PersonaProfile(user_name=row[0], style=row[1], interests=interests, facts=facts)

    def save_profile(self, profile: PersonaProfile) -> None:
        import time
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO persona_profile (user_name, style, interests_json, facts_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_name) DO UPDATE SET
                    style = excluded.style,
                    interests_json = excluded.interests_json,
                    facts_json = excluded.facts_json,
                    updated_at = excluded.updated_at
            """, (
                profile.user_name,
                profile.style,
                json.dumps(profile.interests, ensure_ascii=False),
                json.dumps(profile.facts, ensure_ascii=False),
                time.time(),
            ))
            conn.commit()

    def update_fact(self, key: str, value: str, user_name: str = "Nunzio") -> None:
        prof = self.get_profile(user_name) or PersonaProfile(user_name=user_name, style="conversational", interests=[], facts={})
        facts = dict(prof.facts)
        facts[key] = value
        self.save_profile(PersonaProfile(user_name=prof.user_name, style=prof.style, interests=prof.interests, facts=facts))

    def record_usage(self, phrase: str, category: str) -> None:
        import hashlib
        import time
        key = hashlib.sha256(phrase.encode("utf-8")).hexdigest()[:16]
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO conversation_cache (hash_key, category, phrase, used_count, last_used)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(hash_key) DO UPDATE SET
                    used_count = conversation_cache.used_count + 1,
                    last_used = excluded.last_used
            """, (key, category, phrase, time.time()))
            conn.commit()

    def get_least_used(self, phrases: list[str]) -> str:
        if not phrases:
            return ""
        import hashlib
        scores = {}
        with self._connect() as conn:
            cur = conn.cursor()
            for p in phrases:
                key = hashlib.sha256(p.encode("utf-8")).hexdigest()[:16]
                cur.execute("SELECT used_count, last_used FROM conversation_cache WHERE hash_key = ?", (key,))
                row = cur.fetchone()
                scores[p] = (row[0], row[1]) if row else (0, 0.0)
        return min(phrases, key=lambda p: (scores[p][0], scores[p][1]))


reflex_memory = ReflexMemoryStore()
