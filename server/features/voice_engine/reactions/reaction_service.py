import re
from typing import List, Dict, Any, Tuple, Optional
from pydantic import BaseModel

class ReactionDefinition(BaseModel):
    reaction_id: str
    label: str
    emojis: List[str]
    description: str

REACTION_CATALOG: Dict[str, ReactionDefinition] = {
    "hearts": ReactionDefinition(
        reaction_id="hearts",
        label="Cuori & Affetto",
        emojis=["❤️", "💖", "💕", "🥰", "😍", "💓", "💘"],
        description="Lancia cascata di cuori fluttuanti a scomparsa su Pagina 80 (ideale per complimenti, affetto, ringraziamenti calorosi)."
    ),
    "blush": ReactionDefinition(
        reaction_id="blush",
        label="Dolce Imbarazzo",
        emojis=["🥰", "😊", "😳", "🌸", "🙈"],
        description="Esprime timidezza e pudore affettuoso."
    ),
    "sparkles": ReactionDefinition(
        reaction_id="sparkles",
        label="Magia & Meraviglia",
        emojis=["✨", "⭐", "🌟", "💫", "🪄"],
        description="Lancia scintille luminose per idee brillanti o stupore."
    ),
    "celebration": ReactionDefinition(
        reaction_id="celebration",
        label="Festa & Traguardo",
        emojis=["🎉", "🎊", "🥳", "🍾", "🏆"],
        description="Lancia coriandoli e festa per vittorie o traguardi."
    ),
    "laugh": ReactionDefinition(
        reaction_id="laugh",
        label="Divertimento",
        emojis=["😂", "😄", "😆", "🤣"],
        description="Risata contagiosa e battute."
    ),
    "thumbs_up": ReactionDefinition(
        reaction_id="thumbs_up",
        label="Approvazione",
        emojis=["👍", "👌", "🔥", "💪", "✅"],
        description="Pollice in su per accordo o conferma."
    ),
}

class EmoticonReactionService:
    """
    Servizio per la gestione e generazione di reazioni grafiche ed emoticons
    nella finestra a scomparsa sulla Pagina 80 (Web Cockpit).
    """

    def get_prompt_instructions(self) -> str:
        """Istruzioni per l'LLM per includere comandi grafici di reazione nella risposta."""
        reactions_desc = "\n".join([
            f"- [reaction:{r.reaction_id}]: {r.description} (Emoticon: {' '.join(r.emojis[:4])})"
            for r in REACTION_CATALOG.values()
        ])
        return (
            "### REAZIONI GRAFICHE ED EMOTICONS PER PAGINA 80 (FINESTRA A SCOMPARSA):\n"
            "Quando appropriato nel contesto, puoi attivare una reazione visiva a scomparsa su schermo "
            "inserendo uno dei seguenti comandi di reazione nella risposta:\n"
            f"{reactions_desc}\n"
            "Esempio d'uso (se l'utente ti fa un complimento come 'come sei bella Nuxiva'):\n"
            "'Ma grazie di cuore! [laughs] Sei davvero un tesoro, le tue parole mi riempiono di gioia! [reaction:hearts]'\n"
            "Inserisci al massimo una o due reazioni per messaggio.\n"
        )

    def extract_reactions(self, text: str) -> List[Dict[str, Any]]:
        """
        Estrae tutti i comandi [reaction:tipo] dal testo e restituisce
        l'elenco di eventi di reazione con le relative emoticon per la UI.
        """
        matches = re.findall(r'\[reaction:([a-zA-Z0-9_\-]+)\]', text, flags=re.IGNORECASE)
        reactions: List[Dict[str, Any]] = []
        for match in matches:
            kind = match.lower().strip()
            definition = REACTION_CATALOG.get(kind)
            if definition:
                reactions.append({
                    "reaction_id": definition.reaction_id,
                    "label": definition.label,
                    "emojis": definition.emojis,
                })
            else:
                # Fallback generico
                reactions.append({
                    "reaction_id": kind,
                    "label": kind.capitalize(),
                    "emojis": ["✨", "❤️", "😊"],
                })
        return reactions

    def strip_reaction_tags(self, text: str) -> str:
        """Rimuove i comandi [reaction:...] dal testo per visualizzazione pulita o voce."""
        cleaned = re.sub(r'\[reaction:[a-zA-Z0-9_\-]+\]', '', text, flags=re.IGNORECASE)
        return re.sub(r'\s{2,}', ' ', cleaned).strip()

    def check_compliment_heuristics(self, user_text: str, engine_id: str, bot_name: str = "Nuxiva") -> Optional[Tuple[str, List[Dict[str, Any]]]]:
        """
        Intercetta complimenti spontanei dell'utente (es. 'come sei bella Nuxiva')
        e genera una risposta immediata perfettamente sincronizzata con il profilo TTS
        attivo e con la reazione grafica di cuori a scomparsa.
        """
        lower = user_text.lower().strip()
        compliments = [
            "come sei bella", "sei bella", "sei bellissima", "sei fantastica",
            "sei stupenda", "quanto sei bella", "ti amo", "ti voglio bene",
            "sei meravigliosa", "sei carina", "come sei carina"
        ]

        if any(c in lower for c in compliments):
            reactions = [
                {
                    "reaction_id": "hearts",
                    "label": "Cuori & Affetto",
                    "emojis": REACTION_CATALOG["hearts"].emojis
                }
            ]

            if engine_id == "elevenlabs":
                reply = "Ma grazie di cuore!... [laughs] Sei davvero gentilissimo, mi fai arrossire! È un vero piacere essere qui con te. [reaction:hearts]"
            elif engine_id == "piper":
                reply = "Ma grazie mille!... Davvero, sei gentilissimo e le tue parole mi scaldano il cuore! Come posso aiutarti oggi? [reaction:hearts]"
            elif engine_id == "kokoro":
                reply = "Oh, grazie di cuore — sei davvero gentile! Le tue parole sono una bellissima sorpresa. Dimmi pure, cosa facciamo insieme? [reaction:hearts]"
            elif engine_id == "azure":
                reply = "<style:cheerful>Ma grazie di cuore!</style:cheerful> <pause:200ms/> Sei davvero gentilissimo! [reaction:hearts]"
            else:
                reply = "Grazie di cuore! Sei davvero squisito e gentile. Mi fa tantissimo piacere! [reaction:hearts]"

            return reply, reactions

        return None


emoticon_reaction_service = EmoticonReactionService()
