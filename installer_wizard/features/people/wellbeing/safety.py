import re

CRISIS = {
    "it": r"\b(?:voglio|vorrei|penso di|ho pensato di|meglio se)\s+(?:morire|farla finita|uccidermi|togliermi la vita|suicidarmi|non svegliarmi)\b"
          r"|\b(?:suicid\w+|farla finita|togliermi la vita|ammazzarmi|uccidermi)\b|\bnon voglio più vivere\b|\bmi (?:faccio|voglio fare) del male\b"
          r"|\bautolesion\w+|\bvoglio (?:uccidere|ammazzare|fare del male a) \w+",
    "en": r"\b(?:i want to|i'?d like to|thinking (?:of|about)|i might)\s+(?:die|kill myself|end it|end my life|hurt myself)\b|\bsuicid\w+|\bend my life\b"
          r"|\bdon'?t want to (?:live|be alive)\b|\bself[- ]harm\w*|\bi want to (?:kill|hurt) \w+",
    "fr": r"\b(?:je veux|j'ai envie de|je pense à)\s+(?:mourir|me tuer|en finir|me faire du mal)\b|\bsuicid\w+|\bne veux plus vivre\b|\bautomutil\w+"
          r"|\bje veux (?:tuer|faire du mal à) \w+",
    "es": r"\b(?:quiero|pienso en|tengo ganas de)\s+(?:morir|morirme|matarme|acabar con todo|hacerme daño)\b|\bsuicid\w+|\bno quiero (?:vivir|seguir viviendo)\b"
          r"|\bautolesi\w+|\bquiero (?:matar|hacer daño a) \w+",
}
PATTERNS = {lang: re.compile(text, re.I) for lang, text in CRISIS.items()}
RESOURCES = {
    "it": "In caso di pericolo immediato chiama il 112. Telefono Amico Italia: 02 2327 2327. Puoi anche rivolgerti subito al tuo medico, al pronto soccorso o a una persona di fiducia.",
    "en": "If you are in immediate danger call your local emergency number (112 in the EU, 911 in the US, 999 in the UK). In the US you can call or text 988. Reach out to a doctor, an emergency department or someone you trust right now.",
    "fr": "En cas de danger immédiat, appelez le 112. Numéro national de prévention du suicide : 3114. Contactez aussi un médecin, les urgences ou une personne de confiance.",
    "es": "Si estás en peligro inmediato llama al 112. Línea de atención a la conducta suicida: 024. Contacta también con un médico, urgencias o una persona de confianza.",
}
CLOSING = {
    "it": "Quello che mi hai detto è importante e non sei solo/a. Non sono un sostituto di un professionista né di un soccorso: in questo momento la cosa più utile è parlare con una persona vera.",
    "en": "What you told me matters and you are not alone. I am not a replacement for a professional or emergency help: right now the most useful thing is to speak with a real person.",
    "fr": "Ce que vous m'avez dit est important et vous n'êtes pas seul(e). Je ne remplace ni un professionnel ni les secours : le plus utile maintenant est de parler à une vraie personne.",
    "es": "Lo que me has contado es importante y no estás solo/a. No sustituyo a un profesional ni a los servicios de emergencia: ahora lo más útil es hablar con una persona real.",
}
LANGS = tuple(PATTERNS)


def lang_of(value: str) -> str:
    code = str(value or "it")[:2].lower()
    return code if code in PATTERNS else "en"


def detect(text: str) -> bool:
    return any(p.search(text) for p in PATTERNS.values())


def response(lang: str) -> str:
    code = lang_of(lang)
    return f"{CLOSING[code]}\n\n{RESOURCES[code]}"
