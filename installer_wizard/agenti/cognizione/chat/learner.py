from dataclasses import dataclass
import re


@dataclass(frozen=True)
class LearnedEntity:
    category: str
    entity: str
    details: str
    confidence: float


NAME_PATTERNS = (
    re.compile(r"\b(?:mi chiamo|chiamami|il mio nome è)\s+([A-ZÀ-ÿa-z]+)\b", re.IGNORECASE),
    re.compile(r"\b(?:sono|io sono)\s+([A-ZÀ-ÿ][a-z]+)\b"),
    re.compile(r"\b(?:my name is|i am|i'm|call me)\s+([A-Z][a-z]+)\b", re.IGNORECASE),
    re.compile(r"\b(?:me llamo|mi nombre es|soy)\s+([A-ZÀ-ÿ][a-z]+)\b", re.IGNORECASE),
    re.compile(r"\b(?:je m'appelle|mon nom est|je suis)\s+([A-ZÀ-ÿ][a-z]+)\b", re.IGNORECASE),
)

INTEREST_PATTERNS = (
    re.compile(r"\b(?:tifo|tifoso del(?:la)?|tifosa del(?:la)?|fan di|seguo|passione per|amo)\s+([A-ZÀ-ÿa-z0-9\s]{2,30}?)(?=[.,;!?]|$|\be\b|\bma\b)", re.IGNORECASE),
    re.compile(r"\b(?:i love|i support|fan of|passionate about|interested in)\s+([A-Za-z0-9\s]{2,30}?)(?=[.,;!?]|$|\band\b)", re.IGNORECASE),
    re.compile(r"\b(?:apoyo a|hincha de|me apasiona|fan de|sigo a)\s+([A-ZÀ-ÿa-z0-9\s]{2,30}?)(?=[.,;!?]|$|\by\b)", re.IGNORECASE),
    re.compile(r"\b(?:je supporte|fan de|passionné de|passionnée de)\s+([A-ZÀ-ÿa-z0-9\s]{2,30}?)(?=[.,;!?]|$|\bet\b)", re.IGNORECASE),
)

DESIRE_PATTERNS = (
    re.compile(r"\b(?:vorrei|voglio|desidero|intenzione di|obiettivo è|puntiamo a)\s+([A-ZÀ-ÿa-z0-9\s]{2,40}?)(?=[.,;!?]|$)", re.IGNORECASE),
    re.compile(r"\b(?:i want to|i'd like to|i wish to|goal is to|aiming to)\s+([A-Za-z0-9\s]{2,40}?)(?=[.,;!?]|$)", re.IGNORECASE),
    re.compile(r"\b(?:quisiera|quiero|deseo|mi objetivo es)\s+([A-ZÀ-ÿa-z0-9\s]{2,40}?)(?=[.,;!?]|$)", re.IGNORECASE),
    re.compile(r"\b(?:je voudrais|je veux|mon objectif est)\s+([A-ZÀ-ÿa-z0-9\s]{2,40}?)(?=[.,;!?]|$)", re.IGNORECASE),
)

TECH_PATTERNS = (
    re.compile(r"\b(?:lavoro (?:come|su|in)|sviluppo in|programmo in|sono un dev|sviluppatore)\s+([A-ZÀ-ÿa-z0-9\s]{2,30}?)(?=[.,;!?]|$)", re.IGNORECASE),
    re.compile(r"\b(?:i work (?:as|on|in)|i develop in|i code in|software engineer)\s+([A-Za-z0-9\s]{2,30}?)(?=[.,;!?]|$)", re.IGNORECASE),
    re.compile(r"\b(?:trabajo (?:como|en)|desarrollo en|programo en)\s+([A-ZÀ-ÿa-z0-9\s]{2,30}?)(?=[.,;!?]|$)", re.IGNORECASE),
    re.compile(r"\b(?:je travaille (?:comme|sur|en)|je développe en)\s+([A-ZÀ-ÿa-z0-9\s]{2,30}?)(?=[.,;!?]|$) ", re.IGNORECASE),
)

EXECUTIVE_INDICATORS = (
    re.compile(r"\b(?:direttive|priorità|briefing|kpi|milestone|budget|roadmap|relazione|rapporto)\b", re.IGNORECASE),
    re.compile(r"\b(?:status report|executive|metrics|deadlines|deliverables)\b", re.IGNORECASE),
)

CASUAL_INDICATORS = (
    re.compile(r"\b(?:ciao|ehi|we|amico|scherzo|chiacchiere|relax|tempo libero)\b", re.IGNORECASE),
    re.compile(r"\b(?:hey|mate|dude|chilling|casual)\b", re.IGNORECASE),
)


def _clean_entity(val: str) -> str:
    cleaned = re.sub(r"^(?:il|lo|la|i|gli|le|l'|un|una|uno|the|a|an|el|los|las|les)\s+", "", val.strip(), flags=re.IGNORECASE)
    return cleaned.strip()


class AutonomousLearner:
    def extract_name(self, text: str) -> str | None:
        for pat in NAME_PATTERNS:
            m = pat.search(text)
            if m:
                val = m.group(1).strip()
                if len(val) >= 2 and not val.lower() in ("un", "una", "qui", "lì", "non", "del", "di"):
                    return val.capitalize()
        return None

    def extract_entities(self, text: str) -> list[LearnedEntity]:
        entities: list[LearnedEntity] = []
        for pat in INTEREST_PATTERNS:
            for m in pat.finditer(text):
                val = _clean_entity(m.group(1))
                if len(val) >= 2:
                    entities.append(LearnedEntity(category="interest", entity=val, details=m.group(0), confidence=0.85))
        for pat in DESIRE_PATTERNS:
            for m in pat.finditer(text):
                val = _clean_entity(m.group(1))
                if len(val) >= 2:
                    entities.append(LearnedEntity(category="desire", entity=val, details=m.group(0), confidence=0.80))
        for pat in TECH_PATTERNS:
            for m in pat.finditer(text):
                val = _clean_entity(m.group(1))
                if len(val) >= 2:
                    entities.append(LearnedEntity(category="technology", entity=val, details=m.group(0), confidence=0.90))
        return entities

    def detect_style(self, text: str) -> str:
        for pat in EXECUTIVE_INDICATORS:
            if pat.search(text):
                return "executive"
        for pat in CASUAL_INDICATORS:
            if pat.search(text):
                return "conversational"
        return "balanced"

    def analyze(self, text: str) -> tuple[str | None, list[LearnedEntity], str]:
        name = self.extract_name(text)
        entities = self.extract_entities(text)
        style = self.detect_style(text)
        return name, entities, style


autonomous_learner = AutonomousLearner()
