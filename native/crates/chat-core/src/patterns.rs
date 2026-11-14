pub const PATTERNS: &[(&str, &str)] = &[
    (
        "weather",
        r"\b(meteo|prevision[ei]|piover[àa]|piove|nevicher[àa]|nevica|temperatura (fuori|esterna)|(che|com'?[eè]|come sar[àa]|com'?era) (il )?tempo|tempo (fa|far[àa]|c'?[èe]|ci sar[àa])|(bel|brutto|cattivo) tempo|tempo (per )?(oggi|domani|dopodomani|stasera|stanotte|nel (fine settimana|weekend))|serve l'?ombrello|prendo l'?ombrello|quanti gradi (fa|far[àa]|ci sono fuori)|far[àa] (freddo|caldo)|fa (freddo|caldo) fuori|weather|forecast)\b",
    ),
    (
        "music",
        r"\b(che canzone|che brano|chi canta|come si chiama (questa|la) canzone|cosa (sto|stiamo) ascoltando|che musica [èe]|cosa sta suonando)\b",
    ),
    (
        "study",
        r"\b(cosa stai studiando|stai studiando|cosa (hai|stai) (studiato|imparando|imparato)|i tuoi studi|come vanno (i tuoi )?studi)\b",
    ),
    (
        "brain",
        r"\b(cervello|neuroni|la tua (mente|memoria)|mostrami (la )?(mente|memoria)|cosa ricordi)\b",
    ),
    (
        "system",
        r"\b(stato (del |dei )?sistem[ai]|diagnostica|come stanno i sistemi|risorse del sistema|stato di salute)\b",
    ),
    (
        "camera",
        r"\b(abilita|attiva|accendi|apri|avvia|metti|mostra(?:mi)?|fammi vedere|chiudi|disattiva|spegni|nascondi|ferma)\b[^.?!]*\b(web\s?cam|fotocamera)\b",
    ),
    (
        "vision",
        r"\b(chi (vedi|c'[eè]|hai davanti)|mi vedi|mi riconosci|chi sono( io)?|cosa vedi)\b",
    ),
    (
        "network",
        r"\b(scansiona (la )?rete|dispositivi (in|della|nella|di) rete|chi (è|e') connesso|cosa c'?[èe] in rete|rete di casa|dispositivi connessi)\b",
    ),
    (
        "place",
        r"\b(abito|vivo|mi trovo|ci troviamo|siamo|la casa [èe]|la mia casa [èe])\s+(a|ad|in)\s+[A-Za-zÀ-ÿ']|\b(dove (sei|siamo|ti trovi|ci troviamo)|qual [èe] la (tua|nostra) posizione)\b",
    ),
    (
        "person_info",
        r"\b(?:quanti anni (?:ho|ha\b|abbiamo)|sai quanti anni|mi sai dire quanti anni|che et[àa] ho|qual [èe] la mia et[àa]|quando (?:sono nato|compio gli anni|compie gli anni|[èe] il mio compleanno|[èe] nata?)|data di nascita|mio compleanno|compleanno di \w+|cosa sai di me|cosa ricordi di me|cosa ti ricordi di me|il mio profilo|la mia scheda|che lavoro faccio|qual [èe] il mio lavoro|lavoro come \w+|cosa mi piace|le mie preferenze|il mio piatto preferito|ho \d{1,3} anni|compio \d{1,3} anni|ricordati che ho \d{1,3} anni|appunta che ho \d{1,3} anni|appunta che (?:sono|faccio|il mio|mi piace|ho)|ricordati che (?:sono|faccio|il mio|mi piace)|segna nel (?:mio )?profilo|il mio compleanno [èe]|sono nat[oa] il)\b",
    ),
    ("introduce", r"\b(mi chiamo|il mio nome [èe]|chiamami)\s+\w"),
    (
        "voices",
        r"\b(?:(?:scarica|installa|aggiungi|prendi|procurati|impara)(?:ti)?\s+(?:la\s+|una\s+|le\s+)?voc[ei]|(?:che|quali)\s+(?:voci|lingue)\s+(?:hai|parli|conosci|sai)|in\s+che\s+lingue\s+(?:parli|sai)|download\s+(?:the\s+|a\s+)?\w*\s*voice|which\s+languages\s+(?:do\s+you|can\s+you))\b",
    ),
    (
        "ask_evidence",
        r"\b(?:corriere|fattorino|chi [èe] passat[oa]|com'?era vestit[oa]|passat[oa] (?:un|una|qualcun|il|la)|a che ora [èe] venut[oa]|quando [èe] venut[oa]|(?:chi c'era|chi era)\s+(?:al|alla|davanti|in|nel|sul|fuori|ieri|stamattina|oggi)|did you see|who passed|what time did)\b",
    ),
    (
        "rescue",
        r"\b(?:stato (?:di |dei |del )?(?:soccorso|soccorsi|emergenza|emergenze|allarme|allarmi)|ci sono emergenze|qualcuno [èe] in pericolo|allarme attivo|situazione di emergenza|rescue status|emergency status)\b",
    ),
    (
        "matter",
        r"\b(?:matter|stato matter|dispositivi matter|nodi matter|bridge matter|protocollo matter|matter status|matter devices)\b",
    ),
    (
        "time",
        r"\b(che ore sono|che ora [èe]|che giorno [èe]|che data [èe])\b",
    ),
];
