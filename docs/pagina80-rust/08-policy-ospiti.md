# 08 · Policy ospiti e matrice dei permessi

Crate: `access-core`, integrato con `features/authz`. Regola dell'utente: se parla un ospite e la voce non viene riconosciuta, informazioni personali e azioni complesse o private non vengono eseguite; un ospite può chiedere musica, luci e cose semplici.

## 1. Il problema del modello attuale

`features/authz/risk.py` classifica per **tool** (INFO, HOME, PERSONAL, FILES, CRITICAL) e `policy.py` dà a `guest` e `anonymous` il tetto `HOME` senza prova. Ma `HOME` contiene sia «accendi la luce» sia `ha_call_service` generico, `run_automation`, `emit_event`, `agent_tell`. Il rischio reale dipende da **cosa** si comanda, non dal nome del tool (vedi 01 §4).

## 2. Capacità atomiche

Ogni azione viene ridotta a una capacità con forma `dominio.oggetto.azione`, calcolata dal contenuto concreto della chiamata:

| Chiamata | Capacità |
|----------|----------|
| `ha_call_service(light, turn_on, light.salotto)` | `home.light.on` |
| `ha_call_service(lock, unlock, lock.ingresso)` | `home.lock.unlock` |
| `ha_call_service(climate, set_temperature, …, 30)` | `home.climate.set` con parametro fuori intervallo |
| `music_play(...)` | `media.music.play` |
| `person_profile(...)` | `people.profile.read` |
| `send_email(...)` | `comm.email.send` |
| `run_automation(id)` | `home.automation.run` + capacità delle azioni contenute nell'automazione |

Regole di calcolo:
- Le automazioni e i tool composti ereditano la capacità più rischiosa tra le azioni che contengono (come `COMPOSED` in `risk.py`, esteso alle automazioni Home Assistant lette dal registro).
- Una chiamata con più entità ha la capacità più rischiosa tra le entità.
- Capacità sconosciuta = `critical`. Fail-closed.

## 3. Ruoli e tipi di parlante

| Tipo | Come si determina |
|------|-------------------|
| `owner` | Persona con ruolo proprietario, prova almeno `SINGLE` |
| `family` | Membro della famiglia riconosciuto |
| `staff`, `friend` | Riconosciuti con ruolo dedicato nel Gestore Identità |
| `child` | Membro della famiglia marcato come minore |
| `guest` | Volto o voce non riconosciuti in presenza di un autorizzato |
| `anonymous` | Voce non riconosciuta senza autorizzati presenti, o comando da canale non identificato |

## 4. Matrice dei permessi

Legenda: ✅ consentito · 🔒 richiede proprietario presente con prova forte · ❌ negato · ⚠️ consentito con limiti

### 4.1 Casa

| Capacità | owner | family | staff | child | guest | anonymous |
|----------|-------|--------|-------|-------|-------|-----------|
| Luci on/off, intensità, colore nella stanza corrente | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ solo stanza dello schermo |
| Luci di altre stanze | ✅ | ✅ | ✅ | ⚠️ | ❌ | ❌ |
| Scene di atmosfera («relax», «cinema») | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ solo stanza |
| Tapparelle e tende interne | ✅ | ✅ | ✅ | ⚠️ | ⚠️ stanza corrente | ❌ |
| Coperture sensibili (garage, cancello) | ✅ con conferma | 🔒 | ❌ | ❌ | ❌ | ❌ |
| Serrature: blocca | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Serrature: sblocca o apri | 🔒 | 🔒 | ❌ | ❌ | ❌ | ❌ |
| Allarme: inserisci | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Allarme: disinserisci | 🔒 | 🔒 | ❌ | ❌ | ❌ | ❌ |
| Clima: ±2 °C entro 18-24 °C | ✅ | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| Clima: modalità, programmi, fuori intervallo | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Valvole, acqua, gas | 🔒 | 🔒 | ❌ | ❌ | ❌ | ❌ |
| Prese ed elettrodomestici | ✅ | ✅ | ⚠️ | ❌ | ❌ | ❌ |
| Eseguire automazioni | ✅ | ⚠️ in base alle azioni | ❌ | ❌ | ❌ | ❌ |
| Creare o modificare automazioni | 🔒 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Telecamere: vedere | ✅ | ⚠️ solo comuni | ❌ | ❌ | ❌ | ❌ |
| Telecamere: spegnere o modificare | 🔒 | ❌ | ❌ | ❌ | ❌ | ❌ |

### 4.2 Media e intrattenimento

| Capacità | owner | family | staff | child | guest | anonymous |
|----------|-------|--------|-------|-------|-------|-----------|
| Musica: riproduci, pausa, salta, volume | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Musica: playlist personali di altri | ✅ | ⚠️ proprie | ❌ | ⚠️ proprie | ❌ | ❌ |
| Volume oltre il limite delle ore di silenzio | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| TV, canali, sport in diretta | ✅ | ✅ | ✅ | ⚠️ filtro età | ✅ | ⚠️ |
| Giochi | ✅ | ✅ | ❌ | ⚠️ filtro età | ✅ | ❌ |
| Mostrare widget `public` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

### 4.3 Informazioni

| Capacità | owner | family | staff | child | guest | anonymous |
|----------|-------|--------|-------|-------|-------|-----------|
| Ora, meteo, conversioni, cultura generale | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Notizie e sport | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Timer e sveglie di sessione | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ |
| Agenda, email, contatti | ✅ propri | ✅ propri | ❌ | ⚠️ propri | ❌ | ❌ |
| Salute, umore, parametri | ✅ propri | ✅ propri | ❌ | ❌ | ❌ | ❌ |
| Chi è in casa, dove sono le persone | ✅ | ⚠️ famiglia | ❌ | ❌ | ❌ | ❌ |
| Memoria personale e ricordi | ✅ | ✅ propri | ❌ | ❌ | ❌ | ❌ |
| File e documenti | ✅ | ✅ propri | ❌ | ❌ | ❌ | ❌ |
| Sentinella | 🔒 | ❌ | ❌ | ❌ | ❌ | ❌ |

### 4.4 Sistema e azioni complesse

| Capacità | owner | family | staff | child | guest | anonymous |
|----------|-------|--------|-------|-------|-------|-----------|
| Agenzia: nuovi progetti, delega agli agenti | ✅ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Invio email e messaggi | 🔒 | ⚠️ propri con conferma | ❌ | ❌ | ❌ | ❌ |
| Acquisti e pagamenti | 🔒 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Firewall, VPN, rete, pacchetti, servizi, shell | 🔒 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Impostazioni del display | ✅ | ⚠️ proprie | ❌ | ❌ | ❌ | ❌ |
| Modelli e Cervello | 🔒 | ❌ | ❌ | ❌ | ❌ | ❌ |
| Creare tool, widget, feature | 🔒 | ❌ | ❌ | ❌ | ❌ | ❌ |

## 5. Ragionamento dietro la matrice

1. **Reversibilità**: si concede ciò che si annulla subito (luce, musica). Si nega ciò che ha effetti fisici o sociali difficili da annullare (aprire la porta, inviare email, spendere).
2. **Località**: un ospite è nella stanza; può agire sulla stanza dello schermo, non sulla casa.
3. **Proprietà del dato**: i dati di una persona sono di quella persona; nemmeno un familiare vede la salute di un altro.
4. **Prova proporzionale al danno**: il riconoscimento vocale da solo può essere imitato o registrato, quindi per le capacità 🔒 servono volto con liveness più voce, nella stessa finestra temporale, legati alla frase tramite `HeardLog`.
5. **Silenzio sulle informazioni**: a un ospite che chiede «dov'è Nunzio?» non si risponde nemmeno «non posso dirtelo per motivi di privacy» con dettagli; si usa una risposta neutra e cortese (chiave i18n `access.guest.not_available`), senza confermare l'esistenza del dato.
6. **Limiti di frequenza**: un ospite ha un tetto di comandi al minuto (predefinito 10) per evitare abusi e scherzi ripetuti.
7. **Ore di silenzio**: volume e luci forti limitati per ospiti e minori nelle ore di silenzio della casa.

## 6. Conferme sicure

- La conferma di un'azione sensibile deve venire dalla **stessa persona** che l'ha chiesta, verificata con `HeardLog.verify(slug, testo)`. Oggi `features/home_assistant/commands.py` accetta qualsiasi «conferma» nella finestra.
- Per le capacità 🔒 la conferma vocale non basta: serve anche la prova forte del volto entro 10 s, oppure una conferma sul telefono del proprietario tramite l'app.
- La finestra di conferma resta breve (quella attuale `CONFIRM_WINDOW`) e si annulla se il pubblico cambia.

## 7. Correzioni immediate (Fase 0)

1. `ha_call_service` calcola `sensitive` con `is_sensitive()` per ogni entità e passa dal percorso di conferma, invece di fissare `False`.
2. `DEFAULT_CEILING` per `guest` e `anonymous` resta `HOME`, ma `ha_call_service`, `run_automation`, `toggle_automation`, `emit_event`, `agent_tell`, `ceo_delegate` vengono valutati per capacità con `access-core` (in Python come primo passo, con la stessa tabella che poi passa al crate).
3. Conferma legata al parlante tramite `HeardLog`.

Ognuna con test di regressione: un ospite che chiede «sblocca la porta» all'agente riceve un rifiuto neutro e un evento `access.denied` nella Sentinella.

## 8. Interfaccia del crate

```rust
pub struct Request<'a> {
    pub capability: &'a Capability,
    pub speaker: Speaker,
    pub audience: &'a Audience,
    pub room: RoomId,
    pub params: &'a Params,
    pub now_ms: u64,
}

pub enum Verdict {
    Allow,
    AllowWithLimits(Limits),
    NeedProof(Strength),
    NeedOwnerConfirmation,
    Deny(DenyCode),
}

pub fn decide(req: &Request<'_>, matrix: &Matrix) -> Verdict;
```

La matrice è dati, non codice: file firmato in `/etc/nuxiva/access/matrix.json`, validato all'avvio, modificabile dal proprietario dal pannello autorizzazioni con anteprima delle conseguenze. Se la firma o lo schema non sono validi si usa la matrice di default compilata nel crate.

## 9. Test

- Test generati dalla matrice: per ogni cella un caso positivo e uno negativo.
- Test avversari: voce registrata riprodotta, foto del proprietario davanti alla webcam, automazione innocua che contiene uno sblocco, catena di tool composti, entità con nome ingannevole («luce_porta» che in realtà è una serratura: conta il dominio, non il nome).
