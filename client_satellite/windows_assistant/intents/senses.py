import re

SCREEN = re.compile(r"\b(scherm|finestr|document|questo test|questa (?:pagina|mail|email|tabella|slide|foto)|"
                    r"questo (?:codice|errore|file|disegno|progetto|foglio)|sto (?:scrivendo|leggendo|guardando|"
                    r"lavorando)|cosa vedi|leggi|riassum|correggi|migliora|riformula|tradu|screen|this (?:page|"
                    r"document|code|error)|what.*see|écran|cette page|ce document)", re.I)
WEBCAM = re.compile(r"\b(guardami|mi vedi|webcam|telecamera|fotocamera|come (?:sto|sono vestit)|cosa ho in mano|"
                    r"cosa (?:ti )?mostro|look at me|can you see me|camera|what am i holding|regarde-moi|"
                    r"mírame|mirame)", re.I)


def asks_screen(text: str) -> bool:
    return bool(SCREEN.search(text or ""))


def asks_webcam(text: str) -> bool:
    return bool(WEBCAM.search(text or ""))
