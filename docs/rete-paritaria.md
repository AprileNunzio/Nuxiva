# Rete paritaria di nodi / Peer-to-peer node mesh

## Obiettivo / Goal

IT: la pagina 80 deve girare per intero sul dispositivo che la mostra (APK incluso) senza consumare risorse del server. Il server è un nodo come gli altri: fino a 100 dispositivi connessi, ognuno usa la propria potenza, e per i carichi pesanti uno scheduler sceglie il nodo adatto. Esempio: il progetto viene elaborato in background dal server, lo smartphone mostra la parte grafica.

EN: page 80 must run entirely on the device that shows it (the APK included) without using server resources. The server is just another node: up to 100 connected devices, each using its own power, and for heavy work a scheduler picks the right node. Example: the server processes the project in the background while the phone renders the graphics.

## Audit: cosa fa il server oggi / what the server does today

Verificato nel codice / verified in code:

- La grafica della pagina 80 è già nel browser: `installer_wizard/web/display` (circa 2,7 MB di JS/CSS, WebGL e Canvas in `particles.js`, `avatar.js`, `kernel/`, `agency/office3d.js`). Il server non produce pixel per la pagina 80.
- Il server serve gli asset statici (`pages.py`, `FreshStatic`) con versione `ASSET_VERSION`: ogni client li scarica dal server.
- Il server costruisce gli snapshot di stato (`backend/snapshot.py`, cache condivisa da 1 s e cache delta per ambito) e li invia in streaming a ogni client; il demone Rust `display-daemon` pianifica widget e diff.
- L'APK apre la pagina dentro una WebView puntata all'origine del server (`client_apk/.../hub/HubWebView.kt`): oggi non contiene gli asset e dipende dalla rete per ogni avvio.
- Lavori generativi pesanti (particelle, creazioni 3D in `agenti/creativita`) nascono lato server e arrivano al client già calcolati.

Da spostare / to move:

1. Impacchettare gli asset di `web/display` dentro l'APK e servirli da origine locale, collegando al server solo il canale di stato firmato. Il server smette di servire asset a questi client.
2. Far arrivare ai dispositivi solo dati di stato (diff), mai pixel o frame.
3. I lavori generativi pesanti diventano job `Render`/`Compute` assegnati dallo scheduler: il risultato viaggia come dati geometrici, il rendering finale resta sul dispositivo con la GPU.

## Fase 1: crate `nuxiva-peer-core` (questo commit / this commit)

- Identità per nodo: l'id del nodo è la sua chiave pubblica Ed25519 (64 esadecimali). Nessuna fiducia implicita: un nodo entra solo se la sua chiave è iscritta esplicitamente in `TrustBook`.
- Messaggi firmati (`Envelope`, dominio `nuxiva-peer-v1`): firma su mittente, sequenza, tempo e SHA-256 del payload. Finestra anti-replay a 64 posizioni, tolleranza di orologio 60 s, payload massimo 16 KiB, payload JSON tipizzato (`Message`) con campi sconosciuti rifiutati.
- Registro capacità (`Registry`): CPU (core e punteggio), RAM, GPU (VRAM e punteggio), batteria e ricarica, rete (banda e RTT), ruoli. Stati vivo, sospetto, morto con scadenze configurabili; annunci e heartbeat con numeri di sequenza che scartano i dati vecchi; massimo 256 nodi.
- Scheduler (`Scheduler`): requisiti hard (ruolo, core, RAM, VRAM, soglia batteria per tipo di lavoro), punteggio deterministico, affinità di visualizzazione (un job `Render` va prima sul dispositivo che mostra, se idoneo), prenotazione delle risorse, lease con rinnovo, failover su nodo morto o lease scaduto con nodi già falliti esclusi, fallback degradato (requisiti dimezzati, batteria minima 15%) prima di aspettare capacità, scadenza e tentativi massimi, invio idempotente.
- Coordinatore per job: scelto per hashing rendezvous tra i nodi vivi, quindi lo scheduling è distribuito e nessun nodo, server compreso, è l'unico coordinatore. Le assegnazioni valgono solo se firmate da uno dei primi tre candidati.
- Trasporto (`Gossip`): diffusione epidemica con fanout 5 e TTL 6, deduplica per id messaggio, nessun hub centrale.

## Fase 2: rubrica firmata degli indirizzi / signed address book

IT: ogni nodo pubblica un record `Locate` firmato con i propri indirizzi correnti. Quando un dispositivo cambia rete o IP ne emette uno nuovo con sequenza maggiore; il record si propaga per gossip e ogni nodo tiene l'ultimo valido per ciascun id (`Directory`). Ogni nodo può scrivere solo il proprio record, perché il mittente firmato coincide con il soggetto, quindi non serve un consenso globale né una catena: i record convergono da soli. Ogni 10 secondi un nodo confronta i digest con un pari a caso e scambia i record mancanti (anti-entropia), così chi era spento li recupera al rientro. `candidates(id)` restituisce gli indirizzi in ordine, con quelli appena falliti in fondo (`report_failure` / `report_success`). Indirizzi validati: IP o nome host con porta, niente 0.0.0.0, multicast, porta 0 o schemi.

EN: every node publishes a signed `Locate` record with its current addresses. When a device changes network or IP it emits a new one with a higher sequence; the record spreads by gossip and each node keeps the latest valid one per id (`Directory`). A node can only write its own record because the signed sender is the subject, so no global consensus or chain is needed: records converge on their own. Every 10 seconds a node compares digests with a random peer and exchanges the missing records (anti-entropy), so a node that was offline catches up on return. `candidates(id)` returns the addresses in order, with recently failed ones last. Addresses are validated: IP or hostname with port, no 0.0.0.0, multicast, port 0 or schemes.

Verificato nel test `tests/locator.rs` con 100 nodi finti: 6 nodi cambiano indirizzo e almeno 98 su 99 lo sanno entro 8 secondi simulati; un nodo spento durante il cambio lo recupera dopo il rientro; record vecchi, manomessi o di nodi non iscritti vengono ignorati. Non è ancora collegato alla rete reale: serve il trasporto della fase successiva.

## Fase 3: trasporto UDP, invio dal server e ascolto nei client / UDP transport, server sending and client listening

IT: il crate `nuxiva-peer-net` invia e riceve record `Locate` firmati in un datagramma UDP (massimo 1200 byte, adatto alla rete locale e al broadcast), con limite di frequenza per sorgente e scarto di dati malformati, troppo grandi o di nodi non iscritti. In Python `agenti/nodes/peer_envelope.py` verifica la stessa busta con le stesse regole; i due lati sono tenuti allineati da un file di vettori condiviso (`native/crates/peer-core/tests/fixtures/locate.json`) usato dai test Rust e Python.

Completamento della fase: il server firma e invia il proprio `Locate` ogni 10 secondi in broadcast UDP sulla porta 50507 (`nodes/peer_sender.py`, avviato insieme al beacon dei nodi). L'identità del server è una chiave Ed25519 creata una volta sola in `var/lib/nuxiva/peer_identity.key` (permessi 0600); la sequenza è il tempo in millisecondi ed è sempre crescente anche dopo un riavvio. L'id del server (64 esadecimali) viaggia nel file e nel link di iscrizione (campo `peer`), nella risposta di `/api/nodes/pair` e `/api/nodes/enroll` e in `/api/nodes/pairing-code` (`peer_id`), sempre dentro il canale TLS già fissato sulla CA, quindi il client non si fida mai di una chiave arrivata dalla rete.

Il client Windows (`connection/peer.py`, `connection/relocate.py`) e l'APK (`PeerWatch.kt`, `logic/peer`) ascoltano la porta 50507 con limite di 8 pacchetti al secondo per sorgente, accettano solo la busta firmata dal server noto, con orologio entro 60 secondi e sequenza strettamente crescente. Un nuovo indirizzo viene adottato solo se il collegamento è giù, se i primi 3 candidati rispondono con un certificato firmato dalla CA memorizzata e il server non è già raggiungibile; poi l'indirizzo viene salvato. Il verificatore Python del client è una copia identica di quello del server (un test lo impone) e tutte le implementazioni passano gli stessi vettori `locate.json`.

EN: the server signs and broadcasts its own `Locate` every 10 seconds over UDP port 50507. Its Ed25519 identity is created once (mode 0600) and the sequence is time in milliseconds, always increasing across restarts. The server id travels in the enrollment file and link (`peer`), in the pair and enroll replies and in the pairing-code response, always inside the TLS channel already pinned to the CA, so the client never trusts a key that arrived from the network. The Windows client and the APK listen on 50507 with a per-source rate limit, accept only the known server's signed envelope with clock skew within 60 seconds and a strictly increasing sequence, and move to a new address only when the link is down, the first 3 candidates answer with a certificate signed by the stored CA, and the server is not already reachable.

## Test di carico / load test

`native/crates/peer-core/tests/load_100.rs` simula 100 nodi (1 server, 20 desktop, 79 telefoni con batteria diversa), tutti con messaggi firmati e verificati:

- 300 job misti completati senza fallimenti; il server invia meno del 3% dei messaggi e nessun nodo supera 4 volte la media; almeno l'80% dei job in background gira su nodi non mobili e almeno l'80% dei render gira sul dispositivo richiedente.
- 30 nodi su 100, server compreso, cadono a metà: tutti i job dei richiedenti sopravvissuti finiscono tramite failover e reinvio.
- Traffico di un nodo non iscritto, replay, payload manomesso e assegnazione di un nodo non coordinatore vengono rifiutati e non eseguono nulla.

Semantica: consegna almeno una volta (at-least-once); un job può eseguire due volte durante un cambio di coordinatore, e gli esiti sono deduplicati per id.

## Prossime fasi / next phases

2. Ponte `nuxiva-native` verso Python e integrazione col registro dei nodi esistente (`agenti/infrastruttura/nodes`), con test di parità.
3. Trasporto reale (WebSocket firmati) sopra `Envelope`, e portare lo stesso formato in Kotlin (`client_apk/logic`).
4. APK con asset locali di pagina 80 e canale di stato al posto del caricamento da origine server.
5. Prova su rete reale con più dispositivi.
