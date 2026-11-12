# Nuxiva — registro di implementazione

## Priorità alta

- [x] [Issue #42](https://github.com/AprileNunzio/Nuxiva/issues/42) — Consentire la scrivania del display a un amministratore autenticato via HTTPS su LAN headless con protezione di presenza disattivata.
- [ ] Issue #42 — Riprodurre il problema della trascrizione attraverso il tunnel SSH e collaudare il pannello touch in rete.

- [x] [Issue #41](https://github.com/AprileNunzio/Nuxiva/issues/41) — Ripristinare i widget pubblici nella pagina LAN senza display kiosk e con protezione di presenza disattivata. Verificati HTTP, entrambi gli stream SSE e isolamento dei dati del display fisico.
- [ ] Issue #41 — Collaudare il comportamento in un browser sulla rete dell’installazione segnalata.

## Pubblicato o verificato in locale

- [x] Download Windows da Nodi e Server con pacchetto ZIP e associazione monouso.
- [x] Installer compilato localmente, associazione tramite file e identificativi distinti per le nuove installazioni.
- [x] Azioni Windows per file, app, browser, spostamenti con conferma e creazione o revisione di copie Word.
- [x] Ricerca esplicita e delegata con conferma. Instradamento deterministico degli URL espliciti.
- [x] Ammissione Ollama dopo inattività, coda rispettosa della capacità e chiusura della connessione al ritorno dell’utente.
- [x] Base Rust per lease con account, nodo, scadenza e generazione. Controllo nel relay quando il modulo nativo è disponibile, pubblicato in `7341b4b1`.
- [x] Motore decisionale SMB in Rust per lettura, scrittura, conflitti e permessi per tenant, account e condivisione, pubblicato in `7341b4b1`.
- [x] Schede di installazione Linux, Windows, macOS ed ESP32 con passaggi localizzati. Windows usa un solo download con associazione. ESP32 può rilevare le porte USB sul server.

## In corso — RBAC Nuxiva

- [x] Inventario delle identità distinte per account Nuxiva, sessione Windows e nodo.
- [x] Contratto per assegnazioni account → condivisione con modalità lettura o scrittura e diniego in assenza di assegnazione.
- [x] API limitate alla condivisione assegnata per elenco, download e creazione di sottocartelle su Linux. Verifica del ruolo, della matrice e dell’assegnazione a ogni richiesta.
- [x] Vista WebOS per consultare le condivisioni assegnate, navigare, scaricare, caricare nuovi file e creare cartelle quando consentito.
- [x] Upload scoped via HTTP con limite, verifica prima della pubblicazione e protezione dei file esistenti.
- [x] Download scoped con rivalutazione periodica di ruolo, matrice e assegnazione. La revoca del grant interrompe il trasferimento residuo.
- [ ] Applicare ruolo, prova di identità, ambito e assegnazione alla stessa decisione per API, UI, agenti, voce e MCP.
- [ ] Estendere i binding a tenant e risorse stabili, con delega autenticata tra Supervisor e Core e revoca delle sessioni.
- [x] Cancellazione scoped via API di file regolari senza hard link e cartelle vuote. Verificati permessi, isolamento, traversal, link simbolici e rifiuto della cancellazione ricorsiva.
- [ ] Estendere le API con ambito di directory alla rinomina atomica senza sovrascrittura e integrare rinomina e cancellazione nella vista WebOS.
- [ ] Proteggere il filesystem da traversal, link simbolici, reparse point e sostituzione della directory durante un’operazione.
- [ ] Integrare amministrazione delle assegnazioni, audit e interfaccia responsive con chiavi i18n.

## Da completare

- [ ] Associare un’identità SMB individuale o un trasporto autenticato a ogni account. Verificare cifratura e revoca senza usare la password Samba comune per il worker.
- [ ] Collegare planner SMB Rust, worker Windows e versione comune persistente. Collaudare conflitti, ripresa, revoca e separazione tra utenti.
- [ ] Collegare i lease Rust già pubblicati alla replica a quorum, al subentro tra server, all’isolamento dei tenant e al fencing dopo una partizione.
- [ ] Applicare e misurare limiti CPU, RAM e GPU. Verificare liberazione delle risorse e riassegnazione dei job.
- [ ] Estendere il catalogo Windows con azioni universali e conferme tipizzate. Collaudare voce durante l’esecuzione e isolamento tra sessioni.
- [x] Integrato il classificatore Jev nativo nel planner delle richieste Windows. Attivazione per ID nodo con `NUXIVA_JEV_WINDOWS_NODES` e chiave `TYPESAFE_API_KEY` nel processo Supervisor. Il piano standard resta il fallback.
- [ ] Collaudare Jev sul nodo Windows Hp con credenziali TypeSafe e misurare costo per attività riuscita, accuratezza e latenza rispetto al planner standard.
- [ ] Configurare la firma della release Windows, allineare la versione e provare installazione, aggiornamento, ripristino e revoca su Windows pulito.
- [ ] Preparare e collaudare un installer macOS con associazione guidata.
- [ ] Collegare il flash ESP32 al firmware reale, verificare il dispositivo e attendere il primo heartbeat prima di mostrarlo online.
- [x] Verificata la cronologia Nuxiva Update con 17 revisioni consecutive in un repository Git temporaneo. La cronologia conserva i dettagli bilingui di ogni revisione e la vista li presenta per commit.
- [ ] Portare in Rust il worker Windows e il relay di produzione. Verificare il target Windows dei componenti nativi che usano ancora API Unix.
