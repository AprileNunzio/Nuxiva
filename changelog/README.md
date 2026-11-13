# Note di rilascio / Release notes

Ogni commit su `main` aggiunge **un nuovo file** in questa cartella. La CI fallisce se un commit non lo fa.
Every commit on `main` adds **one new file** to this folder. CI fails when a commit does not.

L'aggiornamento di sistema legge i file aggiunti tra la versione installata e quella nuova e li mostra come **Novità** e **Bugfix** prima e durante l'installazione.
The system updater reads the files added between the installed and the new version and shows them as **New features** and **Bug fixes** before and during the installation.

## Nome del file / File name

`AAAAMMGGhhmmss-slug.json` / `YYYYMMDDhhmmss-slug.json` (UTC), slug in minuscolo con trattini / lowercase slug with dashes.
La data del nome deve coincidere con il campo `date`. / The date in the name must match the `date` field.

## Formato / Format

```json
{
  "schema": 1,
  "date": "2026-11-13",
  "title": { "it": "…", "en": "…", "fr": "…", "es": "…" },
  "features": [{ "it": "…", "en": "…", "fr": "…", "es": "…" }],
  "fixes": [{ "it": "…", "en": "…", "fr": "…", "es": "…" }]
}
```

- Tutte e quattro le lingue sono obbligatorie. / All four languages are required.
- Almeno una voce tra `features` e `fixes`, al massimo 24 per sezione. / At least one entry in `features` or `fixes`, at most 24 per section.
- Titolo fino a 140 caratteri, voci fino a 320, file fino a 16 KB. / Title up to 140 characters, entries up to 320, file up to 16 KB.
- Vietati caratteri di controllo e caratteri invisibili o di direzione del testo; nessun campo extra. / Control characters, invisible and bidirectional characters and extra fields are rejected.
- Scrivi cosa cambia per chi usa Nuxiva, non i dettagli tecnici del codice. / Describe what changes for the people using Nuxiva, not code internals.
