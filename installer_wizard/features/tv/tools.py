from features.agent.registry import tool
from features.tv import targets
from features.tv.store import tv_store

OWNER = "tv"


@tool("tv_list_channels", "elenca o cerca i canali televisivi o IPTV disponibili su Nuxiva",
      {"query": "termine di ricerca per nome canale (facoltativo)",
       "group": "filtro per gruppo/categoria (es. Sport, Cinema, News) (facoltativo)",
       "favorite_only": "mostra solo i canali preferiti (facoltativo, default False)"},
      agent=OWNER)
def tv_list_channels(query: str = "", group: str = "", favorite_only: bool = False) -> list[dict]:
    favorites = set(tv_store.favorites())
    needle = query.strip().lower()
    channels = tv_store.channels()
    res = []
    for c in channels:
        if group and c.get("group") != group:
            continue
        if favorite_only and c["id"] not in favorites:
            continue
        if needle and needle not in c.get("name", "").lower():
            continue
        res.append({
            "id": c["id"],
            "name": c["name"],
            "group": c.get("group", ""),
            "favorite": c["id"] in favorites,
            "has_url": bool(c.get("url")),
        })
    return res[:100]


@tool("tv_play_channel", "sintonizza e riproduce un canale TV o IPTV su uno schermo o dispositivo target (display, PC o Chromecast)",
      {"channel": "nome del canale o ID (es. Rai 1, Sky Sport, o ID esadecimale)",
       "target": "destinazione (display per schermo locale, o ID del dispositivo target) (default 'display')"},
      agent=OWNER)
async def tv_play_channel(channel: str, target: str = "display") -> dict:
    ch = tv_store.find(channel) if not tv_store.channel(channel) else tv_store.channel(channel)
    if not ch:
        return {"error": f"Canale «{channel}» non trovato nella lista canali"}

    # Verifica vincolo VPN
    settings = tv_store.settings()
    if settings.get("vpn_required"):
        try:
            from features.vpn.service import service as vpn_svc
            target_profile = settings.get("vpn_profile")
            if target_profile:
                is_connected = bool(vpn_svc.state.get(target_profile, {}).get("connected"))
            else:
                is_connected = any(st.get("connected") for st in vpn_svc.state.values())
        except Exception:
            is_connected = False
        if not is_connected:
            return {
                "error": "Riproduzione bloccata: la policy di sicurezza IPTV richiede una VPN attiva. Connettiti prima a una VPN."
            }

    try:
        where = await targets.play(ch, target, "agent")
        return {
            "ok": True,
            "channel": ch["name"],
            "where": where,
            "preview_url": targets.live_path(ch),
        }
    except targets.TargetError as exc:
        return {"error": str(exc)}


@tool("tv_get_epg", "mostra la guida programmi EPG reale (in onda e successivi) per un canale specificato",
      {"channel": "nome del canale o ID (es. Rai 1)"},
      agent=OWNER)
def tv_get_epg(channel: str) -> dict:
    ch = tv_store.find(channel) if not tv_store.channel(channel) else tv_store.channel(channel)
    if not ch:
        return {"error": f"Canale «{channel}» non trovato"}
    return tv_store.epg(ch["id"])


@tool("tv_list_tuners", "elenca tutti i tuner TV reali rilevati e configurati su Nuxiva (DVB-T2, HDHomeRun, SAT>IP, Enigma2)",
      {},
      agent=OWNER)
def tv_list_tuners() -> list[dict]:
    return tv_store.tuners()


@tool("tv_add_tuner", "aggiunge una sorgente o tuner TV reale specificando nome, tipo (dvb_t2, hdhomerun, sat_ip, enigma2) e dispositivo/URL",
      {"name": "nome identificativo del tuner",
       "tuner_type": "tipo tuner (dvb_t2, hdhomerun, sat_ip, enigma2)",
       "device": "percorso hardware (/dev/dvb/adapter0) o indirizzo di rete (192.168.1.150:65001)",
       "frequency_band": "banda frequenze opzionale (es. DVB-T/T2 VHF/UHF)"},
      agent=OWNER)
def tv_add_tuner(name: str, tuner_type: str, device: str, frequency_band: str = "DVB-T/T2 VHF/UHF") -> dict:
    return tv_store.add_tuner(name, tuner_type, device, {"frequency_band": frequency_band})


@tool("tv_scan_tuner", "esegue la scansione delle frequenze reali sul tuner specificato per rilevare i canali disponibili",
      {"tuner_id": "ID del tuner da scansionare"},
      agent=OWNER)
def tv_scan_tuner(tuner_id: str) -> dict:
    return tv_store.scan_tuner(tuner_id)


@tool("tv_set_vpn_policy", "configura la protezione VPN obbligatoria per tutti i flussi IPTV di Nuxiva",
      {"vpn_required": "se True, impedisce la riproduzione IPTV a meno che una VPN non sia attiva",
       "vpn_profile": "ID o nome del profilo VPN specifico da verificare (facoltativo)"},
      agent=OWNER)
def tv_set_vpn_policy(vpn_required: bool, vpn_profile: str = "") -> dict:
    return tv_store.update_settings({"vpn_required": vpn_required, "vpn_profile": vpn_profile})
