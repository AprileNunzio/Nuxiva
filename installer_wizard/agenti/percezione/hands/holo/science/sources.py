import re
from urllib.parse import quote

from agenti.hands.holo.catalog import fetch

PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/SDF?record_type={kind}"
PUBCHEM_PAGE = "https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"
RCSB_SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"
RCSB_FILE = "https://files.rcsb.org/download/{id}.pdb"
RCSB_PAGE = "https://www.rcsb.org/structure/{id}"
PDB_ID = re.compile(r"^[0-9][A-Za-z0-9]{3}$")
NAME = re.compile(r"^[\w ,'()+-]{2,80}$")
MAX_SDF = 512 * 1024
MAX_PDB = 8 * 1024 * 1024


async def pubchem(name: str) -> tuple[str, str]:
    if not NAME.match(name):
        raise fetch.FetchError("holo_bad_name")
    last = None
    for kind in ("3d", "2d"):
        try:
            blob = await fetch.download(PUBCHEM.format(name=quote(name, safe=""), kind=kind), MAX_SDF)
        except fetch.FetchError as exc:
            last = exc
            continue
        text = blob.decode("ascii", "replace")
        cid = text.split("\n", 1)[0].strip()
        page = PUBCHEM_PAGE.format(cid=cid) if cid.isdigit() else "https://pubchem.ncbi.nlm.nih.gov/"
        return text, page
    raise last or fetch.FetchError("holo_no_molecule")


async def rcsb_search(query: str) -> str:
    if not NAME.match(query):
        raise fetch.FetchError("holo_bad_name")
    body = {"query": {"type": "terminal", "service": "full_text", "parameters": {"value": query}},
            "return_type": "entry", "request_options": {"paginate": {"start": 0, "rows": 1}}}
    data = await fetch.post_json(RCSB_SEARCH, body)
    hits = data.get("result_set") or []
    found = str(hits[0].get("identifier", "")) if hits and isinstance(hits[0], dict) else ""
    if not PDB_ID.match(found):
        raise fetch.FetchError("holo_no_protein")
    return found.upper()


async def rcsb(pdb_id: str) -> tuple[str, str]:
    if not PDB_ID.match(pdb_id):
        raise fetch.FetchError("holo_bad_name")
    blob = await fetch.download(RCSB_FILE.format(id=pdb_id.upper()), MAX_PDB)
    return blob.decode("ascii", "replace"), RCSB_PAGE.format(id=pdb_id.upper())
