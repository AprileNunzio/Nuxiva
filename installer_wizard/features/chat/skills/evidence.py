def ask_evidence_skill(text: str) -> tuple[str, dict]:
    from features.sentinel.ask import ask_engine
    result = ask_engine.ask(text)
    summary = result.get("summary", "Nessuna informazione disponibile.")
    ui = {
        "mode": "evidence",
        "found": result.get("found", False),
        "citations": result.get("citations", []),
        "scanned": result.get("scanned", 0),
        "matched_count": result.get("matched_count", 0),
    }
    return summary, ui
