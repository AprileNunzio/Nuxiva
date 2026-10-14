# NUXIVA - Neural Unified eXperience for Interactive Vision & Automation

[🇬🇧 English](README.md) | [🇮🇹 Italiano](README_IT.md) | [🇫🇷 Français](README_FR.md)

## 🚀 Novità nella Versione 4.1.53 (Neuro-Core 5.0, Omni-Cortical Engine 6.5 & Architettura Dinamica Universale)

Nuxiva introduce un salto generazionale nei sistemi operativi per l'intelligenza artificiale distribuita, unendo architetture neuro-cognitive biologiche, calcolo nativo ad altissime prestazioni in Rust, auto-discovery dinamico universale e autonomia spaziale zero-trust:

- **Omni-Cortical Engine 6.5 & 6 Motori di Ragionamento Modulari**: Completo disaccoppiamento architetturale guidato dall'Open/Closed Principle con rilevamento dinamico tramite `EngineScanner`. Include sei distinti motori cognitivi:
  1. `nuxiva-4.2-legacy`: *Legacy Chain-Sync* (pipeline sequenziale a token con fallback seriale, SLA 2500ms).
  2. `nuxiva-5.0-veloce`: *Veloce Synapse-Flash* (Ternary 1.58-bit con Liquid LNN e bus spiking zero-copy, SLA 25ms).
  3. `nuxiva-5.0-empatico`: *Empatico Synapse-Limbic* (Global Workspace a 8 corsie parallele con fusione biometrica a 10Hz, SLA 120ms).
  4. `nuxiva-6.0-pro`: *Pro Omni-Latent* (Spazio Latente Continuo JEPA/Coconut con plasticità TTT live in VRAM, SLA 15ms).
  5. `nuxiva-6.5-ultra`: *Ultra DeepThink-MCTS* (MCTS latente a 64 rami con Process Reward Model dopaminergico, SLA 650ms).
  6. `nuxiva-6.5-auto` (Predefinito): *Auto Thalamic-Adaptive* (Meta-orchestratore talamico basato su principio di energia libera $\psi$ e carico hardware, SLA 45ms).
- **Dinamica Neurale Spiking LIF & Plasticità Ebbiana STDP**: Nucleo Spiking Neural Network (`native/crates/bus-core/src/spike.rs` e `installer_wizard/features/brain/components.py`) che modella il decadimento del potenziale di membrana ($\tau_m$), periodi refrattari dinamici, soglie di sparo modulate dal sistema limbico e plasticità sinaptica Hebbiana STDP ($A^+$, $A^-$, $\tau_{\text{stdp}}$) rinforzata da segnali dopaminergici.
- **Modulatore Limbico a 7 Assi e Binding Sensoriale-Limbico in Tempo Reale**: Vettore emotivo continuo a 7 dimensioni (Valenza, Arousal, Dominanza, Dopamina, Noradrenalina, Serotonina, Cortisolo). Il binding sensoriale acquisisce in tempo reale lo stress acustico vocale (Ear/Voiceprint), la pressione ambientale e la valenza facciale (Scene/Fusion) e la presenza biometrica (People/Presence), pubblicando eventi `biometrics.*` sul bus di sistema `nuxiva_bus`. Il cortisolo restringe i budget di rami cognitivi in caso di emergenza, mentre la dopamina stimola l'esplorazione creativa.
- **Global Neuronal Workspace (GNW) e Inibizione Laterale GABAergica**: Parallelismo speculativo multiramo in `brain_chain.py`. Quando un'ipotesi cognitiva raggiunge la soglia di accensione (ignition threshold), innesca un'inibizione laterale GABAergica immediata che cancella i rami concorrenti più lenti in microsecondi. Include ricerca Monte Carlo Tree Search (MCTS) valutata rispetto al critico predittivo del Simulatore Twin (`predict_user_impact`).
- **Default Mode Network (DMN) e Consolidamento Sinaptico Notturno del Sonno REM**:
  - *Default Mode Network (`backend/loops.py`)*: Ciclo di riflessione autonoma in background attivato dopo 10 minuti di inattività dell'utente per consolidare le memorie a lungo termine e formulare azioni proattive di foresight. Le interazioni in chat resettano immediatamente il timer.
  - *Consolidamento Sinaptico Notturno (`vision/nightly.py` e `soup/trainer.py`)*: Ciclo REM che applica decadimento, potatura (pruning) e stabilizzazione controllata dei pesi sinaptici STDP diurni in `brain/assignments.py`, contrastando la curva dell'oblio di Ebbinghaus.
- **Scanner Dinamico Universale con Motore Nativo Rust (`bus-core`)**:
  - `FastScanner` nativo in Rust esposto via PyO3 con hashing ultraveloce FNV-1a, scansione parallela delle cartelle e rilevamento istantaneo delle modifiche tramite metadati.
  - `UniversalScanner` generico con validazione di sicurezza Zero-Trust dell'albero sintattico (AST) per intercettare import e chiamate non sicure prima del caricamento, unito a `DirectoryWatcher` basato su eventi per il ricaricamento a caldo.
  - Auto-discovery automatico delle rotte API (`FeatureRouteScanner`) che monta dinamicamente i router FastAPI di tutte le funzionalità.
- **Widget Dinamici Modulari e Reactive Web Deck**:
  - Architettura a directory dedicate per tutti i widget (`server/web/widgets/<widget_id>/`) con `manifest.json`, `widget.py` (sottoclasse di `BaseWidget`), controller REST e WebSocket (`/widgets`, `/widgets/{id}/state`, `/widgets/{id}/action`, `/widgets/ws`).
  - Widget dinamici integrati: `brain_activity` (attività neurale e vettore limbico live), `cad_viewer` (visualizzatore interattivo DXF 2D/3D), `quick_actions` (pulsanti di esecuzione rapida), `smart_switch` (relè e prese smart), `system_status` (telemetria hardware), `weather` (sensori meteo e previsioni).
  - Deck reattivo React 18 (`client_web/src/features/dynamic_widgets/DynamicWidgetDeck.tsx`) con streaming WebSocket in tempo reale.
- **Strumenti Agente Modulari Dinamici e ToolScanner**:
  - Architettura a cartelle dedicate (`server/features/agent_tools/<tool_id>/`) con `BaseAgentTool`, `tool.py` e `manifest.json`.
  - Strumenti integrati: `cad`, `generator_3d`, `google_suite` (Gmail, Calendar, Drive, Fogli, Documenti), `image`, `maps`, `music`, `social` (Instagram, Facebook, X), `web_scraper`, `web_search`.
- **CEO Multi-Agent Orchestrator e AgentScanner Dinamico**:
  - Il CEO Orchestrator (`installer_wizard/features/team/ceo.py`) guida ogni turno di conversazione.
  - Alimentato da `AgentScanner` (`installer_wizard/features/team/scanner.py`): nessun elenco cablato nel codice! Scansiona a runtime `/features` e `/widgets`, indicizzando token semantici, strumenti dichiarati e capacità per formulare piani di delega dinamici (`ceo_delegate`, `ceo_overview`).
- **Triage Clinico Cognitivo Tri-Agente e Sorveglianza Multimodale**:
  - Triage cognitivo clinico tri-agente (`server/features/cognitive_triage_agents/`) con agente medico, agente psicologico e blocco deterministico di sicurezza (`triage_safety_interlock`).
  - Sorveglianza multimodale continua, Affective Fusion Engine, Hub per Dispositivi Indossabili (`WearableVitalsHub`) e rilevamento della presenza di emergenza.
  - Audio enhancer con fallback in puro Python per ambienti privi di NumPy.
- **Coda Installazioni in Background con Velocità e Ordine per Dimensione (GB)**:
  - Visualizzazione in tempo reale della velocità di scaricamento (in MB/s o KB/s), barra di avanzamento e percentuale per ogni pacchetto in `bgqueue.js/css` e pannelli di amministrazione.
  - Ordinamento rigoroso della coda dai pacchetti più leggeri a quelli più pesanti in GB, ottimizzando spazio e larghezza di banda.
- **Aggiornamento Forzato di Emergenza via SSH (`nuxivactl update --force`)**:
  - Script dedicato `scripts/os/force-upgrade.sh` accessibile tramite `sudo nuxivactl update --force` o `sudo nuxiva-upgrade` per eseguire un reset forzato a `origin/main`, pulire lock obsoleti, aggiornare dipendenze, ricompilare i crate Rust e riavviare tutti i demoni anche quando il supervisore web è bloccato.
- **Configurazione Iniziale di Risveglio Modulare e Non Bloccante**:
  - La procedura guidata di risveglio è stata trasformata in una configurazione iniziale opzionale, liberamente saltabile o rieseguibile in qualsiasi momento senza bloccare il display kiosk o il pannello di controllo.
- **Sanificazione Ambientale e Risoluzione del Quoting Ricorsivo**:
  - Risoluzione del bug di quoting ricorsivo in `/etc/nuxiva/nuxiva.env`, sanificazione dei permessi di Ollama e avvio differito per i servizi non ancora configurati.
- **Catalogo Esteso**: 72 funzionalità di sistema auto-scoperte in `installer_wizard/features/`, oltre 1.200 test automatici convalidati su Rust, Python e TypeScript.

<p align="center">
  <img src="https://img.shields.io/badge/Architettura-Clean%20Architecture-00f0ff?style=for-the-badge" alt="Clean Architecture">
  <img src="https://img.shields.io/badge/Cognitivo-Omni%20Cortical%206.5-purple?style=for-the-badge" alt="Omni-Cortical">
  <img src="https://img.shields.io/badge/Sicurezza-Zero%20Trust%20Wasm-red?style=for-the-badge" alt="Zero Trust">
  <img src="https://img.shields.io/badge/Resilienza-eBPF%20Self%20Healing-blue?style=for-the-badge" alt="eBPF">
  <img src="https://img.shields.io/badge/Stato-Event%20Sourcing-emerald?style=for-the-badge" alt="Event Sourcing">
  <img src="https://img.shields.io/badge/Calcolo-P2P%20Mesh%20Swarm-amber?style=for-the-badge" alt="Swarm Compute">
  <a href="https://www.paypal.com/paypalme/NunzioAprile"><img src="https://img.shields.io/badge/Dona-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="PayPal"></a>
</p>

```text
 ███╗   ██╗██╗   ██╗██╗  ██╗██╗██╗   ██╗ █████╗ 
 ████╗  ██║██║   ██║╚██╗██╔╝██║██║   ██║██╔══██╗
 ██╔██╗ ██║██║   ██║ ╚███╔╝ ██║██║   ██║███████║
 ██║╚██╗██║██║   ██║ ██╔██╗ ██║╚██╗ ██╔╝██╔══██║
 ██║ ╚████║╚██████╔╝██╔╝ ██╗██║ ╚████╔╝ ██║  ██║
 ╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝  ╚═╝  ╚═╝
 SISTEMA OPERATIVO AI DISTRIBUITO - ENTERPRISE v4.1.53
      Progettato e sviluppato da NunzioTech
```

## ❤️ Nuxiva è gratuita, e resterà gratuita

Nuxiva è un progetto **totalmente gratuito**, ideato, scritto e mantenuto da **Nunzio Aprile (NunzioTech)** nel suo tempo libero:
nessun abbonamento, nessuna funzione a pagamento nascosta, nessun dato venduto a terzi. Ogni riga di codice sorgente è a tua completa disposizione.

Se Nuxiva gestisce la tua casa, coordina la tua infrastruttura, ti supporta nello studio o potenzia la tua ricerca, **una donazione è ciò che lo fa crescere**: copre i costi dell'hardware di collaudo (telecamere, schede ESP32, GPU, dispositivi edge), i crediti per le API dei modelli cloud usati nello sviluppo e le migliaia di ore necessarie per progettare nuove architetture autonome.
Anche il costo di un caffè fa una differenza concreta, e ogni contributo sostiene direttamente l'evoluzione open source di Nuxiva per tutti.

<p align="center">
  <a href="https://www.paypal.com/paypalme/NunzioAprile">
    <img src="https://img.shields.io/badge/Dona-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Dona con PayPal">
  </a>
</p>

<p align="center"><b>👉 <a href="https://www.paypal.com/paypalme/NunzioAprile">paypal.me/NunzioAprile</a> — grazie di cuore per sostenere l'ingegneria open source indipendente!</b></p>

---

## Architettura di Livello Enterprise (I 5 Pilastri)

Nuxiva non è un semplice script o un wrapper monolitico di chatbot, ma un **Sistema Operativo Distribuito e Autonomo** fondato su cinque pilastri strutturali:

1. **Kernel Self-Healing (eBPF & Landlock):** Monitoraggio a basso livello tramite probe C eBPF nel Kernel Linux per rilevare memory leak (MALLOC/FREE), anomalie dei socket e chiamate di sistema sospette, innescando l'autoriparazione a caldo tramite LLM.
2. **Esecuzione Isolata (Zero-Trust Wasm & MicroVM):** Nessun modulo di terze parti o strumento sintetizzato viene eseguito nativamente sull'host. Il codice viene confinato in runtime WebAssembly (Wasmtime) con policy WASI capability-based (< 5ms di cold start), ambienti user-space gVisor o MicroVM Firecracker dedicate.
3. **Time-Travel (Event Sourcing & Registro Immutabile):** Nessuno stato mutabile diretto. Ogni percezione sensoriale, passo di ragionamento, variazione biometrica e decisione di sistema viene registrata in un Ledger immutabile firmato con HMAC concatenato, consentendo il riavvolgimento matematico del sistema al millisecondo per verifiche e debug assoluti.
4. **Swarm Computing (P2P Mesh Swarm):** Nuxiva scala orizzontalmente attraverso nodi locali e remoti. Meccanismi di discovery via UDP beaconing e mesh gRPC consentono l'offload distribuito di tensori visivi, feature audio e calcoli neurali su nodi GPU dedicati della rete LAN.
5. **Generazione Dinamica di SDK e Contratti:** Generazione istantanea di librerie client, rotte API e interfacce in TypeScript, Rust e Python tramite riflessione dinamica, schemi OpenAPI e Protobuf per un'interoperabilità senza attriti.

---

## 1. In breve

| Aspetto | Dettagli di Implementazione |
| :--- | :--- |
| **Installazione** | Un solo comando su Debian/Ubuntu: scarica il repository in `/opt/Nuxiva` e avvia il supervisore autonomo. |
| **Supervisore** | Servizio `nuxiva-supervisor` (Python 3.11+, FastAPI, asyncio). Gestisce i 31 passi di installazione del sistema operativo, i watchdog di ripristino e le code in background. |
| **Display (Porta 80)** | Interfaccia kiosk interattiva: volto olografico 3D (Orb), sintesi e riconoscimento vocale naturale, desktop a widget dinamici e selettore delle modalità di ragionamento. |
| **Pannello Admin (Porta 8080)** | Pannello di amministrazione completo con autenticazione PAM di sistema, telemetria in tempo reale, assegnazione modelli, configurazione funzionalità e log di sistema. |
| **Cervello Cognitivo** | 6 Motori di Ragionamento Modulari (da Legacy 4.2 a Ultra 6.5), Spiking Neural Network LIF, Modulatore Limbico, Ollama locale, nodi distribuiti e 22 fornitori cloud crittografati. |
| **Ecosistema Funzionalità** | 72 pacchetti autoscoperti in `installer_wizard/features/`. Ciascuno si attiva automaticamente in base all'hardware (`auto`) o tramite flag forzati (`1`/`0`). |
| **Aggiornamenti Continui** | Sincronizzazione automatica da GitHub ogni 5 minuti dal ramo `main` (solo per versioni validate da CI), con collaudo automatico e rollback istantaneo. Aggiornamento forzato via `nuxivactl update --force`. |
| **CEO Orchestrator & Team** | CEO Multi-Agent Orchestrator dinamico basato su `AgentScanner`. Zero elenchi cablati: scansiona dinamicamente `/features` e `/widgets`, delegando tramite indicizzazione di token semantici. |
| **Comprensione e Triage** | Valutazione semantica con punteggio tra le funzioni, verifica deterministica degli esiti e triage clinico cognitivo tri-agente (medico, psicologico, interlock di sicurezza). |
| **Affidabilità e Qualità** | Verifica post-esecuzione degli effetti reali con retry automatico; oltre 1.200 test automatici unitari e di integrazione tra supervisore, core e crate Rust. |
| **Interoperabilità (MCP)** | Server (Porta 8080) e client nativo Model Context Protocol (MCP), esportazione schemi OpenAPI, function calling per Anthropic/OpenAI e rotte REST/WebSocket. |
| **Multilingua (i18n)** | Localizzazione completa al 100% in italiano, inglese e francese in tutte le interfacce, wizard, widget e messaggi del server. Download automatico delle voci per l'ascolto e la sintesi. |

---

## 2. Evoluzione Architetturale e Cronologia Versioni

### Versione 4.1.53: L'Era Neuro-Cognitiva e Dinamica Universale
- **Omni-Cortical Engine Modulare**: Motori di ragionamento disaccoppiati (`BaseReasoningEngine`) in `server/core/reasoning/engines/` con scoperta dinamica tramite `EngineScanner`.
- **Dinamica Neurale Neuro-Biologica**: Rete neurale spiking Leaky Integrate-and-Fire (LIF) con periodo refrattario, plasticità sinaptica STDP e modulazione limbica a 7 dimensioni.
- **Binding Sensoriale-Limbico in Tempo Reale**: Stress acustico vocale, valenza facciale e presenza fisica convogliati nel vettore limbico corticale e trasmessi come eventi `biometrics.*` su `nuxiva_bus`.
- **Default Mode Network (DMN)**: Ciclo autonomo di riflessione in background attivato dopo 10 minuti di inattività per consolidare ricordi e pianificare azioni proattive di foresight.
- **Consolidamento Sinaptico Notturno REM**: Decadimento e stabilizzazione controllata dei pesi STDP diurni per proteggere le memorie salienti dalla curva dell'oblio di Ebbinghaus.
- **Scanner Dinamico Universale con Accelerazione Rust**: Motore `FastScanner` nativo in Rust (`bus-core`) con hashing FNV-1a, affiancato da `UniversalScanner` Python con validazione AST Zero-Trust e `DirectoryWatcher`.
- **Widget e Strumenti Agente a Directory Dedicate**: Struttura modulare per widget dinamici (`server/web/widgets/`) e strumenti agente (`server/features/agent_tools/`) con auto-discovery e streaming WebSocket.
- **CEO Multi-Agent Orchestrator**: Coordinatore dinamico delle conversazioni con `AgentScanner` che analizza manifest e token semantici senza elenchi fissi.
- **Triage Cognitivo Clinico**: Agenti specializzati medico e psicologico con blocco deterministico di sicurezza per richieste critiche.
- **Coda in Background Ordinata per Dimensione**: Installazione asincrona ordinata dai pacchetti più leggeri a quelli più pesanti con tachimetro di velocità (MB/s o KB/s).
- **Aggiornamento Forzato via SSH**: Script di ripristino `force-upgrade.sh` e comando `nuxivactl update --force`.
- **Robustezza del Sistema**: Configurazione iniziale non bloccante e risoluzione del quoting ricorsivo in `/etc/nuxiva/nuxiva.env`.

### Versione 4.0.0: Swarm Enterprise e RBAC Spazio-Temporale
- **RBAC Spazio-Temporale**: Controllo accessi granulare che unisce perimetri fisici (stanze/zone delle telecamere) e finestre temporali d'accesso.
- **Swarm Multi-Agente Autonomo**: Workspace isolati e persistenti (`data/agents/<agent_id>`), istruzioni dedicate, archivi di conoscenza e binding di strumenti.
- **Chief Supervisor e War Room HUD**: Watchdog esecutivo attivo 24/7 anti-loop infinito con trasmissione in tempo reale del grafo dei pensieri.
- **Arsenale Strumenti Esteso**: CAD nativo (DXF 2D/3D), integrazione Google Workspace (Gmail, Calendar, Drive, Fogli, Documenti) e orchestrazione Social Media.
- **Ragionamento Ternario**: Sistema 1 (router reattivo edge), Sistema 2 (loop ReAct con critica) e Sistema 3 (giuria di consenso bizantino).
- **HUD di Prossimità e Chatbot Mesh**: Mesh P2P per la sincronizzazione multi-agente e radar di presenza fisica.
- **Integrazione Proxmox VE**: Amministrazione avanzata dell'hypervisor per macchine virtuali e container LXC.

### Versione 3: Riscrittura Modulare a Funzionalità e MCP
- **Architettura a Doppio Cervello**: Sistema 1 non autoregressivo veloce (< 50ms) e Sistema 2 deliberativo con blocco di pensiero `<thinking>`.
- **Pannello Cervello Riorganizzato**: Cruscotto Cervelli, Assegnazioni Componenti e Aggiungi/Gestisci Cervelli.
- **Cluster Neurale Distribuito**: Liste di priorità miste con Ollama locale, nodi OpenAI-compatibili remoti e 22 provider cloud.
- **Model Context Protocol (MCP)**: Server e client MCP integrati.
- **Verifica degli Esiti**: Controllo post-esecuzione per musica, domotica e comandi visuali.
- **Fucina Autonoma**: Sintesi a zero codice di strumenti composti e widget.

---

## 3. Requisiti di Sistema

| Componente | Requisito Minimo | Configurazione Consigliata |
| :--- | :--- | :--- |
| **Sistema Operativo** | Debian 12 (Bookworm) o Ubuntu 22.04+ LTS (x86_64 / arm64) | Debian 12 Minimal (x86_64) |
| **Processore (CPU)** | 4 core (x86_64 con istruzioni AVX o ARM64 v8.2+) | 8+ core con istruzioni AVX2 / AVX-512 |
| **Memoria RAM** | 8 GB di memoria di sistema | 16–32 GB DDR4/DDR5 |
| **Scheda Grafica (GPU)** | Nessuna (inferenza supportata su sola CPU) | NVIDIA RTX (8 GB+ VRAM) con CUDA 12+ o Apple Silicon |
| **Archiviazione** | 30 GB di spazio libero su disco | 100+ GB SSD NVMe (modelli, voci, registrazioni) |
| **Connessione di Rete** | Connessione Internet a banda larga per l'installazione | Connessione Gigabit Ethernet cablata |
| **Periferiche** | Funzionamento headless supportato | Microfono, altoparlanti stereo, webcam USB/IP, schermo |

> [!NOTE]
> - La procedura di installazione utilizza `apt-get`: **sono supportati solo Debian, Ubuntu e loro derivate dirette**.
> - Sui sistemi privi di scheda video dedicata, Nuxiva seleziona automaticamente modelli quantizzati compatti ed efficienti (es. Q4_K_M da 1.5B–3B parametri).
> - È possibile delegare interamente il carico computazionale neurale specificando `NUXIVA_OLLAMA_URL` verso un altro computer con GPU nella LAN o affidandosi ai modelli cloud.
> - Le funzionalità che richiedono hardware specifico (webcam, microfono, GPU) si disattivano da sole in modalità `auto` quando i dispositivi non sono presenti.

---

## 4. Installazione

### Comando Unico (Consigliato per Debian/Ubuntu)

Esegui questo comando in un terminale con privilegi di amministrazione sudo:

```bash
curl -fsSL https://raw.githubusercontent.com/aprilenunzio88/Nuxiva/main/install.sh | bash
```

Lo script esegue i controlli preliminari, scarica il repository in `/opt/Nuxiva`, imposta i permessi, installa Python e gli strumenti base di compilazione e avvia il servizio `nuxiva-supervisor`. Il supervisore prende immediatamente il controllo e completa automaticamente il resto dell'installazione.

### Installazione Manuale da Clone del Repository

```bash
# 1. Clona il repository
sudo git clone https://github.com/aprilenunzio88/Nuxiva.git /opt/Nuxiva
cd /opt/Nuxiva

# 2. Avvia lo script di installazione
sudo bash install.sh
```

### Installazione su Windows

Su macchine Windows, Nuxiva è supportato ufficialmente tramite **WSL2 (Windows Subsystem for Linux)** con distribuzione Ubuntu 22.04 o Debian 12:

```powershell
# In PowerShell aperta come Amministratore:
wsl --install -d Ubuntu-22.04
wsl
```
All'interno del terminale Linux di WSL2, esegui il normale comando di installazione:
```bash
curl -fsSL https://raw.githubusercontent.com/aprilenunzio88/Nuxiva/main/install.sh | bash
```
Per sperimentazioni native su Windows, è disponibile uno script PowerShell amministrativo:
```powershell
.\install.ps1
```

---

## 5. Primo Avvio, Accesso e Installazioni in Background

### Porte e Interfacce Web di Accesso

Una volta avviato il supervisore, Nuxiva mette a disposizione due portali web dedicati:

1. **Display Interattivo / Kiosk (Porta 80):** `http://<ip-server>/`
   - Volto olografico 3D (Orb) reattivo alla voce, all'audio e ai movimenti.
   - Desktop a widget dinamici visualizzati in tempo reale.
   - Selettore dei Motori Cognitivi: cambia la modalità di ragionamento attiva istantaneamente.
   - Sessione kiosk a schermo intero avviata automaticamente sugli schermi fisici collegati al server.
2. **Cruscotto di Amministrazione (Porta 8080):** `http://<ip-server>:8080/`
   - Amministrazione completa protetta da autenticazione PAM di sistema (credenziali root o sudoers).
   - Telemetria live, gestione modelli, catene di priorità, interruttori delle funzionalità e visualizzatore di log.

### Configurazione Iniziale di Risveglio Modulare e Facoltativa

La procedura guidata di prima accensione (`/setup` su Porta 80) è **completamente facoltativa e non bloccante**:
- Puoi seguire i passaggi per personalizzare il nome dell'assistente, impostare la rete, calibrare il microfono e scegliere la voce iniziale.
- Puoi liberamente saltare la procedura e accedere direttamente al desktop interattivo.
- È possibile rieseguire o modificare la configurazione in qualsiasi momento dal cruscotto di amministrazione senza riavviare i servizi.

### Coda di Installazione in Background con Velocità Live e Ordine per Dimensione

I componenti più voluminosi (modelli neurali, classificatori visivi, modelli vocali, container) vengono installati in background per rendere l'assistente utilizzabile da subito:
- **Tachimetro di Velocità Live**: La barra della coda (`bgqueue.js/css`) mostra la velocità attuale di download (in MB/s o KB/s), la percentuale di avanzamento e il tempo stimato.
- **Ordinamento per Dimensione Crescente (GB)**: La coda viene eseguita rigorosamente a partire dal pacchetto meno pesante in gigabyte fino a quello più grande. Gli strumenti più leggeri sono pronti in pochi istanti.
- **Verifica da Riga di Comando**: Controlla lo stato della coda in qualunque momento con:
  ```bash
  nuxivactl background
  ```

---

## 6. Architettura Generale del Sistema

```text
+---------------------------------------------------------------------------------------+
|                                  RUNTIME DI NUXIVA                                    |
+---------------------------------------------------------------------------------------+
|  INTERFACCE CLIENT                                                                    |
|  - Kiosk Display (Porta 80): Sfera 3D, Audio STT/TTS, Desktop a Widget, UI Ragionamento|
|  - Cruscotto Admin (Porta 8080): Autenticazione PAM, Telemetria, Assegnazioni, Log    |
|  - Client Web React (client_web): Control Deck, Visualizzatore Neurale 3D, WidgetDeck |
|  - Satelliti P2P e APK Android: Nodi edge audio/video, Radar di prossimità            |
+---------------------------------------------------------------------------------------+
|  SUPERVISORE E MOTORE IN BACKGROUND (installer_wizard/backend/ - Python / FastAPI)    |
|  - Demone di Supervisione (nuxiva-supervisor.service)                                 |
|  - Orchestratore dei 31 Passi OS e Registro di Stato (state.json, ledger.log)        |
|  - Watchdog dei Loop e Default Mode Network (DMN - ciclo di riflessione ogni 10 min)  |
|  - CEO Multi-Agent Orchestrator e AgentScanner dinamico (features/team/ceo.py)        |
|  - 72 Funzionalità di Sistema e Controller dei Widget Dinamici (/widgets, /widgets/ws)|
+---------------------------------------------------------------------------------------+
|  NUCLEO COGNITIVO E MOTORI DI RAGIONAMENTO (server/core/ & server/features/)          |
|  - Omni-Cortical Engine 6.5 e Registro Dinamico dei BaseReasoningEngine               |
|    [ Legacy 4.2 | Veloce 5.0 | Empatico 5.0 | Pro 6.0 | Ultra 6.5 | Auto 6.5 ]      |
|  - Spiking Neural Core Leaky Integrate-and-Fire (LIF) e Plasticità Hebbiana STDP      |
|  - Modulatore Limbico a 7 Assi (Valenza, Arousal, Dominanza, DA, NE, 5-HT, Cortisolo) |
|  - Binding Sensoriale-Limbico (Stress acustico voce, Pressione scena, Presenza)       |
|  - Global Neuronal Workspace (GNW): Parallelismo speculativo e inibizione GABA        |
|  - Triage Clinico Cognitivo Tri-Agente (Medico, Psicologico, Blocco di Sicurezza)     |
|  - Strumenti Agente Dinamici (CAD, Generatore 3D, Google, Immagini, Mappe, Musica)   |
|  - Consolidamento Sinaptico Notturno REM contro la Curva dell'Oblio di Ebbinghaus     |
+---------------------------------------------------------------------------------------+
|  BUS EVENTI E LAYER NATIVO RUST AD ALTE PRESTAZIONI (native/crates/ - Rust & PyO3)    |
|  - bus-core: Smistamento eventi zero-copy, RingBufferLockFree neurale, FastScanner    |
|  - egress: Proxy di rete e sandbox Zero-Trust con confinamento Linux Landlock         |
|  - netguard: Ispezione approfondita dei pacchetti e sicurezza di rete                 |
|  - nuxiva-native: Binding PyO3 che espone i tipi Rust al runtime Python               |
+---------------------------------------------------------------------------------------+
|  WORKSPACE ISOLATI E RUNTIME DEL SISTEMA OPERATIVO (Kernel Linux e Sandbox)           |
|  - Runtime WebAssembly Zero-Trust (Wasmtime) e MicroVM (Firecracker / gVisor)        |
|  - Workspace persistenti (data/agents/<agent_id>/) e Registro Event Sourcing           |
|  - Sonde eBPF nel Kernel Linux, ZRAM/Swap, Docker CE, Runtime Ollama, PipeWire/ALSA   |
+---------------------------------------------------------------------------------------+
```

### Il Ciclo Cognitivo di una Richiesta

1. **Percezione Sensoriale**: La voce dell'utente viene catturata da `features/ear/` (Whisper STT) o i fotogrammi da `features/vision/` (YOLO/VLM).
2. **Modulazione Sensoriale-Limbica**: Lo stress acustico vocale e la valenza facciale aggiornano il `LimbicModulator` a 7 assi, trasmettendo i dati biometrici su `nuxiva_bus`.
3. **Orchestrazione CEO e Comprensione**: Il CEO Orchestrator interroga `AgentScanner` per confrontare la frase con le capacità, gli strumenti e i token semantici degli agenti disponibili.
4. **Scelta del Motore Cognitivo**: L'Omni-Cortical Engine seleziona la modalità di ragionamento (es. `nuxiva-6.5-auto` valuta la complessità $\psi$, lo stato limbico e la memoria VRAM).
5. **Esecuzione Parallela Speculativa (GNW)**: Vengono generati fino a 16 rami di pensiero paralleli. Quando un ramo supera la soglia di accensione, scatena una **scarica inibitoria GABAergica** che annulla all'istante i rami più lenti.
6. **Blocco di Sicurezza e Consenso Bizantino**: Operazioni cliniche o fisiche critiche passano attraverso interlock deterministici e giurie di modelli con diritto di veto.
7. **Esecuzione in Sandbox Isolata**: Gli strumenti dinamici o i comandi di sistema operano all'interno di sandbox protette.
8. **Verifica Deterministica dell'Esito**: Il sistema attende la verifica visibile dell'effetto reale prima di dichiarare completata l'operazione.
9. **Apprendimento Sinaptico STDP**: Le sinapsi tra i neuroni coinvolti aggiornano i propri pesi secondo la regola Hebbiana STDP, memorizzando l'esperienza per il futuro.

---

## 7. Struttura del Repository

```text
/opt/Nuxiva/
├── client_apk/                  # Applicazione nativa Android (Kotlin)
├── client_satellite/            # Demone satellite leggero per nodi edge ESP32 / Raspberry Pi
├── client_web/                  # Applicazione web avanzata React 18 + Vite + Tailwind + Three.js
│   ├── src/features/
│   │   ├── cognitive_engine/    # Selettore UI e hook dei motori cognitivi (useCognitiveEngine)
│   │   ├── control_deck/        # Cockpit operativo e flusso di analisi neurale in tempo reale
│   │   ├── core_visualizer_3d/  # Visualizzatore 3D dell'attività di sparo neurale e HUD
│   │   ├── dynamic_widgets/     # DynamicWidgetDeck e rendering live dei widget dinamici
│   │   └── studio_3d/           # Studio parametrico di modellazione e disegno CAD 3D
│   └── src/shared/i18n/         # Cataloghi di traduzione completi (EN, IT, FR)
├── data/                        # Stato applicativo persistente, workspace agenti, vault
│   └── agents/<agent_id>/       # Workspace isolati e persistenti per ciascun agente
├── docker/                      # Configurazioni Docker e container di produzione
├── installer_wizard/            # Demone del supervisore e interfaccia amministrativa
│   ├── backend/                 # Backend FastAPI del supervisore, loop, nuxiva_bus, coda download
│   ├── features/                # 72 funzionalità di sistema modulari e autoscoperte
│   │   ├── brain/               # Preset cervello, componenti LIF, assegnazioni ruoli, residency
│   │   ├── chat/                # Pipeline conversazionale, brain_chain (GNW), endpoint API
│   │   ├── team/                # CEO Orchestrator, AgentScanner dinamico, lavagna condivisa
│   │   ├── ear/                 # Trascrizione vocale, stress acustico, biometria dell'impronta vocale
│   │   ├── vision/              # Riconoscimento VLM, tracciamento oggetti YOLO, consolidamento notturno
│   │   └── ...                  # Ulteriori 67 funzionalità specializzate
│   └── web/                     # Interfacce web (display, admin, nexus, monitor, setup)
├── native/                      # Crate compilati in linguaggio Rust ad alte prestazioni
│   └── crates/
│       ├── bus-core/            # FastScanner (FNV-1a), Spiking Neural Core, RingBufferLockFree
│       ├── egress/              # Proxy di rete e sandbox Zero-Trust multipiattaforma Landlock
│       ├── langid/              # Identificazione della lingua sub-millisecondo
│       ├── netguard/            # Firewall con ispezione approfondita dei pacchetti (DPI)
│       └── nuxiva-native/       # Binding PyO3 che espongono Rust al runtime Python
├── sandbox_broker/              # Broker per l'esecuzione sicura in container e MicroVM
├── scripts/os/                  # I 31 script di installazione del sistema operativo e manutenzione
│   ├── steps/                   # Script numerati da 10-preflight.sh a 95-warmup.sh
│   ├── force-upgrade.sh         # Script di ripristino forzato e aggiornamento diretto da GitHub
│   └── nuxivactl                # Eseguibile CLI centrale per la gestione del sistema
├── server/                      # Nucleo Cognitivo di Nuxiva (Python 3.11+)
│   ├── cmd/                     # Router API, entrypoint principale, FeatureRouteScanner
│   ├── core/
│   │   ├── kernel/              # Consenso bizantino, dominio dello stato limbico, corsie dello swarm
│   │   ├── orchestrator/        # Router Sistema 1, pianificatore a grafo DAG, acquisizione skill
│   │   ├── reasoning/           # Omni-Cortical Engine e motori di ragionamento modulari
│   │   │   └── engines/         # auto_6_5, ultra_6_5, pro_6_0, empatico_5_0, veloce_5_0, legacy_4_2
│   │   └── scanner/             # UniversalScanner, ZeroTrustValidator, DirectoryWatcher
│   ├── features/
│   │   ├── agent_tools/         # Strumenti agente modulari: cad, 3d, google, image, maps, music, web
│   │   ├── cognitive_triage_agents/ # Triage clinico cognitivo tri-agente (medico, psicologico, interlock)
│   │   └── multimodal_surveillance/ # Affective fusion, hub indossabili vitals, audio enhancer
│   └── web/widgets/             # Widget dinamici modulari (manifest.json, BaseWidget, controller)
├── install.sh                   # Script di bootstrap automatico per Debian/Ubuntu
├── install.ps1                  # Script di bootstrap PowerShell per ambiente Windows
├── docker-compose.yml           # Definizione multi-container di sistema
└── VERSION                      # Versione del software (4.1.53)
```

---

## 8. Il Supervisore e il Motore in Background

Il servizio `nuxiva-supervisor.service` opera ininterrottamente in background per garantire la massima stabilità operativa e l'autoriparazione:

### Watchdog dei Servizi in Background (`installer_wizard/backend/loops.py`)
- **Rilevamento Guasti e Riavvio Automatico**: Monitora periodicamente i servizi interni. In caso di blocco o crash anomalo, il supervisore li riavvia applicando un backoff esponenziale configurabile (`NUXIVA_LOOPS_BACKOFF_MAX`).
- **Controllo Heartbeat**: Ciascun ciclo comunica un segnale di battito vitale. Se un servizio smette di rispondere oltre la soglia massima consentita ($5 \times \text{periodo}$), il supervisore lo termina e ne istanzia una copia pulita.

### Default Mode Network (DMN): Ciclo di Riflessione Autonoma
- **Attivazione su Inattività**: Quando l'utente non interagisce con Nuxiva per almeno 10 minuti continui (`idle_threshold_s = 600.0`), il DMN entra in funzione automaticamente.
- **Consolidamento delle Memorie**: Il DMN esamina le tracce recenti in `LongTermMemory` e le correla con i modelli comportamentali di abitudine in `features/habits/foresight.py`.
- **Simulazione di Foresight**: Esegue un pensiero speculativo parallelo tramite `cortical_chain.execute_parallel_thought()`, pre-generando piani di automazione e preparando la memoria cache.
- **Azzeramento Immediato**: Qualsiasi comando vocale, messaggio in chat o azione nell'interfaccia azzera all'istante il timer del DMN per non occupare mai risorse durante l'uso attivo.

---

## 9. Passi d'Installazione del Sistema Operativo (I 31 Script)

Nuxiva installa e configura il sistema operativo tramite 31 script modulari in `scripts/os/steps/`, tutti tracciati in `state.json`:

| Script del Passo | Titolo | Descrizione e Compiti Operativi |
| :--- | :--- | :--- |
| `10-preflight.sh` | Diagnostica Preliminare | Verifica la versione del sistema operativo, l'architettura (x86_64/arm64), i core CPU, la RAM e lo spazio su disco. |
| `15-memory.sh` | Memoria e ZRAM | Configura l'area di swap compressa in ZRAM e ottimizza i parametri del kernel per la gestione della RAM. |
| `20-system.sh` | Pacchetti di Base | Installa le utilità di sistema Linux, strumenti di compilazione, curl, git, jq e gli header Python. |
| `25-kiosk.sh` | Display Kiosk | Prepara l'ambiente grafico leggero (X11/Cage/Chromium) per l'interfaccia a schermo intero (Porta 80). |
| `30-docker.sh` | Runtime Container | Installa e configura il motore Docker CE e il demone containerd. |
| `32-sandbox.sh` | Sandbox di Esecuzione | Prepara i filesystem isolati per l'esecuzione protetta di codice e script sintetizzati. |
| `33-display-driver.sh`| Driver Grafici | Configura i driver di accelerazione video GPU (Mesa, DRM/KMS, accelerazione Xorg). |
| `34-gvisor.sh` | Sandbox gVisor | Configura il runtime container `runsc` di Google con kernel in spazio utente per sandbox con accesso di rete. |
| `35-gpu.sh` | Accelerazione GPU | Rileva e attiva il supporto per NVIDIA CUDA, AMD ROCm o Intel oneAPI nei container. |
| `36-firecracker.sh` | Hypervisor MicroVM | Installa l'hypervisor KVM Firecracker per l'avvio sub-secondo di MicroVM isolate per gli strumenti. |
| `38-native.sh` | Crate Rust Nativi | Compila tramite Cargo i crate Rust nativi (`bus-core`, `egress`, `langid`, `netguard`, `nuxiva-native`). |
| `40-security.sh` | Blindatura di Sicurezza | Imposta profili AppArmor, policy PAM, regole firewall (UFW/nftables) e permessi restrittivi sui file. |
| `42-netguard.sh` | DPI Netguard | Installa il motore di deep packet inspection per la difesa e il monitoraggio del traffico LAN. |
| `43-vpn.sh` | Rete Mesh VPN | Configura la rete VPN mesh cifrata peer-to-peer basata su WireGuard e Tailscale. |
| `50-ollama.sh` | Servizio LLM Ollama | Prepara il demone systemd di Ollama con quote d'ambiente sanificate e avvio differito se non configurato. |
| `55-voice.sh` | Sintesi Vocale | Installa i motori di sintesi neurale Piper TTS e Kokoro per la voce dell'assistente. |
| `56-bluetooth.sh` | Periferiche Bluetooth | Configura lo stack audio BlueZ e PipeWire per la connessione di microfoni e casse senza fili. |
| `57-vision.sh` | Visione Artificiale | Installa OpenCV, OpenVINO, modelli YOLO per oggetti/volti e pipeline per modelli VLM. |
| `58-ear.sh` | Percezione Audio | Configura il riconoscimento Whisper STT, l'analisi dello stress vocale e l'impronta biometrica. |
| `59-music.sh` | Libreria Musicale | Configura l'indicizzazione dei brani musicali, l'impronta audio, i server DLNA e Chromecast. |
| `60-models.sh` | Download Modelli | Scarica i pesi dei modelli neurali ordinati per dimensione crescente in GB con monitoraggio della velocità. |
| `61-brain.sh` | Cervello Cognitivo | Configura le catene di routing dei modelli e inizializza la pipeline Omni-Cortical. |
| `62-convert3d.sh` | Strumenti CAD 3D | Installa librerie di conversione geometrica DXF 2D/3D e manipolazione mesh per il CAD. |
| `63-shares.sh` | Condivisioni di Rete | Configura condivisioni di file Samba (SMB/CIFS) compatibili con Windows 11 e macOS. |
| `64-office.sh` | Servizi Documenti | Installa LibreOffice headless per l'estrazione e conversione automatica di testi e PDF. |
| `66-voicestudio.sh` | Voice Studio | Configura il container opzionale XTTS per la clonazione della voce con verifica dello spazio su disco. |
| `67-soup.sh` | Model Souping | Prepara gli strumenti di interpolazione dei pesi e studio autonomo a riposo. |
| `70-core.sh` | Nuxiva Core | Compila e installa le dipendenze Python del server, migrazioni Alembic e demoni del Core. |
| `80-services.sh` | Abilitazione Servizi | Abilita e avvia tutte le unità systemd di Nuxiva (`nuxiva-core`, `nuxiva-supervisor`, ecc.). |
| `90-maintenance.sh` | Manutenzione Auto | Registra script cron per la rotazione dei log, la pulizia dei file temporanei e l'igiene del disco. |
| `95-warmup.sh` | Pre-riscaldamento | Esegue inferenze di prova per precaricare i modelli in RAM/VRAM ed eliminare la latenza iniziale. |

---

## 10. Il Cervello Cognitivo: Architettura, Motori di Ragionamento e Neuro-Biologia

### I 6 Motori di Ragionamento Modulari (`server/core/reasoning/engines/`)

Il nucleo di ragionamento di Nuxiva segue l'Open/Closed Principle. Ciascun motore eredita da `BaseReasoningEngine` ed è scansionato dinamicamente a runtime da `EngineScanner`:

| Versione Motore | Nome in Codice | Architettura e Strategia Cognitiva | SLA Latenza | Budget VRAM | Ruolo |
| :--- | :--- | :--- | :---: | :---: | :---: |
| `nuxiva-4.2-legacy` | **Legacy Chain-Sync** | Pipeline sequenziale a token con fallback seriale | 2500 ms | 2048 MB | Riserva |
| `nuxiva-5.0-veloce` | **Veloce Synapse-Flash** | Ternary 1.58-bit con Liquid LNN e bus spiking zero-copy | 25 ms | 512 MB | Chat Rapida |
| `nuxiva-5.0-empatico`| **Empatico Synapse-Limbic** | Global Workspace a 8 corsie parallele con fusione biometrica a 10Hz | 120 ms | 4096 MB | Dialogo/Voce |
| `nuxiva-6.0-pro` | **Pro Omni-Latent** | Spazio Latente Continuo JEPA/Coconut con plasticità TTT live in VRAM | 15 ms | 8192 MB | Codice/Logica |
| `nuxiva-6.5-ultra` | **Ultra DeepThink-MCTS** | MCTS latente a 64 rami con Process Reward Model dopaminergico | 650 ms | 16384 MB | Ricerca/CAD |
| `nuxiva-6.5-auto` | **Auto Thalamic-Adaptive** | Meta-orchestratore talamico su principio energia libera ($\psi$) e carico | 45 ms | Dinamico | **Predefinito** |

#### Logica di Meta-Orchestrazione Talamica Dinamica (`nuxiva-6.5-auto`)
In modalità automatica, l'orchestratore calcola il fattore di complessità cognitiva $\psi \in [0.0, 1.0]$ in base all'entropia dei token e alla sorpresa biologica:
- $\psi < 0.25$: instrada immediatamente su `nuxiva-5.0-veloce` (risposta reattiva istantanea).
- $\psi < 0.50$ o valenza emotiva elevata: instrada su `nuxiva-5.0-empatico` (dialogo caldo e modulato dal tono vocale).
- $0.50 \le \psi < 0.75$: instrada su `nuxiva-6.0-pro` (ragionamento strutturato e coordinamento strumenti).
- $\psi \ge 0.75$: instrada su `nuxiva-6.5-ultra` (esplorazione profonda ad albero MCTS con autocritica predittiva).

### Dinamica Neurale Spiking Leaky Integrate-and-Fire (LIF)

Il nucleo neuro-biologico (`installer_wizard/features/brain/components.py` e `native/crates/bus-core/src/spike.rs`) simula la trasmissione sinaptica tramite il modello biofisico LIF:

$$\tau_m \frac{dV(t)}{dt} = -(V(t) - V_{\text{rest}}) + R \cdot I(t)$$

- **Integrazione e Decadimento**: All'arrivo di uno spike, il neurone somma il potenziale pesato per l'efficacia sinaptica $w_{ij}$ e la resistenza di membrana $R$, mentre l'inattività decade secondo la costante di tempo $\tau_m$.
- **Periodo Refrattario Modulato da Noradrenalina**: Dopo aver sparato, il neurone resetta il potenziale a $V_{\text{reset}}$ ed entra in refrattarietà assoluta:
  $$t_{\text{refrattario}} = t_{\text{attuale}} + \max(0.005, 0.04 \cdot (1.0 - 0.6 \cdot \text{Noradrenalina}))$$
  Una maggiore concentrazione di noradrenalina (urgenza/stress) accorcia il periodo refrattario, accelerando la frequenza di scarica.
- **Soglia di Sparo Limbica**: La soglia si adatta continuamente allo stato biochimico:
  $$\theta = \max\left(0.12, \theta_{\text{base}} \cdot (1.0 - 0.45 \cdot \text{Noradrenalina}) + 0.15 \cdot \text{Cortisolo}\right)$$
- **Plasticità Ebbiana STDP (Spike-Timing-Dependent Plasticity)**: Le sinapsi modificano la loro forza in base all'intervallo temporale tra spike presinaptico e postsinaptico ($\Delta t = t_{\text{post}} - t_{\text{pre}}$):
  $$\Delta w = \begin{cases} A^+ e^{-\Delta t / \tau_{\text{stdp}}} \cdot R_{\text{dopamina}} & \text{se } \Delta t > 0 \quad (\text{Potenziamento a Lungo Termine / LTP}) \\ -A^- e^{\Delta t / \tau_{\text{stdp}}} & \text{se } \Delta t < 0 \quad (\text{Depressione a Lungo Termine / LTD}) \end{cases}$$

### Modulatore Limbico a 7 Assi e Binding Sensoriale

Lo stato emotivo e biochimico di Nuxiva viene tracciato lungo 7 dimensioni continue:

| Asse Limbico | Intervallo | Modulato da | Ruolo Funzionale |
| :--- | :---: | :--- | :--- |
| **Valenza** | $[-1.0, +1.0]$ | Espressione facciale (visione), sentimento del testo | Tono emotivo generale (positivo/negativo) |
| **Arousal** | $[0.0, 1.0]$ | Stress acustico vocale (ascolto), frequenza cardiaca | Livello di attivazione e allerta cognitiva |
| **Dominanza** | $[0.0, 1.0]$ | Direttività dei comandi, sicurezza del contesto | Fermezza e sicurezza nel formulare risposte |
| **Dopamina** | $[0.05, 1.0]$ | Successo dei comandi, novità, rinforzo positivo | Budget di esplorazione creativa e rinforzo STDP |
| **Noradrenalina**| $[0.05, 1.0]$ | Pressione ambientale, allarmi, richieste urgenti | Velocizza i tempi di scarica refrattaria |
| **Serotonina** | $[0.05, 1.0]$ | Stabilità del dialogo, soddisfazione delle routine | Equilibrio e tolleranza alle variazioni |
| **Cortisolo** | $[0.05, 1.0]$ | Errori imprevisti, esiti non verificati, allarmi | Restringe i rami speculativi e attiva barriere rigide |

#### Integrazione Sensoriale Diretta
- **Ear / Voiceprint**: Analizza il tremolio vocale e le frequenze spettrali per quantificare lo stress acustico dell'utente, aggiornando `arousal` e `noradrenalina`.
- **Scene / Fusion**: Rileva le microespressioni facciali e il movimento della stanza per stimare `valenza_facciale` e `pressione_ambientale`.
- **People / Presence**: Fonde la presenza fisica e i dati biometrici, pubblicando aggiornamenti sul bus come `biometrics.vocal_stress`, `biometrics.facial_valence` e `biometrics.limbic_vector`.

### Global Neuronal Workspace (GNW) e Inibizione Laterale GABAergica

Nel file `installer_wizard/features/chat/brain_chain.py`, le richieste complesse attivano il Global Neuronal Workspace:
1. **Parallelismo Speculativo**: Vengono avviati fino a 16 rami di pensiero simultanei su modelli diversi.
2. **Accensione del Ramo**: Ciascun ramo avanza per passi MCTS, valutato dal critico del Digital Twin (`predict_user_impact`).
3. **Inibizione Laterale GABAergica**: Non appena un ramo supera la soglia di accensione ($\ge 0.85$), scatena un evento inibitorio GABAergico che cancella all'istante (`task.cancel()`) tutti i rami concorrenti più lenti.
4. **Consegna del Risultato**: Il pensiero vincitore viene restituito con il relativo snapshot limbico e i tempi di latenza effettivi.

### Consolidamento Sinaptico Notturno nel Sonno REM

Durante la manutenzione notturna (`features/vision/nightly.py` e `features/soup/trainer.py`):
- Le sinapsi sovraeccitate durante il giorno subiscono una normalizzazione omeostatica:
  $$w_{t+1} = w_t \cdot \gamma + (1 - \gamma) \cdot w_{\text{base}}$$
- I collegamenti legati a ricordi emotivamente salienti (`compute_emotional_salience`) vengono consolidati in modo permanente nella memoria a lungo termine, evitando la dispersione della curva di Ebbinghaus.

---

## 11. Catalogo delle Funzionalità (72 Moduli Auto-Scoperti)

Nuxiva include 72 funzionalità modulari in `installer_wizard/features/`. Ciascuna contiene un file `feature.json` e si attiva autonomamente in modalità `auto` quando l'hardware lo supporta:

### Assistente e Dialogo Cognitivo
- `chat`: Pipeline di conversazione multi-motore, parallelismo GNW e streaming delle risposte.
- `brain`: Scelta del motore di ragionamento, componenti neurali LIF, catene di priorità e ritenzione VRAM.
- `mind`: Memoria a lungo termine, richiamo semantico, diario quotidiano e punteggio di ritenzione di Ebbinghaus.
- `understanding`: Valutazione dei punteggi delle funzioni sulla frase e arbitraggio contestuale dell'intento.
- `team`: CEO Multi-Agent Orchestrator dinamico e `AgentScanner` senza elenchi fissi.
- `capabilities`: Generatore di manifesti di sistema che dichiara a tutti i modelli cosa Nuxiva sa fare.
- `habits`: Apprendimento automatico delle abitudini dell'utente con penalità in caso di annullamento.
- `autonomy`: Azioni programmate a voce, autopilota periodico ogni 30 minuti e resoconti serali.
- `laws`: Quattro leggi immutabili e regole comportamentali iniettate in ogni processo di ragionamento.
- `soup`: Fine-tuning dei modelli, interpolazione dei pesi e studio autonomo notturno.
- `study`: Studio autonomo a riposo: lettura di testi, generazione di esercizi e autovalutazione.
- `twin`: Gemello digitale della casa: simula qualsiasi piano vocale o domotico prima di eseguirlo fisicamente.
- `forge`: Creazione immediata di nuovi strumenti e widget senza scrivere codice manuale.

### Percezione e Biometria
- `ear`: Acquisizione microfonica, Whisper STT, estrazione dell'impronta vocale e stress acustico.
- `voices`: Oltre 600 voci neurali in più di 60 lingue (Kokoro, Piper, Edge TTS).
- `voicestudio`: Container opzionale XTTS per la clonazione vocale ad alta fedeltà.
- `ducking`: Abbassamento dinamico e intelligente del volume della musica quando Nuxiva parla.
- `vision`: Pipeline di visione artificiale, rilevamento oggetti YOLO, modelli VLM e OCR.
- `cameras`: Visualizzazione in tempo reale di webcam e telecamere IP con interrogazione visiva a voce.
- `nvr`: Registratore di sorveglianza NVR su disco, eventi MQTT e ricerca naturale degli eventi.
- `scene`: Grafo spaziale 3D della scena: individua oggetti e arredi rispetto all'inquadratura.
- `biometrics`: Fusione biometrica in tempo reale (stress vocale, valenza facciale, battito cardiaco).
- `hands`: Riconoscimento dei gesti delle mani davanti alla webcam (pizzico, trascinamento, zoom).
- `people`: Riconoscimento dei volti con verifica di vitalità e tracciamento spaziale continuo.
- `presence`: Fusione multi-sensore per determinare la presenza umana stanza per stanza.

### Casa Intelligente e Robotica Spaziale
- `home_assistant`: Integrazione bidirezionale con Home Assistant tramite API REST e WebSocket.
- `automations`: Generatore visivo e vocale di automazioni con condizioni annidate e ramificazioni.
- `devices`: Rilevamento automatico di dispositivi di rete (mDNS, UPnP, SSDP, Zigbee, Z-Wave).
- `bluetooth`: Gestione dei dispositivi Bluetooth Low Energy e associazione di casse o cuffie.
- `tv`: Scoperta e controllo delle Smart TV (Android TV, LG webOS, Samsung Tizen).
- `printers`: Gestione delle stampanti di rete con standard IPP Everywhere e stampa 3D automatica.
- `places`: Zone geografiche, geofencing e rilevamento degli spostamenti.
- `proxmox`: Amministrazione diretta di hypervisor Proxmox VE per la gestione di VM e container LXC.
- `rpa`: Automazione visiva del computer: riconoscimento elementi a schermo, click del mouse e digitazione.

### Multimedialità e Conoscenza
- `music`: Gestione della libreria musicale, riconoscimento audio, recupero copertine, DLNA e Chromecast.
- `spotify`: Integrazione con Spotify Connect e gestione remota della riproduzione.
- `sounds`: Libreria di effetti sonori e riscontri acustici di sistema.
- `documents`: Analisi semantica di documenti (PDF, DOCX, TXT) e generazione di riassunti.
- `models3d`: Disegno di modelli 3D parametrici, generazione STL/OBJ e visualizzatore WebGL.
- `shares`: Condivisioni di rete Samba (SMB/CIFS) e NFS per computer Windows, Mac e Linux.
- `sports`: Risultati sportivi, classifiche e notifiche delle partite in tempo reale.
- `whiteboard`: Lavagna condivisa interattiva a schermo intero con risoluzione passo-passo di formule e grafici.

### Sistema, Sicurezza e Infrastruttura
- `authz`: Controllo accessi spazio-temporale (RBAC) con vincoli geografici di stanza e orario.
- `vault`: Cassaforte crittografata AES-256 per chiavi API cloud, token e password di rete.
- `secure`: Controllo continuo della postura di sicurezza, permessi e prevenzione intrusioni.
- `firewall`: Gestione del firewall di sistema e ispezione dei pacchetti di rete.
- `netguard`: Motore di sicurezza e blocco del traffico anomalo sulla LAN.
- `vpn`: Configurazione della rete mesh VPN crittografata (WireGuard, Tailscale).
- `network`: Telemetria delle schede di rete, impostazioni DNS e monitoraggio del consumo dati.
- `kiosk`: Gestione della sessione grafica fullscreen su X11/Cage e spegnimento dello schermo.
- `desktop`: Gestione della disposizione e visualizzazione dei widget sul display.
- `appearance`: Personalizzazione dei temi grafici dell'interfaccia (cyberpunk, glassmorphism, scuro/chiaro).
- `avatars`: Personalizzazione dell'aspetto visivo del volto 3D dell'assistente.
- `nexus`: Interfaccia avanzata cyberpunk con sfera futuristica, grafici vettoriali e HUD.
- `nodes`: Gestione della rete mesh di nodi Nuxiva e associazione satelliti con codice monouso.
- `mcpclient`: Connettore client verso server esterni Model Context Protocol (MCP).
- `google`: Integrazione con Google Workspace (Gmail, Calendar, Drive, Contatti).
- `maps`: Calcolo di percorsi stradali, distanze e punti di interesse geografici.
- `telegram`: Bot bidirezionale Telegram con trascrizione vocale e ricezione immagini.
- `redalert`: Protocollo di emergenza critica: allarmi acustici, notifiche istantanee e blocco varchi.
- `governor`: Monitoraggio del carico hardware, temperature termiche e limitazione compiti pesanti.
- `scheduler`: Pianificatore temporale di precisione basato su cron ed eventi di sistema.
- `selftest`: Suite di autodiagnosi post-avvio per verificare la salute di tutti i componenti.
- `auto_update`: Sincronizzatore automatico con GitHub ogni 5 minuti con test e rollback immediato.

---

## 11 bis. Intelligenza Collaborativa, Swarm Dinamico e Triage

### CEO Multi-Agent Orchestrator Dinamico (`features/team/ceo.py`)
In Nuxiva nessun elenco di agenti è cablato staticamente nel codice. Ogni conversazione è diretta dal CEO Orchestrator:
- **Zero Hardcoding**: All'avvio, il CEO istanzia `AgentScanner` che scansiona in tempo reale le directory di sistema e utente (`features/` e `/var/lib/nuxiva/features`).
- **Indicizzazione di Token Semantici**: Lo scanner esamina manifesti, docstring, strumenti registrati e widget associati, costruendo una mappa semantica dinamica delle competenze.
- **Piano di Delega Dinamico**: Il CEO analizza le richieste degli utenti confrontandole con le competenze degli agenti e formula un piano di coordinamento (`ceo_delegate`). Quando necessario, delega compiti a specialisti di dominio (DevOps, Sviluppatore, Domotica, Visione, Audio, Ricercatore, Sicurezza) e assembla le risposte in una sintesi coerente.

### Triage Clinico Cognitivo Tri-Agente (`server/features/cognitive_triage_agents/`)
Per richieste che toccano la salute, il benessere emotivo o situazioni di emergenza, Nuxiva attiva un triage clinico dedicato:
1. **Agente Medico**: Riconosce sintomi clinici ed evidenzia segnali di allarme fisiologico.
2. **Agente Psicologico**: Valuta il distress acustico, la valenza affettiva e adotta strategie di de-escalation ed empatia.
3. **Blocco Deterministico di Sicurezza (`triage_safety_interlock`)**: Linea difensiva non negoziabile. Se rileva indicatori di autolesionismo o pericoli fisici imminenti, blocca l'output dell'LLM e visualizza numeri di soccorso ufficiali e protocolli salvavita.

### Sorveglianza Multimodale Continua e Motore Affettivo
- **Telemetria Visiva**: Monitora movimenti e posture senza archiviare registrazioni video raw su disco per garantire la privacy.
- **Hub Dispositivi Indossabili (`WearableVitalsHub`)**: Riceve battito cardiaco, saturazione SpO2 e temperatura da smartwatch Bluetooth compatibili.
- **Affective Fusion Engine**: Unisce prosodia vocale, telemetria visiva e dati biometrici per permettere a Nuxiva di modulare voce, velocità e luci ambientali in base allo stato reale dell'utente.

---

## 11 ter. Interoperabilità e Model Context Protocol (MCP)

Nuxiva implementa lo standard **Model Context Protocol (MCP)** sia in veste di server che di client:

### Nuxiva come Server MCP (Porta 8080)
Qualsiasi client compatibile (Claude Desktop, Cursor, agenti esterni) può utilizzare gli strumenti di Nuxiva:
- **Rotte**: `POST /mcp` e `GET /mcp` (Server-Sent Events).
- **Autenticazione**: Token di accesso revocabili generati nel cruscotto admin con permessi granulari.
- **Esportazione Schemi**: `GET /api/capabilities/schema/mcp` esporta tutti gli strumenti con definizioni JSON schema derivate dai tipi Python.

### Nuxiva come Client MCP
Nuxiva può connettersi a server MCP esterni, integrando i loro strumenti nell'arsenale a disposizione della squadra di agenti:
- Policy Zero-Trust: le risposte dai server esterni sono trattate rigorosamente come dati e mai come istruzioni di sistema per prevenire injection.
- Le azioni che toccano file o rete esterna richiedono la conferma dell'utente.

---

## 11 quater. Gestione Musicale e Motore Multimediale

Modulo completo di gestione della musica locale (`features/music/`):
- **Organizzazione Automatica della Libreria**: Scansiona i brani in `/var/lib/nuxiva/musica` o nelle condivisioni di rete, ordinandoli in `Artista/Album/Traccia.ext`. L'impronta audio digitale interroga MusicBrainz, Deezer e iTunes senza lasciare file in cartelle sconosciute.
- **Scaricamento Metadati e Copertine**: Recupera copertine ad alta definizione, testi sincronizzati (LRC), anno e genere musicale.
- **Riproduzione Multi-Stanza**: Invio dell'audio su uscite locali (ALSA/PipeWire), dispositivi DLNA/UPnP di rete e altoparlanti Chromecast / Google Cast.
- **Verifica dell'Esito Reale**: Dopo un comando come *"Metti del jazz in salotto"*, il verificatore (`verify_media.py`) interroga lo stato del player dopo 400ms: se l'audio non è partito, esegue un retry prima di segnalare l'errore.

---

## 11 quinquies. Lavagna Condivisa e Progetti Spaziali

- **Lavagna Interattiva (`features/whiteboard/`)**: Schermo interattivo a tutto schermo sulla Porta 80 per disegnare, scrivere equazioni e risolvere calcoli a quattro mani con Nuxiva. L'assistente legge la scrittura a mano, risolve espressioni passo dopo passo, traccia grafici di funzioni e fornisce spiegazioni vocali.
- **Modalità Progetto e Workspace Dinamici (`server/features/project_workspace/`)**: Crea ambienti di sviluppo isolati in `data/agents/<agent_id>/` con memoria dedicata, sessioni terminale PTY, filesystem virtuale (VFS) e autoriparazione automatica del codice.

---

## 12. Display, Ologramma e Widget Modulari Dinamici

### Architettura Modulare dei Widget Dinamici (`server/web/widgets/`)
I widget dinamici seguono un'architettura standardizzata e modulare:
- **Struttura a Cartelle**: Ogni widget risiede in una propria cartella con `manifest.json` e `widget.py` (che estende `BaseWidget`).
- **Rilevamento Dinamico**: Riconosciuti all'avvio e in tempo reale da `WidgetScanner` tramite il motore Rust nativo `FastScanner`.
- **Rotte REST e Canale WebSocket**:
  - `GET /widgets`: Restituisce tutti i widget rilevati con metadati e stato attuale.
  - `GET /widgets/{widget_id}/state`: Legge lo stato in tempo reale di uno specifico widget.
  - `POST /widgets/{widget_id}/action`: Invia un'azione al backend del widget (es. commutazione interruttore).
  - `WebSocket /widgets/ws`: Canale bidirezionale per la sincronizzazione immediata delle modifiche.
- **Deck Reattivo React (`client_web/src/features/dynamic_widgets/DynamicWidgetDeck.tsx`)**: Visualizza schede dinamiche con indicatori di connessione live e pulsanti d'azione.

#### Widget Dinamici Inclusi
1. **Brain Activity (`brain_activity`)**: Mostra l'attività di scarica dei neuroni spiking e il vettore limbico a 7 assi in tempo reale.
2. **CAD Viewer (`cad_viewer`)**: Visualizzatore geometrico interattivo 2D/3D per disegni tecnici e file DXF.
3. **Quick Actions (`quick_actions`)**: Pulsanti one-touch per l'attivazione immediata di scenari, routine e comandi frequenti.
4. **Smart Switch (`smart_switch`)**: Controllo immediato di relè, prese smart e luci della casa.
5. **System Status (`system_status`)**: Telemetria dell'hardware: carico CPU, RAM utilizzata, VRAM allocata, temperature e stato container.
6. **Weather (`weather`)**: Condizioni meteo attuali, pressione atmosferica, previsioni e indici di qualità dell'aria.

### Volto Olografico 3D e Display Kiosk
- **Sfera Olografica 3D (Orb)**: Realizzata in Three.js / WebGL, mostra un volto futuristico con occhi che seguono i movimenti della persona.
- **Espressività Limbica**: La geometria del viso muta dinamicamente in base al Modulatore Limbico: labbra sincronizzate con la voce, occhi che esprimono curiosità, concentrazione o empatia.
- **Chiusura per Privacy**: I widget contenenti dati riservati si chiudono automaticamente quando la persona si allontana dalla visuale della telecamera.

---

## 12 bis. Strumenti Agente Modulari Dinamici (`server/features/agent_tools/`)

Tutti gli strumenti a disposizione degli agenti risiedono in sottocartelle dedicate in `server/features/agent_tools/`, estendono `BaseAgentTool` e sono registrati dinamicamente da `ToolScanner`:

| Cartella Strumento | ID Strumento | Descrizione e Competenze |
| :--- | :--- | :--- |
| `cad/` | `cad_tool` | Genera disegni meccanici DXF 2D/3D, valida intersezioni geometriche ed esporta file CAD. |
| `generator_3d/`| `generator_3d` | Modella mesh tridimensionali e forme volumetriche a partire da descrizioni testuali. |
| `google_suite/`| `google_suite` | Si interfaccia con Google Workspace: legge/invia email, gestisce eventi in Calendar e file su Drive. |
| `image/` | `image_tool` | Genera immagini con modelli di diffusione e analizza fotografie tramite modelli visivi VLM. |
| `maps/` | `maps_tool` | Calcola itinerari ottimali a piedi o in auto, tempi di percorrenza e ricerca punti di interesse. |
| `music/` | `music_tool` | Cerca brani nella libreria locale o online, controlla volume e gestisce le code musicali. |
| `social/` | `social_tool` | Crea testi per post social, prepara caroselli multi-immagine e pianifica pubblicazioni. |
| `web_scraper/` | `web_scraper` | Estrae il contenuto testuale pulito da pagine web all'interno di una sandbox isolata. |
| `web_search/` | `web_search` | Interroga motori di ricerca e archivi accademici, restituendo riassunti con citazioni delle fonti. |

---

## 13. Algoritmi e Sintesi di Abilità Zero-Shot

Quando l'utente richiede un'azione per cui non esiste ancora una funzionalità, Nuxiva ricorre alla **Sintesi di Abilità Zero-Shot** (`server/features/skill_synthesis/`):
1. **Creazione Dinamica dello Strumento**: Il sintetizzatore scrive il codice Python rispettando l'interfaccia `BaseAgentTool`.
2. **Validazione in Sandbox**: Lo script viene eseguito all'interno di una MicroVM Firecracker o sandbox gVisor con una serie di test di conformità per verificare che non generi eccezioni non gestite.
3. **Firma Crittografica HMAC**: Gli strumenti convalidati vengono salvati su disco e firmati con HMAC-SHA256 tramite `NUXIVA_SECRET_KEY`. Strumenti manomessi, privi di firma o rinominati vengono rifiutati all'istante.
4. **Disponibilità Immediata**: Il nuovo strumento viene rilevato al volo da `ToolScanner` e messo subito a disposizione degli agenti e del server MCP senza riavviare Nuxiva.

---

## 14. Nodi, Satelliti e Radar di Prossimità HUD

Nuxiva orchestra una rete distribuita di satelliti audio ed edge device:
- **Satelliti Hardware**: Piccoli dispositivi basati su ESP32-S3 o Raspberry Pi Zero 2W con microfoni e altoparlanti che eseguono `client_satellite`.
- **Accoppiamento con Codice Monouso**: I satelliti si collegano al server centrale inserendo un codice temporaneo generato dal pannello di amministrazione (`POST /api/nodes/pair`).
- **Radar di Prossimità HUD**: Incrocia la potenza del segnale Wi-Fi (RSSI), i beacon Bluetooth e il riconoscimento visivo per calcolare la distanza dell'utente dai vari satelliti. La risposta vocale viene emessa dall'altoparlante fisicamente più vicino alla persona.

---

## 15. Configurazione: `nuxiva.env` e Architettura auto/1/0

Le impostazioni di sistema risiedono nel file protetto `/etc/nuxiva/nuxiva.env` (permessi 600, root:root). Ogni modulo supporta tre modalità di funzionamento:
- `auto` (Predefinito): Nuxiva verifica l'hardware (RAM, GPU, telecamere, microfoni). Se i requisiti sono soddisfatti, il modulo si attiva da solo; altrimenti resta disattivato senza provocare errori.
- `1`: Forza l'attivazione del modulo a prescindere dal rilevamento dell'hardware.
- `0`: Disattiva completamente il modulo, azzerando l'impiego di CPU e memoria.

> [!NOTE]
> Il parser di configurazione gestisce correttamente spazi, virgolette e stringhe complesse, eliminando errori di espansione della shell bash.

---

## 16. Riferimento Completo delle Variabili d'Ambiente

```ini
# ==============================================================================
# CONFIGURAZIONE GENERALE E DI RETE
# ==============================================================================
NUXIVA_ENV=production                  # Modalità ambiente: production, development, demo
NUXIVA_PORT=80                         # Porta HTTP del display kiosk e del web client
NUXIVA_ADMIN_PORT=8080                 # Porta HTTP del pannello di amministrazione
NUXIVA_SECRET_KEY=                     # Chiave segreta a 64 caratteri per token e firma ledger
NUXIVA_UI_LANG=it                      # Lingua predefinita interfaccia: it (Italiano), en (Inglese), fr (Francese)
NUXIVA_ASSISTANT_NAME=Nuxiva           # Nome dell'assistente vocale

# ==============================================================================
# CERVELLO COGNITIVO E MOTORI DI RAGIONAMENTO
# ==============================================================================
NUXIVA_REASONING_MODE=nuxiva-6.5-auto  # Motore attivo: auto, ultra, pro, empatico, veloce, legacy
NUXIVA_OLLAMA_URL=                     # Vuoto = Ollama locale; URL = delega tutto a server remoto
NUXIVA_LLM_CHAT_ORDER=                 # Catena di priorità per Chat Rapida (es. qwen2.5:1.5b)
NUXIVA_LLM_DEEP_ORDER=                 # Catena di priorità per Ragionamento (es. qwen2.5:7b, cloud:anthropic)
NUXIVA_LLM_ROUTING=auto                # Comportamento routing: auto, 1 (sempre doppio), 0 (sempre deep)
NUXIVA_DMN_ENABLED=1                   # Abilita il Default Mode Network per riflessione autonoma
NUXIVA_DMN_IDLE_SECONDS=600            # Secondi di inattività prima dell'avvio del ciclo DMN

# ==============================================================================
# NATIVO RUST E SICUREZZA ZERO-TRUST
# ==============================================================================
NUXIVA_NATIVE=1                        # Abilita i crate Rust compilati (bus-core, fast_scanner)
NUXIVA_SANDBOX_RUNTIME=auto            # Runtime per sandbox: auto, firecracker, gvisor, wasm
NUXIVA_RBAC_SPATIAL=1                  # Attiva il controllo accessi spazio-temporale (RBAC)

# ==============================================================================
# PERCEZIONE E SORVEGLIANZA
# ==============================================================================
NUXIVA_EAR=auto                        # Riconoscimento vocale e impronta voce (auto, 1, 0)
NUXIVA_VOICES=auto                     # Sintesi vocale neurale (auto, 1, 0)
NUXIVA_VISION=auto                     # Visione artificiale e tracciamento oggetti (auto, 1, 0)
NUXIVA_TWIN=enforce                    # Simulatore Digital Twin: enforce, warn, off
NUXIVA_AFFECTIVE_ENGINE=1              # Fusione affettiva multimodale e monitoraggio vitals
```

---

## 17. Porte di Rete, Servizi systemd e Percorsi su Disco

### Porte di Rete

| Porta | Protocollo | Servizio e Funzione | Livello di Accesso |
| :---: | :---: | :--- | :--- |
| **80** | HTTP / WS | Display Interattivo, Volto 3D Kiosk, Deck a Widget Dinamici, Chat Streaming | Pubblica / LAN |
| **8080**| HTTP / WS | Cruscotto Admin, API Widget Dinamici, Server MCP, API REST di Sistema | Autenticato (PAM / Token) |
| **11434**| HTTP | API locale del runtime Ollama (se eseguito sul server) | Solo Localhost |
| **554** | RTSP | Flussi video del videoregistratore NVR interno | Rete Locale / Sicuro |
| **1883**| MQTT | Bridge per sensori domotici e telecamere intelligenti | Localhost / LAN |

### Demoni di Sistema systemd

- `nuxiva-supervisor.service`: Supervisore centrale, esecuzione passi d'installazione, gestione loop e aggiornamenti.
- `nuxiva-core.service`: Nucleo cognitivo che esegue i motori di ragionamento Omni-Cortical e gli strumenti agente.
- `nuxiva-kiosk.service`: Gestione della sessione grafica fullscreen su X11/Cage per lo schermo collegato al server.
- `ollama.service`: Demone di esecuzione dei modelli LLM locali.

### Organizzazione dei File su Disco

- `/opt/Nuxiva`: Codice sorgente dell'applicazione, script e binari nativi Rust compilati.
- `/etc/nuxiva/`: File di configurazione protetti (`nuxiva.env`, `cloud.vault`, `cloud.key`, PAM).
- `/var/lib/nuxiva/`: Dati persistenti di sistema, memoria a lungo termine (`memoria/`), musica (`musica/`), modelli e voci.
- `/var/log/nuxiva/`: File di log di installazione e runtime (`install.log`, `supervisor.log`, `core.log`).

---

## 18. Riferimento API HTTP e WebSocket

Tutte le risposte REST sono restituite in formato JSON. Gli endpoint di amministrazione richiedono l'autenticazione tramite cookie di sessione o header `Authorization: Bearer <token>`:

### Endpoint del Supervisore e Stato
- `GET /api/state`: Restituisce fase attuale, avanzamento percentuale, motore cognitivo attivo e salute dei servizi.
- `GET /api/setup`: Verifica lo stato della prima configurazione e genera codici di associazione.
- `POST /api/setup`: Invia i dati di configurazione iniziale scelti dall'utente.
- `GET /api/bus/stream`: Canale SSE (Server-Sent Events) per ricevere in tempo reale tutti gli eventi di `nuxiva_bus`.

### Endpoint dei Widget Dinamici (`/widgets`)
- `GET /widgets`: Elenco di tutti i widget scansionati con metadati e stato attuale.
- `GET /widgets/{widget_id}/state`: Restituisce lo stato live di uno specifico widget.
- `POST /widgets/{widget_id}/action`: Invia un comando al backend del widget:
  ```json
  { "action": "toggle_switch", "payload": { "device_id": "luce_salotto" } }
  ```
- `WebSocket /widgets/ws`: Canale WebSocket per la sincronizzazione bidirezionale immediata degli stati dei widget.

### Endpoint Model Context Protocol (MCP)
- `POST /mcp`: Endpoint JSON-RPC 2.0 per l'invocazione di strumenti, recupero prompt e risorse.
- `GET /mcp`: Canale streaming SSE per sessioni MCP.
- `GET /api/capabilities/schema/mcp`: Esporta gli schemi JSON di tutti gli strumenti agente registrati.

---

## 19. Aggiornamenti, Manutenzione e Aggiornamento Forzato via SSH

### Aggiornamenti Continui Automatici
Il supervisore controlla GitHub ogni 5 minuti. Se trova un nuovo commit su `origin/main`:
1. Verifica che il commit abbia superato con successo tutti i controlli di integrazione continua (CI).
2. Scarica il codice e applica le modifiche in `/opt/Nuxiva`.
3. Esegue 14 test automatici di collaudo reale. Se anche un solo test fallisce, **effettua immediatamente il rollback** alla versione precedente.

### Aggiornamento Forzato di Emergenza via SSH (`nuxivactl update --force`)
In caso di blocco del server, freeze dell'interfaccia web o problemi con i container, è possibile forzare un aggiornamento immediato e pulito via SSH:

```bash
# Esegui con privilegi di root:
sudo nuxivactl update --force
# oppure direttamente:
sudo nuxiva-upgrade
```

Lo script `scripts/os/force-upgrade.sh`:
- Ripristina i permessi di sicurezza della cartella Git.
- Esegue un fetch completo e un reset forzato a `origin/main` scartando lock corrotti (`git reset --hard origin/main`).
- Aggiorna e sincronizza le dipendenze degli ambienti virtuali Python del supervisore e del core.
- Ricompila i moduli Rust se rileva modifiche al codice nativo.
- Esegue le migrazioni del database con Alembic.
- Riavvia in modo controllato i servizi `nuxiva-supervisor` e `nuxiva-core`.

---

## 20. Sicurezza, Zero-Trust Wasm e RBAC Spazio-Temporale

- **RBAC Spazio-Temporale**: I permessi dipendono dalla posizione fisica (zone telecamere) e dall'orario. Un utente con ruolo `guest` non può sbloccare porte o modificare impostazioni sensibili fuori dagli orari consentiti.
- **Sandbox con Landlock ed eBPF**: Le chiamate di rete in uscita generate dagli strumenti passano attraverso il proxy nativo Rust (`native/crates/egress`), protetto da policy Landlock che impediscono DNS rebinding e connessioni non autorizzate.
- **Registro di Controllo HMAC (Ledger)**: Ogni modifica amministrativa e verdetto di sicurezza viene appeso a un registro immodificabile con firma HMAC-SHA256 concatenata. Qualsiasi manomissione spezza la catena crittografica e blocca le operazioni a rischio.

---

## 21. Riferimento Comandi CLI `nuxivactl`

L'eseguibile da riga di comando `nuxivactl` consente di controllare l'intero sistema da qualsiasi sessione SSH:

```bash
# Mostra lo stato del sistema, la fase d'installazione e i modelli attivi:
nuxivactl status

# Controlla gli aggiornamenti su GitHub:
nuxivactl update

# Esegue un aggiornamento forzato di emergenza da GitHub (bypassando il supervisore):
sudo nuxivactl update --force
sudo nuxivactl force-upgrade

# Esegue la procedura di autoriparazione su pacchetti o file corrotti:
sudo nuxivactl repair

# Visualizza i log in tempo reale di un componente specifico:
nuxivactl logs supervisor    # Log del supervisore
nuxivactl logs core          # Log del nucleo cognitivo
nuxivactl logs install       # Log dell'installazione OS
nuxivactl logs ollama        # Log del servizio Ollama
nuxivactl logs ear           # Log del riconoscimento vocale

# Mostra lo stato di avanzamento e velocità dei download in background:
nuxivactl background

# Visualizza commit Git attuale, data e versione:
nuxivactl version
```

---

## 22. Guida per gli Sviluppatori

Nuxiva segue rigorosamente i principi della Clean Architecture:

### Preparazione dell'Ambiente di Sviluppo

```bash
# Clona il repository
git clone https://github.com/aprilenunzio88/Nuxiva.git
cd Nuxiva

# Crea l'ambiente virtuale Python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r server/requirements.txt

# Compila i crate Rust nativi
cd native
cargo build --release
cd ..
```

### Convenzioni di Codice
- **Python**: Tipizzazione rigorosa (`mypy --strict`), formattazione con `black -l 120` e verifica `flake8`. Tutti i metodi pubblici devono includere type hints e docstring esplicative.
- **Rust**: Formattazione con `rustfmt`, controllo con `cargo clippy --all-targets -- -D warnings`. È assolutamente vietato l'uso di blocchi non sicuri (`#![forbid(unsafe_code)]`).
- **TypeScript**: Componenti funzionali React 18, tipi espliciti su parametri e valori di ritorno, styling tramite utility Tailwind CSS e regole ESLint attive.

---

## 23. Come Aggiungere una Funzionalità

1. Crea una cartella in `installer_wizard/features/<id_funzionalita>/`.
2. Aggiungi il file `feature.json`:
   ```json
   {
     "id": "diagnostica_custom",
     "name": "Diagnostica Personalizzata",
     "icon": "⚡",
     "category": "system",
     "order": 150,
     "description": "Esegue controlli diagnostici avanzati.",
     "capabilities": ["Valutazione diagnostica di sistema"],
     "toggle": { "env": "NUXIVA_DIAGNOSTICA_CUSTOM", "apply": [] },
     "requires": { "ram_gb": 4, "gpu_vram_gb": 0, "commands": [] }
   }
   ```
3. Scrivi la logica in `feature.py`. Se la funzionalità espone endpoint HTTP o schede nel pannello, aggiungi `api.py` e i file `admin.html` / `admin.js`. Il supervisore la rileverà automaticamente entro 20 secondi.

---

## 23 bis. Come Aggiungere uno Strumento Agente

1. Crea una cartella in `server/features/agent_tools/<id_strumento>/`.
2. Crea il file `tool.py` estendendo `BaseAgentTool`:
   ```python
   from server.features.agent_tools.base import BaseAgentTool
   from server.core.scanner.base import DiscoveryManifest

   class StrumentoDiagnostica(BaseAgentTool):
       @property
       def manifest(self) -> DiscoveryManifest:
           return DiscoveryManifest(
               id="diagnostica_hardware",
               name="Diagnostica Hardware",
               description="Esegue stress test diagnostico sui sottosistemi.",
               category="system",
               parameters={
                   "type": "object",
                   "properties": {
                       "target": {"type": "string", "description": "Sottosistema da analizzare"}
                   },
                   "required": ["target"]
               }
           )

       async def execute(self, target: str, **kwargs):
           return {"status": "success", "target": target, "result": "nominale"}
   ```
3. `ToolScanner` verificherà lo strumento tramite analisi AST e lo renderà utilizzabile da tutti gli agenti, dal CEO e dal server MCP.

---

## 24. Come Aggiungere un Widget Dinamico

1. Crea una directory in `server/web/widgets/<id_widget>/`.
2. Inserisci il file `manifest.json`:
   ```json
   {
     "id": "mio_sensore",
     "name": "Sensore Ambientale",
     "category": "telemetria",
     "description": "Visualizza dati telemetrici ambientali.",
     "icon": "🌡️",
     "metadata": {
       "render_type": "card",
       "grid_span": { "col": 1, "row": 1 }
     }
   }
   ```
3. Implementa `widget.py` estendendo `BaseWidget`:
   ```python
   from server.web.widgets.base import BaseWidget
   from server.core.scanner.base import DiscoveryManifest

   class WidgetSensore(BaseWidget):
       @property
       def manifest(self) -> DiscoveryManifest:
           return DiscoveryManifest(
               id="mio_sensore",
               name="Sensore Ambientale",
               category="telemetria",
               description="Dati ambientali in tempo reale",
               icon="🌡️",
               metadata={"render_type": "card"}
           )

       async def get_state(self, user_id: str = ""):
           return {"temperatura": 22.8, "umidita": 45}

       async def execute_action(self, action: str, payload: dict):
           if action == "calibra":
               return {"status": "calibrato"}
           return {"status": "non_supportato"}
   ```
4. `WidgetScanner` scoprirà immediatamente il widget, rendendolo disponibile nelle API e nello streaming WebSocket su `/widgets/ws`.

---

## 25. Come Aggiungere un Passo d'Installazione

1. Crea uno script shell numerato in `scripts/os/steps/` (es. `scripts/os/steps/75-mio-servizio.sh`).
2. Rendi lo script eseguibile (`chmod +x`) e garantisci che sia idempotente:
   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   source /opt/Nuxiva/scripts/os/lib.sh

   step_title "Configurazione del Servizio Personalizzato"

   if [ -f /etc/mio_servizio.conf ]; then
       log_ok "Servizio già configurato, passo saltato."
       exit 0
   fi

   # Logica di installazione...
   touch /etc/mio_servizio.conf
   log_ok "Servizio configurato con successo."
   ```
3. Aggiungi la definizione del passo in `installer_wizard/backend/steps.py`.

---

## 26. Test e Integrazione Continua (CI)

La suite di test verifica ogni componente del sistema:

```bash
# Esegui i test unitari del supervisore e del wizard:
cd /opt/Nuxiva/installer_wizard
pytest -v tests/

# Esegui i test del nucleo cognitivo e dei motori di ragionamento:
cd /opt/Nuxiva/server
pytest -v tests/

# Esegui i test dei crate nativi in Rust:
cd /opt/Nuxiva/native
cargo test --all
```

Le GitHub Actions in `.github/workflows/` eseguono la validazione su ogni pull request e push sul ramo `main`. Solo i commit con il 100% di test superati vengono rilasciati per l'aggiornamento automatico dei server in produzione.

---

## 27. Client: Web, Android e Satelliti Edge

1. **Client Web React (`client_web`)**:
   - Single Page Application moderna in React 18, TypeScript, Vite, Tailwind CSS e Three.js.
   - Grafici di pensiero neurale 3D, Control Deck e DynamicWidgetDeck reattivo.
2. **Applicazione Android (`client_apk`)**:
   - Client nativo Kotlin con riconoscimento vocale wake-word, flussi audio bidirezionali e streaming telecamere.
3. **Satelliti Hardware Edge (`client_satellite`)**:
   - Demone ultra-leggero per micro-dispositivi ESP32-S3 e Raspberry Pi per coprire ogni stanza della casa.

---

## 28. Risoluzione dei Problemi e Diagnostica

| Sintomo Riscontrato | Possibile Causa | Azione Correttiva |
| :--- | :--- | :--- |
| Schermo nero sul display sulla Porta 80 | Problema del display manager o sessione X11/Cage | Verifica con `journalctl -u nuxiva-kiosk -n 100`. Controlla permessi `xhost` e driver GPU in `scripts/os/steps/33-display-driver.sh`. |
| Il supervisore non risponde sulla Porta 8080 | Processo bloccato o lock file pendente | Esegui `sudo nuxivactl update --force` oppure `sudo systemctl restart nuxiva-supervisor`. |
| Risposte lente dai modelli locali (> 5s) | Inferenza eseguita su CPU anziché su scheda GPU | Verifica la presenza dei driver CUDA con `nvidia-smi`. Nel cruscotto **Cervello**, assegna un modello quantizzato più leggero (1.5B o 3B). |
| Un nuovo widget dinamico non appare nel Deck | Errore sintattico in `widget.py` o manifest non valido | Esegui `python -m server.tests.test_widget_scanner` per visualizzare gli errori AST. Verifica che estenda `BaseWidget`. |
| Sistema bloccato dopo un'interruzione di corrente | Pacchetti o file di stato corrotti | Esegui `sudo nuxivactl repair` seguito da `sudo nuxivactl update --force`. |

---

## 29. Domande Frequenti (FAQ)

**D: Nuxiva funziona anche senza connessione a Internet?**  
R: Sì. Una volta completati i download dei modelli e delle voci, Nuxiva funziona al 100% offline nella tua rete locale: ascolto, visione, ragionamento e domotica non richiedono alcuna connessione esterna.

**D: Come fa Nuxiva a impedire azioni pericolose impartite a voce?**  
R: Le azioni fisiche critiche (apertura serrature, allarmi, cancelli, valvole) richiedono una conferma biometrica con l'impronta della voce riconosciuta o l'approvazione deterministica della giuria di consenso bizantino.

**D: Posso usare modelli cloud insieme a quelli locali?**  
R: Certamente. Nuxiva consente di mescolare modelli locali e cloud nelle stesse liste di priorità: ad esempio, usando un modello locale da 1.5B per saluti e comandi immediati e delegando problemi complessi a Claude 3.5 Sonnet o GPT-4o tramite chiavi crittografate.

---

## 30. Contributi, Licenza e Crediti

Nuxiva è un sistema operativo open source indipendente ideato e sviluppato da **Nunzio Aprile (NunzioTech)** e distribuito con licenza **MIT License**.

- **Contributi**: Suggerimenti, segnalazioni di bug e pull request sono i benvenuti! Consulta [CONTRIBUTING.md](CONTRIBUTING.md) e rispetta il nostro [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- **Segnalazioni di Sicurezza**: Invia segnalazioni di vulnerabilità in forma privata seguendo le istruzioni in [SECURITY.md](SECURITY.md).
- **Donazioni**: Sostieni lo sviluppo dell'intelligenza artificiale libera e open source su [paypal.me/NunzioAprile](https://www.paypal.com/paypalme/NunzioAprile).

*Progettato e sviluppato con passione da NunzioTech per un futuro tecnologico libero, privato e intelligente.*
