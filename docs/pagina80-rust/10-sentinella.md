# 10 · App Sentinella

Nuova applicazione nelle Applicazioni della pagina 8080, con un diario super dettagliato di ciò che Nuxiva vede, sente e fa. Esempi richiesti:

- «Ho visto Nunzio con una maglia grigia andare via»
- «Ho visto ospite 1 con occhiali neri»
- «Sono da tanto tempo senza fare nulla, mi sono messo a studiare X»
- «Ho avviato l'automazione X per controllare la casa»

## 1. Collocazione nel codice

| Parte | Percorso | Contenuto |
|-------|----------|-----------|
| Crate | `native/crates/sentinel-core/` | Schema eventi, narrazione a chiavi, diario a catena di hash, cifratura per giorno, conservazione |
| Binding | `native/crates/nuxiva-native/src/sentinel.rs` | Esposizione a Python |
| Feature backend | `installer_wizard/features/sentinel/` | `feature.json`, `api.py`, `collectors/` (presenza, aspetto, automazioni, attività di Nuxiva, accessi), `language/` |
| App 8080 | `client_web/src/apps/sentinel/` | `manifest.json`, `View.tsx`, `Timeline.tsx`, `Filters.tsx`, `EventCard.tsx`, `People.tsx`, `Settings.tsx`, `api.ts`, `types.ts`, `useSentinel.ts`, `sentinel.css`, `language/{it,en,es,fr}.json`, `icon.png` |
| Widget pagina 80 (facoltativo) | `installer_wizard/widgets/sentinel_pulse/` | Ultimi eventi non personali, solo con proprietario presente |

Stesso schema delle app esistenti come `client_web/src/apps/system_logs` (manifest con `featureIds`, `capabilities`, schede, azioni con permessi).

## 2. Modello dell'evento

```rust
pub struct SentinelEvent {
    pub id: EventId,
    pub at_ms: u64,
    pub kind: EventKind,
    pub subject: Subject,
    pub place: Option<RoomId>,
    pub attributes: Attributes,
    pub narrative: Narrative,
    pub sensitivity: Sensitivity,
    pub source: SourceModule,
    pub links: SmallVec<[EventId; 2]>,
}

pub enum Subject {
    Person(PersonKey),
    Guest(GuestTag),
    Nuxiva,
    Device(DeviceId),
    Automation(AutomationId),
}

pub struct Narrative {
    pub key: &'static str,
    pub params: Params,
}
```

- `narrative.key` è una chiave i18n, per esempio `sentinel.presence.left_wearing`. I parametri sono valori strutturati (`person`, `garment`, `color`). La frase viene composta nella lingua di chi legge, al momento della lettura.
- `GuestTag` è un numero progressivo per giornata («ospite 1», «ospite 2»), associato a una firma d'aspetto temporanea che non lascia la memoria del processo e viene distrutta a fine giornata.

### 2.1 Tipi di evento

| Gruppo | `kind` | Esempio di narrazione (it) |
|--------|--------|----------------------------|
| Presenza | `presence.arrived`, `presence.left`, `presence.near_screen` | «Ho visto Nunzio arrivare in salotto» |
| Aspetto | `appearance.noted` | «Ho visto Nunzio con una maglia grigia andare via» |
| Ospiti | `guest.arrived`, `guest.left`, `guest.appearance` | «Ho visto ospite 1 con occhiali neri» |
| Voce | `voice.recognized`, `voice.unknown` | «Ho sentito una voce che non conosco chiedere la musica» |
| Accessi | `access.allowed`, `access.denied`, `access.confirm_requested` | «Ospite 1 ha chiesto di sbloccare la porta: non l'ho fatto» |
| Automazioni | `automation.started`, `automation.finished`, `automation.failed` | «Ho avviato l'automazione Controllo casa» |
| Attività di Nuxiva | `self.idle_study`, `self.learned`, `self.maintenance` | «Sono da tanto tempo senza fare nulla, mi sono messo a studiare X» |
| Display | `display.scene_changed`, `display.privacy_shutter` | «Ho nascosto i dati della salute perché è arrivato un ospite» |
| Sistema | `system.alert`, `system.recovered` | «Il servizio di ascolto si è riavviato» |

## 3. Raccolta degli attributi d'aspetto

| Attributo | Metodo | Dove |
|-----------|--------|------|
| Colore del capo superiore | Regione del busto stimata sotto il box del volto, colore dominante in spazio Lab con k-means a 3 cluster, mappato su una palette di 12 nomi di colore (chiavi i18n) | `features/vision/appearance.py` nuovo, oppure modulo Rust in `sentinel-core` alimentato dai fotogrammi condivisi (`features/vision/shared_frames.py`) |
| Tipo di capo (maglia, giacca, camicia) | Classificatore leggero locale opzionale; in assenza si usa solo «capo» | Locale, mai cloud |
| Occhiali, cappello | Classificatore leggero su regione del volto, soglia di confidenza alta, altrimenti non riportato | Locale |
| Direzione (arriva, va via) | Direzione della traccia rispetto alla porta della stanza configurata | `features/vision/tracks.py` |

Regole:
- Un attributo viene scritto solo se la confidenza supera la soglia (predefinita 0,8). Meglio non dire che dire il falso.
- Nessuna immagine viene salvata: solo gli attributi in forma di codici.
- Gli attributi sensibili (etnia, età stimata, corporatura, stato emotivo dei visitatori) non vengono mai dedotti né salvati.

## 4. Attività autonome di Nuxiva

- `self.idle_study` richiede un vero ciclo di apprendimento quando il sistema è inattivo. Oggi `server/features/continuous_learning/learning_loop.py` è uno stub non collegato. La Sentinella registra solo ciò che accade davvero: l'evento nasce dal futuro ciclo di studio (per esempio aggiornamento dell'indice della memoria, studio di documentazione di un dispositivo appena collegato, ripasso delle abitudini) e mai da un testo inventato.
- Le automazioni scrivono `automation.started` e `automation.finished` dal motore automazioni (`features/automations`, crate `admin-os/automations.rs`) e da Home Assistant (`features/home_assistant/automations`).
- L'agenzia (`features/agency`) scrive gli avvii e gli esiti dei progetti come eventi `self.*` con link al progetto.

## 5. Cifratura e integrità

| Aspetto | Scelta |
|---------|--------|
| Cifratura a riposo | XChaCha20-Poly1305 per evento, nonce casuale a 192 bit |
| Chiavi | Chiave madre nel vault di sistema; chiave del giorno con HKDF-SHA-256 (`info = "sentinel" ‖ data`); chiavi dei giorni scaduti distrutte, così la cancellazione è crittografica |
| Integrità | Catena di hash BLAKE3: ogni voce contiene l'hash della precedente; ogni ora un blocco firmato con Ed25519 (chiave locale del sistema) |
| Archiviazione | File append-only per giorno in `STATE_DIR/sentinel/`, permessi `0600`, proprietario utente del servizio |
| Ricerca | Indice cifrato per tipo, soggetto pseudonimo e ora; testo libero mai indicizzato in chiaro |

## 6. Accesso

- Solo il proprietario, con prova forte (volto con liveness più sessione 8080 autenticata o conferma sul telefono). Capacità `sentinel.read` (vedi 08).
- Ogni lettura genera a sua volta un evento `sentinel.read` nel diario: chi ha letto cosa e quando.
- Un familiare può vedere solo gli eventi in cui è soggetto lui, se il proprietario lo abilita.
- API: `GET /api/sentinel/events` con filtri validati (intervallo massimo 31 giorni, paginazione a cursore, limite 200), `GET /api/sentinel/summary`, `POST /api/sentinel/export` (file cifrato con password scelta), `DELETE /api/sentinel/events` per intervallo o per soggetto.

## 7. Conservazione predefinita

| Tipo | Conservazione | Motivo |
|------|---------------|--------|
| Aspetto delle persone | 7 giorni | Dettaglio utile nel breve, invasivo nel lungo |
| Aspetto degli ospiti | 24 ore | Minimizzazione dei dati di terzi |
| Presenza | 30 giorni | Abitudini e sicurezza |
| Accessi negati e allarmi | 180 giorni | Sicurezza |
| Automazioni e attività di Nuxiva | 90 giorni | Diagnostica |

Tutto configurabile dal proprietario, con limiti massimi. Nelle impostazioni c'è anche l'opzione di avviso agli ospiti (messaggio vocale o cartello digitale sul nucleo al primo rilevamento), utile per la conformità alle norme sulla videosorveglianza domestica.

## 8. Interfaccia dell'app

Responsive, nessun testo letterale, chiavi in `language/{it,en,es,fr}.json`.

| Scheda | Contenuto |
|--------|-----------|
| Diario | Timeline verticale per ora, frasi narrative con icona del gruppo, filtro rapido per persona, ospiti, automazioni, Nuxiva |
| Persone | Per ogni persona: arrivi, uscite, tempo in casa, ultimi aspetti noti |
| Ospiti | Ospiti del giorno con attributi, senza immagini |
| Sicurezza | Accessi negati, conferme richieste, otturatore privacy attivato |
| Nuxiva | Cosa ha fatto Nuxiva da sola: studio, manutenzione, automazioni |
| Impostazioni | Conservazione, avviso agli ospiti, attributi registrati, esportazione, cancellazione |

Su mobile la timeline è a colonna singola con filtri in un pannello a scomparsa; su desktop a due colonne con dettaglio dell'evento a destra. Stile coerente con le app 8080 esistenti, carte senza sfondo pesante.

## 9. Test

- Narrazione: per ogni `kind` una frase in ogni lingua, test che verifica che tutte le chiavi esistano in `it`, `en`, `es`, `fr` (stesso schema di `tests/test_widget_language.py`).
- Cifratura: un byte modificato rompe la verifica della catena; chiave del giorno distrutta rende illeggibili gli eventi di quel giorno.
- Accesso: un familiare non legge gli eventi di altri; un ospite non può nemmeno sapere che la Sentinella esiste.
- Prestazioni: scrittura di un evento sotto 200 µs nel daemon; lettura di un giorno con 10.000 eventi sotto 150 ms.
