import json
import logging
import re

import httpx

from agenti.rpa import releases

log = logging.getLogger("nuxiva.rpa")
NAME = "release.json"
LANGS = ("it", "en", "fr", "es")
MAX_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 2000
VERSION = re.compile(r"\d+\.\d+\.\d+")
TAG = re.compile(r"(?:assistant-|android-)?v\d+\.\d+\.\d+")
SHA = re.compile(r"[0-9a-f]{64}")


def official_url(tag: str) -> str:
    return releases._official(tag, NAME)


def _texts(value) -> dict:
    if not isinstance(value, dict) or set(value) != set(LANGS) or not all(isinstance(value[l], str) and value[l].strip() for l in LANGS):
        raise ValueError("testo multilingue non valido")
    return {lang: value[lang] for lang in LANGS}


def _items(values) -> list:
    if not isinstance(values, list) or len(values) > MAX_ITEMS:
        raise ValueError("elenco voci non valido")
    out = []
    for item in values:
        if not isinstance(item, dict) or not isinstance(item.get("source"), str) or not isinstance(item.get("date"), str):
            raise ValueError("voce non valida")
        out.append({"source": item["source"], "date": item["date"], "text": _texts(item.get("text"))})
    return out


def _assets(values) -> list:
    if not isinstance(values, list) or not values or len(values) > 32:
        raise ValueError("risorse non valide")
    out = []
    for asset in values:
        name, size, digest = (asset.get(k) if isinstance(asset, dict) else None for k in ("name", "size", "sha256"))
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", name) or type(size) is not int or size <= 0 \
                or not isinstance(digest, str) or not SHA.fullmatch(digest):
            raise ValueError("risorsa non valida")
        out.append({"name": name, "size": size, "sha256": digest})
    return out


def parse(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise ValueError("release.json troppo grande")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise ValueError("schema non supportato")
    version, tag = data.get("version"), data.get("tag")
    if not isinstance(version, str) or not VERSION.fullmatch(version) or not isinstance(tag, str) or not TAG.fullmatch(tag) or not tag.endswith(version):
        raise ValueError("versione o tag non validi")
    components = data.get("components")
    if not isinstance(components, dict) or any(
            not isinstance(components.get(n), dict) or components[n].get("version") != version for n in ("server", "android", "windows")):
        raise ValueError("componenti non allineati alla versione")
    return {"version": version, "tag": tag, "title": _texts(data.get("title")), "assets": _assets(data.get("assets")),
            "features": _items(data.get("features")), "fixes": _items(data.get("fixes")),
            "components": {n: components[n]["version"] for n in ("server", "android", "windows")}}


async def fetch(tag: str) -> dict:
    if not TAG.fullmatch(tag):
        return {}
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(official_url(tag))
        response.raise_for_status()
        return parse(response.content)
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("release.json di %s non leggibile: %s", tag, exc)
        return {}
