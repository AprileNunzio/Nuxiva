export const ZONES = [
  { id: "home", title: "Dashboard", glyph: "⬡", group: "Inizia",
    lead: "Centro di controllo neurale, telemetria in tempo reale, velocità e consumi." },
  { id: "widgets", title: "Widget", glyph: "▣", group: "Inizia",
    lead: "Gestione consumi, stato e proiezione su schermo dei widget." },
  { id: "brain", title: "Cervello", glyph: "◈", group: "Intelligenza",
    lead: "Chi pensa, cosa ricorda e cosa sta imparando Nuxiva.",
    sections: [["models", "Cervello e modelli"], ["f/mind", "Mente"], ["study", "Studio autonomo"]] },
  { id: "flows", title: "Flussi", glyph: "⟁", group: "Intelligenza",
    lead: "Come ragiona Nuxiva, passo per passo, e quali algoritmi usa.",
    sections: [["models", "Catene di cervelli"], ["skills", "Algoritmi"]] },
  { id: "tools", title: "Strumenti", glyph: "▦", group: "Intelligenza",
    lead: "Tutti gli strumenti e le abilità di Nuxiva in un solo posto." },
  { id: "trust", title: "Regole e Fiducia", glyph: "⚖", group: "Protezione",
    lead: "Cosa Nuxiva può fare da sola e cosa deve chiederti prima.",
    sections: [["laws", "Leggi"], ["autonomy", "Autonomia"], ["capabilities", "Capacità"]] },
  { id: "network", title: "Rete e Sicurezza", glyph: "⌬", group: "Protezione",
    lead: "Porte, connessioni, firewall e dispositivi della tua rete.",
    sections: [["firewall", "Firewall"], ["vpn", "VPN"], ["network", "Rete Locale"], ["shares", "Cartella condivisa"]] },
  { id: "system", title: "Sistema", glyph: "⚙", group: "Macchina",
    lead: "Pacchetti, risorse fisiche della macchina, satelliti e nodi cluster.",
    sections: [["overview", "Panoramica"], ["packages", "Pacchetti"], ["steps", "Installazione"], ["config", "Configurazione"], ["updates", "Aggiornamenti"], ["nodes", "Nodi e server"]] },
  { id: "observatory", title: "Osservatorio", glyph: "◷", group: "Macchina",
    lead: "Telemetria eventi storici, diagnostica e log del kernel.",
    sections: [["logs", "Log"], ["events", "Eventi"]] },
  { id: "awakening", title: "Configurazione Iniziale", glyph: "✦", group: "Inizia", accent: true,
    lead: "Procedura guidata iniziale per configurare Nuxiva (facoltativa)." },
];

export const GROUPS = ["Inizia", "Intelligenza", "Protezione", "Macchina"];

export const zone = (id) => ZONES.find((z) => z.id === id);
