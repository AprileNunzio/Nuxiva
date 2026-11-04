from features.voices import languages, overview

LIMIT = 80


async def voices(lang: str) -> list[dict]:
    data = await overview.overview()
    base = languages.base(lang)
    rows = [v for v in data["voices"] if v["installed"] and (not base or v["lang"] == base or v.get("multi"))]
    rows.sort(key=lambda v: (not v.get("preferred"), v["engine"] != "kokoro", v["gender"], v["name"]))
    return [{"id": v["id"], "name": v["name"], "lang": v["lang"], "gender": v["gender"], "engine": v["engine"], "preferred": bool(v.get("preferred"))} for v in rows[:LIMIT]]
