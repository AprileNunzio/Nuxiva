from agenti.voices import languages
from agenti.voices.catalog import (HOME_LANG, KOKORO_KNOWN, auto_download, custom_order, describe, fallback_voice,
                                     is_online, is_piper, kokoro_voices, lang_prefs, online_catalog, online_enabled,
                                     piper_catalog, piper_installed, voice_order)
from agenti.voices.downloads import downloading
from state import store


async def overview() -> dict:
    kv = await kokoro_voices()
    piper, online = piper_catalog(), online_catalog()
    prefs = lang_prefs()
    items = [{**describe(v), "installed": kv is not None, "downloadable": False}
             for v in (kv if kv is not None else KOKORO_KNOWN)]
    items += [{**describe(v, piper, online), "installed": piper_installed(v), "downloadable": True,
               "downloading": v in downloading} for v in piper]
    items += [{**describe(v, piper, online), "installed": True, "downloadable": False} for v in online]
    for i in items:
        i["preferred"] = prefs.get(i["lang"]) == i["id"]
    items.sort(key=lambda x: (x["lang"] != HOME_LANG, languages.label(x["lang"]),
                              {"elevenlabs": 0, "kokoro": 1, "online": 2, "piper": 3, "studio": 4}.get(x["engine"], 5),
                              x["gender"] != "m", x["name"]))
    known = {i["id"]: i for i in items}
    custom = custom_order()

    def entry(v: str) -> dict:
        d = known.get(v) or {**describe(v, piper, online), "installed": piper_installed(v) if is_piper(v)
                             else (online_enabled() if is_online(v) else kv is not None)}
        return {**d, "safety": v not in custom and v == fallback_voice()}

    langs = sorted({i["lang"] for i in items}, key=lambda c: (c != HOME_LANG, languages.label(c)))
    from agenti.voices.audio_vault import audio_vault
    from config import env_get
    engine_mode = env_get("NUXIVA_VOICE_ENGINE_MODE", "hybrid").lower()
    eleven_configured = bool(env_get("NUXIVA_ELEVENLABS_API_KEY", "").strip())
    return {"order": [entry(v) for v in voice_order()], "custom": bool(custom), "voices": items,
            "kokoro_online": kv is not None, "online_enabled": online_enabled(), "auto_download": auto_download(),
            "engine_mode": engine_mode, "elevenlabs_configured": eleven_configured,
            "vault_stats": audio_vault.get_stats(),
            "langs": {c: languages.label(c) for c in langs}, "lang_prefs": prefs,
            "by_lang": {c: entry(v) for c, v in prefs.items()},
            "fallback": fallback_voice(), "pull": getattr(store, "voice_pull", None),
            "counts": {"kokoro": sum(i["engine"] == "kokoro" for i in items), "piper": len(piper),
                       "online": len(online), "italiano": sum(i["lang"] == "it" or bool(i.get("multi")) for i in items)}}
