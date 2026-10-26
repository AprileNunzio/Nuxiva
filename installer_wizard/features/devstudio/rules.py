RULES = (
    "1. Architettura: Clean Architecture, Separation of Concerns e Single Responsibility Principle; ogni file ha una sola responsabilità.\n"
    "2. Purezza: solo codice puro, mai commenti né docblock dentro il codice.\n"
    "3. Nessun file oltre 500 righe: se serve di più, dividi in più file.\n"
    "4. Interfaccia totalmente responsive (mobile e desktop), multilingua: nessun testo scritto nel codice, solo chiavi di traduzione "
    "con file di lingua separati (it ed en come minimo).\n"
    "5. Sicurezza Zero-Trust e OWASP: valida e sanifica ogni input, escape di ogni output, query preparate, protezione CSRF, "
    "intestazioni di sicurezza, sessioni con cookie HttpOnly/Secure/SameSite, password con hash moderno, dati sensibili cifrati, segreti mai nel codice.\n"
    "6. Errori: gestione globale degli errori, try/catch solo nei punti di integrazione (I/O, rete, database), mai eccezioni ignorate in silenzio.\n"
    "7. Organizzazione per funzionalità: ogni pagina o modulo in una cartella dedicata con vista, logica, stili e interfacce propri."
)

COMMENT_MARKERS = {
    ".js": ("//", "/*", "*/"), ".mjs": ("//", "/*", "*/"), ".ts": ("//", "/*", "*/"), ".tsx": ("//", "/*", "*/"),
    ".php": ("//", "/*", "*/", "#"), ".css": ("/*", "*/"), ".py": ("#",), ".html": ("<!--",), ".phtml": ("<!--", "//", "/*"),
}
