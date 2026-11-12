def rescue_skill() -> tuple[str, dict]:
    try:
        from agenti.rescue.coordinator import coordinator
        st = coordinator.status()
        stage = st.get("stage", "calm")
        hazard = st.get("hazard")
        if stage == "calm":
            speech = "Tutto tranquillo, nessun allarme o situazione di emergenza attiva."
        else:
            hazard_txt = f" ({hazard})" if hazard else ""
            speech = f"Attenzione: stato di soccorso {stage}{hazard_txt} in corso."
        ui = {
            "mode": "rescue",
            "stage": stage,
            "hazard": hazard,
            "deadline": st.get("deadline"),
            "incident": st.get("incident", 0),
        }
        return speech, ui
    except Exception:
        return "Stato di soccorso non disponibile.", {"mode": "rescue", "error": True}
