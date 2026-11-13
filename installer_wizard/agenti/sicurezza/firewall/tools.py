from agenti.agent.registry import tool
from agenti.firewall import model
from agenti.firewall.applier import applier
from agenti.firewall.events import monitor
from agenti.firewall.store import store

MODES = {"off": "spento", "monitor": "solo monitoraggio", "protect": "protezione", "lockdown": "lockdown (solo autorizzati)"}


@tool("firewall_status", "stato del firewall di Nuxiva: modalità, regole, blocchi attivi e ultimi allarmi di rete", {},
      agent="firewall")
async def firewall_status() -> str:
    snap = store.snapshot()
    alerts = list(monitor.alerts)[-5:]
    lines = [f"modalità {MODES.get(snap['policy']['mode'], snap['policy']['mode'])}, {len(snap['rules'])} regole, "
             f"{len(snap['blocks'])} blocchi, analisi del traffico {'attiva' if monitor.connected else 'non collegata'}"]
    lines += [f"- {a['severity']} {a['kind']} da {a['src']}: {a['detail']}" for a in alerts]
    if applier.last.get("error"):
        lines.append(f"ultimo errore: {applier.last['error']}")
    return "\n".join(lines)


@tool("firewall_block", "blocca un indirizzo IP, una rete o un MAC per un certo numero di minuti (0 = finché non lo sblocchi)",
      {"address": "IP, rete CIDR o MAC", "minutes": "durata in minuti", "reason": "motivo"}, confirm=True, agent="firewall")
async def firewall_block(address: str, minutes: int = 60, reason: str = "richiesta vocale") -> str:
    target = model.address(address)
    if target.family == "set":
        raise ValueError("indica un indirizzo o un MAC, non un gruppo")
    if store.trusted(target):
        raise ValueError(f"{target.value} è tra gli indirizzi fidati: toglilo prima dai fidati")
    outcome = await monitor.block(target, max(0, min(int(minutes), 525_600)) or 525_600, reason)
    return f"{target.value} bloccato" + ("" if outcome.get("ok") else f" (non applicato: {outcome.get('error')})")


@tool("firewall_unblock", "toglie il blocco a un indirizzo IP, una rete o un MAC", {"address": "IP, rete CIDR o MAC"},
      confirm=True, agent="firewall")
async def firewall_unblock(address: str) -> str:
    target = model.address(address)
    with store.lock:
        if target.value not in store.blocks:
            return f"{target.value} non era bloccato"
        store.checkpoint(f"sblocco {target.value}")
        del store.blocks[target.value]
        store.save()
    await applier.apply(f"sblocco di {target.value}")
    return f"{target.value} sbloccato"


@tool("firewall_trusted", "elenco dei dispositivi affidabili del firewall, che non vengono mai bloccati", {}, agent="firewall")
async def firewall_trusted() -> str:
    from agenti.firewall.defense.trust import trust
    devices = trust.listing()
    if not devices:
        return "nessun dispositivo affidabile"
    return "\n".join(f"- {d['label'] or 'senza nome'} ({d['address']})" for d in devices)


@tool("firewall_trust", "aggiunge un dispositivo di casa agli affidabili del firewall dopo la conferma esplicita dell'utente",
      {"address": "IP o MAC del dispositivo di casa", "label": "nome del dispositivo"}, confirm=True, agent="firewall")
async def firewall_trust(address: str, label: str = "") -> str:
    from agenti.firewall.defense.trust import apply, trust
    entry = trust.request(address, label, "voce")
    if entry["risks"]:
        raise ValueError("questo indirizzo non è un singolo dispositivo di casa: aggiungilo dalla pagina del firewall")
    confirmed = trust.confirm(entry["id"], entry["code"], False)
    await apply(confirmed["addresses"], True, "voce", confirmed["label"])
    return f"{confirmed['label'] or address} è ora affidabile ({', '.join(confirmed['addresses'])}); puoi revocarlo quando vuoi"


@tool("firewall_untrust", "toglie un dispositivo dagli affidabili del firewall", {"address": "IP o MAC del dispositivo"},
      confirm=True, agent="firewall")
async def firewall_untrust(address: str) -> str:
    from agenti.firewall.defense.trust import apply
    target = model.text_of(model.address(address))
    await apply([target], False, "voce")
    return f"{target} non è più affidabile"


@tool("firewall_incidents", "attacchi in corso o recenti rilevati dal firewall: tipo, gravità, paese di origine e dispositivi colpiti", {},
      agent="firewall")
async def firewall_incidents() -> str:
    from agenti.firewall.defense.guardian import guardian
    state = guardian.snapshot()
    rows = state["incidents"][:8]
    head = f"stato della difesa: {state['posture']}, {len(state['incidents'])} incidenti, {len(state['responses'])} difese attive"
    return "\n".join([head] + [f"- {i['level']} {','.join(i['kinds'])} da {i['src']}"
                              f"{' (' + i['country'] + ')' if i['country'] else ''}, {len(i['targets'])} bersagli" for i in rows])


@tool("firewall_show_view", "mostra a schermo intero la vista 3D della difesa: dispositivi, attacchi, paese di origine e difese attive", {},
      agent="firewall")
async def firewall_show_view() -> str:
    from agenti.firewall.defense.stage import stage
    if not await stage.show(True):
        return "lo schermo non è raggiungibile in questo momento"
    return "vista della difesa aperta a schermo intero"


@tool("firewall_hide_view", "chiude la vista 3D della difesa", {}, agent="firewall")
async def firewall_hide_view() -> str:
    from agenti.firewall.defense.stage import stage
    await stage.close()
    return "vista della difesa chiusa"


@tool("firewall_defend", "attiva una difesa temporanea e reversibile contro un indirizzo o un paese (blocco, tarpit, limite, esca, quarantena, sinkhole)",
      {"kind": "block, tarpit, rate_limit, honeypot, quarantine, sinkhole o country_block", "target": "IP, MAC o codice paese",
       "minutes": "durata in minuti"}, confirm=True, agent="firewall")
async def firewall_defend(kind: str, target: str, minutes: int = 60) -> str:
    from agenti.firewall.defense.responder import responder
    from agenti.firewall.defense.routes import MANUAL
    if kind not in MANUAL:
        raise ValueError("difesa sconosciuta")
    await responder.execute({"kind": kind, "target": str(target)[:80], "minutes": int(minutes), "reason": "richiesta vocale"}, "voce")
    return f"difesa {kind} attiva su {target} per {max(1, min(int(minutes), 525_600))} minuti, revocabile in qualsiasi momento"


@tool("firewall_defense_revoke", "revoca una difesa attiva del firewall", {"key": "chiave della difesa, per esempio tarpit:203.0.113.9"},
      confirm=True, agent="firewall")
async def firewall_defense_revoke(key: str) -> str:
    from agenti.firewall.defense.responder import responder
    await responder.revoke(str(key)[:120], "voce")
    return f"difesa {key} revocata"
