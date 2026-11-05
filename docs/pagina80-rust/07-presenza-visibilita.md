# 07 · Presenza e visibilità

Crate: `presence-core`. Regola dell'utente: pulsanti, widget e chat sono visibili solo quando un utente autorizzato viene visto o parla. Se non c'è nessuno, o ci sono solo ospiti, tutto scompare tranne il nucleo centrale, per risparmiare memoria e proteggere la privacy.

## 1. Segnali in ingresso

| Segnale | Origine attuale | Cosa porta |
|---------|-----------------|------------|
| Volto | `features/vision/tracks.py`, `features/people/presence.py` | `slug` o sconosciuto, confidenza, `near`, `since`, traccia |
| Liveness del volto | `features/biometrics/liveness.py` | Punteggio anti foto e anti schermo |
| Voce | `features/ear/voiceprint.py` (`identify`, evento `biometrics.voice`) | `slug` o nessuno, punteggio, margine sui gemelli |
| Frase legata alla voce | `features/authz/heard.py` (`HeardLog`) | Prova che una frase è stata detta da una voce riconosciuta negli ultimi 45 s |
| Dispositivo personale | `features/places/locate.py` (BLE, telefono) | Presenza probabile nella stanza, prova debole |
| Stanza dello schermo | Token di schermo (04 §5.1) | Quali telecamere e microfoni contano per quello schermo |

## 2. Modello del pubblico

```rust
pub enum AudienceKind {
    Empty,
    GuestOnly,
    Authorized,
    Mixed,
    Uncertain,
}

pub struct Audience {
    pub kind: AudienceKind,
    pub members: SmallVec<[Member; 4]>,
    pub guests: u8,
    pub confidence: f32,
    pub since_ms: u64,
}

pub struct Member {
    pub person: PersonKey,
    pub role: Role,
    pub proof: Strength,
    pub near: bool,
}
```

| Tipo | Condizione |
|------|------------|
| `Empty` | Nessun volto e nessuna voce da almeno `away_s` (oggi `NUXIVA_PRIVACY_AWAY_S`, 10 s) |
| `GuestOnly` | Solo volti sconosciuti o voci non riconosciute |
| `Authorized` | Solo persone riconosciute con ruolo `owner`, `family` o altri ruoli autorizzati al display |
| `Mixed` | Almeno un autorizzato e almeno un ospite |
| `Uncertain` | Segnali in conflitto o confidenza sotto soglia; trattato come il caso più restrittivo tra quelli possibili |

### 2.1 Fusione

- Prova per persona = massimo tra volto (con liveness) e voce, con bonus se entrambi concordano nella stessa finestra di 10 s. Le soglie si leggono dai valori attuali di `voiceprint` (`match_base`, `margin`) e della visione, non vengono duplicate.
- La forza della prova segue `Strength` di `features/authz/principal.py`: `WEAK` dispositivo, `SINGLE` volto o voce, `STRONG` volto con liveness più voce concordante.
- Una persona riconosciuta solo dal dispositivo BLE non rende il pubblico `Authorized`: serve almeno volto o voce.

### 2.2 Isteresi

| Transizione | Tempo |
|-------------|-------|
| Verso più permessi (`Empty` → `Authorized`) | Stabile per 1,2 s (oggi `STABLE_SECONDS`) |
| Verso meno permessi per arrivo di un ospite (`Authorized` → `Mixed`) | **Immediata**, nessuna attesa |
| Verso `Empty` | Dopo `away_s` |
| Perdita temporanea del volto durante la conversazione | Tenuta finché la voce autorizzata continua (oggi `NUXIVA_PRIVACY_VOICE_S`, 30 s) |

Asimmetria voluta: chiudere è sempre più rapido che aprire.

## 3. Cosa si vede in ogni stato

| Elemento | `Empty` | `GuestOnly` | `Mixed` | `Authorized` |
|----------|---------|-------------|---------|--------------|
| Nucleo | `CoreHero` al centro | `CoreHero` | Forma decisa dal planner | Forma decisa dal planner |
| Dock, pulsanti, rail laterali | Nascosti | Nascosti | Solo comandi `public` | Tutti quelli permessi al ruolo |
| Chat e sottotitoli | Nascosti | Solo la risposta in corso all'ospite, senza cronologia | Senza cronologia personale | Completa per la persona presente |
| Widget `public` | Nessuno | Nessuno, o orologio e meteo se il proprietario lo abilita (`NUXIVA_DISPLAY_GUEST_PUBLIC`, predefinito spento) | Sì | Sì |
| Widget `household` | Nessuno | Nessuno | Solo se il proprietario ha marcato gli ospiti come fidati | Sì |
| Widget `personal` | Nessuno | Nessuno | Nessuno | Solo del proprietario presente |
| Widget `sensitive` | Nessuno | Nessuno | Nessuno | Solo se la persona è sola o con persone autorizzate da lei |
| Allarmi `safety` | Sì | Sì, senza dettagli personali | Sì | Sì |
| Effetti | Solo nucleo | Solo nucleo | Planner | Planner |

## 4. Risparmio di memoria con la scena vuota

Quando il pubblico diventa `Empty` o `GuestOnly`:

1. Il planner produce un piano con il solo nucleo.
2. Lo scheduler porta tutti i widget a Frozen subito (nessun rendering), poi a Dormant dopo il periodo di grazia (predefinito 60 s): DOM, scene GPU, sottoscrizioni e script inutilizzati vengono rilasciati.
3. Il renderer condiviso libera texture e buffer non referenziati dal nucleo.
4. Il daemon riduce le cadenze delle sorgenti a Warm o le sospende.

Il ritorno di un autorizzato riporta la scena in meno di 1 s grazie ai dati Warm nel daemon, con transizione elegante del nucleo che «apre» la scena.

## 5. Otturatore privacy

Situazione critica: il proprietario sta guardando la propria salute e entra un ospite.

- Il browser ha un otturatore locale (`presence/`) che reagisce all'evento `audience` con il tipo `Mixed` o `GuestOnly` **prima** che arrivi il nuovo piano: tutte le superfici con sensibilità `personal` o `sensitive` vengono nascoste con una dissolvenza di 120 ms e il loro DOM svuotato.
- Subito dopo il daemon invia il piano filtrato e lo scheduler rilascia le risorse.
- Obiettivo misurabile: dall'apparizione del volto sconosciuto alla scomparsa dei dati personali sotto 300 ms al 95° percentile, di cui la parte di visione è la quota principale (vedi 13).

## 6. Persone riconosciute ma non autorizzate al display

Ruoli come `staff` (per esempio collaboratrice domestica) o `friend` vengono riconosciuti ma non sono autorizzati ai widget personali di altri. Per il display contano come ospiti, mentre per i comandi ricevono la matrice del proprio ruolo (vedi 08). Il proprietario sceglie per ogni persona nel Gestore Identità se è autorizzata al display.

## 7. Integrazione con il codice esistente

| Oggi | Domani |
|------|--------|
| `features/desktop/privacy.py` (`away`, `voice_s`) | Diventa un adattatore che legge le impostazioni e le passa a `presence-core`; la logica passa al crate |
| `features/people/presence.py` (`smooth`, `merge`) | Resta proprietario della pipeline di visione e saluti, pubblica le osservazioni a `presence-core` tramite binding |
| Snapshot `presence` nello store | Gli schermi ricevono solo `audience:<screen>` con il tipo, mai nomi né conteggi dettagliati se non autorizzati |

## 8. Impostazioni

Nella feature `desktop`, con chiavi i18n:

| Chiave | Predefinito | Effetto |
|--------|-------------|---------|
| `NUXIVA_DISPLAY_PRESENCE_GATE` | acceso | Attiva la visibilità basata sulla presenza |
| `NUXIVA_PRIVACY_AWAY_S` | 10 | Secondi senza nessuno prima di `Empty` (esistente) |
| `NUXIVA_PRIVACY_VOICE_S` | 30 | Tenuta con sola voce (esistente) |
| `NUXIVA_DISPLAY_GUEST_PUBLIC` | spento | Con ospiti mostra anche orologio e meteo |
| `NUXIVA_DISPLAY_TRUST_GUESTS` | spento | Con ospiti mostra anche i widget `household` |
| `NUXIVA_DISPLAY_SLEEP_GRACE_S` | 60 | Secondi prima di liberare le risorse dei widget |

## 9. Test

- Tabella di verità completa di §3 su tutti i tipi di pubblico e sensibilità.
- Sequenze temporali: arrivo ospite durante widget sensibile; proprietario che esce e rientra; voce autorizzata senza volto; volto noto senza liveness (foto davanti alla webcam) che non deve aprire nulla.
- Iniezione di guasti: visione ferma, microfono fermo, daemon riavviato. In tutti i casi lo stato risultante deve essere il più restrittivo.
