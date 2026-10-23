import re

from config import env_get
from identity import assistant_name, self_line

from features.chat import context as request_context
from features.people import identity

def _self_vocative_re() -> re.Pattern:
    assist_name = assistant_name()
    if assist_name.lower() == "nuxiva":
        return re.compile(r"([,!]\s*|^)(?:A\.\s?T\.\s?E\.\s?N\.\s?A\.?|Nuxiva)(?=\s*[!?.,;:]|\s*$)", re.I)
    return re.compile(rf"([,!]\s*|^)(?:{re.escape(assist_name)}|Nuxiva)(?=\s*[!?.,;:]|\s*$)", re.I)


def name() -> str:
    profile = identity.current(request_context.voice.get())
    if profile:
        return identity.first_name(profile)
    return env_get("NUXIVA_USER_NAME", "").strip().split(" ")[0]


def instruction() -> str:
    who = name()
    assist_name = assistant_name()
    if assist_name.lower() != "nuxiva":
        base = f"Tu sei {assist_name}. {self_line()} Non chiamarti mai Nuxiva."
    else:
        base = (f"Tu sei Nuxiva (NUXIVA), l'assistente. {self_line()} La persona che ti parla NON si chiama Nuxiva: "
                "non chiamarla mai «Nuxiva» o «NUXIVA».")
    if who:
        return f"{base} Stai parlando con {who}: chiamalo {who} oppure «signore»."
    return f"{base} Non conosci ancora il suo nome: chiamalo «signore»."


def fix_address(reply: str) -> str:
    if not reply:
        return reply
    who = name()

    def swap(m: re.Match) -> str:
        lead = m.group(1)
        if who:
            return f"{lead}{who}"
        return "" if lead.strip() in (",", "") else lead.strip()

    return _self_vocative_re().sub(swap, reply)
