import base64
import binascii
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sealed import write_private

from features.fleet.model import (
    BULK_MAX, CATEGORIES, DEFAULT_LIMIT, DESCRIPTION_MAX, INSTRUCTIONS_MAX, KINDS, LINK_KINDS, LINKS_MAX, MAX_LIMIT, NAME_MAX, STATES,
    AgentSpec, FleetError, clean_text, require_choice, require_id, require_priority, require_ref,
)
from features.fleet.shards import SHARDS, Shards, shard_of

FACETS = ("state", "kind", "category", "origin")
PREVIEW_LINKS = 12
SUMMARY_TTL = 5.0
EDITABLE = {"name", "kind", "category", "state", "priority", "description", "instructions"}


@dataclass(frozen=True, slots=True)
class Filter:
    state: str = ""
    kind: str = ""
    category: str = ""
    origin: str = ""
    prefix: str = ""
    tool: str = ""
    widget: str = ""


def encode_cursor(shard: int, agent_id: str) -> str:
    raw = json.dumps([shard, agent_id], separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[int, str]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        shard, agent_id = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, TypeError, binascii.Error):
        raise FleetError("invalid_cursor")
    if not isinstance(shard, int) or isinstance(shard, bool) or not 0 <= shard < SHARDS:
        raise FleetError("invalid_cursor")
    return shard, require_id(agent_id)


def clamp_limit(value: int) -> int:
    return max(1, min(MAX_LIMIT, value))


class FleetStore:
    def __init__(self, root: Path) -> None:
        self.shards = Shards(root)
        self.key_path = root / "fleet.key"
        self._cipher: Fernet | None = None
        self._summary: tuple[float, dict] | None = None

    def _fernet(self) -> Fernet:
        if self._cipher is None:
            if not self.key_path.exists():
                write_private(self.key_path, Fernet.generate_key())
            self._cipher = Fernet(self.key_path.read_bytes())
        return self._cipher

    def _seal(self, text: str) -> bytes:
        return self._fernet().encrypt(text.encode("utf-8"))

    def _unseal(self, blob: bytes) -> str:
        try:
            return self._fernet().decrypt(bytes(blob)).decode("utf-8")
        except InvalidToken:
            raise FleetError("sealed_unreadable", 500)

    @staticmethod
    def _bump(connection: sqlite3.Connection, row: dict, delta: int) -> None:
        for dim in FACETS:
            connection.execute(
                "INSERT INTO counts(dim, val, n) VALUES(?, ?, ?) ON CONFLICT(dim, val) DO UPDATE SET n = n + excluded.n",
                (dim, row[dim], delta),
            )

    def _insert(self, connection: sqlite3.Connection, spec: AgentSpec, now: int) -> bool:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO agents(id, name, kind, category, state, priority, origin, description, instructions, created, updated) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (spec.id, spec.name, spec.kind, spec.category, spec.state, spec.priority, spec.origin, spec.description,
             self._seal(spec.instructions), now, now),
        )
        if cursor.rowcount:
            self._bump(connection, {"state": spec.state, "kind": spec.kind, "category": spec.category, "origin": spec.origin}, 1)
        return bool(cursor.rowcount)

    def create(self, spec: AgentSpec) -> None:
        with self.shards.write(shard_of(spec.id)) as connection:
            if not self._insert(connection, spec, int(time.time())):
                raise FleetError("exists", 409)
        self._summary = None

    def create_many(self, specs: list[AgentSpec]) -> int:
        if len(specs) > BULK_MAX:
            raise FleetError("too_many")
        grouped: dict[int, list[AgentSpec]] = {}
        for spec in specs:
            grouped.setdefault(shard_of(spec.id), []).append(spec)
        now = int(time.time())
        created = 0
        for index, group in grouped.items():
            with self.shards.write(index) as connection:
                created += sum(1 for spec in group if self._insert(connection, spec, now))
        self._summary = None
        return created

    def exists(self, agent_id: str) -> bool:
        index = shard_of(require_id(agent_id))
        if not self.shards.exists(index):
            return False
        with self.shards.open(index) as connection:
            return connection.execute("SELECT 1 FROM agents WHERE id = ?", (agent_id,)).fetchone() is not None

    def get(self, agent_id: str) -> dict:
        index = shard_of(require_id(agent_id))
        if not self.shards.exists(index):
            raise FleetError("not_found", 404)
        with self.shards.open(index) as connection:
            row = connection.execute("SELECT * FROM agents WHERE id = ?", (agent_id,)).fetchone()
            if row is None:
                raise FleetError("not_found", 404)
            links = connection.execute("SELECT kind, ref FROM links WHERE agent_id = ? ORDER BY kind, ref", (agent_id,)).fetchall()
        record = dict(row)
        record["instructions"] = self._unseal(record["instructions"])
        record["tools"] = [link["ref"] for link in links if link["kind"] == "tool"]
        record["widgets"] = [link["ref"] for link in links if link["kind"] == "widget"]
        return record

    def update(self, agent_id: str, changes: dict) -> dict:
        if not isinstance(changes, dict) or not changes or not set(changes) <= EDITABLE:
            raise FleetError("invalid_body")
        current = self.get(agent_id)
        merged = dict(current)
        if "name" in changes:
            merged["name"] = clean_text(changes["name"], NAME_MAX)
            if not merged["name"]:
                raise FleetError("invalid_name")
        if "kind" in changes:
            merged["kind"] = require_choice(changes["kind"], KINDS, "invalid_kind")
        if "category" in changes:
            merged["category"] = require_choice(changes["category"], CATEGORIES, "invalid_category")
        if "state" in changes:
            merged["state"] = require_choice(changes["state"], STATES, "invalid_state")
        if "priority" in changes:
            merged["priority"] = require_priority(changes["priority"])
        if "description" in changes:
            merged["description"] = clean_text(changes["description"], DESCRIPTION_MAX)
        if "instructions" in changes:
            merged["instructions"] = clean_text(changes["instructions"], INSTRUCTIONS_MAX, multiline=True)
        with self.shards.write(shard_of(agent_id)) as connection:
            connection.execute(
                "UPDATE agents SET name=?, kind=?, category=?, state=?, priority=?, description=?, instructions=?, updated=? WHERE id=?",
                (merged["name"], merged["kind"], merged["category"], merged["state"], merged["priority"], merged["description"],
                 self._seal(merged["instructions"]), int(time.time()), agent_id),
            )
            self._bump(connection, current, -1)
            self._bump(connection, merged, 1)
        self._summary = None
        return self.get(agent_id)

    def delete(self, agent_id: str) -> None:
        current = self.get(agent_id)
        with self.shards.write(shard_of(agent_id)) as connection:
            connection.execute("DELETE FROM links WHERE agent_id = ?", (agent_id,))
            connection.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
            self._bump(connection, current, -1)
        self._summary = None

    def link(self, agent_id: str, kind: str, refs: list[str]) -> None:
        require_choice(kind, LINK_KINDS, "invalid_link_kind")
        clean = sorted({require_ref(ref) for ref in refs})
        current = self.get(agent_id)
        if len(set(current["tools"] if kind == "tool" else current["widgets"]) | set(clean)) > LINKS_MAX:
            raise FleetError("too_many_links")
        with self.shards.write(shard_of(agent_id)) as connection:
            connection.executemany("INSERT OR IGNORE INTO links(agent_id, kind, ref) VALUES(?, ?, ?)", [(agent_id, kind, ref) for ref in clean])

    def unlink(self, agent_id: str, kind: str, ref: str) -> None:
        require_choice(kind, LINK_KINDS, "invalid_link_kind")
        self.get(agent_id)
        with self.shards.write(shard_of(agent_id)) as connection:
            connection.execute("DELETE FROM links WHERE agent_id = ? AND kind = ? AND ref = ?", (agent_id, kind, require_ref(ref)))

    @staticmethod
    def _where(flt: Filter, after: str | None) -> tuple[str, list]:
        clauses: list[str] = []
        params: list = []
        for column in FACETS:
            value = getattr(flt, column)
            if value:
                clauses.append(f"a.{column} = ?")
                params.append(value)
        if flt.prefix:
            clauses.append("a.name COLLATE NOCASE >= ? AND a.name COLLATE NOCASE < ?")
            params.extend([flt.prefix, flt.prefix + "\U0010ffff"])
        for kind, ref in (("tool", flt.tool), ("widget", flt.widget)):
            if ref:
                clauses.append("a.id IN (SELECT agent_id FROM links WHERE kind = ? AND ref = ?)")
                params.extend([kind, ref])
        if after is not None:
            clauses.append("a.id > ?")
            params.append(after)
        return (" WHERE " + " AND ".join(clauses)) if clauses else "", params

    def _page_rows(self, connection: sqlite3.Connection, flt: Filter, after: str | None, take: int) -> list[dict]:
        where, params = self._where(flt, after)
        rows = connection.execute(
            "SELECT a.id, a.name, a.kind, a.category, a.state, a.priority, a.origin, a.description, a.created, a.updated "
            f"FROM agents a{where} ORDER BY a.id LIMIT ?",
            [*params, take],
        ).fetchall()
        items = [dict(row) for row in rows]
        if items:
            marks = ",".join("?" * len(items))
            links = connection.execute(
                f"SELECT agent_id, kind, ref FROM links WHERE agent_id IN ({marks}) ORDER BY agent_id, kind, ref",
                [item["id"] for item in items],
            ).fetchall()
            for item in items:
                item["tools"], item["widgets"] = [], []
            index = {item["id"]: item for item in items}
            for link in links:
                bucket = index[link["agent_id"]]["tools" if link["kind"] == "tool" else "widgets"]
                if len(bucket) < PREVIEW_LINKS:
                    bucket.append(link["ref"])
        return items

    def list(self, flt: Filter, cursor: str = "", limit: int = DEFAULT_LIMIT) -> dict:
        limit = clamp_limit(limit)
        start, after = decode_cursor(cursor) if cursor else (0, None)
        items: list[dict] = []
        for index in range(start, SHARDS):
            if not self.shards.exists(index):
                continue
            with self.shards.open(index) as connection:
                rows = self._page_rows(connection, flt, after if index == start else None, limit + 1 - len(items))
            for row in rows:
                items.append({**row, "shard": index})
            if len(items) > limit:
                break
        more = len(items) > limit
        items = items[:limit]
        next_cursor = encode_cursor(items[-1]["shard"], items[-1]["id"]) if more and items else ""
        for item in items:
            item.pop("shard")
        return {"items": items, "next": next_cursor, "more": more}

    def summary(self) -> dict:
        now = time.monotonic()
        if self._summary and now - self._summary[0] < SUMMARY_TTL:
            return self._summary[1]
        totals: dict[str, dict[str, int]] = {dim: {} for dim in FACETS}
        used = 0
        for index in range(SHARDS):
            if not self.shards.exists(index):
                continue
            used += 1
            with self.shards.open(index) as connection:
                for row in connection.execute("SELECT dim, val, n FROM counts WHERE n > 0"):
                    totals[row["dim"]][row["val"]] = totals[row["dim"]].get(row["val"], 0) + row["n"]
        result = {"total": sum(totals["state"].values()), "shards": SHARDS, "shards_used": used, **totals}
        self._summary = (now, result)
        return result

    def change_state(self, flt: Filter, state: str, limit: int = BULK_MAX) -> dict:
        require_choice(state, STATES, "invalid_state")
        limit = max(1, min(BULK_MAX, limit))
        changed = 0
        for index in range(SHARDS):
            if changed >= limit:
                break
            if not self.shards.exists(index):
                continue
            where, params = self._where(flt, None)
            extra = " AND a.state != ?" if where else " WHERE a.state != ?"
            with self.shards.write(index) as connection:
                rows = connection.execute(
                    "SELECT a.id, a.kind, a.category, a.state, a.origin FROM agents a" + where + extra + " ORDER BY a.id LIMIT ?",
                    [*params, state, limit - changed],
                ).fetchall()
                for row in rows:
                    connection.execute("UPDATE agents SET state = ?, updated = ? WHERE id = ?", (state, int(time.time()), row["id"]))
                    self._bump(connection, dict(row), -1)
                    self._bump(connection, {**dict(row), "state": state}, 1)
                changed += len(rows)
        self._summary = None
        return {"changed": changed, "more": changed >= limit}
