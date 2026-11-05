# 02 · Architettura obiettivo

## 1. Visione d'insieme

La pagina 80 diventa un piccolo sistema operativo di visualizzazione composto da tre livelli fisici:

1. **Daemon Rust `nuxiva-display`**: decide e distribuisce. Riceve candidati, presenza, risorse e input; produce piani di scena e delta di stato per ogni schermo. Non disegna.
2. **Backend Python esistente** (`installer_wizard`): resta il proprietario delle feature (meteo, persone, Home Assistant, agente). Parla con il daemon tramite il binding PyO3 `nuxiva-native` per le chiamate sincrone brevi e tramite socket Unix per il flusso continuo.
3. **Runtime browser della pagina 80 e di `/screen`**: disegna. Un solo renderer GPU per schermo, widget come moduli isolati, hot path in WebAssembly compilato dagli stessi crate Rust.

```
 sensori e feature Python           daemon Rust nuxiva-display                 schermi
┌──────────────────────┐   UDS    ┌───────────────────────────────┐  WSS/SSE  ┌────────────────────┐
│ vision, ear, people  │────────▶ │ presence-core                 │──────────▶│ pagina 80          │
│ authz, brain.privacy │          │ access-core                   │  delta    │ /screen?n=1..16    │
│ desktop, widgets     │────────▶ │ display-planner  + learner    │──────────▶│ visore XR          │
│ governor             │────────▶ │ display-scheduler             │◀──────────│ proiettore olo     │
│ home_assistant       │          │ display-stream (fan-out)      │  input    └────────────────────┘
└──────────────────────┘          │ sentinel-core (diario)        │
                                  └───────────────────────────────┘
```

## 2. Strati Clean Architecture

| Strato | Contenuto | Dipende da | Vietato |
|--------|-----------|------------|---------|
| Dominio | Tipi e regole pure: `Widget`, `Candidate`, `Surface`, `Screen`, `Audience`, `Capability`, `ScenePlan`, `SentinelEvent` | Niente, solo `serde` per la forma dei dati | I/O, orologio di sistema, rete, logging |
| Casi d'uso | `PlanScene`, `ScheduleTick`, `ResolveAudience`, `AuthorizeCapability`, `RecordObservation` | Dominio e trait di porta | Tipi concreti di adattatori |
| Porte | Trait: `Clock`, `CandidateSource`, `PresenceFeed`, `BudgetFeed`, `FeedbackStore`, `SealedJournal`, `StreamSink` | Dominio | Implementazioni |
| Adattatori | Socket Unix, PyO3, SQLite cifrato, WebSocket, file sigillati, sonde di sistema | Porte e librerie esterne | Regole di business |
| Composizione | `main.rs` del daemon e `lib.rs` del binding: costruiscono il grafo e lo avviano | Tutto | Logica |

Regola di dipendenza: le frecce puntano solo verso il dominio. Un crate di dominio che importa `tokio` o `rusqlite` fa fallire la CI (controllo con `cargo deny` e un test di dipendenze in `xtask`).

## 3. Crate Rust nuovi e riusati

Tutti dentro `native/crates/`, aggiunti al workspace con i lint già esistenti (`unsafe_code = "forbid"`, nessun `unwrap`, `expect`, `panic`, indicizzazione o aritmetica non controllata).

| Crate | Tipo | Responsabilità unica |
|-------|------|----------------------|
| `display-domain` | lib, dominio | Tipi della scena: widget, categorie, priorità, superfici, schermi, budget, pubblico |
| `display-planner` | lib, casi d'uso | Dal set di candidati al piano di scena: vincoli, punteggio, collocazione, conflitti, isteresi, spiegazione |
| `display-learner` | lib, casi d'uso | Preferenze apprese per persona e contesto, bandit contestuale con guardrail |
| `display-scheduler` | lib, casi d'uso | Ciclo di vita dei widget, cadenze di aggiornamento, coalescenza, contabilità del budget |
| `display-stream` | lib, adattatore | Stato versionato, calcolo dei delta, fan-out verso N schermi, eventi una tantum con cursore |
| `presence-core` | lib, dominio + casi d'uso | Fusione volto, voce, dispositivo in un `Audience` con confidenza e isteresi |
| `access-core` | lib, dominio + casi d'uso | Capacità atomiche, matrice dei permessi per ruolo e pubblico, prove richieste |
| `sentinel-core` | lib | Eventi della Sentinella, narrazione a chiavi, diario a catena di hash, cifratura per giorno |
| `surface-core` | lib, dominio | Descrittori di display: monitor, visore XR, proiettore olografico, con capacità e input |
| `display-daemon` | bin `nuxiva-display` | Composizione, socket Unix `/run/nuxiva/display/display.sock`, unit systemd |
| `display-wasm` | cdylib `wasm32` | Esporta al browser smoothing dei gesti, hit-test, interpolazione del layout, decodifica dei delta |
| `molecule-core` | lib, futuro | Parsing PDB/mmCIF, strutture secondarie, superfici, LOD (vedi 11) |
| `stage-core` | riuso | Stati `Shown`/`Min`/`Hidden` e regia delle superfici del nucleo |
| `spatial-core` | riuso | `PriorityArbiter`, `ZLayer`, `SafeZone`, `AssistantMorphology` |
| `gesture-core` | riuso | Landmark, pose, `duo.rs` a due mani, profili |
| `token-core` | riuso | Token firmati per accoppiare schermi e visori |
| `nuxiva-native` | riuso | Binding PyO3: aggiunge moduli `display`, `presence`, `access`, `sentinel` |

## 4. Struttura interna di un crate

Colocation per funzionalità anche dentro i crate. Esempio `display-planner`:

```
native/crates/display-planner/
├── Cargo.toml
└── src/
    ├── lib.rs
    ├── error.rs
    ├── constraints/
    │   ├── mod.rs
    │   ├── audience.rs
    │   ├── budget.rs
    │   └── capability.rs
    ├── scoring/
    │   ├── mod.rs
    │   ├── weights.rs
    │   └── context.rs
    ├── placement/
    │   ├── mod.rs
    │   ├── grid.rs
    │   ├── nucleus.rs
    │   └── packing.rs
    ├── conflicts/
    │   ├── mod.rs
    │   ├── exclusive.rs
    │   └── media.rs
    ├── stability/
    │   ├── mod.rs
    │   └── hysteresis.rs
    ├── explain/
    │   └── mod.rs
    └── tests/
        ├── placement_tests.rs
        └── conflicts_tests.rs
```

Ogni file sotto 500 righe, idealmente sotto 250. `lib.rs` contiene solo `pub mod` e le riesportazioni.

## 5. Contratti tra moduli

### 5.1 Porte del daemon

```rust
pub trait CandidateSource: Send + Sync {
    fn candidates(&self, screen: ScreenId) -> Result<Vec<Candidate>, SourceError>;
}

pub trait PresenceFeed: Send + Sync {
    fn audience(&self, screen: ScreenId) -> Audience;
}

pub trait BudgetFeed: Send + Sync {
    fn budget(&self, screen: ScreenId) -> Budget;
}

pub trait StreamSink: Send + Sync {
    fn publish(&self, screen: ScreenId, frame: DeltaFrame) -> Result<(), StreamError>;
}

pub trait FeedbackStore: Send + Sync {
    fn record(&self, sample: FeedbackSample) -> Result<(), StoreError>;
    fn model(&self, person: PersonKey) -> Result<PreferenceModel, StoreError>;
}

pub trait SealedJournal: Send + Sync {
    fn append(&self, event: SentinelEvent) -> Result<EntryId, JournalError>;
}
```

### 5.2 Protocollo sul socket Unix

- Framing: lunghezza `u32` big endian + payload CBOR (RFC 8949). JSON solo in modalità diagnostica.
- Autenticazione: socket con permessi `0660` e gruppo `nuxiva-display`, verifica `SO_PEERCRED` dell'UID chiamante, più token di sessione HMAC da `token-core` ruotato all'avvio.
- Operazioni idempotenti con `request_id` (UUIDv7) e risposta tipizzata `Ok | Err{code}`. I codici di errore sono chiavi i18n, mai testo.
- Limiti: frame massimo 1 MiB, coda di ingresso limitata con backpressure, timeout per operazione.

### 5.3 Contratto browser

- Trasporto: WebSocket sicuro su origine identica, sottoprotocollo `nuxiva.display.v1`, con fallback SSE sola lettura.
- Messaggi: `hello`, `plan`, `delta`, `event`, `budget`, `input`, `ack`. Dettagli in 04.
- Il browser non decide mai cosa è permesso: riceve solo ciò che il pubblico corrente può vedere.

## 6. Runtime browser modulare

`display.html` passa da 52 script globali a un caricatore unico a moduli ES:

```
installer_wizard/web/display/
├── boot/            avvio, registro servizi, gestore globale degli errori
├── kernel/          scheduler rAF a corsie, bus eventi, ciclo di vita widget
├── renderer/        renderer GPU condiviso, pool di scene, atlas di texture
├── transport/       client del flusso, applicazione dei delta, riconnessione
├── nucleus/         avatar, sfera, flusso vocale lineare, transizioni
├── presence/        reazione al pubblico, otturatore privacy
├── hands/           pipeline due mani, cursori, hit-test (WASM)
├── layout/          applicazione del piano di scena, animazioni FLIP
├── widgets-host/    sandbox dei widget, API `ctx` stabile
└── i18n/            caricamento chiavi, formattazione locale
```

Ogni directory contiene vista, logica, stili, tipi e traduzioni propri. Il gestore globale degli errori (`boot/errors`) intercetta `error` e `unhandledrejection`, registra con contesto del modulo, invia un report limitato al backend e mostra all'utente solo uno stato discreto del nucleo, mai uno stack.

### 6.1 API stabile per i widget

I widget esistenti si registrano con `NuxivaDesk.register`. La nuova API `ctx` resta compatibile e aggiunge:

| Metodo | Scopo |
|--------|-------|
| `ctx.subscribe(source, handler)` | Sottoscrizione condivisa a una sorgente; una sola connessione per sorgente per schermo |
| `ctx.scene(options)` | Richiede una scena nel renderer condiviso invece di creare un contesto WebGL |
| `ctx.frame(handler, lane)` | Callback di frame nella corsia `interactive`, `live` o `ambient` |
| `ctx.visibility(handler)` | Notifica `live`, `frozen`, `hibernated` |
| `ctx.t(key, params)` | Traduzione |
| `ctx.report(error)` | Errore verso il gestore globale |

Un widget che crea direttamente `WebGLRenderer` o `getContext("webgl")` fallisce il test di conformità dei widget (vedi 13).

## 7. Modularità da sistema operativo

- **Manifest per modulo**: ogni crate, feature Python e modulo browser dichiara nome, versione, capacità richieste, porte esposte, costo atteso. Il daemon rifiuta moduli che chiedono capacità non concesse.
- **Isolamento dei guasti**: un widget che lancia errori ripetuti viene messo in quarantena dallo scheduler, il resto della scena prosegue. Un adattatore che fallisce degrada la sua sezione, non il daemon.
- **Supervisione**: `nuxiva-display` sotto systemd con `Restart=on-failure`, `MemoryMax`, `ProtectSystem=strict`, `NoNewPrivileges`, `PrivateTmp`, `RestrictAddressFamilies=AF_UNIX`, `SystemCallFilter=@system-service`.
- **Avvio a freddo**: se il daemon non risponde, la pagina 80 mostra solo il nucleo e la regola di privacy più restrittiva. Fail-closed.
- **Aggiornabilità**: protocollo versionato, il browser dichiara `v1` e il daemon risponde con la versione più alta comune.

## 8. Sicurezza trasversale

| Minaccia | Contromisura |
|----------|--------------|
| Client non autorizzato che si collega al flusso | Cookie di sessione display + token di schermo firmato (`token-core`), legato all'ID dispositivo del governatore |
| Iniezione nei dati dei widget (testo dall'LLM) | Sanitizzazione al confine nel daemon, rendering solo con `textContent` o template sicuri, CSP `script-src 'self'` senza `unsafe-inline` |
| Fuga di dati personali su schermi in presenza di ospiti | Il filtro è nel daemon, il browser non riceve mai dati che il pubblico non può vedere |
| Replay della voce per ottenere azioni | Prova forte richiesta per capacità sensibili, liveness e finestra temporale legata a `HeardLog` |
| Manomissione del diario Sentinella | Catena di hash, firma per blocco, cifratura AEAD per giorno |
| Esaurimento risorse | Code limitate, budget per schermo, quarantena widget, `MemoryMax` |

## 9. Cosa non cambia

- Le feature Python restano proprietarie dei propri dati e API.
- I 73 widget esistenti continuano a funzionare tramite lo strato di compatibilità finché non vengono migrati.
- La regola già in produzione sul nucleo (resta fermo finché i widget non lo coprono, poi solo voce) diventa una regola del planner, con lo stesso comportamento visibile.
