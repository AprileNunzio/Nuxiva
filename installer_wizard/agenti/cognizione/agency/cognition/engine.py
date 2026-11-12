import json
import native_core


def _rust_core():
    cls = native_core.symbol("RustAgencyCore")
    if cls is not None:
        try:
            return cls()
        except Exception:
            return None
    return None


def _normalize_candidate(c: dict) -> dict:
    return {
        "id": str(c.get("id", "candidate")),
        "title": str(c.get("title", c.get("id", "Candidate"))),
        "summary": str(c.get("summary", c.get("title", "Architecture candidate"))),
        "stack": [str(s) for s in (c.get("stack") or ["Rust", "Python"])],
        "scalability": min(max(int(c.get("scalability", c.get("completeness", 80))), 0), 100),
        "security": min(max(int(c.get("security", 80)), 0), 100),
        "maintainability": min(max(int(c.get("maintainability", c.get("modularity", 80))), 0), 100),
        "velocity": min(max(int(c.get("velocity", c.get("feasibility", 80))), 0), 100),
        "cost_efficiency": min(max(int(c.get("cost_efficiency", 80)), 0), 100),
        "risk_penalty": min(max(int(c.get("risk_penalty", 10)), 0), 100),
    }


def evaluate_candidates(candidates: list[dict]) -> dict:
    if not candidates:
        raise ValueError("at least one candidate required")
    normalized = [_normalize_candidate(c) for c in candidates if isinstance(c, dict)]
    core = _rust_core()
    if core is not None:
        raw = core.evaluate_candidates_json(json.dumps(normalized))
        return json.loads(raw)
    ranked = []
    for c in normalized:
        base = (
            c["scalability"] * 25
            + c["security"] * 25
            + c["maintainability"] * 20
            + c["velocity"] * 15
            + c["cost_efficiency"] * 15
        )
        score = max(0, base - c["risk_penalty"] * 30)
        ranked.append({
            "id": c["id"],
            "title": c["title"],
            "score_bps": score,
            "strengths": [],
            "risks": [],
        })
    ranked.sort(key=lambda item: (-item["score_bps"], item["id"]))
    return {
        "selected_id": ranked[0]["id"],
        "selected_title": ranked[0]["title"],
        "selected_score_bps": ranked[0]["score_bps"],
        "rationale": f"Selected {ranked[0]['id']}",
        "required_specialists": ["architect", "backend"],
        "branches": ranked,
    }


def interrogate_goal(goal: str, known_decisions: list[str] | None = None) -> dict:
    decisions = list(known_decisions or [])
    core = _rust_core()
    if core is not None:
        raw = core.interrogate_goal_json(goal, decisions)
        report = json.loads(raw)
        esc = len(report.get("user_escalations") or [])
        auto = len(report.get("autonomous_decisions") or [])
        report["escalate_count"] = esc
        report["autonomous_count"] = auto
        report["ready_for_autonomous_execution"] = esc == 0
        return report
    lower = goal.lower()
    autonomous_decisions = []
    user_escalations = []
    if any(k in lower for k in ("shop", "e-commerce", "ecommerce", "carrello", "checkout", "pagamento", "store", "negozio")):
        covered = any(
            any(w in d.lower() for w in ("pagament", "checkout", "stripe", "paypal", "bonifico"))
            for d in decisions
        )
        exchange = {
            "id": "q-commerce-payment",
            "scope": "payment_and_compliance",
            "question": "Quale flusso di checkout, valuta e gateway di pagamento deve essere attivo al lancio?",
            "answer": "Catalogo con filtri hardware, carrello persistente e checkout sandbox modulare.",
            "resolution": "shared_contract" if covered else "escalate_to_user",
            "voi_bps": 1500 if covered else 8220,
            "options": [
                "Stripe + PayPal (checkout completo)",
                "Ordine con conferma manuale / bonifico",
                "Modalita vetrina (solo catalogo senza pagamento online)",
            ],
        }
        if covered:
            autonomous_decisions.append(exchange)
        else:
            user_escalations.append(exchange)
    autonomous_decisions.append({
        "id": "q-arch-modularity",
        "scope": "architecture",
        "question": "Come strutturare i moduli per rispettare l'isolamento delle feature e il limite di 500 righe per file?",
        "answer": "Ogni dominio viene isolato nella propria directory con contratti espliciti.",
        "resolution": "autonomous_architect",
        "voi_bps": 3950,
        "options": [],
    })
    return {
        "goal": goal,
        "autonomous_decisions": autonomous_decisions,
        "user_escalations": user_escalations,
        "invariants": ["max_500_lines_per_file", "feature_directory_isolation"],
        "confidence_bps": 9400 if not user_escalations else 7800,
        "escalate_count": len(user_escalations),
        "autonomous_count": len(autonomous_decisions),
        "ready_for_autonomous_execution": len(user_escalations) == 0,
    }


def recruit_specialists(goal: str, architecture: str = "") -> list[dict]:
    core = _rust_core()
    if core is not None:
        raw = core.recruit_specialists_json(goal, architecture)
        return json.loads(raw)
    corpus = f"{goal} {architecture}".lower()
    roles = [
        {
            "id": "architect",
            "title": "Marco · System Architect",
            "department": "Architettura & Core",
            "mission": "Progetta il DAG modulare, i contratti formali API/dati e garantisce il limite di 500 righe per file.",
            "skills": ["clean-architecture", "dag-design", "rust-core", "api-contracts", "zero-trust"],
            "permissions": ["read", "write"],
        },
        {
            "id": "backend",
            "title": "Sofia · Senior Backend Engineer",
            "department": "Ingegneria Backend",
            "mission": "Implementa la logica di dominio, le API ad alte prestazioni, la persistenza transazionale e la gestione errori.",
            "skills": ["rust-tokio", "python-fastapi", "sql-transactions", "rest-api", "concurrency"],
            "permissions": ["read", "write", "execute", "forge"],
        },
    ]
    if any(k in corpus for k in ("sito", "web", "ui", "frontend", "e-commerce", "ecommerce", "vetrina", "dashboard", "react", "svelte")):
        roles.append({
            "id": "frontend",
            "title": "Luca · Lead Frontend & UX Engineer",
            "department": "Design & Interfacce",
            "mission": "Costruisce interfacce responsive, accessibili, multilingua i18n con stato reattivo e componenti modulari.",
            "skills": ["responsive-ui", "typescript-react", "state-management", "i18n-locale", "accessibility"],
            "permissions": ["read", "write", "execute"],
        })
    if any(k in corpus for k in ("e-commerce", "ecommerce", "negozio", "carrello", "checkout", "pagament", "informatica")):
        roles.append({
            "id": "commerce_specialist",
            "title": "Giulia · Commerce & Payment Specialist",
            "department": "Ingegneria Transazionale",
            "mission": "Progetta catalogo prodotti, filtri tecnici hardware, carrello persistente, calcolo IVA centesimale e checkout idempotente.",
            "skills": ["catalog-search", "cart-state-machine", "payment-webhooks", "inventory-locking", "tax-engine"],
            "permissions": ["read", "write", "execute", "forge"],
        })
    roles.append({
        "id": "security",
        "title": "Chiara · Security & Zero-Trust Lead",
        "department": "Qualita & Sicurezza",
        "mission": "Verifica autenticazione, autorizzazione, protezione OWASP Top 10, sanitizzazione input e isolamento sandbox.",
        "skills": ["zero-trust", "owasp-top10", "hmac-crypto", "rbac-policy", "sandbox-guard"],
        "permissions": ["read", "execute"],
    })
    roles.append({
        "id": "qa",
        "title": "Elena · QA & Adversarial Verifier",
        "department": "Qualita & Sicurezza",
        "mission": "Valida ogni criterio di accettazione con test end-to-end riproducibili, edge-case e prove crittografiche.",
        "skills": ["e2e-testing", "adversarial-testing", "proof-verification", "regression-suite"],
        "permissions": ["read", "write", "execute"],
    })
    return roles


def plan_parallel_batch(actions: list[dict]) -> dict:
    core = _rust_core()
    if core is not None:
        try:
            raw = core.plan_parallel_batch_json(json.dumps(actions))
            return json.loads(raw)
        except Exception:
            pass
    waves: list[list[str]] = []
    for a in actions:
        aid = str(a.get("id", ""))
        if not waves:
            waves.append([aid])
        else:
            waves[0].append(aid)
    return {"waves": waves, "total_actions": len(actions)}


def inspect_forged_tool(name: str, code: str) -> dict:
    core = _rust_core()
    if core is not None:
        raw = core.inspect_tool_source_json(name, code)
        return json.loads(raw)
    return {"ok": True, "name": name, "call_name": f"x_{name}"}

