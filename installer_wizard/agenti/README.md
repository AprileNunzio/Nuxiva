# Agenti di Nuxiva

Ogni agente è una cartella con un file `feature.json`. Il supervisore scansiona in background
(ogni 20 secondi) queste posizioni e la funzionalità compare da sola, come scheda, in
**Pannello → Funzionalità**:

| Cartella | Chi la crea |
|---|---|
| `installer_wizard/agenti/<categoria>/<id>/` | agenti di sistema, arrivano con gli aggiornamenti da GitHub |
| `/var/lib/nuxiva/agenti/<categoria>/<id>/` | agenti aggiunti dall'utente o creati da Nuxiva stessa |
| `/var/lib/nuxiva/features/<id>/` | funzionalità utente del formato precedente, ancora lette |

Una funzionalità non ha bisogno di modificare il pannello: la scheda, l'interruttore, le impostazioni e
la voce nel menu laterale (se l'utente la aggiunge ai preferiti) sono generati dal manifest.

## Struttura di un agente

Ogni agente vive in `agenti/<categoria>/<id>/` e ha sempre la stessa forma:

| Parte | Ruolo |
|---|---|
| `feature.json` | manifest: capacità, parole che lo richiamano (`routing`), risorse richieste (`profile`) |
| `agent.py` | coordinatore: ciclo di vita (`start`, `stop`) e `describe()` per il CEO |
| `tools/` | strumenti dell'agente registrati con `@tool(..., agent="<id>")` |
| `skills/` | abilità composte che usano gli strumenti |
| `algorithms/` | algoritmi generali dell'agente, mai codice scritto per un solo caso |
| `language/it.json`, `en.json`, `fr.json`, `es.json` | tutti i testi, nessuno scritto nel codice |
| `widget/` | facoltativo: widget dell'agente, senza sfondo e senza bordi |
| `icon.png` | icona generata dalla categoria |

Si importa sempre per id, `agenti.<id>.<modulo>`, mai per categoria. `agenti.<categoria>.<id>` resta
una vista in sola lettura utile per esplorare.

## Creare un agente nuovo

```bash
cd installer_wizard
python -m agenti nuovo --id calcio --categoria sport --nome "Calcio" \
  --descrizione "Risultati, classifiche e statistiche" --parole partita --parole classifica
python -m agenti verifica calcio
```

Il comando crea la cartella completa in un passaggio unico (nessuna cartella a metà se qualcosa va storto)
e rifiuta l'id se esiste già, anche come modulo interno di un'altra categoria. Se trova un agente che fa
già cose simili si ferma e lo indica: meglio potenziare quello. `--comunque` serve solo quando un agente
nuovo è davvero necessario. `verifica` senza id controlla tutti gli agenti e i manifesti rifiutati.

La generazione è scritta in Rust (`native/crates/agent-core`), con una copia Python identica byte per byte
usata quando il modulo nativo non è installato.

## Altri file

| File | Ruolo |
|---|---|
| `api.py` | rotte HTTP: `public_routes` (porta 80) e `admin_routes` (porta 8080), registrate in `backend/nuxiva_supervisor.py` |
| `service.py` | servizio esterno con una propria unità systemd (voce, visione, ascolto) |
| `admin.html` | una `<section class="tab" id="tab-<panel>">` inserita nel pannello |
| `admin.js` | registra la scheda con `NuxivaAdmin.tab("<panel>", { init, load, onState, leave })` |
| `admin.css` | stili della sola scheda |

Il supervisore inserisce da solo `admin.html`, `admin.js` e `admin.css` di ogni cartella nella pagina
del pannello: aggiungere una scheda non richiede di modificare `web/admin`.

## Manifest

```json
{
  "id": "meteo_avanzato",
  "name": "Meteo avanzato",
  "icon": "⛅",
  "category": "domotica",
  "order": 200,
  "source": "ai",
  "description": "Allerta meteo e qualità dell'aria per la tua zona.",
  "capabilities": ["Allerte della protezione civile", "Pollini e qualità dell'aria"],
  "pinned": false,
  "panel": "",
  "toggle": { "env": "NUXIVA_METEO_PLUS", "apply": [] },
  "requires": { "ram_gb": 2, "gpu_vram_gb": 0, "video": false, "commands": ["curl"], "features": ["ear"] },
  "settings": [
    { "key": "soglia_vento", "label": "Avvisami con vento oltre (km/h)", "type": "number", "default": "60" },
    { "key": "zona", "label": "Zona di allerta", "type": "select", "options": ["Campania", "Lazio"] }
  ]
}
```

| Campo | Significato |
|---|---|
| `id` | inizia con una lettera, poi minuscole, cifre e `_`; uguale al nome della cartella e unico in tutte le categorie |
| `category` | `creativita`, `percezione`, `cognizione`, `sicurezza`, `domotica`, `infrastruttura`, `multimedia`, `comunicazione`, `conoscenza`, `salute`, `sport`, `scienza`, `informatica` (deve coincidere con la cartella) |
| `source` | solo per le cartelle utente: `ai` (creata da Nuxiva) o `user` |
| `pinned` | se `true` compare già nel menu laterale alla prima scoperta |
| `panel` | scheda dedicata già presente nel pannello (es. `telegram`); vuoto = pagina generata |
| `toggle` | assente = sempre attiva. `env`: variabile `1`/`0` in `nuxiva.env` (con `tri: true` vale `auto`/`1`/`0`), `apply`: step da riconvergere. `hook`: interruttore Python registrato dal modulo (`registry.register_hook`) |
| `requires` | requisiti per la modalità **automatica**: se mancano la funzionalità resta spenta, con il motivo |
| `settings` | campi del modulo generato: `text`, `number`, `select`, `color`, `secret`, `bool`. Le chiavi MAIUSCOLE vanno in `nuxiva.env` (solo quelle ammesse per le funzionalità esterne), le altre restano nello stato della funzionalità (`registry.settings_of(id)`) |

## Nexus: zona, livello e procedura guidata

Campi facoltativi letti dal nuovo pannello Nexus (`/nexus`); se mancano, Nuxiva li deduce da `id` e `category`.

| Campo | Significato |
|---|---|
| `zone` | `brain`, `flows`, `tools`, `trust`, `network`, `system`, `observatory` |
| `family` | solo per `tools`: `perception`, `home`, `communication`, `leisure`, `productivity` |
| `level` | da quale livello è visibile: `explorer`, `pilot` (predefinito), `architect` |
| `wizard` | passi di «Configura con me»: `{"kind": "mode"}` oppure `{"setting": "<chiave>", "title": "…", "text": "…"}` |

Senza `wizard` la procedura viene generata da sola: modalità (se c'è `toggle`) e un passo per ogni impostazione.
Il Nexus mostra da solo il badge **Novità** per una funzionalità comparsa da meno di 7 giorni e **Aggiornato** quando
i suoi file cambiano con un aggiornamento.

## Modalità

Ogni funzionalità con interruttore ha tre modalità, scelte dalla scheda:

- **Automatica** (predefinita): Nuxiva la accende se l'hardware soddisfa `requires`, e la riaccende da
  solo quando l'hardware cambia (es. si collega una webcam);
- **Sempre attiva**: accesa comunque, a rischio dell'utente (la scheda mostra cosa manca);
- **Disattivata**.
