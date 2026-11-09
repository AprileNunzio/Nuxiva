# Nuxiva — registro di implementazione

## Pubblicato o verificato in locale

- [x] Download Windows da Nodi e Server con pacchetto ZIP e associazione monouso.
- [x] Installer compilato localmente, associazione tramite file e identificativi distinti per le nuove installazioni.
- [x] Azioni Windows per file, app, browser, spostamenti con conferma e creazione o revisione di copie Word.
- [x] Ricerca esplicita e delegata con conferma. Instradamento deterministico degli URL espliciti.
- [x] Ammissione Ollama dopo inattività, coda rispettosa della capacità e chiusura della connessione al ritorno dell’utente.
- [x] Base Rust per lease con account, nodo, scadenza e generazione. Collegamento al relay verificato in locale quando il modulo nativo è disponibile.
- [x] Motore decisionale SMB in Rust per lettura, scrittura, conflitti e permessi per tenant, account e condivisione. Verificato in locale.
- [x] Schede di installazione Linux, Windows, macOS ed ESP32 con passaggi localizzati. Windows usa un solo download con associazione. ESP32 può rilevare le porte USB sul server.

## In corso — RBAC Nuxiva

- [x] Inventario delle identità distinte per account Nuxiva, sessione Windows e nodo.
- [x] Contratto per assegnazioni account → condivisione con modalità lettura o scrittura e diniego in assenza di assegnazione.
- [x] API limitate alla condivisione assegnata per elenco, download e creazione di sottocartelle su Linux. Verifica del ruolo, della matrice e dell’assegnazione a ogni richiesta.
- [x] Vista WebOS per consultare le condivisioni assegnate, navigare, scaricare, caricare nuovi file e creare cartelle quando consentito.
- [x] Upload scoped via HTTP con limite, verifica prima della pubblicazione e protezione dei file esistenti.
- [ ] Applicare ruolo, prova di identità, ambito e assegnazione alla stessa decisione per API, UI, agenti, voce e MCP.
- [ ] Estendere i binding a tenant e risorse stabili, con delega autenticata tra Supervisor e Core e revoca delle sessioni.
- [ ] Estendere le API con ambito di directory a rinomina e cancellazione con test per ogni rotta e operazione.
- [ ] Proteggere il filesystem da traversal, link simbolici, reparse point e sostituzione della directory durante un’operazione.
- [ ] Integrare amministrazione delle assegnazioni, audit e interfaccia responsive con chiavi i18n.

## Da completare

- [ ] Associare un’identità SMB individuale o un trasporto autenticato a ogni account. Verificare cifratura e revoca senza usare la password Samba comune per il worker.
- [ ] Collegare planner SMB Rust, worker Windows e versione comune persistente. Collaudare conflitti, ripresa, revoca e separazione tra utenti.
- [ ] Integrare lease Rust, replica a quorum, subentro tra server, isolamento dei tenant e fencing dopo una partizione.
- [ ] Applicare e misurare limiti CPU, RAM e GPU. Verificare liberazione delle risorse e riassegnazione dei job.
- [ ] Estendere il catalogo Windows con azioni universali e conferme tipizzate. Collaudare voce durante l’esecuzione e isolamento tra sessioni.
- [ ] Qualificare Jev o un equivalente misurando costo per attività riuscita, accuratezza e latenza.
- [ ] Configurare la firma della release Windows, allineare la versione e provare installazione, aggiornamento, ripristino e revoca su Windows pulito.
- [ ] Preparare e collaudare un installer macOS con associazione guidata.
- [ ] Collegare il flash ESP32 al firmware reale, verificare il dispositivo e attendere il primo heartbeat prima di mostrarlo online.
- [ ] Verificare che Nuxiva Update mostri le novità di tutte le revisioni installate.
- [ ] Portare in Rust il worker Windows e il relay di produzione. Verificare il target Windows dei componenti nativi che usano ancora API Unix.
