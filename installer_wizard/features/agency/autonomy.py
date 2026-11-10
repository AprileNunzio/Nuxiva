from dataclasses import asdict, dataclass
import re

CRITICAL_PATTERNS = (
    r"\b(?:password|passwd|secret|api_key|token|credential|private_key)\b",
    r"\b(?:iban|conto\s+corrente|bank\s+account|credit_card|cvv)\b",
    r"\b(?:drop\s+database|drop\s+table|format\s+[a-z]:|rm\s+-rf\s+/|chmod\s+777)\b",
    r"\b(?:sudo\s+|mkfs|fdisk|dd\s+if=)\b",
)

HIGH_PATTERNS = (
    r"\b(?:delete|remove|truncate|unlink|purge)\b",
    r"\b(?:migration|alter\s+table|schema|deploy|production)\b",
    r"\b(?:external_api|webhook|payment|stripe|checkout)\b",
)

MEDIUM_PATTERNS = (
    r"\b(?:endpoint|route|controller|handler|service|query)\b",
    r"\b(?:write_file|create_file|patch|refactor|update)\b",
)

LOW_PATTERNS = (
    r"\b(?:test|spec|doc|readme|comment|style|css|html|view)\b",
    r"\b(?:lint|format|i18n|translate|locale|asset)\b",
)


@dataclass(frozen=True)
class Decision:
    approved: bool
    risk: str
    confidence: float
    reversible: bool
    requires_double_permission: bool
    autonomous: bool
    rationale: str

    def to_dict(self) -> dict:
        return asdict(self)


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def classify_risk(task: dict, checkpoint: str = "") -> str:
    haystack = f"{task.get('id', '')} {task.get('title', '')} {task.get('role', '')} {checkpoint}"
    for acceptance in task.get("acceptance", []):
        text = acceptance.get("text", "") if isinstance(acceptance, dict) else str(acceptance)
        haystack += f" {text}"

    if _matches(CRITICAL_PATTERNS, haystack):
        return "critical"
    if _matches(HIGH_PATTERNS, haystack):
        return "high"
    if _matches(MEDIUM_PATTERNS, haystack):
        return "medium"
    return "low"


def compute_confidence(task: dict, proofs: list[dict], critic_approved: bool | None = None) -> float:
    if task.get("status") == "done":
        return 0.98

    acceptances = task.get("acceptance") or []
    if acceptances and all(a.get("verified") for a in acceptances if isinstance(a, dict)):
        return 0.96

    if not proofs and critic_approved is None:
        return 0.85

    score = 0.90
    if proofs:
        verified_count = sum(1 for p in proofs if p.get("verified"))
        ratio = verified_count / max(1, len(proofs))
        score = 0.70 + (0.28 * ratio)
    else:
        score = 0.88

    if critic_approved is True:
        score = min(0.99, score + 0.08)
    elif critic_approved is False:
        score = max(0.40, score - 0.35)

    return round(score, 3)


def is_reversible(risk: str, task: dict) -> bool:
    if risk == "critical":
        return False
    title = str(task.get("title", "")).lower()
    if "irreversible" in title or "permanent" in title:
        return False
    return True


def evaluate(task: dict, checkpoint: str = "", proofs: list[dict] | None = None,
             critic_approved: bool | None = None) -> Decision:
    proof_list = proofs or []
    risk = classify_risk(task, checkpoint)
    confidence = compute_confidence(task, proof_list, critic_approved)
    reversible = is_reversible(risk, task)
    double_perm = risk == "critical"

    if risk in ("low", "medium") and confidence >= 0.94 and reversible and critic_approved is not False:
        approved = True
        autonomous = True
        rationale = f"CEO autonomo: approvato per rischio {risk} e confidenza {int(confidence * 100)}%"
    elif risk == "critical":
        approved = False
        autonomous = False
        rationale = "Blocco di sicurezza: azione critica richiedente doppio permesso umano"
    elif risk == "high":
        approved = False
        autonomous = False
        rationale = f"Revisione umana richiesta: rischio {risk} (confidenza {int(confidence * 100)}%)"
    else:
        approved = False
        autonomous = False
        rationale = f"In attesa di verifica: confidenza {int(confidence * 100)}% insufficiente"

    return Decision(
        approved=approved,
        risk=risk,
        confidence=confidence,
        reversible=reversible,
        requires_double_permission=double_perm,
        autonomous=autonomous,
        rationale=rationale,
    )


def enrich_task_kanban(item: dict) -> dict:
    decision = evaluate(item)
    return {
        **item,
        "risk": decision.risk,
        "confidence": decision.confidence,
        "autonomous": decision.autonomous,
        "requires_double_permission": decision.requires_double_permission,
        "rationale": decision.rationale,
    }
