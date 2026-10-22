import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, Path
from pydantic import BaseModel, ConfigDict, Field

from server.core.skill_forge.composition import skill_forge
from server.core.skill_forge.contracts import MAX_SOURCE_CHARS

router = APIRouter(prefix="/api/v1/cognition/skills", tags=["Nuxiva Skill Forge"])

NEURON_PATH = Path(pattern=r"^[a-z][a-z0-9_.-]{2,63}$")


class ForgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest: Dict[str, Any]
    source: str = Field(min_length=1, max_length=MAX_SOURCE_CHARS)


def _unwrap(result):
    if not result.is_ok:
        raise result.error
    return result.value


@router.get("")
async def list_skills() -> List[Dict[str, Any]]:
    return _unwrap(skill_forge().listing())


@router.post("", status_code=201)
async def forge_skill(body: ForgeRequest) -> Dict[str, Any]:
    return _unwrap(await asyncio.to_thread(skill_forge().forge, body.manifest, body.source, "manual"))


@router.delete("/{neuron_id}")
async def retire_skill(neuron_id: str = NEURON_PATH) -> Dict[str, Any]:
    removed = _unwrap(await asyncio.to_thread(skill_forge().retire, neuron_id))
    return {"neuron_id": neuron_id, "removed": removed}
