import re
from typing import List

from server.features.autonomous_solver.models import DiagnosticFinding


class LogDiagnosticEngine:
    """
    Analizzatore cross-OS di log (stdout/stderr/exit_code) per Linux, Windows, macOS,
    Python, Bash, PowerShell, SSH e porte seriali.
    Identifica la causa radice e suggerisce una strategia di auto-riparazione mirata.
    """

    def analyze(self, command: str, exit_code: int, stdout: str, stderr: str) -> List[DiagnosticFinding]:
        combined = f"{stderr}\n{stdout}"
        findings: List[DiagnosticFinding] = []

        if exit_code == -1 and "timeout" in combined.lower():
            findings.append(DiagnosticFinding(
                category="timeout",
                root_cause="Il comando ha superato il tempo massimo di esecuzione.",
                suggested_fix_strategy="Aggiungere flag non-interattivi, ridurre l'ambito o aumentare il timeout.",
            ))

        m_py = re.search(r"ModuleNotFoundError:\s+No module named ['\"]([^'\"]+)['\"]", combined)
        if m_py:
            pkg = m_py.group(1).split(".")[0]
            findings.append(DiagnosticFinding(
                category="missing_python_module",
                root_cause=f"Modulo Python mancante: '{pkg}'.",
                suggested_fix_strategy=f"Installare '{pkg}' via pip oppure riscrivere lo script usando solo la libreria standard.",
                extracted_symbol=pkg,
            ))

        m_bin = (
            re.search(r"(?:bash|sh|zsh):\s+(?:line \d+:\s+)?([^\s:]+):\s+command not found", combined)
            or re.search(r"['\"]([^'\"]+)['\"] is not recognized as (?:an internal or external command|the name of a cmdlet)", combined, re.IGNORECASE)
            or re.search(r"No such file or directory:\s*['\"]([^'\"]+)['\"]", combined)
        )
        if m_bin:
            binary = m_bin.group(1)
            findings.append(DiagnosticFinding(
                category="missing_binary",
                root_cause=f"Eseguibile o file non trovato: '{binary}'.",
                suggested_fix_strategy=f"Usare un binario alternativo compatibile con il sistema operativo (es. python3/python) o installare '{binary}'.",
                extracted_symbol=binary,
            ))

        if re.search(r"Permission denied|Access is denied|EACCES|Operation not permitted", combined, re.IGNORECASE):
            findings.append(DiagnosticFinding(
                category="permission_denied",
                root_cause="Permessi insufficienti per eseguire il file o accedere alla risorsa.",
                suggested_fix_strategy="Applicare chmod +x sullo script o usare directory scrivibile / elevazione controllata.",
            ))

        if re.search(r"SyntaxError|IndentationError|NameError|TypeError|ZeroDivisionError|ValueError|KeyError", combined):
            m_err = re.search(r"((?:Syntax|Indentation|Name|Type|ZeroDivision|Value|Key)Error:[^\n]*)", combined)
            err_line = m_err.group(1).strip() if m_err else "Errore nello script generato."
            findings.append(DiagnosticFinding(
                category="script_error",
                root_cause=err_line,
                suggested_fix_strategy="Correggere lo script sorgente sulla base dello stacktrace e rieseguire.",
                extracted_symbol=err_line,
            ))

        if re.search(r"Address already in use|could not open port|Device or resource busy", combined, re.IGNORECASE):
            findings.append(DiagnosticFinding(
                category="resource_busy",
                root_cause="Porta di rete o seriale già occupata da un altro processo.",
                suggested_fix_strategy="Selezionare una porta libera alternativa o attendere il rilascio della risorsa.",
            ))

        if re.search(r"Connection refused|No route to host|Temporary failure in name resolution|Connection timed out|Name or service not known", combined, re.IGNORECASE):
            findings.append(DiagnosticFinding(
                category="network_error",
                root_cause="Errore di connettività di rete verso l'host target.",
                suggested_fix_strategy="Verificare host/porta, provare metodo di connessione alternativo o timeout più ampio.",
            ))

        if not findings and exit_code != 0:
            snippet = (stderr.strip() or stdout.strip() or f"exit code {exit_code}")[-240:]
            findings.append(DiagnosticFinding(
                category="command_failed",
                root_cause=f"Comando '{command}' fallito (exit={exit_code}): {snippet}",
                suggested_fix_strategy="Analizzare l'output completo, aggiornare lo script o il comando e riprovare.",
            ))

        return findings


log_diagnostic_engine = LogDiagnosticEngine()
