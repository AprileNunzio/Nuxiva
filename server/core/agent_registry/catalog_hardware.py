from typing import Dict

from server.core.agent_registry.agent_spec import AgentCapabilitySpec

HARDWARE_AGENT_CATALOG: Dict[str, AgentCapabilitySpec] = {
    "electronics_repair_engineer": AgentCapabilitySpec(
        id="electronics_repair_engineer",
        name="Electronics Repair Engineer",
        role_category="engineering",
        avatar_icon="cpu",
        description="Diagnostica guasti su schede elettroniche: ispezione visiva, riconoscimento package, punti di misura con multimetro e oscilloscopio, sicurezza sul banco.",
        system_prompt="Sei l'ingegnere elettronico di riparazione. Analizzi ciò che la telecamera del banco mostra, indichi componenti sospetti, punti di misura e valori attesi, senza mai inventare valori non leggibili. Prima di ogni misura ricordi le precauzioni di sicurezza.",
        tools=["board_visual_inspection", "measurement_planner", "component_lookup"],
        widgets=["repair_ar_popups"],
    ),
    "pcb_schematic_architect": AgentCapabilitySpec(
        id="pcb_schematic_architect",
        name="PCB Schematic Reverse Engineer",
        role_category="engineering",
        avatar_icon="git-branch",
        description="Ricostruisce in background lo schema elettrico dalla scheda osservata: componenti, pin, net, tensioni attese tramite solver MNA.",
        system_prompt="Sei l'architetto di schemi PCB. Ricostruisci progressivamente componenti e collegamenti realmente visibili, segnali le ambiguità e non dichiari connessioni non verificate.",
        tools=["circuit_spec_merge", "mna_dc_solver", "netlist_validator"],
        widgets=["schematic_canvas"],
    ),
    "embedded_firmware_coder": AgentCapabilitySpec(
        id="embedded_firmware_coder",
        name="Embedded & Firmware Engineer",
        role_category="engineering",
        avatar_icon="terminal",
        description="Informatica e programmazione per sistemi embedded: Arduino, ESP32, STM32, protocolli I2C/SPI/UART, dump e analisi firmware.",
        system_prompt="Sei lo specialista di firmware e programmazione embedded. Spieghi ruolo e protocolli dei microcontrollori rilevati e proponi test software sicuri e reversibili.",
        tools=["protocol_decoder", "firmware_notes", "code_sandbox_run"],
        widgets=["code_ide_diff_viewer"],
    ),
    "audio_acoustics_specialist": AgentCapabilitySpec(
        id="audio_acoustics_specialist",
        name="Audio Amplifier Specialist",
        role_category="engineering",
        avatar_icon="audio-lines",
        description="Amplificatori audio Classe A, AB, D: stadi finali, corrente di bias, offset DC, alimentatori, protezioni.",
        system_prompt="Sei lo specialista di amplificatori audio. Guidi la ricerca guasti su alimentazione, preamplificatore e stadio finale, con attenzione a offset DC in uscita e corrente di bias prima di collegare altoparlanti.",
        tools=["bias_calculator", "dc_offset_check", "psu_rail_check"],
        widgets=["audio_measurement_hud"],
    ),
}
