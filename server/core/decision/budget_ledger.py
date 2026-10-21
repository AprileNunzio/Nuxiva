import hashlib
import hmac
import os
import time
import uuid
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel
from server.core.decision.contracts import DecisionDomainException


class LedgerEntry(BaseModel):
    entry_id: str
    reservation_id: str
    adapter_id: str
    action: Literal["RESERVE", "SETTLE"]
    reserved_usd: float
    actual_usd: Optional[float] = None
    tokens_used: int = 0
    timestamp: float
    prev_signature: str
    signature: str


class ReservationRecord(BaseModel):
    reservation_id: str
    request_id: str
    adapter_id: str
    reserved_usd: float
    actual_usd: Optional[float] = None
    max_tokens: int
    actual_tokens: int = 0
    settled: bool = False
    created_at: float
    settled_at: Optional[float] = None


class DecisionBudgetLedger:
    def __init__(self, cap_usd: float = 25.0, secret_key: Optional[str] = None) -> None:
        if cap_usd <= 0.0:
            raise DecisionDomainException(
                message="Budget cap must be strictly positive",
                details={"cap_usd": cap_usd},
            )
        self._cap_usd = float(cap_usd)
        raw_secret = secret_key or os.environ.get("NUXIVA_LEDGER_HMAC_KEY", "nuxiva-decision-zero-trust-ledger-v2")
        self._secret = raw_secret.encode("utf-8")
        self._reservations: Dict[str, ReservationRecord] = {}
        self._entries: List[LedgerEntry] = []

    @property
    def cap_usd(self) -> float:
        return self._cap_usd

    def set_cap_usd(self, new_cap_usd: float) -> float:
        if new_cap_usd < self.committed_usd():
            raise DecisionDomainException(
                message="New budget cap cannot be lower than currently committed spend",
                details={"new_cap_usd": new_cap_usd, "committed_usd": self.committed_usd()},
            )
        self._cap_usd = round(float(new_cap_usd), 6)
        return self._cap_usd

    def committed_usd(self) -> float:
        total = 0.0
        for rec in self._reservations.values():
            if rec.settled and rec.actual_usd is not None:
                total += rec.actual_usd
            else:
                total += rec.reserved_usd
        return round(total, 6)

    def remaining_usd(self) -> float:
        return round(max(0.0, self._cap_usd - self.committed_usd()), 6)

    def reserve(
        self,
        adapter_id: str,
        worst_case_usd: float,
        max_tokens: int = 2048,
        request_id: Optional[str] = None,
    ) -> ReservationRecord:
        amount = float(worst_case_usd)
        if amount < 0.0:
            raise DecisionDomainException(
                message="Reservation amount cannot be negative",
                details={"worst_case_usd": amount},
            )
        projected = self.committed_usd() + amount
        if projected > self._cap_usd + 1e-9:
            raise DecisionDomainException(
                message="Budget cap exceeded during pre-request reservation",
                details={
                    "requested_usd": round(amount, 6),
                    "committed_usd": self.committed_usd(),
                    "cap_usd": self._cap_usd,
                },
            )

        res_id = f"rsv_{uuid.uuid4().hex[:16]}"
        req_id = request_id or f"req_{uuid.uuid4().hex[:12]}"
        now = time.time()
        record = ReservationRecord(
            reservation_id=res_id,
            request_id=req_id,
            adapter_id=str(adapter_id)[:80],
            reserved_usd=round(amount, 6),
            max_tokens=max(1, int(max_tokens)),
            created_at=now,
        )
        self._reservations[res_id] = record
        self._append_entry(
            reservation_id=res_id,
            adapter_id=record.adapter_id,
            action="RESERVE",
            reserved_usd=record.reserved_usd,
            actual_usd=None,
            tokens_used=0,
            timestamp=now,
        )
        return record

    def settle(
        self,
        reservation_id: str,
        actual_usd: float,
        actual_tokens: int = 0,
    ) -> ReservationRecord:
        record = self._reservations.get(reservation_id)
        if record is None:
            raise DecisionDomainException(
                message="Cannot settle unknown reservation ID",
                details={"reservation_id": reservation_id},
            )
        if record.settled:
            raise DecisionDomainException(
                message="Reservation has already been settled",
                details={"reservation_id": reservation_id},
            )
        actual = float(actual_usd)
        if actual < 0.0:
            raise DecisionDomainException(
                message="Actual settled cost cannot be negative",
                details={"actual_usd": actual},
            )
        if actual > record.reserved_usd + 1e-6:
            raise DecisionDomainException(
                message="Actual spend exceeded worst-case reservation",
                details={
                    "reservation_id": reservation_id,
                    "reserved_usd": record.reserved_usd,
                    "actual_usd": round(actual, 6),
                },
            )

        now = time.time()
        record.actual_usd = round(actual, 6)
        record.actual_tokens = max(0, int(actual_tokens))
        record.settled = True
        record.settled_at = now

        self._append_entry(
            reservation_id=reservation_id,
            adapter_id=record.adapter_id,
            action="SETTLE",
            reserved_usd=record.reserved_usd,
            actual_usd=record.actual_usd,
            tokens_used=record.actual_tokens,
            timestamp=now,
        )
        return record

    def verify_integrity(self) -> bool:
        prev_sig = "GENESIS"
        for entry in self._entries:
            if entry.prev_signature != prev_sig:
                return False
            expected = self._compute_hmac(
                entry_id=entry.entry_id,
                reservation_id=entry.reservation_id,
                adapter_id=entry.adapter_id,
                action=entry.action,
                reserved_usd=entry.reserved_usd,
                actual_usd=entry.actual_usd,
                tokens_used=entry.tokens_used,
                timestamp=entry.timestamp,
                prev_signature=prev_sig,
            )
            if not hmac.compare_digest(entry.signature, expected):
                return False
            prev_sig = entry.signature
        return True

    def summary(self) -> Dict[str, Any]:
        settled_list = [r for r in self._reservations.values() if r.settled]
        unsettled_list = [r for r in self._reservations.values() if not r.settled]
        settled_usd = sum(r.actual_usd or 0.0 for r in settled_list)
        unsettled_usd = sum(r.reserved_usd for r in unsettled_list)
        total_tokens = sum(r.actual_tokens for r in settled_list)
        return {
            "cap_usd": round(self._cap_usd, 4),
            "committed_usd": self.committed_usd(),
            "settled_usd": round(settled_usd, 6),
            "unsettled_reserved_usd": round(unsettled_usd, 6),
            "remaining_usd": self.remaining_usd(),
            "total_reservations": len(self._reservations),
            "settled_count": len(settled_list),
            "unsettled_count": len(unsettled_list),
            "total_tokens": total_tokens,
            "chain_integrity_verified": self.verify_integrity(),
            "recent_entries": [e.model_dump() for e in self._entries[-12:]],
        }

    def _append_entry(
        self,
        reservation_id: str,
        adapter_id: str,
        action: Literal["RESERVE", "SETTLE"],
        reserved_usd: float,
        actual_usd: Optional[float],
        tokens_used: int,
        timestamp: float,
    ) -> None:
        prev_sig = self._entries[-1].signature if self._entries else "GENESIS"
        entry_id = f"led_{len(self._entries) + 1:05d}"
        sig = self._compute_hmac(
            entry_id=entry_id,
            reservation_id=reservation_id,
            adapter_id=adapter_id,
            action=action,
            reserved_usd=reserved_usd,
            actual_usd=actual_usd,
            tokens_used=tokens_used,
            timestamp=timestamp,
            prev_signature=prev_sig,
        )
        self._entries.append(
            LedgerEntry(
                entry_id=entry_id,
                reservation_id=reservation_id,
                adapter_id=adapter_id,
                action=action,
                reserved_usd=reserved_usd,
                actual_usd=actual_usd,
                tokens_used=tokens_used,
                timestamp=timestamp,
                prev_signature=prev_sig,
                signature=sig,
            )
        )

    def _compute_hmac(
        self,
        entry_id: str,
        reservation_id: str,
        adapter_id: str,
        action: str,
        reserved_usd: float,
        actual_usd: Optional[float],
        tokens_used: int,
        timestamp: float,
        prev_signature: str,
    ) -> str:
        payload = (
            f"{entry_id}|{reservation_id}|{adapter_id}|{action}|"
            f"{reserved_usd:.6f}|{actual_usd if actual_usd is not None else 'NONE'}|"
            f"{tokens_used}|{timestamp:.6f}|{prev_signature}"
        )
        return hmac.new(self._secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
