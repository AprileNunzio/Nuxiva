# 05 · Motore decisionale dei widget

Crate: `display-planner`. Input: candidati, schermi, pubblico, budget, contesto, preferenze apprese. Output: un **piano di scena** per schermo, con spiegazione di ogni scelta.

## 1. Domande a cui risponde

1. Quanti widget mostrare su ogni schermo adesso.
2. Quali, in base a categoria, priorità, contesto e pubblico.
3. Dove: schermo, superficie, dimensione, livello Z.
4. Come risolvere i conflitti tra widget.
5. Che forma deve avere il nucleo: intero, ridotto, sfera, flusso vocale lineare.
6. Quando cambiare, senza far ballare lo schermo.

## 2. Modello dei dati

### 2.1 Candidato

```rust
pub struct Candidate {
    pub instance: InstanceId,
    pub widget: WidgetId,
    pub category: Category,
    pub priority: Priority,
    pub sensitivity: Sensitivity,
    pub owner: Option<PersonKey>,
    pub size: SizeClass,
    pub cost: Cost,
    pub cadence: Cadence,
    pub exclusive: Option<ExclusiveGroup>,
    pub media: Option<MediaChannel>,
    pub screen_role: Option<ScreenRole>,
    pub forced: Forced,
    pub born_at_ms: u64,
    pub ttl_ms: Option<u64>,
}
```

### 2.2 Categorie

| Categoria | Esempi di widget attuali | Peso base |
|-----------|--------------------------|-----------|
| `safety` | `alarm`, `alert_*`, red alert | Forzato |
| `conversation` | risposte della chat, sottotitoli, ragionamento | 0,95 |
| `personal` | `health_hub`, `vital_check`, `mood_aura`, `sync_pulse`, agenda | 0,85 |
| `home` | Home Assistant, energia, telecamere | 0,75 |
| `work` | `code_view`, `kanban_board`, `document_viewer`, `lavagna`, `studio_3d` | 0,7 |
| `media` | musica, TV, karaoke, spettro audio | 0,65 |
| `info` | meteo, notizie, sport, borsa | 0,5 |
| `system` | risorse, rete, firewall, token | 0,4 |
| `ambient` | orologio grande, particelle, diorama decorativo | 0,2 |

La categoria si dichiara nel nuovo campo `category` di `widget.json`; per i 73 widget esistenti viene assegnata da una tabella di migrazione nel crate, verificata da test.

### 2.3 Priorità

Si riusa `NotificationPriority` di `spatial-core` (P0-P3) per l'urgenza, e la `priority` numerica esistente dei manifest (0-100) per l'importanza. Sono due assi diversi: urgenza dice quando, importanza dice quanto.

### 2.4 Sensibilità

| Livello | Significato | Chi può vederlo |
|---------|-------------|-----------------|
| `public` | Nessun dato personale | Chiunque, anche ospiti, se le impostazioni lo permettono |
| `household` | Dati della casa non personali | Membri della casa autorizzati |
| `personal` | Dati di una persona | Solo la persona proprietaria, presente e riconosciuta |
| `sensitive` | Salute, finanze, documenti, posizione | Solo la persona proprietaria, da sola davanti allo schermo, o con persone esplicitamente autorizzate |

Allineata ai livelli di `features/brain/privacy` (public, personal, sensitive) con l'aggiunta di `household`.

## 3. Pipeline del planner

```
candidati ─▶ 1 vincoli rigidi ─▶ 2 punteggio ─▶ 3 selezione nel budget ─▶ 4 collocazione
          ─▶ 5 conflitti ─▶ 6 forma del nucleo ─▶ 7 stabilità ─▶ 8 spiegazione ─▶ piano
```

### 3.1 Vincoli rigidi (filtri, mai violati)

- **Pubblico**: un candidato `personal` o `sensitive` passa solo se il proprietario è nel pubblico dello schermo con la confidenza richiesta e nessuno non autorizzato è presente (vedi 07).
- **Permesso**: il pubblico deve poter vedere la categoria secondo `access-core` (vedi 08).
- **Capacità dello schermo**: un widget 3D che richiede WebGL2 non va su uno schermo che non lo supporta; un widget XR solo su superfici XR.
- **Ruolo `person`**: solo widget del proprietario dello schermo.
- **Quarantena**: widget in quarantena esclusi.

### 3.2 Punteggio

```
score = w_cat · categoria
      + w_imp · importanza/100
      + w_urg · urgenza
      + w_ctx · rilevanza_contesto
      + w_rec · freschezza
      + w_pref · preferenza_appresa(persona, contesto, widget)
      + w_int · interazione_recente
      − w_cost · costo/budget
      − w_age · età_oltre_ttl
```

- `rilevanza_contesto`: corrispondenza con l'intento dell'ultima frase (gli `intents` dei manifest), con il progetto attivo dell'agenzia, con l'ora del giorno, con la stanza.
- `preferenza_appresa`: dal crate `display-learner` (vedi 06), limitata in `[-0,3, +0,3]` per non scavalcare urgenze e categorie.
- I pesi `w_*` sono in un file di configurazione validato, versionato, con valori di default nel crate. Il learner può regolare solo `w_pref` e i pesi di contesto entro limiti.

### 3.3 Quanti widget

Selezione greedy per rapporto `score / costo` (problema dello zaino con limite di superficie e budget), con tre tetti:

1. **Budget** di risorse dello schermo (vedi 03 §4).
2. **Superficie**: area libera dopo l'area minima del nucleo nella forma corrente.
3. **Carico cognitivo**: tetto di widget simultanei in base al contesto.

| Contesto | Tetto cognitivo predefinito |
|----------|-----------------------------|
| Conversazione attiva | 3 |
| Lavoro su progetto | 6 |
| Ambiente, nessuna interazione | 4 |
| Multi-schermo, schermo `work` o `visual` | 8 |
| Ospiti presenti | 0 personali, solo `public` se attivato |

L'utente può alzare o abbassare i tetti nelle impostazioni del display; il learner propone, non impone.

### 3.4 Collocazione

- Griglia logica per schermo (12 colonne × righe in base al rapporto d'aspetto), con area protetta del nucleo (`SafeZone` di `spatial-core`).
- Algoritmo: skyline bin packing per dimensione decrescente, con posizioni preferite per categoria (conversazione vicino al nucleo, urgenze in alto al centro, media in basso, info ai lati).
- Rispetto delle posizioni fissate dall'utente (`pos` esistente): sono vincoli, non suggerimenti.
- Layout mobile e desktop: su schermi stretti la griglia diventa una colonna con paginazione, sempre dallo stesso piano.
- Nessuno sfondo e nessun bordo: la separazione tra widget si ottiene con spaziatura e tipografia, quindi il planner garantisce un margine minimo tra superfici (`MARGIN` di `stage-core`).

### 3.5 Conflitti

| Tipo | Esempio | Regola |
|------|---------|--------|
| Gruppo esclusivo | Due lettori video, `tv_player` e `cam_stream` a tutto schermo | Vince il punteggio più alto, l'altro va su un altro schermo o in Warm |
| Canale media | Musica e TV con audio | Un solo canale audio attivo; l'altro passa a muto con indicatore |
| Stessa sorgente | `weather` grande e badge meteo | Si tiene il più informativo, l'altro si fonde |
| Copertura del nucleo | Widget grande sopra l'avatar | Si sposta il widget o si cambia forma al nucleo (§3.6) |
| Sovrapposizione Z | Urgenza e takeover | Arbitrato con `PriorityArbiter` e `ZLayer` di `spatial-core` |
| Privacy | Widget personale con un ospite in arrivo | Il vincolo rigido lo rimuove subito, prima di ogni altra regola |

### 3.6 Forma del nucleo

Si riusa `AssistantMorphology`:

| Forma | Quando | Area |
|-------|--------|------|
| `CoreHero` | Lo spazio libero permette l'avatar intero al centro | Intera |
| `FloatingOrb` | I widget scelti coprirebbero il centro: il nucleo si rimpicciolisce e si sposta nell'area libera più ampia | 8-15 % del lato corto |
| `AmbientStream` | Lo spazio libero scende sotto il 20 % del lato corto (soglia già in produzione in `desk.js`) | Flusso vocale lineare elegante su un bordo |
| `WhisperPill` | Takeover a tutto schermo (video, 3D immersivo) | Indicatore minimo che reagisce alla voce |

Regole:
- Il nucleo resta `CoreHero` finché i widget non coprono davvero la sua area. Il planner prova prima a collocare i widget attorno al nucleo, poi riduce il nucleo, infine passa al flusso vocale.
- Senza pubblico autorizzato il nucleo è sempre `CoreHero` da solo (vedi 07).
- Transizioni morbide con interpolazione calcolata da `display-wasm`, mai salti.

### 3.7 Stabilità

- **Isteresi di ingresso e uscita**: un candidato entra se supera la soglia di ingresso, esce solo sotto la soglia di uscita (come `SHOWN_AT` e `MIN_AT` di `stage-core`).
- **Permanenza minima**: un widget mostrato resta almeno 8 s salvo chiusura dell'utente, privacy o urgenza.
- **Costo di spostamento**: cambiare posizione a un widget visibile ha un costo nel punteggio, così il layout non salta per piccole variazioni.
- **Frequenza massima di ripianificazione**: 4 Hz per schermo, con ripianificazione immediata solo per privacy e urgenze.

### 3.8 Spiegazione

Ogni piano porta per ogni candidato una traccia compatta: `shown | hidden`, motivo principale (codice), contributi del punteggio. È visibile nel pannello admin del desktop a widget e nella Sentinella, come chiavi i18n («Ho nascosto il meteo per fare spazio alla chiamata»). Serve per fiducia, debug e per il learner.

## 4. Interfaccia del crate

```rust
pub struct PlannerInput<'a> {
    pub screens: &'a [ScreenState],
    pub candidates: &'a [Candidate],
    pub audiences: &'a AudienceMap,
    pub budgets: &'a BudgetMap,
    pub context: &'a Context,
    pub preferences: &'a dyn PreferenceView,
    pub previous: &'a ScenePlanSet,
    pub now_ms: u64,
}

pub fn plan(input: &PlannerInput<'_>, policy: &PlannerPolicy) -> Result<ScenePlanSet, PlanError>;
```

Funzione pura e deterministica a parità di input: si può testare con proprietà (proptest) e riprodurre ogni decisione dai log.

## 5. Prestazioni attese

- Complessità O(n log n) sui candidati per schermo; n tipico sotto 100.
- Obiettivo: piano completo per 4 schermi e 100 candidati sotto 2 ms su CPU x86-64 di riferimento (da verificare con il banco di prova in 13).
- Nessuna allocazione nel percorso caldo dopo il riscaldamento: buffer riusati per schermo.

## 6. Test specifici

- Proprietà: nessun widget `personal` nel piano se il proprietario non è nel pubblico; nessuna sovrapposizione di superfici; budget mai superato da widget non forzati; nucleo mai coperto.
- Scenari dorati: conversazione + meteo + musica; progetto 3D su schermo `work`; ospite che entra durante la visione della salute; takeover video.
- Stabilità: sequenze di input rumorose non producono più di N cambi di layout al minuto.
