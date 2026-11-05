# 06 · Apprendimento continuo del layout

Crate: `display-learner`. Scopo: il motore decisionale migliora nel tempo osservando cosa l'utente usa, chiude, sposta o guarda, senza mai scavalcare privacy, sicurezza e urgenze.

## 1. Segnali raccolti

| Segnale | Origine | Interpretazione |
|---------|---------|-----------------|
| Chiusura entro 3 s | `input` dal browser | Forte negativo per quel widget in quel contesto |
| Chiusura dopo uso | `input` | Neutro, compito concluso |
| Interazione (tocco, gesto, scroll) | `input` | Positivo |
| Permanenza dello sguardo o della mano | Gesti e stima dello sguardo, solo se le mani via webcam sono attive | Positivo debole |
| Spostamento manuale | `input` `move` | Preferenza di posizione |
| Ingrandimento o riduzione | `input` `resize` | Preferenza di dimensione |
| Richiesta vocale esplicita («mostrami il meteo») | Agente | Positivo forte, contesto annotato |
| Richiesta di nascondere | Agente | Negativo forte |
| Widget ignorato e scaduto | Scheduler | Negativo debole |

Nessun segnale contiene contenuti del widget: solo identificatori, contesto codificato e tempi.

## 2. Contesto

Vettore compatto di caratteristiche, discreto per robustezza:

- fascia oraria (6 fasce), giorno feriale o festivo
- stanza e ruolo dello schermo
- persona proprietaria (chiave pseudonima)
- attività: conversazione, lavoro su progetto, media, ambiente
- numero di persone presenti (0, 1, 2+)
- intento recente (gruppo di `intents`)

## 3. Algoritmo

### 3.1 Bandit contestuale

Per ogni coppia `(persona, widget)` si tiene un modello lineare bayesiano sulle caratteristiche di contesto (Thompson sampling con priori gaussiane, o LinUCB come alternativa deterministica per i test). L'output è `preferenza_appresa ∈ [-0,3, +0,3]` usata nel punteggio (05 §3.2).

Motivi della scelta:
- impara online con pochi dati e costi minimi di memoria (matrici piccole per widget),
- gestisce esplorazione e sfruttamento in modo misurabile,
- è spiegabile: si può mostrare il contributo di ogni caratteristica.

### 3.2 Preferenze di posizione e dimensione

Istogrammi decadenti per `(persona, widget, ruolo schermo)` sulle celle della griglia e sulle classi di dimensione. Il planner usa la moda come posizione preferita se libera.

### 3.3 Decadimento

Ogni statistica decade con emivita configurabile (predefinita 21 giorni), così le abitudini nuove sostituiscono quelle vecchie.

### 3.4 Pesi globali

Il learner può proporre aggiustamenti ai pesi di contesto (`w_ctx`, `w_pref`) entro ±20 % dei valori di default. La proposta si applica solo se la valutazione offline (§5) mostra un miglioramento; altrimenti resta un suggerimento nel pannello admin.

## 4. Guardrail

| Regola | Motivo |
|--------|--------|
| Il learner non vede né modifica vincoli rigidi (pubblico, permessi, capacità) | Privacy e sicurezza non si imparano |
| Categoria `safety` e urgenze P0-P1 escluse dall'apprendimento | Un allarme non deve mai diventare «poco gradito» |
| Contributo massimo limitato | Nessuna preferenza appresa può nascondere un widget richiesto esplicitamente |
| Esplorazione solo su widget `info`, `ambient`, `system`, `media` e mai con ospiti | Evita sorprese e fughe di dati |
| Tasso massimo di esplorazione 5 % delle decisioni | Esperienza stabile |
| Freno di emergenza: reset del modello di una persona dal pannello e dalla voce del proprietario | Controllo all'utente |

## 5. Valutazione

- **Offline**: replay dei log di decisione (05 §3.8) con stimatore inverse propensity scoring per stimare il valore di una nuova politica prima di attivarla.
- **Online**: metriche per persona su finestre di 7 giorni: tasso di chiusura rapida, interazioni per widget mostrato, richieste esplicite di widget non mostrati (segno che il planner li ha persi).
- I risultati sono visibili nel pannello admin come numeri, senza promesse qualitative.

## 6. Memoria e privacy

- Persistenza in SQLite con righe sigillate AEAD (XChaCha20-Poly1305), chiave derivata con HKDF dalla chiave del vault del sistema e dall'identificatore della persona. Si riusa il modello di `features/biometrics/sealed_rows.py` lato Python, con implementazione nativa nel crate.
- Chiavi persona pseudonime (HMAC dello slug con chiave locale), mai nomi in chiaro nel modello.
- Esportazione e cancellazione per persona dal Gestore Identità, coerente con il principio «niente di imparato va perso» ma con diritto di cancellazione esplicito.
- Ospiti: nessun apprendimento persistente. Solo statistiche di sessione in memoria, cancellate quando l'ospite esce.

## 7. Interfaccia

```rust
pub trait PreferenceView {
    fn affinity(&self, person: PersonKey, widget: WidgetId, ctx: &ContextVector) -> Affinity;
    fn placement(&self, person: PersonKey, widget: WidgetId, role: ScreenRole) -> Option<CellHint>;
}

pub struct Learner<S: FeedbackStore> {
    store: S,
    models: ModelCache,
    policy: LearnerPolicy,
}

impl<S: FeedbackStore> Learner<S> {
    pub fn observe(&mut self, sample: FeedbackSample) -> Result<(), LearnError>;
    pub fn snapshot(&self) -> PreferenceSnapshot;
    pub fn reset(&mut self, person: PersonKey) -> Result<(), LearnError>;
}
```

`PreferenceSnapshot` è immutabile e condiviso con il planner tramite `Arc`, aggiornato al massimo una volta al secondo: il planner non aspetta mai il learner.
