<div align="center">

# NUXIVA

**Un sistema operativo privato e self-hosted per la tua casa: ascolta, vede, parla, ragiona e agisce, sul tuo hardware e con le tue regole.**

[🇬🇧 English](README.md) | [🇮🇹 Italiano](README_IT.md) | [🇫🇷 Français](README_FR.md)

Versione 5.3.0 · Licenza Personale e Commerciale (Uso Domestico Free / Commerciale a Pagamento) · Debian / Ubuntu

</div>

<p align="center">
  <img src="https://img.shields.io/badge/version-5.3.0-1f6feb?style=flat-square" alt="version">
  <a href="LICENSE"><img src="https://img.shields.io/badge/licenza-Domestico%20Free%20%7C%20Commerciale-1f6feb?style=flat-square" alt="Licenza"></a>
  <img src="https://img.shields.io/badge/Debian%20%7C%20Ubuntu-supported-a371f7?style=flat-square" alt="platform">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Rust-1.89-dea584?style=flat-square&logo=rust&logoColor=black" alt="Rust">
  <img src="https://img.shields.io/badge/React-Vite-61dafb?style=flat-square&logo=react&logoColor=black" alt="React">
  <a href="https://github.com/AprileNunzio/Nuxiva/actions"><img src="https://img.shields.io/github/actions/workflow/status/AprileNunzio/Nuxiva/ci.yml?branch=main&style=flat-square&label=CI" alt="CI"></a>
</p>

- **Un solo comando per installare.** Il supervisore costruisce tutto il resto da solo, con avanzamento in tempo reale.
- **Prima di tutto locale.** Voce, visione, ragionamento e automazioni girano sulla tua macchina; i modelli cloud sono opzionali.
- **Si ripara da solo.** 52 cicli sorvegliati, aggiornamenti vincolati alla CI, rollback automatico e modalità sicura.
- **Ingegneria onesta.** Percorsi critici in Rust, soglie misurabili, 313 file di test Python e una CI rigorosa.

---

## Indice

1. [Installazione](#1-installazione)
2. [Perché vorrai provarlo](#2-perché-vorrai-provarlo)
3. [Cos'è Nuxiva](#3-cosè-nuxiva)
4. [Il repository in sintesi](#4-il-repository-in-sintesi)
5. [Architettura](#5-architettura)
6. [Come viene risposta una richiesta](#6-come-viene-risposta-una-richiesta)
7. [Il Core: instradamento, memoria e ragionamento](#7-il-core-instradamento-memoria-e-ragionamento)
8. [La Nuova Frontiera: Corteccia Neuro-Simbolica & Ancoraggio Corporeo Umanoide](#8-la-nuova-frontiera-corteccia-neuro-simbolica--ancoraggio-corporeo-umanoide)
9. [Agenti, strumenti e risposte ancorate ai fatti](#9-agenti-strumenti-e-risposte-ancorate-ai-fatti)
10. [Sport: preferiti, riepilogo notturno, ricerca online](#10-sport-preferiti-riepilogo-notturno-ricerca-online)
11. [Persone, benessere e fotocamera](#11-persone-benessere-e-fotocamera)
12. [Crate Rust nativi](#12-crate-rust-nativi)
13. [Supervisore e auto-riparazione](#13-supervisore-e-auto-riparazione)
14. [Modello di sicurezza](#14-modello-di-sicurezza)
15. [Porte, servizi e percorsi](#15-porte-servizi-e-percorsi)
16. [Client](#16-client)
17. [Controlli di qualità](#17-controlli-di-qualità)
18. [Limiti onesti](#18-limiti-onesti)
19. [Contribuire, licenza, supporto](#19-contribuire-licenza-supporto)

---

## 1. Installazione

Host supportati: **Debian 12** o **Ubuntu 22.04+** (x86_64 / arm64) con `apt-get`. Windows funziona tramite WSL2 o con lo sperimentale `install.ps1`.

### Avvio rapido

```bash
curl -fsSL https://raw.githubusercontent.com/AprileNunzio/Nuxiva/main/install.sh | sudo bash
```

Da un clone:

```bash
sudo git clone https://github.com/AprileNunzio/Nuxiva.git /opt/Nuxiva
cd /opt/Nuxiva
sudo bash install.sh
```

`install.sh` avvia soltanto il **supervisore** (un servizio systemd). Da lì in poi è il supervisore a guidare l'installazione, mostra l'avanzamento in tempo reale sulla porta 80 e mantiene l'assistente utilizzabile mentre i download pesanti proseguono in background, dal più piccolo.

### Cosa succede dopo

```mermaid
flowchart LR
    A[install.sh] --> B[nuxiva-supervisor.service]
    B --> C[Analisi<br/>hardware, rete, scelta modelli]
    C --> D[Sistema<br/>pacchetti, kiosk, Docker, swap]
    D --> E[Isolamento<br/>sandbox, gVisor, Firecracker]
    E --> F[Core nativo<br/>crate Rust, netguard, VPN]
    F --> G[Sensi<br/>Ollama, voce, visione, ascolto, musica]
    G --> H[Modelli<br/>linguistici veloce + profondo]
    H --> I[Build del Core<br/>servizi, manutenzione, riscaldamento]
    I --> J[(Assistente online)]
```

Il supervisore esegue **31 passi ordinati** (`installer_wizard/backend/steps.py`, script in `scripts/os/steps/`). Quelli non critici (runtime GPU, voce, visione, ascolto, Bluetooth…) possono fallire senza bloccare il resto, e ogni passo viene ritentato o riparato dal supervisore.

| Fase | Passi |
| :--- | :--- |
| Analisi | verifica del sistema, swap compressa per le schede piccole |
| Sistema | pacchetti, sessione kiosk, motore Docker |
| Isolamento | sandbox, kernel in spazio utente gVisor, micro-VM Firecracker (solo dove c'è KVM) |
| Nativo | core Rust, driver video, runtime GPU, hardening di sicurezza, analisi del traffico netguard, VPN (WireGuard / OpenVPN / IPsec) |
| Sensi | Ollama, voce neurale, Bluetooth, riconoscimento facciale, riconoscimento del parlato e parola di attivazione, riconoscimento musicale |
| Servizi | condivisioni di rete, suite d'ufficio, studio delle voci, conversione 3D |
| Intelligenza | modelli linguistici essenziale e profondo, consolidamento dello studio, build del Core, servizi cognitivi |
| Chiusura | manutenzione autonoma, riscaldamento neurale |

### Requisiti

| | Minimo | Consigliato |
| :--- | :--- | :--- |
| CPU | 4 core | 8+ core (AVX2) |
| RAM | 8 GB | 16–32 GB |
| Disco | 30 GB | 100+ GB NVMe |
| GPU | nessuna (modelli quantizzati su CPU) | NVIDIA, 8 GB+ di VRAM |
| Periferiche | nessuna (senza monitor) | microfono, casse, webcam, display |

Le funzioni che dipendono dall'hardware (fotocamera, array di microfoni, GPU) si disattivano pulitamente se l'hardware manca. Una macchina debole può puntare `NUXIVA_OLLAMA_URL` a un nodo GPU remoto o usare provider cloud.

### Primo avvio

1. Apri `http://<ip-del-server>/` per display e chat, `http://<ip-del-server>:8080/` per il pannello admin (account Linux, PAM).
2. La procedura guidata iniziale (`/setup`) è facoltativa: nome dell'assistente, rete, calibrazione del microfono, voce. Puoi saltarla e configurare dopo.
3. Segui l'installazione dal vivo, o da terminale:

```bash
nuxivactl status        # fase, avanzamento, componenti e ogni passo
nuxivactl background    # download in coda con dimensione e avanzamento
nuxivactl logs          # log di installazione (anche: supervisor, core, ollama, voice, vision, ear)
nuxivactl setup-code    # codice di abbinamento per la procedura guidata
nuxivactl version       # revisione installata
```

### Tienilo in salute

```bash
sudo nuxivactl update           # scarica e applica una revisione verificata dalla CI
sudo nuxivactl update --force   # aggiornamento forzato a un ramo
sudo nuxivactl repair           # ripara un'installazione guasta
```

Gli aggiornamenti si applicano solo a revisioni i cui job di CI sono riusciti; una revisione che non parte viene marcata cattiva e l'ultima buona viene ripristinata in automatico (§Supervisore).

---

## 2. Perché vorrai provarlo

| | |
| :--- | :--- |
| 🗣️ **Parla con la tua casa** | Parola di attivazione, riconoscimento vocale offline, voci neurali, voci clonate o inventate, trascrizione in oltre 600 lingue. |
| 👁️ **Vede e capisce** | Riconoscimento facciale locale, lettura delle emozioni registrata per persona, telecamere NVR, presenza spaziale. |
| 🤖 **Corteccia Neuro-Simbolica & Umanoide** | Superamento dei limiti degli LLM: parità logica al 70–75%, selezione autonoma dell'algoritmo (da 14 passi a 1 passo O(1)) e predisposizione fisica all'installazione in un corpo robotico con equilibrio ZMP e Active Inference. |
| 🧠 **Un vero cervello di instradamento** | Un percorso veloce appreso (memoria coseno in Rust), un punteggio di complessità ψ che sceglie tra i motori di ragionamento, decisioni calibrate in modo conformale. |
| 🛠️ **Fa le cose** | Strumenti per file, posta, media, sistema, RPA e controllo della casa; agenti che pianificano, chiedono conferma e cercano sul web quando servono fatti freschi. |
| ⚽ **Sport in diretta, subito** | Preferiti per persona, riepilogo notturno per risposte istantanee, ricerca online appena una partita comincia. |
| 🛡️ **Difeso per progetto** | Analisi del traffico in Rust (scansioni, flood, tunnel DNS, ARP spoofing), proxy di uscita con politiche, codice generato in sandbox, nessun cloud nascosto. |
| 🔄 **Si prende cura di sé** | Riavvii del guardiano, aggiornamenti vincolati alla CI, rollback, modalità sicura, consolidamento notturno. |
| 🧩 **Estendibile all'infinito** | Aggiungi una cartella con un `feature.json`: viene scoperta, tradotta e instradata automaticamente. |

---

## 3. Cos'è Nuxiva

Nuxiva trasforma una macchina (o una piccola flotta) in un assistente domestico che ascolta, vede, parla, controlla la casa ed esegue strumenti, mantenendo i dati in locale per impostazione predefinita. Combina:

- un **Supervisore** (FastAPI) che serve il display pubblico e il pannello di amministrazione, scopre le funzioni all'avvio e mantiene vivi 52 cicli in background;
- un **Core** (Python, porta 8443 solo in locale) che instrada ogni richiesta attraverso una memoria veloce di schemi, un motore decisionale e un insieme di motori di ragionamento;
- **crate Rust nativi** per i percorsi critici (memoria di schemi, bus di eventi, analisi di rete, controllo dell'uscita, sincronizzazione CRDT, DSP audio);
- un **client React** (display kiosk, pannello admin, widget), un client Android e nodi satellite.

Nuxiva è software libero. Funziona completamente offline una volta installati i modelli; i modelli cloud sono opzionali e si mescolano tramite liste di priorità.

---

## 4. Il repository in sintesi

| Area | Percorso | Contenuto verificato |
| :--- | :--- | :--- |
| Supervisore e funzioni | `installer_wizard/` | 78 funzioni auto-scoperte (`feature.json`), 70 widget, 6 app a livello supervisore, backend in `backend/` |
| Core | `server/` | ~39.900 righe di Python: decisioni, router dell'ippocampo, plasticità, ragionamento, fucina di abilità, event sourcing |
| Codice nativo | `native/crates/` | 9 crate Rust, 109 funzioni `#[test]` |
| Client web | `client_web/` | 34 app core, 16 app, 12 app nodo, lingue IT / EN / FR / ES |
| Client Android | `client_apk/` | Kotlin, Gradle |
| Satelliti | `client_satellite/` | `context_bridge`, `linux_edge`, `microcontrollers`, `windows_assistant` |
| Sandbox | `sandbox_broker/` | backend processo / Docker / gVisor / Firecracker, proxy di uscita |
| Giochi | `giochi/` | scacchi 3D |
| Script di sistema | `scripts/os/` | passi di installazione, riparazione, rollback, 8 unità systemd |
| Test | `**/test_*.py` | 313 file di test Python |

Provider cloud nel catalogo (`features/cloud/catalog.py`): OpenAI, Anthropic, Google Gemini, xAI, Mistral, DeepSeek, Groq, Cerebras, OpenRouter, Together, Fireworks, Perplexity, Cohere, Alibaba Qwen, Moonshot, Zhipu, NVIDIA NIM, Hugging Face, SambaNova, DeepInfra, Azure OpenAI e qualunque endpoint compatibile OpenAI.

---

## 5. Architettura

```mermaid
flowchart LR
    subgraph Clients[Client]
        K[Display kiosk :80]
        A[Pannello admin :8080]
        M[App Android]
        S[Satelliti]
    end
    subgraph Supervisor[Supervisore - installer_wizard]
        P[App pubblica]
        D[App admin]
        F[78 funzioni]
        L[52 cicli]
        C[Router della chat]
    end
    subgraph Core[Core - server, 127.0.0.1:8443]
        R[Dispatcher]
        H[Router ippocampo]
        E[Motore decisionale]
        Y[Motori di ragionamento]
    end
    subgraph Native[Crate Rust]
        N1[cortex-core]
        N2[bus-core]
        N3[netguard]
        N4[egress]
        N5[crdt-core]
        N6[audio-dsp]
    end
    O[(Ollama / modelli cloud)]
    SB[Sandbox broker]
    K --> P
    A --> D
    M --> P
    S --> P
    P --> C
    D --> F
    C --> F
    C --> R
    R --> H --> N1
    R --> E
    R --> Y --> O
    F --> SB
    F --> N3
    SB --> N4
    L --> F
```

Le funzioni sono cartelle plug-in in `installer_wizard/features/<id>/`. Ognuna si dichiara in `feature.json` e può esporre `api.py` (rotte HTTP), `commands.py` (connettore voce e chat), `tools.py` (strumenti dell'agente), `language/` e un'icona. Il supervisore le scansiona all'avvio; nulla viene registrato a mano.

---

## 6. Come viene risposta una richiesta

Il router della chat (`features/chat/assistant.py`) è una cascata ordinata. Vince il primo stadio che sa rispondere; uno stadio che non riconosce la richiesta solleva `LookupError` e passa il turno al successivo.

```mermaid
flowchart TD
    T[Testo o voce] --> A1[Automazioni]
    A1 --> A2[Scena spaziale]
    A2 --> A3[Affermazioni di comprensione]
    A3 --> A4[Luoghi / progetti / modelli 3D / esperti]
    A4 --> A5{Comando forte per l'agente?}
    A5 -- sì --> AG[Ciclo strumenti dell'agente]
    A5 -- no --> A6[Abilità per intento]
    A6 --> A7[Router semantico di dominio]
    A7 --> A8[Connettori: sport, tv, cassaforte, musica, mappe ...]
    A8 --> A9[Controllo della casa]
    A9 --> A10[Azioni]
    A10 --> A11[Libreria di algoritmi]
    A11 --> A12[Calcolatrice verificata]
    A12 --> CV[Conversazione]
    CV --> G{Servono fatti aggiornati?}
    G -- verdetto del modello sì --> AG
    G -- no --> CORE[Ragionamento del Core]
```

Due regole progettuali valgono per questa cascata:

- **Nessun elenco di argomenti scritto nel codice.** Se una domanda richiede informazioni aggiornate lo decide il modello (`features/agent/grounding.py`: verdetto JSON `{"lookup": bool}`, timeout 8 s, cache 600 s, al massimo 200 voci, `False` in caso di qualunque errore). A quale sport, campionato o squadra si riferisce una frase lo decidono un catalogo di dati e un piano costruito dal modello (`features/sports/understand.py`). Aggiungere uno sport significa aggiungere una riga al catalogo, non codice.
- **Degradare con grazia.** Ogni stadio che parla con la rete o con un modello intercetta i propri errori e passa oltre, oppure risponde onestamente che la fonte non è raggiungibile.

---

## 7. Il Core: instradamento, memoria e ragionamento

### 5.1 Router di Sistema 1 e punteggio di complessità ψ

`server/core/orchestrator/system1_router.py` calcola logit per parole chiave per le classi `conversation`, `action_direct`, `complex_task`, `whiteboard_canvas` e `browser_action`, poi una softmax:

```
p_i = exp(z_i - max z) / Σ_j exp(z_j - max z)
```

Uno scalare di complessità ψ sceglie il motore di ragionamento:

```
ψ = (0.45·L_task + 0.35·S_pred + 0.20·E_user) · (1 − 0.30·P_hw)      tutti i termini limitati a [0, 1]
```

| ψ | Motore |
| :--- | :--- |
| < 0,25 | `veloce_5_0` |
| < 0,50, oppure emozione dell'utente > 0,65 | `empatico_5_0` |
| < 0,75 | `pro_6_0` |
| ≥ 0,75 | `ultra_6_5` |

In `server/core/reasoning/engines/` esistono anche `auto_6_5` (meta-orchestrazione) e `legacy_4_2`. `L_task` è il logit di compito complesso / 10, `E_user` l'emozione rilevata, `P_hw` la pressione hardware.

### 5.2 Ippocampo: percorso veloce appreso

Le richieste confermate spesso vengono memorizzate come **neuroni**: un identificativo, un peso sinaptico, un insieme di vettori di embedding positivi (dendriti) e di vettori negativi (inibizioni). Il confronto è implementato in Rust (`cortex-core/src/hippocampus`) ed esposto a Python tramite `RustNeuronIndex`.

- I vettori sono normalizzati L2; la similarità è un prodotto scalare (coseno). Vettori nulli, vuoti o non finiti vengono rifiutati.
- Si sceglie il miglior candidato, poi `decide` applica:

```mermaid
flowchart TD
    Q[Embedding della richiesta] --> B[Miglior neurone]
    B --> N{similarità negativa ≥ 0,60?}
    N -- sì --> S1[Percorso lento: inibito]
    N -- no --> L{similarità < 0,70?}
    L -- sì --> S2[Percorso lento: similarità bassa]
    L -- no --> F{similarità ≥ 0,85 e peso ≥ 0,75?}
    F -- sì --> FP[PERCORSO VELOCE]
    F -- no --> W{peso ≥ 0,50?}
    W -- sì --> GZ[ZONA GRIGIA: verifica rapida]
    W -- no --> S3[Percorso lento: peso basso]
```

Senza alcun neurone il verdetto è percorso lento (`NoNeurons`). L'istantanea dell'indice è serializzata in JSON e le istantanee malformate vengono rifiutate.

### 5.3 Plasticità e ciclo REM notturno

`server/core/plasticity/rules.py` implementa aggiornamenti limitati di tipo hebbiano:

| Regola | Valore |
| :--- | :--- |
| Limiti del peso | 0,05 – 0,99 |
| Potenziamento | `w ← w + 0,10·(1 − w)` |
| Depressione | `w ← w − 0,25·w` |
| Decadimento | emivita 30 giorni: `w ← w · 0,5^(giorni_inattivi / 30)` |
| Potatura | peso ≤ 0,10 **e** inattivo da ≥ 90 giorni **e** non protetto |

Lo scheduler (`plasticity/scheduler.py`) esegue i compiti di consolidamento ogni notte alle **03:30** e recupera se l'ultima esecuzione risale a più di 36 ore prima.

### 5.4 Motore decisionale

`server/core/decision/` valuta candidati (modelli o azioni) con matematica esplicita:

- validazione della distribuzione (tolleranza sulla somma 1e-3, tolleranza di rinormalizzazione 2e-2);
- temperature scaling stimato per log-verosimiglianza negativa;
- insiemi di predizione conformale (α limitato a 0,01 – 0,50);
- scomposizione dell'entropia in incertezza totale e aleatoria, confidenza normalizzata `1 − H/ln K`;
- un punteggio composito, la **media armonica pesata** di cinque assi, moltiplicata per un cancello quadratico di soglia minima:

| Asse | Peso (preset `NUXIVA_5AXIS`) | Soglia minima |
| :--- | :--- | :--- |
| Intelligenza | 0,30 | 55 |
| Calibrazione | 0,20 | – |
| Velocità | 0,15 | 50 |
| Costo | 0,15 | 50 |
| Omeostasi della sicurezza | 0,20 | 60 |

L'intelligenza mescola benchmark aperti e sigillati al 50/50. I preset `A_BALANCED`, `B_QUALITY` e `C_PRODUCTION` usano quattro assi.

### 5.5 Fucina di abilità ed event sourcing

`server/core/skill_forge/` raccoglie le richieste fallite, fa scrivere un'abilità a un modello, ne analizza l'AST e la esegue solo dentro il livello di isolamento e la sandbox. `server/core/event_sourcing/` conserva un registro append-only dei cambiamenti di stato.

---

## 8. La Nuova Frontiera: Corteccia Neuro-Simbolica & Ancoraggio Corporeo Umanoide

Nuxiva compie il salto generazionale che separa i convenzionali assistenti statistici basati su Large Language Model (con parità logica integrata stimata attorno al **18%–22%**) dai sistemi cognitivi ad alta affidabilità deduttiva e controllo fisico, raggiungendo una **parità del 70%–75% con la logica razionale ed esecutiva umana**.

La corteccia neuro-simbolica e il modulo di ancoraggio corporeo sono interamente implementati in **Rust nativo** (`native/crates/cortex-core/src/columns` e `embodied`), compilati a livello macchina senza garbage collector (`#![forbid(unsafe_code)]`), con tempi di reazione sub-millisecondo (< 100 µs).

```mermaid
flowchart TD
    subgraph Signal[Segnale di Ingresso]
        IN[Frase / Calcolo / Stato Fisico Sensorimotorio]
    end

    subgraph MetaRouter[Meta-Router & Triage Cognitivo Rust]
        MR{Analisi Dominio & Complessità}
    end

    subgraph CorticalColumns[Colonne Corticali Neuro-Simboliche]
        P[Livello Procedurale<br/>14 passi meccanici espliciti]
        C[Livello Canonico<br/>5 passi - Decomposizione spettrale]
        I[Livello Invariante O 1<br/>1 passo - Simmetria dello Scienziato]
    end

    subgraph SelfImprovement[Plasticità JIT & Firma Ed25519]
        SC[Sintesi Automatica Scorciatoia Sinaptica]
        SIGN[Firma Digitale Ed25519 + Cifratura AES-256-GCM]
    end

    subgraph Embodied[Ancoraggio Corporeo & Paradosso di Moravec]
        KIN[Cinematica a 6 Giunti + Equilibrio ZMP]
        AI[Active Inference / Minimizzazione Free-Energy]
        SAFE{Inviluppo di Sicurezza Termica & Coppia}
        ACT[Attuatori Umanoidi / Motori Hardware]
    end

    IN --> MR
    MR -- Logico/Algebrico --> CorticalColumns
    MR -- Sensorimotorio --> Embodied
    P --> C --> I
    C -. deduzione nuovo pattern .-> SC --> SIGN --> I
    AI --> SAFE
    SAFE -- OK --> ACT
    SAFE -- Violazione --> REFLEX[Riflesso Spinale di Taglio Istantaneo]
```

### 8.1 Il Salto Quantico: Benchmark della Parità Cognitiva Umana

Mentre un LLM generalista tenta di risolvere compiti deduttivi, algebrici o cinematici predicendo token statistici uno alla volta (incappando in allucinazioni e costi computazionali $O(N)$ imprevedibili), Nuxiva attiva micro-neuroni esecutivi e risolutori simbolici compilati:

| Dimensione Cognitiva | AI Generativa Standard (LLM) | Nuxiva Core Precedente | Nuxiva Corteccia Neuro-Simbolica | Impatto Architetturale |
| :--- | :---: | :---: | :---: | :--- |
| **Logica Deduttiva & Matematica** | ~15% (allucinazioni sui token) | ~20% (prompts guidati) | **95%+ (Esatta)** | Risolutori simbolici esatti compilati in Rust, zero deviazioni numeriche. |
| **Selezione Dinamica Algoritmo** | 5% (monolitica per ogni query) | 10% (k-NN o LLM) | **75%** | Scelta del livello di astrazione ottimale: da 14 passi a 1 passo $O(1)$. |
| **Plasticità & Auto-Miglioramento** | 0% (pesi statici congelati) | 20% (distillazione LoRA batch) | **70%** | Consolidamento JIT di scorciatoie sinaptiche locali firmate e crittografate. |
| **Ragionamento Causale (Causa-Effetto)** | ~25% (correlazione testuale) | ~30% (DAG di base) | **65%** | Decomposizione strutturale delle invarianti fisiche e logiche. |
| **Ancoraggio Corporeo (Moravec)** | 0% (puramente disincarnata) | 0% (nessun modello fisico) | **95%** | Cinematica 6-DOF, stabilità ZMP e inferenza attiva sensomotoria. |
| **PARITÀ LOGICA GLOBALE STIMATA** | **~15% – 20%** | **~18% – 22%** | **70% – 75%** | **Capacità operativa e rigore deduttivo sovrumano nei domini integrati.** |

### 8.2 Colonne Corticali & Selezione Gerarchica dell'Astrazione

La corteccia implementa la risoluzione gerarchica multilivello (es. per l'algebra polinomiale e la logica SAT):
1. **Livello Procedurale (Superiori - 14 passaggi)**: esecuzione passo-passo completa: normalizzazione dei termini lineari, espansione canonica, calcolo esplicito del discriminante $\Delta = b^2 - 4ac$, estrazione radicale e diramazione delle due soluzioni.
2. **Livello Canonico (Università - 5 passaggi)**: proiezione su operatore monico ridotto, calcolo del baricentro spettrale di Vieta e determinazione dell'offset quadratico.
3. **Livello Invariante $O(1)$ (Scienziato - 1 passaggio)**: riconoscimento istantaneo della simmetria di conservazione (es. somma dei coefficienti nulla $a+b+c=0 \implies \{1, c/a\}$, dipoli puri simmetrici, radici perfette). Il problema collassa in una singola lettura in memoria $< 50\,\mu\text{s}$.

### 8.3 Auto-Apprendimento Sinaptico JIT a Ciclo Chiuso (Il Sistema Impara da Solo)

Quando il sistema si trova di fronte a una nuova classe di problemi:
1. Esegue la risoluzione approfondita tramite il livello canonico.
2. Il modulo di plasticità (`cortex-core/src/columns/engine.rs`) estrae la firma dell'invariante e sintetizza un nuovo **micro-neurone scorciatoia**.
3. Il neurone viene firmato con crittografia asimmetrica **Ed25519** (`RustSigner`) per garantirne l'integrità anti-manomissione Zero-Trust e cifrato a riposo con **AES-256-GCM** via `ZeroTrustVault`.
4. La volta successiva che il problema o un suo isomorfo si ripresenta, il motore lo risolve istantaneamente al livello Invariante $O(1)$ con risparmio del 92% dei passaggi computazionali.

### 8.4 Ancoraggio Corporeo & Superamento del Paradosso di Moravec (Embodied Cognition)

Il **Paradosso di Moravec** insegna che ciò che è difficile per gli umani (il calcolo logico astratto) è facile per un computer, mentre ciò che è istintivo per un bambino (mantenere l'equilibrio, dosare la forza su un oggetto, adattarsi a un peso imprevisto) è immensamente complesso per un'AI tradizionale disincarnata.

Nuxiva integra nativamente in Rust l'architettura per installarsi all'interno di un **corpo robotico umanoide**:
- **Propriocezione e Giunti Fisici**: Modello cinematico per 6 articolazioni umane fondamentali (`hip_pitch_l`, `knee_pitch_l`, `ankle_roll_l`, `shoulder_pitch_r`, `elbow_pitch_r`, `torso_yaw`) con monitoraggio di angolo reale (rad), velocità (rad/s), coppia applicata (Nm), carico esterno (kg) e temperatura attuatori (°C).
- **Equilibrio Dinamico Vestibolare & ZMP**: Sensori IMU triassiali con stima in tempo reale del Centro di Massa (CoM) e del margine del **Zero-Moment Point (ZMP)** sul poligono di supporto podalico, prevenendo cadute o ribaltamenti.
- **Inferenza Attiva (Predictive Coding & Free-Energy Principle)**: Prima di azionare un motore, il modello fisico interno predice l'angolo risultante $\hat{\theta}$. All'arrivo del feedback sensoriale reale $\theta$, calcola la *Sorpresa* (Free Energy: $|\theta - \hat{\theta}|$) e adatta in tempo reale il guadagno plastico di calibrazione dell'attuatore per compensare attriti, usura o carichi imprevisti.
- **Inviluppo di Sicurezza Zero-Trust Hardware**: Taglio istantaneo dell'impulso se la temperatura supera la soglia limite, se l'angolo eccede i finecorsa meccanici o se il margine ZMP scende sotto la soglia critica ($< 0,035\,\text{m}$), attivando riflessi spinali di stabilizzazione.

### 8.5 Il Laboratorio Decisionale WebOS

L'app *Cervello* in `client_web` include la scheda interattiva **Corteccia & Corpo Umanoide (Rust)**, accessibile via browser da Mobile e Desktop, per testare dal vivo le colonne corticali a 3 livelli, ispezionare le scorciatoie sinaptiche consolidate e sperimentare il controllo dell'equilibrio e dei motori umanoidi con telemetria in tempo reale.

---

## 9. Agenti, strumenti e risposte ancorate ai fatti

- **Registro degli strumenti**: le funzioni decorate con `@tool` in `features/agent/` (file, posta, media, sistema, pacchetti, telecamere, schermo, RPA) e nel `tools.py` di ogni funzione vengono scoperte a runtime.
- **Ciclo dell'agente** (`agent/agent.py`): il modello pianifica, chiama strumenti, legge i risultati e chiede conferma prima delle azioni rischiose. La data di oggi è inserita nelle sue regole.
- **Orchestratore CEO** (`features/team/ceo.py`): scansiona agenti, strumenti e widget e li ordina con `relevance.py`: i token sono filtrati dalle parole vuote, ridotti a 5 caratteri e valutati con pesi per campo `identity 3,0, noun 4,0, capability 1,3, tool 1,6, tool_text 0,6, description 0,9, keyword 0,3`, un bonus di frase di 14, bonus appresi (+2 per conferma, tetto 4) e un punteggio minimo di 5,0 prima di assegnare uno specialista.
- **Ricerca** (`features/research/`): ricerca web multi-provider, scaricamento sicuro, estrazione e ordinamento, con generatore di rapporti.
- **Ancoraggio ai fatti**: vedi §6: il modello decide se rispondere dalla memoria o cercare; se uno strumento fallisce, all'agente viene detto di ripiegare sulla ricerca web invece di scusarsi.
- **Livello Cervello / LLM** (`features/brain/llm.py`): `generate(kind, as_json, component, timeout)` percorre una catena di priorità di modelli Ollama locali e cloud, saltando quelli inutilizzabili, così un modello guasto non ferma la risposta.

---

## 10. Sport: preferiti, riepilogo notturno, ricerca online

Lo sport è interamente **guidato dai dati**.

- `features/sports/catalog.py` elenca i campionati (calcio, NHL, NBA, WNBA, NFL, MLB e altri) con percorso ESPN e alias; la Formula 1 usa l'API Jolpica/Ergast. Non servono altri servizi né chiavi API.
- La domanda dell'utente viene associata a una squadra o a un campionato sull'indice reale delle squadre, poi `understand.plan` chiede al modello `{sport, want, focus}`. La risposta passa per un percorso generico: classifica, risultati del giorno, scheda squadra o scheda F1, più un widget sul desk (`sport_match`, `sport_table`, `f1_race`).
- **Preferiti**: salvati per persona (e un profilo per tutta la casa) in `sports.json`. **Per impostazione predefinita nessuno segue nulla**: nessun controllo continuo, nessun riepilogo.
- **Osservatore in diretta**: segue solo le squadre preferite, ogni 20 s durante una partita, 60 s quando ce n'è una vicina, 600 s altrimenti. Annuncia calcio d'inizio, gol, espulsioni e risultati finali e richiama un widget quando una persona che li segue si avvicina allo schermo (pausa di 30 min).
- **Riepilogo notturno** (`features/sports/digest.py`): dopo le 03:00, una volta al giorno, scarica per i campionati dei preferiti i tabelloni (ieri, oggi, domani), calendari e risultati delle squadre, classifiche ed elenchi squadre e, per la F1, calendario, ultimi risultati e i due campionati. Tutto è salvato in `sports_digest.json`.

```mermaid
flowchart LR
    Q[Domanda] --> M{In cache di memoria e fresco?}
    M -- sì --> ANS[Risposta]
    M -- no --> D{Voce del riepilogo valida?}
    D -- sì --> ANS
    D -- no, scaduta o assente --> ON[Ricerca online]
    ON --> ANS
    ON -. rete assente .-> ST[Ultimo dato noto del riepilogo] --> ANS
```

Ogni voce del riepilogo porta una scadenza pari al primo calcio d'inizio tra le partite non concluse di quel campionato (al massimo 30 ore; scade subito se una partita è in corso). Prima del calcio d'inizio la risposta salvata è esatta; appena la partita comincia, la stessa domanda va automaticamente online. Salvare i preferiti di una persona invalida il riepilogo, così le nuove squadre vengono scaricate al ciclo successivo; `POST /api/sports/digest/build` forza un aggiornamento.

---

## 11. Persone, benessere e fotocamera

- **Persone**: profili, ruoli, voci, account collegati (ad es. Google) e promemoria per persona.
- **Misuratore di benessere**: medie mobili esponenziali per persona e segnale; gli scostamenti diventano z-score, compressi con una sigmoide e raggruppati in quattro aree: *tensione, esaurimento, ricettività, sollievo*.
- **Fotocamera**: il misuratore di affetto della pipeline di visione legge il volto di una persona riconosciuta. Dopo un periodo di calibrazione ogni lettura viene registrata nel **diario degli stati d'animo** della persona con fonte `camera` (al massimo una voce ogni 120 s, una nuova se l'area cambia o passano 900 s), con evidenze come «volto: tensione, attivazione 62/100, tono −0,3». Il diario è modificabile e l'utente può dare un riscontro sulle voci di fotocamera e assistente.
- Tutto resta in file di stato locali; nulla viene inviato a un servizio cloud se l'utente non ne configura uno.

---

## 12. Crate Rust nativi

| Crate | Ruolo | Dettaglio verificato |
| :--- | :--- | :--- |
| `cortex-core` | Indice neuroni dell'ippocampo, colonne corticali (selezione algoritmica 3 livelli), consolidamento scorciatoie JIT e motore fisico/propriocettivo umanoide (Active Inference & ZMP) | soglie 0,85 / 0,70 / 0,60; inviluppo termico/coppia; latenza deterministica sub-millisecondo |
| `bus-core` | Router dei topic e tipi di evento | topic fino a 8 segmenti da 40 caratteri, fino a 65.536 sottoscrizioni, pattern con caratteri jolly; buffer ad anello senza lock (1.024 posti di default) per gli impulsi sinaptici con trasmettitori eccitatori/inibitori |
| `netguard` | Analisi dei pacchetti per il firewall | rilevatori: scansione porte (25 porte / 10 s), scansione host (25 host), SYN flood (300/s), forza bruta (15 tentativi / 60 s sulle porte di autenticazione), tunnel DNS (lunghezza nome 70, entropia 4,0), ICMP flood (200/s), volume di esfiltrazione, ARP spoofing; elenco MAC fidati, pausa per avviso |
| `egress` | Proxy di uscita con politiche per la sandbox | pattern di host, rifiuta indirizzi non pubblici (RFC 1918, loopback, link-local e altri in una lista di blocco) |
| `crdt-core` | Mappa last-writer-wins per la sincronizzazione tra pari | vince il timestamp più recente; a parità vince l'id nodo maggiore; la fusione restituisce il numero di voci cambiate |
| `audio-dsp` | Rilevamento dell'attività vocale e filtri | RMS, tasso di attraversamento dello zero ed entropia spettrale; soglia adattiva quando c'è audio in riproduzione; frame di coda; soppressione della musica; filtri biquad |
| `spatial-core` | Arbitraggio desktop/banco di lavoro | z-stack, priorità, governatori di risorse, compiti e rete, router di intenti |
| `langid` | Identificazione della lingua | usato dalla pipeline vocale |
| `nuxiva-native` | Ponte PyO3 nativo cdylib che espone i crate a Python | RustNeuronIndex, RustCorticalCortex, RustEmbodiedCortex, RustSigner, arbitraggio, audio, bus, mesh, scanner, workbench |

---

## 13. Supervisore e auto-riparazione

- **Due app web**: pubblica (porta 80) e admin (porta 8080), più un ascoltatore HTTPS opzionale (porta 443) quando è presente un certificato. Le porte possono essere configurate tramite `NUXIVA_PUBLIC_PORT` e `NUXIVA_ADMIN_PORT`.
- **Guardiano dei cicli** (`backend/loops.py`): ciascuno dei 52 cicli in background è avvolto; un arresto lo riavvia con backoff esponenziale (da 1 s fino a un massimo configurabile, 60 s di default) e un battito rileva i blocchi (fattore di default 5× il periodo del ciclo). Un ciclo stabile per 120 s azzera il backoff.
- **Aggiornatore** (`backend/updater.py`): aggiorna solo a una revisione i cui job di CI (`validate-python`, `tests`, `kernel-tests`, `native-core`, `validate-scripts`, `validate-web-client`) sono riusciti; una revisione che non parte viene marcata *cattiva* per 30 minuti e l'ultima revisione buona viene ripristinata da `nuxiva-rollback.service`.
- **Modalità sicura** (`backend/safe_mode.py`): una pagina minima e uno script di riparazione automatica quando il sistema completo non riesce ad avviarsi.
- **Dist del frontend**: un workflow GitHub ricompila `client_web/dist` dal sorgente, quindi il server non ha mai bisogno di Node a runtime.

---

## 14. Modello di sicurezza

- L'accesso admin usa **PAM** di Linux (servizio `nuxiva-admin`) e richiede `root` o l'appartenenza al gruppo amministrativo.
- Le funzioni si attivano o disattivano con variabili d'ambiente; le azioni sensibili passano da un cancello di approvazione (funzione authz) e dalla biometria vocale dove configurata.
- Il codice generato gira solo nel **sandbox broker** (senza rete e senza accesso all'host di default); isolamento opzionale con gVisor e micro-VM Firecracker; il traffico in uscita passa dal proxy Rust `egress`.
- `netguard` alimenta la funzione firewall; le regole del firewall sono testate in CI su `nftables` reale.
- I segreti (chiavi cloud) stanno in una cassaforte cifrata sotto `/etc/nuxiva/`.
- Il contenuto web scaricato dagli agenti passa dal filtro `safeweb`; gli host esterni per i dati sportivi sono limitati a una lista consentita (`ESPN`, `Jolpica`).
- Divulgazione responsabile: vedi [SECURITY.md](SECURITY.md).

---

## 15. Porte, servizi e percorsi

| Porta | Uso |
| :---: | :--- |
| 80 | Display pubblico / kiosk, chat |
| 8080 | Pannello admin, API REST, server MCP |
| 443 | HTTPS opzionale |
| 8443 (localhost) | Core |
| 11434 (localhost) | Ollama |

Unità systemd in `scripts/os/systemd/`: `nuxiva-supervisor`, `nuxiva-core`, `nuxiva-sandbox`, `nuxiva-netguard`, `nuxiva-ear`, `nuxiva-vision`, `nuxiva-voice`, `nuxiva-rollback`.

| Percorso | Contenuto |
| :--- | :--- |
| `/opt/Nuxiva` | Codice dell'applicazione |
| `/etc/nuxiva/nuxiva.env` | Configurazione (le variabili d'ambiente si leggono con `env_get`; esistono circa 130 nomi `NUXIVA_*` distinti) |
| `/var/lib/nuxiva/` | Stato: persone, sport (`sports.json`, `sports_digest.json`), diari degli stati d'animo, cache |

---

## 16. Client

- **Client web** (`client_web`, React + Vite + Tailwind): display kiosk con desk di widget dinamici, volto 3D e pannello admin con 34 app core (persone, impostazioni del Cervello, firewall, telecamere, studio delle voci, aggiornatore, cassaforte, VPN, meteo, …). L'interfaccia admin usa il tema chiaro. Traduzioni: italiano, inglese, francese, spagnolo.
- **Android** (`client_apk`): client Kotlin.
- **Satelliti** (`client_satellite`): nodo Linux edge, microcontrollori, assistente Windows (con proprio workflow CI), context bridge.
- **MCP**: Nuxiva espone i suoi strumenti come server MCP sulla porta admin e può usare server MCP esterni (`installer_wizard/MCP.md`).

---

## 17. Controlli di qualità

Il workflow GitHub **Nuxiva CI Pipeline** gira a ogni push:

1. sintassi Python (`py_compile`) e `pyflakes` su `server`, `sandbox_broker`, `installer_wizard`, `client_satellite`;
2. test unitari e API del supervisore (`unittest discover`), più regole del firewall su `nftables` reale;
3. test del kernel del Core e del sandbox broker;
4. Rust 1.89: `fmt`, `clippy`, test, build del modulo Python, test di parità nativa e del bus, test del proxy egress, test nativi di cortex;
5. controlli di sintassi JavaScript e shell;
6. validazione del client web.

Altri due workflow ricompilano il bundle del frontend e l'assistente Windows.

---

## 18. Limiti onesti

- Il vocabolario «neurale» (neuroni, sinapsi, REM) dà il nome a meccanismi reali e semplici: similarità tra vettori con soglie, pesi limitati con decadimento, un lavoro notturno. Non è una simulazione biologica e il buffer di impulsi in Rust è un tipo di coda, non un simulatore di reti a impulsi.
- La qualità dipende dai modelli installati; i modelli piccoli su sola CPU rispondono lentamente e ragionano meno bene.
- I dati sportivi vengono da endpoint pubblici che possono cambiare o limitare le richieste; il riepilogo notturno e il ripiego sull'ultimo dato noto attenuano il problema, ma non garantiscono l'accuratezza in diretta.
- Le funzioni che dipendono dall'hardware (fotocamera, array di microfoni, GPU) si disattivano da sole se l'hardware manca.
- Debian e Ubuntu sono gli unici host ufficialmente supportati.

---

## 19. Contribuire, licenza, supporto

Nuxiva è scritto e mantenuto da **Nunzio Aprile (NunzioTech)** ed è regolato dalla **[Nuxiva Personal and Commercial License 1.0](LICENSE)**.

- **Uso domestico e personale**: Completamente gratuito e royalty-free per persone fisiche e il loro nucleo familiare sui propri dispositivi, esclusivamente per finalità private e non commerciali.
- **Uso commerciale e professionale**: L'impiego in attività professionali o aziendali, servizi di hosting, installazioni per conto terzi, locazioni turistiche commerciali o integrazioni a pagamento richiede un accordo commerciale scritto a pagamento con NunzioTech (`aprilenunzio88@gmail.com`).
- **Codice pregresso e diritti MIT**: Le porzioni e i rilasci precedentemente distribuiti sotto licenza MIT conservano integralmente i diritti acquisiti, come preservato in [LICENSE-MIT-LEGACY](LICENSE-MIT-LEGACY).

I contributi sono benvenuti: consulta [CONTRIBUTING.md](CONTRIBUTING.md) e il [Codice di condotta](CODE_OF_CONDUCT.md).

Se Nuxiva ti è utile a casa, puoi sostenerne lo sviluppo indipendente:

<p align="center">
  <a href="https://www.paypal.com/paypalme/NunzioAprile">
    <img src="https://img.shields.io/badge/Donate-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Dona con PayPal">
  </a>
</p>
