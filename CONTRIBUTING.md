# Contributing to Nuxiva OS

*Riepilogo in italiano in fondo al documento.*

Thank you for your interest in **Nuxiva OS**, the home assistant and agent platform engineered by
**NunzioTech**. This guide explains how to propose, build and review changes so that contributions are quick to
accept and safe to ship: **every commit on `main` is installed automatically on running servers** once its CI is
green, so quality and safety are part of the contribution, not an extra.

By taking part you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Security problems are reported
privately as described in [SECURITY.md](SECURITY.md), never through public issues or pull requests.

## Ways to contribute

- **Report a bug** or **propose a feature** with the issue templates. Search existing issues first.
- **Improve documentation**: the README ([English](README.md), [Italiano](README_IT.md), [Français](README_FR.md)), [installer_wizard/features/README.md](installer_wizard/features/README.md) and [installer_wizard/MCP.md](installer_wizard/MCP.md).
- **Add or fix a feature, tool, widget, algorithm or installation step**: see
  [how to add things](#adding-things-to-nuxiva).
- **Review pull requests** and reproduce reported problems.

For anything larger than a small fix, **open an issue first** and describe the problem, the proposed design and
the impact on privacy and security. It avoids wasted work.

## Development environment

Requirements: Python 3.11+, Node.js 20 (for the JavaScript syntax checks and `client_web`), `bash`, `git`.

```bash
git clone https://github.com/AprileNunzio/Nuxiva.git
cd Nuxiva/installer_wizard
python3 -m venv venv
venv/bin/pip install -r backend/requirements.txt -r features/documents/requirements.txt pyflakes
cd backend
../venv/bin/python nuxiva_supervisor.py
```

Nuxiva runs on real data and real connected hardware; there is no synthetic demo mode.
By default, the public interface listens on port 80 (or `NUXIVA_PUBLIC_PORT`) and the admin cockpit
on port 8080 (or `NUXIVA_ADMIN_PORT`). During development, unit and integration tests run offline
without touching live household hardware (using isolated test harnesses and `httpx.MockTransport`).
OS installation scripts (`scripts/os/steps/*.sh`) must be validated on disposable Debian/Ubuntu test machines.

## Repository map

| Path | Content |
| :--- | :--- |
| `installer_wizard/backend/` | Supervisor core: orchestration, health, updater, configuration, authentication |
| `installer_wizard/features/<id>/` | One folder per capability: logic, API, admin panel tab, `feature.json` manifest |
| `installer_wizard/widgets/<id>/` | Display widgets |
| `installer_wizard/skills/` | Verified Python algorithms |
| `installer_wizard/web/` | Display, admin shell, shared assets |
| `installer_wizard/tests/` | Unit and API tests (`unittest`) |
| `scripts/os/` | Installation steps, systemd units, `nuxivactl` |
| `server/` · `sandbox_broker/` | Nuxiva Core and the isolated sandbox broker |
| `native/crates/` | Rust crates for latency-critical paths (embedding index, event bus, netguard, egress proxy, CRDT sync, audio DSP), exposed to Python via PyO3 |
| `client_satellite/` · `client_web/` · `client_apk/` | Nodes, web dashboard, Android client |

## Engineering standards

These rules are enforced in review and, where possible, by CI.

| Rule | Detail |
| :--- | :--- |
| **Clean architecture** | Business logic is isolated from frameworks, transport and infrastructure. One module, one responsibility: `api.py` holds routes only, logic lives in dedicated modules. |
| **No comments, no docstrings** | The code must explain itself through expressive names, small functions and type hints. |
| **500 lines at most per file** | Applies to every code file; split by responsibility. The README is the only exception. |
| **Feature-based layout** | Everything about a capability lives in `features/<id>/`. Shared code goes in `backend/` only if the supervisor needs it. |
| **Zero trust** | Every endpoint, RPC call, tool argument and file path is authenticated and validated: types, ranges, sizes, allowed values, path containment. Prevent the OWASP Top 10 classes (injection, broken access control, cryptographic failures, SSRF, unsafe deserialization). |
| **Errors** | Fail loudly with a clear message; never silence exceptions. User-facing messages are in Italian. |
| **Async** | The supervisor is `asyncio`: no blocking calls in the loop (use `httpx.AsyncClient`, `asyncio.create_subprocess_exec`, `asyncio.to_thread`). |
| **Idempotence** | Installation steps and repairs can be run repeatedly without damage. |
| **Secrets** | Never in the repository, tests, logs or examples. Use `nuxiva.env`, the sealed files or the vault. |
| **Privacy** | Local by default. Anything that sends data outside the server must be optional, documented and switchable off. |
| **Dependencies** | Add one only when the standard library or an existing dependency cannot do the job; pin versions and check the license. |

## Security requirements for changes

A change that can act on the real world must be safe **in code**, because a language model cannot be relied on
to refuse.

- **Tools** (`@tool` in `features/agent/registry.py`): declare `confirm` for sensitive actions (a boolean or a
  function of the arguments), the owning `agent`, and a `verify` function when success can be checked. Confirmation
  is inherited by delegation, forged tools and MCP calls; do not bypass it. See
  [installer_wizard/MCP.md](installer_wizard/MCP.md).
- **MCP exposure**: a tool is visible to *standard* tokens only if its owner is in `SAFE_AGENTS`
  (`features/capabilities/mcp.py`) and it needs no confirmation. Add an agent there only if it has no sensitive effects.
- **Untrusted content** (web pages, e-mail, documents, replies of external MCP servers, model output) is data,
  never instructions, and must not be able to trigger sensitive actions on its own.
- **Generated or external code** never runs outside the sandbox.
- **New endpoints** declare their audience: `require_admin` (panel session, anti-CSRF header on changes),
  `require_display` (local display or session), node token, or signed URL; never an unauthenticated write.
- **Limits**: cap sizes, counts and durations of anything a client can send or store.
- **Personal data** (faces, voices, camera frames, calendars) is minimized, protected and never logged in clear.

## Testing and checks

New behavior needs tests, and a bug fix needs a test that fails without the fix. Tests use `unittest`, run
offline and never depend on real devices or services: patch network discovery and use `httpx.MockTransport`.
Hardware-dependent behavior is isolated behind an interface that tests can replace.

Run everything CI runs before opening a pull request:

```bash
python -m py_compile $(find server sandbox_broker installer_wizard client_satellite -name "*.py" -not -path "*/venv/*")
python -m pyflakes server sandbox_broker installer_wizard client_satellite
(cd installer_wizard && python -m unittest discover -s tests -t .)
python -m unittest discover -s server/tests -t .
for f in $(find installer_wizard -name "*.js" -not -path "*/venv/*"); do node --check "$f"; done
for f in $(find scripts installer_wizard -name "*.sh") scripts/os/nuxivactl install.sh; do bash -n "$f"; done
find installer_wizard server sandbox_broker scripts -type f \( -name "*.py" -o -name "*.js" -o -name "*.sh" -o -name "*.css" -o -name "*.html" \) \
  -not -path "*/venv/*" -exec awk 'END { if (NR > 500) print FILENAME ": " NR }' {} \;
```

The last command must print nothing. If you touch `client_web`, also run `npm ci && npm run build` there. CI runs
these jobs on every push and pull request: Python validation, supervisor tests, Core and sandbox tests, script
syntax and the web client build.

`.pre-commit-config.yaml` covers whitespace, YAML, large files, private keys, secret detection and the colocated
i18n check. Do not reformat existing files with external formatters: unrelated formatting changes make reviews
harder.

## Commits and branches

- Branch from `main`: `feature/<topic>`, `fix/<topic>` or `docs/<topic>`.
- Small, focused commits written as [Conventional Commits](https://www.conventionalcommits.org/):
  `feat(music): …`, `fix(understanding): …`, `docs(readme): …`, `test(forge): …`, `refactor(team): …`. The message
  says what changes for the user and why. English or Italian are both fine.
- **Sign off** your commits (`git commit -s`) to certify the
  [Developer Certificate of Origin](https://developercertificate.org/): that you wrote the change or have the
  right to submit it under the project license.

## Pull requests

1. Fork the repository and create your branch.
2. Make the change with its tests and documentation, and run the checks above.
3. Open the pull request against `main` using the template, describing the problem, the design, the impact on
   security and privacy, and how you verified it (commands, screenshots for UI changes). Use a *draft* pull
   request for early feedback.
4. Respond to review. A pull request is merged when CI is green, a maintainer approves it and the checklist is
   complete. Keep the branch up to date with `main`.

**Why CI matters here**: installations pull `main` automatically but only install commits whose CI run passed, and
roll back if the nightly self-test or the post-update checks fail. A red build blocks every installation from
receiving your change, and a green build means it will be running on real homes minutes after the merge.

Review looks at: correctness, tests, security and privacy, compliance with the standards above, clarity, effect
on existing installations (migrations, defaults, upgrade path) and documentation.

## Adding things to Nuxiva

| To add | Read |
| :--- | :--- |
| A feature (agent) with panel tab and settings | [installer_wizard/features/README.md](installer_wizard/features/README.md) |
| A tool for agents and MCP | [installer_wizard/MCP.md](installer_wizard/MCP.md) and `installer_wizard/features/agent/registry.py` |
| A command the understanding layer can route | `installer_wizard/features/understanding/` |
| A display widget | an existing folder in `installer_wizard/widgets/` as a template |
| An algorithm (skill) | `installer_wizard/skills/` |
| An installation step | `installer_wizard/backend/steps.py` and `scripts/os/steps/` |
| An admin console app | [docs/WEBOS.md](docs/WEBOS.md) |

Update the three READMEs (and `installer_wizard/MCP.md` for agents and MCP) in the same pull request that changes
behavior, configuration variables, API routes or security properties.

## Licensing of contributions

Current Nuxiva releases are distributed under the **[Nuxiva Personal and Commercial License 1.0](LICENSE)**:
free for personal home use, with commercial use requiring a separate paid commercial license from NunzioTech.
Earlier portions distributed under the MIT License retain their permissions under [LICENSE-MIT-LEGACY](LICENSE-MIT-LEGACY).

By contributing, you agree that your contribution is submitted under the repository's license terms. You retain
your moral authorship, while granting the rights necessary to incorporate and distribute your work as part of
Nuxiva. Do not submit code, data, models, fonts, sounds or images that you do not have the right to license,
and do not incorporate material from projects with incompatible proprietary or copyleft restrictions. Third-party
material must retain its original license notices and be documented in THIRD_PARTY_NOTICES.md.

## AI-assisted contributions

Assistants may help you write code, but you are the author: review every line, run the checks, and make sure the
change follows these standards and does not include secrets or code you do not understand.

## Getting help

Open an issue with the *question* in the title, or comment on the relevant pull request. For conduct concerns see
the [Code of Conduct](CODE_OF_CONDUCT.md); for vulnerabilities see [SECURITY.md](SECURITY.md).

---

# Contribuire (riepilogo in italiano)

Ogni commit su `main` viene installato da solo sui server **solo se la CI è verde**: qualità e sicurezza fanno
parte del contributo.

1. **Prima di iniziare**: per modifiche non banali apri una issue; le vulnerabilità si segnalano in privato
   ([SECURITY.md](SECURITY.md)); rispetta il [Codice di condotta](CODE_OF_CONDUCT.md).
2. **Ambiente**: Python 3.11+, Node 20. Il sistema si basa unicamente su dati reali e hardware effettivo,
   senza modalità demo. La porta pubblica è 80 (`NUXIVA_PUBLIC_PORT`) e la plancia admin è 8080 (`NUXIVA_ADMIN_PORT`).
   I test unitari girano offline tramite harness isolati (`httpx.MockTransport`).
3. **Regole**: niente commenti né docstring; massimo 500 righe per file; codice per funzionalità
   (`features/<id>/`); responsabilità singola; zero-trust (autenticazione e validazione di ogni ingresso); nessun
   segreto nel repository; errori mai silenziati; messaggi per l'utente in italiano.
4. **Sicurezza nel codice**: le azioni delicate hanno la conferma **nel codice dello strumento** (che si eredita
   da deleghe, fucina e MCP), con `verify` quando l'esito è controllabile; i contenuti esterni sono dati, mai
   istruzioni; il codice generato gira solo nella sandbox; ogni nuova rotta dichiara chi può usarla.
5. **Test**: ogni comportamento nuovo ha test (`unittest`, offline, senza dispositivi reali); esegui in locale gli
   stessi controlli della CI (comandi nella sezione *Testing and checks*), compreso il controllo delle 500 righe.
6. **Commit**: piccoli, nello stile Conventional Commits (`feat(music): …`), firmati con `git commit -s`
   (Developer Certificate of Origin); inglese o italiano.
7. **Pull request**: da un fork verso `main`, con il modello compilato (problema, progettazione, impatto su
   sicurezza e privacy, come hai verificato); si fonde con CI verde, approvazione e checklist completa.
8. **Documentazione**: aggiorna i tre README (e `installer_wizard/MCP.md`) nella stessa pull request quando cambiano
   comportamento, variabili, API o sicurezza.
9. **Licenza**: i contributi sono regolati dalla [Nuxiva Personal and Commercial License](LICENSE)
   (uso domestico gratuito, uso commerciale a pagamento). I diritti MIT pregressi sono preservati in [LICENSE-MIT-LEGACY](LICENSE-MIT-LEGACY).
