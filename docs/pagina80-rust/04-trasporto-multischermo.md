# 04 · Trasporto dati e multi-schermo

## 1. Problema

`backend/snapshot.py` ricalcola e serializza lo snapshot completo per ogni client ogni volta che `store.version` cambia, e consuma `holo_action` alla prima lettura (vedi 01 §2.1 e §2.2). Serve un flusso che costi una volta per modifica, indipendentemente dal numero di schermi, e che consegni gli eventi una tantum a tutti.

## 2. Modello

### 2.1 Stato versionato per sezione

Lo stato della pagina 80 viene diviso in sezioni indipendenti, ognuna con la propria versione monotona:

| Sezione | Proprietario | Visibilità |
|---------|--------------|------------|
| `system` | supervisor | pubblica |
| `nucleus` | regia | pubblica |
| `plan:<screen>` | planner | per schermo |
| `widget:<instance>` | sorgente del widget | per pubblico e schermo |
| `audience:<screen>` | presence-core | solo il codice del pubblico, mai le identità agli schermi |
| `brains`, `now_playing`, `home` | feature esistenti | in base alla sensibilità |
| `admin` | supervisor | solo sessioni admin |

### 2.2 Delta

- Formato iniziale: JSON Merge Patch (RFC 7396) per sezione, facile da migrare dal codice esistente.
- Formato finale: CBOR con campi numerici abbreviati, decodificato nel browser da `display-wasm`.
- Ogni frame contiene `{section, from, to, patch}`. Il client applica solo se `from` coincide con la propria versione; altrimenti chiede `resync` di quella sezione.
- Snapshot completo solo alla connessione e al `resync`.

### 2.3 Calcolo una volta, fan-out a N

```
modifica ─▶ assemblatore della sezione ─▶ delta calcolato una volta ─▶ broadcast
                                                                     ├─▶ filtro schermo 0 ─▶ coda 0 ─▶ pagina 80
                                                                     ├─▶ filtro schermo 1 ─▶ coda 1 ─▶ /screen?n=1
                                                                     └─▶ filtro schermo N ─▶ coda N ─▶ ...
```

- `tokio::sync::broadcast` con capacità limitata. Un client lento che perde frame riceve `resync` invece di bloccare gli altri.
- Il filtro per schermo applica pubblico, ruolo dello schermo e permessi prima dell'invio. È lo stesso punto Zero-Trust per tutti i trasporti.
- Serializzazione condivisa: i byte del delta sono `Arc<[u8]>`, copiati zero volte per i client che ricevono la stessa sezione.

### 2.4 Eventi una tantum

Le azioni come `holo_action`, suoni, comandi della regia non sono stato: diventano **eventi** in un registro circolare con numero di sequenza. Ogni client tiene il proprio cursore e riceve tutti gli eventi dopo il cursore, con scadenza (per esempio 5 s per le azioni olografiche). Nessun evento viene consumato da un solo client.

## 3. Migrazione senza rotture

| Passo | Cosa | Rischio |
|-------|------|---------|
| 1 | In Python: memoizzazione dello snapshot per `(store.version, admin)` e serializzazione unica condivisa tra i client SSE | Basso, nessun cambio di formato |
| 2 | In Python: `holo_action` spostato in un registro eventi con cursore per client | Basso, risolve il difetto multi-schermo |
| 3 | In Python: errori delle sezioni registrati con logger e campo `health` per sezione al posto di `except: pass` | Basso |
| 4 | Daemon Rust: sezioni e delta, endpoint WebSocket `nuxiva.display.v1` dietro feature flag `NUXIVA_DISPLAY_STREAM=rust` | Medio, doppio percorso per due release |
| 5 | Browser: `transport/` applica delta, `connectState` resta come fallback SSE | Medio |
| 6 | Rimozione del percorso snapshot completo quando le metriche (vedi 13) lo confermano | Basso |

## 4. Protocollo `nuxiva.display.v1`

| Messaggio | Direzione | Campi |
|-----------|-----------|-------|
| `hello` | client → daemon | `screen`, `device`, `token`, `caps` (WebGL2, WebGPU, XR, refresh, DPR, memoria), `versions` |
| `welcome` | daemon → client | `session`, `protocol`, `snapshot` filtrato |
| `delta` | daemon → client | `section`, `from`, `to`, `patch` |
| `event` | daemon → client | `seq`, `kind`, `payload`, `expires` |
| `plan` | daemon → client | piano di scena per lo schermo (vedi 05) |
| `budget` | daemon → client | budget e tier di qualità |
| `input` | client → daemon | interazioni utente aggregate: tocco, gesto, chiusura, spostamento, permanenza |
| `metrics` | client → daemon | campioni di costo per widget, ogni 5 s |
| `ack` | entrambe | `seq` o `to` per controllo di flusso |
| `resync` | client → daemon | `section` |

Validazione: ogni messaggio in ingresso ha schema rigido (`serde` con `deny_unknown_fields`), dimensione massima, frequenza massima per tipo. Messaggi non validi chiudono la connessione con codice applicativo e finiscono nel diario di sicurezza.

## 5. Multi-schermo

### 5.1 Identità dello schermo

- Ogni schermo ha un `device` stabile (già in `governor.js`, `localStorage` `nuxiva-device`) e un **token di schermo** firmato da `token-core`, rilasciato all'accoppiamento dal pannello admin o dal kiosk (`scripts/os/kiosk/session.sh`).
- Il token lega: indice `n`, ruolo, posizione nella stanza, capacità massime, scadenza e rotazione.
- Un client senza token valido vede solo il nucleo.

### 5.2 Ruoli e assegnazione

I ruoli esistenti (`agent`, `work`, `visual`, `person`) restano. Il planner li usa come vincoli morbidi:

| Ruolo | Preferisce | Evita |
|-------|------------|-------|
| `agent` (pagina 80) | Nucleo, conversazione, widget personali, urgenze | Widget pesanti di lavoro se esiste uno schermo `work` |
| `work` | Codice, documenti, lavagna, 3D di progetto, sistema | Media di intrattenimento |
| `visual` | Telecamere, sport, TV, diorama, modelli 3D, ologrammi | Testo lungo |
| `person` | Salute, umore, sincronizzazione personale | Qualsiasi dato di altre persone |

### 5.3 Spostamento tra schermi

- Il planner può spostare un widget su un altro schermo se libera il nucleo o risolve un conflitto. Lo spostamento è animato: uscita sul bordo verso lo schermo di destinazione e ingresso dal bordo opposto, usando la posizione fisica nota dal token.
- Il gesto «lancia verso lo schermo» (vedi 09) produce un `input` di tipo `move_to_screen`.
- Gli spostamenti hanno isteresi: un widget non cambia schermo più di una volta ogni 30 s salvo azione dell'utente.

### 5.4 Pubblico per schermo

Gli schermi possono essere in stanze diverse. Il pubblico (vedi 07) è calcolato per schermo usando le telecamere e i microfoni associati alla stanza dello schermo. Uno schermo in salotto con ospiti mostra solo il nucleo anche se lo studio, con il proprietario da solo, mostra tutto.

## 6. Sicurezza del trasporto

- Solo stessa origine, WebSocket su TLS dove la pagina è servita in TLS, cookie `HttpOnly`, `Secure`, `SameSite=Strict`.
- Controllo dell'header `Origin` all'upgrade.
- Il daemon ascolta solo sul socket Unix; il backend Python fa da proxy autenticato dell'upgrade WebSocket, così l'esposizione di rete resta quella attuale.
- Nessun dato personale nei log del trasporto: si registrano sezione, dimensione, durata, esito.
